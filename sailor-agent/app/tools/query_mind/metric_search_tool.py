# -*- coding: utf-8 -*-
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple, Type

from fastapi import Body
from langchain_core.callbacks import AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field

from app.logs.logger import logger
from app.errors import ToolFatalError
from app.tools.base import AFTool, api_tool_decorator
from app.service.adp_service import ADPService
from app.utils.common import run_blocking
from app.utils.lightweight import LightweightSearchEngine
from app.utils.password import get_authorization
from config import get_settings

_SETTINGS = get_settings()

_DEFAULT_PAGE_SIZE = 200


class MetricSearchArgs(BaseModel):
    query: str = Field(default="", description="用户问题，用于筛选相关指标")
    action: str = Field(
        default="filter",
        description="操作类型：get_all_metrics 获取所有指标，filter 根据问题筛选指标（默认）",
    )


class MetricSearchTool(AFTool):
    """指标搜索工具：基于 ADP get_metric_list（entries + total_count）全量拉取与本地筛选。"""

    name: str = "metric_search"
    description: str = dedent(
        """
        指标搜索工具：
        1) 通过 ADP 接口获取全部指标（分页聚合，与 get_metric_list 返回结构一致）
        2) 基于用户问题在名称、说明、标签等字段上做关键词筛选
        """
    )
    args_schema: Type[BaseModel] = MetricSearchArgs

    adp_service: Optional[ADPService] = None
    data_source_num_limit: int = int(_SETTINGS.INDICATOR_RECALL_TOP_K)
    page_size: int = _DEFAULT_PAGE_SIZE
    token: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.adp_service is None:
            self.adp_service = ADPService()

    def _run(self, *args, **kwargs):
        return run_blocking(self._arun(*args, **kwargs))

    async def _arun(
        self,
        query: str = "",
        action: str = "filter",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        self._validate_auth()
        normalized_action = (action or "filter").strip().lower()

        if normalized_action in ("get_all_metrics", "show_ds", "all"):
            return await self._aget_all_metrics()

        return await self._afilter_metrics(query=query)

    def _validate_auth(self):
        if not self.token or self.token == "''":
            raise ToolFatalError("缺少认证信息，请提供有效的 token")
        if not self.adp_service:
            raise ToolFatalError("ADP 服务未初始化")

    def _fetch_metric_pages(
        self, extra_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """按 get_metric_list 契约分页拉取，直到拿满 total_count 或无更多 entries。"""
        page_size = self.page_size if self.page_size > 0 else _DEFAULT_PAGE_SIZE
        offset = 0
        all_entries: List[Dict[str, Any]] = []
        total_count = 0

        while True:
            page_extra = {"offset": offset, "limit": page_size}
            if extra_params:
                page_extra.update(extra_params)

            chunk = self.adp_service.get_metric_list(token=self.token, extra_params=page_extra)
            entries = chunk.get("entries") or []
            if offset == 0:
                total_count = int(chunk.get("total_count") or 0)

            all_entries.extend(entries)

            if not entries:
                break
            if len(entries) < page_size:
                break
            if total_count and len(all_entries) >= total_count:
                break
            offset += page_size

        if not total_count:
            total_count = len(all_entries)

        return all_entries, total_count

    @staticmethod
    def _metric_entry_search_blob(entry: Dict[str, Any]) -> str:
        parts: List[str] = [
            str(entry.get("id") or ""),
            str(entry.get("name") or ""),
            str(entry.get("comment") or ""),
            str(entry.get("measure_name") or ""),
            str(entry.get("metric_type") or ""),
            str(entry.get("query_type") or ""),
            str(entry.get("data_view_id") or ""),
        ]
        tags = entry.get("tags")
        if isinstance(tags, list):
            parts.extend(str(t) for t in tags)
        for dim in entry.get("analysis_dimensions") or []:
            if isinstance(dim, dict):
                parts.append(str(dim.get("name") or ""))
                parts.append(str(dim.get("display_name") or ""))
                parts.append(str(dim.get("comment") or ""))
        return " ".join(parts).lower()

    def _search_entries_with_engine(self, entries: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        使用轻量级搜索引擎检索指标。
        - exact：优先命中完整子串
        - fuzzy：补充分词召回
        """
        if not entries:
            return []

        engine = LightweightSearchEngine()
        index_name = f"metric_search_{id(self)}"
        doc_id_to_entry: Dict[str, Dict[str, Any]] = {}
        search_docs: List[Dict[str, Any]] = []

        for idx, entry in enumerate(entries):
            doc_id = f"{entry.get('id') or 'metric'}__{idx}"
            doc_id_to_entry[doc_id] = entry
            search_docs.append(
                {
                    "id": doc_id,
                    "text": self._metric_entry_search_blob(entry),
                }
            )

        engine.build_index(index_name=index_name, documents=search_docs, overwrite=True)
        try:
            # exact 放前面可以保持“精确命中优先”的直觉排序
            exact_hits = engine.search(index_name=index_name, query=query, mode="exact", top_k=len(entries))
            fuzzy_hits = engine.search(index_name=index_name, query=query, mode="fuzzy", top_k=len(entries))

            merged_hits: List[Dict[str, Any]] = []
            seen_ids = set()
            for hit in exact_hits + fuzzy_hits:
                doc_id = hit.get("id")
                if not doc_id or doc_id in seen_ids:
                    continue
                entry = doc_id_to_entry.get(doc_id)
                if entry is None:
                    continue
                merged_hits.append(entry)
                seen_ids.add(doc_id)
            return merged_hits
        finally:
            engine.delete_index(index_name)

    @staticmethod
    def _to_metric_summary(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": entry.get("id", ""),
            "name": entry.get("name", ""),
            "comment": entry.get("comment", ""),
            "metric_type": entry.get("metric_type", ""),
            "query_type": entry.get("query_type", ""),
            "unit": entry.get("unit", ""),
            "measure_name": entry.get("measure_name", ""),
            "data_view_id": entry.get("data_view_id", ""),
        }

    async def _aget_all_metrics(self):
        entries, total_count = self._fetch_metric_pages()

        return {
            "title": "指标搜索-全部指标",
            "action": "get_all_metrics",
            "total_count": total_count,
            "metrics": entries,
            "metric_summary": [self._to_metric_summary(e) for e in entries],
        }

    async def _afilter_metrics(self, query: str):
        if not query or not query.strip():
            raise ToolFatalError("筛选指标时 query 不能为空")

        entries, total_count = self._fetch_metric_pages()
        matched = self._search_entries_with_engine(entries=entries, query=query)

        limit = self.data_source_num_limit
        if limit and limit > 0:
            matched = matched[:limit]

        return {
            "title": "指标搜索-筛选结果",
            "action": "filter",
            "query": query,
            "total_count": total_count,
            "matched_count": len(matched),
            "metrics": matched,
            "metric_summary": [self._to_metric_summary(e) for e in matched],
        }

    @classmethod
    @api_tool_decorator
    async def as_async_api_cls(
        cls,
        params: dict = Body(...),
        stream: bool = False,
        mode: str = "http",
    ):
        """异步 API：仅需有效 token（data_source.token 或 auth.token / user+password）。"""
        try:
            config_dict = params.get("config", {})

            token = params.get("auth", {}).get("token", "")
            if not token or token == "''":

                raise ToolFatalError(reason="获取 token 失败")

            tool = cls(
                adp_service=ADPService(),
                data_source_num_limit=config_dict.get("data_source_num_limit", _SETTINGS.INDICATOR_RECALL_TOP_K),
                page_size=int(config_dict.get("page_size", _DEFAULT_PAGE_SIZE)),
                token=token,
                api_mode=True,
            )

            query = params.get("query", "")
            action = params.get("action", "filter")
            return await tool._arun(query=query, action=action)
        except Exception as e:
            logger.error(f"metric_search as_async_api_cls failed: {e}")
            raise

    @staticmethod
    async def get_api_schema():
        return {
            "post": {
                "summary": "metric_search",
                "description": (
                    "指标搜索：调用 ADP get_metric_list（返回 entries、total_count），"
                    "支持 get_all_metrics 与按 query 本地筛选。"
                ),
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "auth": {
                                        "type": "object",
                                        "description": "认证（可选，与 data_source.token 二选一）",
                                        "properties": {
                                            "auth_url": {"type": "string"},
                                            "user": {"type": "string"},
                                            "password": {"type": "string"},
                                            "token": {"type": "string"},
                                        },
                                    },
                                    "data_source": {
                                        "type": "object",
                                        "properties": {
                                            "token": {
                                                "type": "string",
                                                "description": "Bearer 或裸 token，工具内会规范为 Bearer",
                                            },
                                        },
                                    },
                                    "config": {
                                        "type": "object",
                                        "properties": {
                                            "data_source_num_limit": {
                                                "type": "integer",
                                                "description": "filter 时最多返回的匹配条数",
                                            },
                                            "page_size": {
                                                "type": "integer",
                                                "description": "拉取列表时每页 limit，默认 200",
                                            },
                                            "session_type": {"type": "string"},
                                            "session_id": {"type": "string"},
                                        },
                                    },
                                    "action": {
                                        "type": "string",
                                        "enum": ["get_all_metrics", "filter"],
                                        "default": "filter",
                                    },
                                    "query": {"type": "string"},
                                    "input": {"type": "string"},
                                },
                            }
                        }
                    }
                },
            }
        }
