from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.logs.logger import logger
from app.memory.models import (
    MemoryDocumentDTO,
    MemoryQueryDTO,
    MemorySearchResultDTO,
)
from app.memory.service import MemoryService


def coerce_memory_user_id(raw: Any) -> str:
    """
    将 HTTP / 工具入参中的 user_id 规范为去首尾空白的字符串。
    兼容 JSON 中数字类型（如 10001 会变为 "10001"）。
    """
    if raw is None:
        return ""
    return str(raw).strip()


@dataclass(slots=True)
class MemorySearchToolInput:
    """
    供 LLM 工具调用使用的记忆搜索入参。

    检索默认覆盖所有记忆类型（例如 profile / business_rule），无需也不建议传“类型过滤”。
    如需限定检索范围，只需传 datasource_ids（数据源 id）即可。
    """

    user_id: str
    query: str
    top_k: int | None = None
    # 可选的数据源过滤；用户偏好场景一般不传
    datasource_ids: list[str] | None = None
    filters: dict[str, Any] | None = None


@dataclass(slots=True)
class MemorySearchToolOutput:
    memories: list[MemorySearchResultDTO]


@dataclass(slots=True)
class MemoryWriteToolInput:
    """
    供 LLM 工具调用使用的记忆写入入参。
 
    仅在文档级别支持 `datasource_id` 字段；如果需要区分不同数据源，请在每条 document 中显式设置
    `datasource_id`，而不是依赖顶层默认值。
    """
 
    user_id: str
    documents: list[dict[str, Any]]


@dataclass(slots=True)
class MemoryWriteToolOutput:
    written_ids: list[str]


class MemoryTools:
    """
    记忆工具封装层。

    - 不负责“要不要搜/写”的决策，只在被调用时忠实执行；
    - 方便在工具路由等场景中以 function/tool 形式暴露给大模型。
    """

    def __init__(self) -> None:
        self._service = MemoryService()

    def search(self, payload: MemorySearchToolInput) -> MemorySearchToolOutput:
        top_k = payload.top_k or 8
        query = MemoryQueryDTO(
            user_id=payload.user_id,
            query=payload.query,
            top_k=top_k,
            source_types=None,
            datasource_ids=payload.datasource_ids,
            filters=payload.filters,
        )
        memories = self._service.search(query)
        return MemorySearchToolOutput(memories=memories)

    def write(self, payload: MemoryWriteToolInput) -> MemoryWriteToolOutput:
        docs: list[MemoryDocumentDTO] = []
        for item in payload.documents:
            try:
                raw_id = str(item.get("id") or "").strip()
                if not raw_id:
                    # 可以在上层生成 id，这里仅兜底
                    from uuid import uuid4

                    raw_id = uuid4().hex
                datasource_id = (
                    str(item.get("datasource_id")).strip()
                    if item.get("datasource_id") is not None
                    else None
                )
                doc = MemoryDocumentDTO(
                    id=raw_id,
                    user_id=payload.user_id,
                    # 默认按“问数”场景落为业务规则记忆，避免出现无意义的 other 类型
                    source_type=item.get("source_type", "business_rule"),
                    text=str(item.get("text") or ""),
                    title=item.get("title"),
                    location=item.get("location"),
                    metadata=item.get("metadata") or {},
                    datasource_id=datasource_id or None,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("跳过字段异常的记忆写入项: %s", exc)
                continue
            if not doc.text.strip():
                continue
            docs.append(doc)

        if not docs:
            return MemoryWriteToolOutput(written_ids=[])

        try:
            self._service.upsert_documents_with_embeddings(docs)
        except Exception:  # noqa: BLE001
            logger.exception("写入记忆及向量失败，退回仅写入文档")
            self._service.upsert_documents(docs)
        return MemoryWriteToolOutput(written_ids=[d.id for d in docs])

