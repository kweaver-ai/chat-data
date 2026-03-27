from __future__ import annotations

from typing import Any, Dict

from app.logs.logger import logger

from app.memory.tools import (
    MemorySearchToolInput,
    MemoryTools,
    MemoryWriteToolInput,
    coerce_memory_user_id,
)


class MemorySearchTool:
    """
    记忆搜索工具，对接 tools 体系。
    """

    name = "memory_search"
    description = (
        "长期记忆检索工具。"
        "当你需要回顾用户在过去历史对话中表达过的稳定偏好、长期约定、业务规则、配置信息等内容时，应优先调用此工具。"
        "你需要根据当前问题，主动用自然语言构造一个简短的 query（通常为一两句中文搜索词或问题），"
        "检索默认覆盖所有记忆类型（例如 profile / business_rule），无需也不建议传“类型过滤”。"
        "如需限定检索范围，只需传 datasource_ids（数据源 id）即可；不传则检索全部数据源。"
        "返回结果中每条记忆都包含一个唯一的 id，该 id 可在后续调用 memory_write 时使用，用于更新该条记忆。"
        "user_id 等内部标识由系统自动注入，你无需也不能填写；你只需专注于构造合适的 query 和合理的过滤条件。"
    )

    def __init__(self) -> None:
        self._backend = MemoryTools()

    async def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        params 约定字段：
        - user_id: str
        - query: str
        - top_k: int (可选)
        - datasource_ids: list[str] | str (可选)，按数据源过滤；用户偏好场景一般不传。
        - filters: dict (可选)
        """

        try:
            raw_ds = params.get("datasource_ids")
            if isinstance(raw_ds, str):
                datasource_ids = [raw_ds]
            else:
                datasource_ids = list(raw_ds or [])
            payload = MemorySearchToolInput(
                user_id=coerce_memory_user_id(params.get("user_id")),
                query=str(params.get("query", "") or ""),
                top_k=params.get("top_k"),
                datasource_ids=datasource_ids or None,
                filters=params.get("filters"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[MemorySearchTool] 参数解析失败: {exc}")
            return {"memories": []}

        result = self._backend.search(payload)
        return {
            "memories": [
                {
                    "id": m.id,
                    "document_id": m.document_id,
                    "text": m.text,
                    "score": m.score,
                    "title": m.title,
                    "location": m.location,
                    "metadata": m.metadata,
                    "datasource_id": m.datasource_id,
                }
                for m in result.memories
            ]
        }


class MemoryWriteTool:
    """
    记忆写入工具，对接 tools 体系。
    """

    name = "memory_write"
    description = (
        "长期记忆写入工具。"
        "当你在当前对话中发现了“对未来多轮对话有持续帮助”的信息时，应考虑使用本工具进行持久化存储，"
        "例如：用户的偏好（语言、风格、格式）、长期适用的业务规则、稳定不频繁变化的配置说明、经多次确认后形成的协作约定等。"
        "写入内容应是对信息的简洁自然语言摘要，而不是原始对话原文；请尽量提炼为简明扼要、可直接复用的一两句话，以便后续通过 memory_search 更容易被检索到。"
        "使用 source_type: \"profile\" 时，一般无需传顶层 datasource_id。"
        "请避免写入无意义的信息，以免记忆污染和冗余。"
        "如果需要更新已有记忆：需要使用 memory_search 检索到的目标记忆 id；"
        "再次调用本工具时，在 documents 中传入该 id，并附上新的 text（及必要的其他字段），即可对该条记忆进行覆盖更新，而不是新建一条重复记忆。"
        "user_id 等内部标识由系统自动注入，你无需关注；你只需专注于“是否值得写入长期记忆”以及“如何高质量地总结这条记忆”。"
    )

    def __init__(self) -> None:
        self._backend = MemoryTools()

    async def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        params 约定字段：
        - user_id: str
        - documents: list[dict]，每个 dict 支持字段：
          - id: 可选，字符串
          - text: 必填，字符串
          - title/location/metadata/source_type/datasource_id: 可选
        """

        try:
            payload = MemoryWriteToolInput(
                user_id=coerce_memory_user_id(params.get("user_id")),
                documents=list(params.get("documents") or []),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[MemoryWriteTool] 参数解析失败: {exc}")
            return {"written_ids": []}

        result = self._backend.write(payload)
        return {"written_ids": result.written_ids}

