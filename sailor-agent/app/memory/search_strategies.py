from __future__ import annotations

from collections.abc import Sequence

from app.memory.bm25 import BM25Config, BM25Scorer
from app.memory.models import MemoryQueryDTO, MemorySearchResultDTO, MemoryStatusDTO
from app.memory.repository import MemoryRepository


class HybridSearcher:
    """
    混合检索策略：
    - 同时考虑向量相似度与关键词匹配；
    - 在向量服务不可用时自动退回纯关键词检索。
    """

    def __init__(
        self,
        repo: MemoryRepository,
        *,
        bm25_config: BM25Config | None = None,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        vector_candidate_size: int = 64,
    ):
        self._repo = repo
        self._bm25_config = bm25_config or BM25Config()
        # 融合权重，需保证非负；归一化在内部完成
        self._vector_weight = max(vector_weight, 0.0)
        self._bm25_weight = max(bm25_weight, 0.0)
        # 初始向量候选集大小（向量检索 top_k），应大于最终返回的 top_k
        self._vector_candidate_size = max(vector_candidate_size, 1)

    def search(self, query: MemoryQueryDTO) -> list[MemorySearchResultDTO]:
        # 当前实现中，是否进行向量检索由上层决定是否提供 query_embedding。
        # 这里简单实现一个“仅关键词检索”的占位逻辑，向量检索由服务层融合。
        return self._repo.keyword_search(query)

    @staticmethod
    def _normalize_scores(results: list[MemorySearchResultDTO]) -> dict[str, float]:
        """
        将结果列表中的 score 归一化到 [0, 1] 区间，返回 document_id -> normalized_score。
        """

        if not results:
            return {}
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        if max_score <= min_score:
            return {r.document_id: 1.0 for r in results}
        span = max_score - min_score
        return {r.document_id: (r.score - min_score) / span for r in results}

    def _bm25_rerank(
        self,
        query: MemoryQueryDTO,
        vector_results: list[MemorySearchResultDTO],
    ) -> list[MemorySearchResultDTO]:
        """
        在向量召回的候选集上使用 BM25 计算文本相关性分数，并写回 score 字段。
        """

        if not vector_results or not query.query.strip():
            return [
                MemorySearchResultDTO(
                    id=r.id,
                    document_id=r.document_id,
                    text=r.text,
                    score=0.0,
                    title=r.title,
                    location=r.location,
                    metadata=r.metadata,
                    datasource_id=r.datasource_id,
                )
                for r in vector_results
            ]

        texts: list[str] = [r.text or "" for r in vector_results]

        def _simple_tokenizer(text: str) -> list[str]:
            # 这里假定上层已经对文档做了合理的预处理（如分句/摘要），
            # BM25 只需在该片段上做简单 token 拆分。
            return text.split()

        bm25 = BM25Scorer.from_texts(
            texts,
            config=self._bm25_config,
            tokenizer=_simple_tokenizer,
        )

        # 为 query 同样做简单拆分；未来可考虑直接复用 MemoryService 的分词逻辑传入 tokens
        query_tokens = query.query.split()
        scores = bm25.score(query_tokens)

        reranked: list[MemorySearchResultDTO] = []
        for base, bm25_score in zip(vector_results, scores, strict=False):
            reranked.append(
                MemorySearchResultDTO(
                    id=base.id,
                    document_id=base.document_id,
                    text=base.text,
                    score=bm25_score,
                    title=base.title,
                    location=base.location,
                    metadata=base.metadata,
                    datasource_id=base.datasource_id,
                )
            )
        return reranked

    def hybrid_search(
        self,
        query: MemoryQueryDTO,
        query_embedding: Sequence[float] | None,
    ) -> list[MemorySearchResultDTO]:
        """
        在向量召回候选集上使用 BM25 做重排，并融合向量分数与 BM25 分数。
        """

        if not query_embedding:
            return self._repo.keyword_search(query)

        vector_query = MemoryQueryDTO(
            user_id=query.user_id,
            query=query.query,
            top_k=max(self._vector_candidate_size, query.top_k),
            source_types=query.source_types,
            datasource_ids=query.datasource_ids,
            filters=query.filters,
        )
        vector_results = self._repo.vector_search(vector_query, query_embedding)
        if not vector_results:
            return self._repo.keyword_search(query)

        bm25_results = self._bm25_rerank(query, vector_results)

        vec_norm = self._normalize_scores(vector_results)
        bm25_norm = self._normalize_scores(bm25_results)

        weight_vec = self._vector_weight
        weight_bm25 = self._bm25_weight
        if weight_vec <= 0.0 and weight_bm25 <= 0.0:
            weight_vec = 1.0
            weight_bm25 = 0.0
        weight_sum = weight_vec + weight_bm25
        weight_vec /= weight_sum
        weight_bm25 /= weight_sum

        fused: list[MemorySearchResultDTO] = []
        for vec_item in vector_results:
            doc_id = vec_item.document_id
            v_score = vec_norm.get(doc_id, 0.0)
            b_score = bm25_norm.get(doc_id, 0.0)
            final_score = weight_vec * v_score + weight_bm25 * b_score
            fused.append(
                MemorySearchResultDTO(
                    id=vec_item.id,
                    document_id=doc_id,
                    text=vec_item.text,
                    score=final_score,
                    title=vec_item.title,
                    location=vec_item.location,
                    metadata=vec_item.metadata,
                    datasource_id=vec_item.datasource_id,
                )
            )

        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[: query.top_k]

    def status(self) -> MemoryStatusDTO:
        return self._repo.count_stats()

