from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body

from app.logs.logger import logger
from app.memory.tools import (
    MemorySearchToolInput,
    MemoryTools,
    MemoryWriteToolInput,
    coerce_memory_user_id,
)
from app.routers.agent_temp_router import MemoryRouter


MemoryAPIRouter = APIRouter()


@MemoryAPIRouter.post(f"{MemoryRouter}/search", summary="记忆搜索接口")
async def memory_search_api(params: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    记忆搜索接口，供 HTTP 直接调用。

    请求体示例:
    {
      "user_id": "10001",
      "query": "用户喜欢喝什么咖啡？",
      "top_k": 5,
      "datasource_ids": ["user_profile"],
      "filters": {...}
    }
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
        logger.error(f"[memory_search_api] 参数解析失败: {exc}")
        return {"memories": []}

    tools = MemoryTools()
    result = tools.search(payload)
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


@MemoryAPIRouter.post(f"{MemoryRouter}/write", summary="记忆写入接口")
async def memory_write_api(params: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    记忆写入接口，供 HTTP 直接调用。

    请求体示例:
    {
      "user_id": "10001",
      "documents": [
        {
          "id": "coffee_pref_001",
          "text": "用户喜欢喝无糖拿铁，一周大约点 3 次。",
          "title": "咖啡偏好",
          "location": "app://order/coffee",
          "source_type": "profile",
          "datasource_id": "user_profile",
          "metadata": {...}
        }
      ]
    }
    """
    try:
        payload = MemoryWriteToolInput(
            user_id=coerce_memory_user_id(params.get("user_id")),
            documents=list(params.get("documents") or []),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[memory_write_api] 参数解析失败: {exc}")
        return {"written_ids": []}

    tools = MemoryTools()
    result = tools.write(payload)
    return {"written_ids": result.written_ids}

