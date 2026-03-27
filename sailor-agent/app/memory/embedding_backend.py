from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.logs.logger import logger
from app.service.adp_service import ADPService


class EmbeddingBackend(Protocol):
    """
    向量嵌入后端抽象。

    通过简单的同步接口提供文本到向量的映射能力，便于在记忆模块内部解耦外部服务。
    """

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class ADPEmbeddingBackend:
    """
    基于 ADP 模型服务的 embedding 实现。

    通过 ADPService.get_adp_embedding 调用后端服务，返回向量列表。
    """

    def __init__(self) -> None:
        self._client = ADPService()

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            resp = self._client.get_adp_embedding(list(texts))
        except Exception as exc:  # noqa: BLE001
            logger.error(f"调用 ADP embedding 服务失败: {exc}")
            return []
        data = resp.get("data") or []
        embeddings: list[list[float]] = []
        for item in data:
            emb = item.get("embedding")
            if isinstance(emb, list):
                try:
                    embeddings.append([float(x) for x in emb])
                except (TypeError, ValueError):
                    continue
        if len(embeddings) != len(texts):
            logger.warning(
                "ADP embedding 返回条数与输入不一致: input=%d, output=%d",
                len(texts),
                len(embeddings),
            )
        return embeddings

