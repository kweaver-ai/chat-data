from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from functools import lru_cache
from math import sqrt

import jieba
from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session

from app.logs.logger import logger
from app.utils.stop_word import get_default_stop_words
from app.memory.db_models import MemoryChunkRecord, MemoryDocumentRecord
from app.memory.bm25 import BM25Config, BM25Scorer
from app.memory.models import (
    MemoryDocumentDTO,
    MemoryDocumentListItemDTO,
    MemoryListQueryDTO,
    MemoryListResultDTO,
    MemoryQueryDTO,
    MemorySearchResultDTO,
    MemoryStatusDTO,
)


class MemoryRepository:
    """
    记忆持久化仓储层。

    仅负责 ORM 读写与基础查询，不包含“是否要搜/写”的语义逻辑。
    """

    def __init__(self, session: Session):
        self._session = session

    @staticmethod
    @lru_cache(maxsize=1)
    def _memory_stop_words() -> set[str]:
        """
        使用项目默认停用词集合过滤检索 token。
        """
        return get_default_stop_words()

    def upsert_documents(self, docs: Iterable[MemoryDocumentDTO]) -> None:
        for doc in docs:
            existing = self._session.get(MemoryDocumentRecord, doc.id)
            metadata_json = json.dumps(doc.metadata or {}, ensure_ascii=False)
            if existing is None:
                record = MemoryDocumentRecord(
                    id=doc.id,
                    user_id=doc.user_id,
                    source_type=doc.source_type,
                    datasource_id=doc.datasource_id,
                    title=doc.title,
                    text=doc.text,
                    location=doc.location,
                    extra_metadata=metadata_json,
                    segmented_text=doc.segmented_text,
                )
                self._session.add(record)
            else:
                existing.user_id = doc.user_id
                existing.source_type = doc.source_type
                existing.datasource_id = doc.datasource_id
                existing.title = doc.title
                existing.text = doc.text
                existing.location = doc.location
                existing.extra_metadata = metadata_json
                existing.segmented_text = doc.segmented_text

    def delete_documents(self, ids: list[str]) -> None:
        if not ids:
            return
        stmt = select(MemoryDocumentRecord).where(MemoryDocumentRecord.id.in_(ids))
        for record in self._session.scalars(stmt):
            self._session.delete(record)

    def delete_chunks_by_document_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        stmt = select(MemoryChunkRecord).where(MemoryChunkRecord.document_id.in_(ids))
        for record in self._session.scalars(stmt):
            self._session.delete(record)

    def list_documents(self, query: MemoryListQueryDTO) -> MemoryListResultDTO:
        """
        分页列出当前用户的记忆文档，支持按关键词和来源类型简单过滤。
        """

        page = max(query.page, 1)
        page_size = max(min(query.page_size, 200), 1)

        base_stmt: Select[MemoryDocumentRecord] = select(MemoryDocumentRecord).where(
            MemoryDocumentRecord.user_id == query.user_id
        )

        if query.datasource_ids:
            base_stmt = base_stmt.where(
                MemoryDocumentRecord.datasource_id.in_(list(query.datasource_ids))
            )

        if query.source_types:
            base_stmt = base_stmt.where(
                MemoryDocumentRecord.source_type.in_(list(query.source_types))
            )

        if query.query:
            text_query = query.query.strip()
            if text_query:
                like_pattern = f"%{text_query}%"
                base_stmt = base_stmt.where(
                    MemoryDocumentRecord.text.ilike(like_pattern)
                )

        count_stmt: Select[int] = select(func.count()).select_from(base_stmt.subquery())
        total = int(self._session.scalar(count_stmt) or 0)

        if total == 0:
            return MemoryListResultDTO(items=[], total=0)

        offset = (page - 1) * page_size
        stmt = (
            base_stmt.order_by(MemoryDocumentRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        rows: list[MemoryDocumentRecord] = list(self._session.scalars(stmt))
        items: list[MemoryDocumentListItemDTO] = []

        for record in rows:
            full_text = record.text or ""
            snippet = full_text[:200]

            try:
                metadata = (
                    json.loads(record.extra_metadata) if record.extra_metadata else None
                )
            except Exception:  # noqa: BLE001
                logger.warning("解析记忆 metadata 失败，忽略该字段", record_id=record.id)
                metadata = None

            items.append(
                MemoryDocumentListItemDTO(
                    id=record.id,
                    user_id=record.user_id,
                    source_type=record.source_type,  # type: ignore[arg-type]
                    text_snippet=snippet,
                    title=record.title,
                    location=record.location,
                    metadata=metadata,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    datasource_id=record.datasource_id,
                )
            )

        return MemoryListResultDTO(items=items, total=total)

    def upsert_chunks_with_embeddings(
        self,
        docs: Sequence[MemoryDocumentDTO],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """
        为每个文档写入或更新一条分块记录，承载向量信息。

        当前约定：每个文档对应一条 chunk（id 由文档 id 派生），后续如需更细粒度切片，
        可以在上层拆分 text 并传入多条 doc+embedding。
        """

        if not docs or not embeddings:
            return

        for doc, emb in zip(docs, embeddings, strict=False):
            if not emb:
                continue
            emb_json = json.dumps(list(emb), ensure_ascii=False)
            chunk_id = doc.id  # 一文一块，直接复用文档 id 作为主键
            existing = self._session.get(MemoryChunkRecord, chunk_id)
            if existing is None:
                record = MemoryChunkRecord(
                    id=chunk_id,
                    document_id=doc.id,
                    user_id=doc.user_id,
                    datasource_id=doc.datasource_id,
                    text=doc.text,
                    embedding_json=emb_json,
                    keyword_score_hint=None,
                    extra_metadata=None,
                )
                self._session.add(record)
            else:
                existing.document_id = doc.id
                existing.user_id = doc.user_id
                existing.datasource_id = doc.datasource_id
                existing.text = doc.text
                existing.embedding_json = emb_json

    def keyword_search(self, query: MemoryQueryDTO) -> list[MemorySearchResultDTO]:
        """
        基于数据库候选集做“全文检索风格”的关键词检索：
        - 先用 LIKE 从文本/分词结果中粗召回候选；
        - 再在候选集上基于 jieba 分词使用 BM25 进行相关性打分与排序。

        - segmented_text 由上层通过 jieba 预分词得到；
        - 当前实现不依赖 MySQL FULLTEXT 索引，仅通过候选集上的 BM25 提升检索质量。
        """

        text_query = query.query.strip()
        if not text_query:
            return []

        stop_set = MemoryRepository._memory_stop_words()
        # 将 query 切成 token，然后用 token 维度做 LIKE 粗召回，提升中文场景 recall。
        query_tokens: list[str] = [
            tok.strip()
            for tok in jieba.cut(text_query, cut_all=False)
            if tok.strip() and tok.strip() not in stop_set
        ]
        # 防止特别长 query 导致 SQL 条件过多
        query_tokens = query_tokens[:20]
        if not query_tokens:
            return []

        # match_count：命中的 token 数量（用于在 limit 之前更严谨地选择候选）
        match_count_expr = None

        stmt: Select[tuple[MemoryDocumentRecord, int]] = select(
            MemoryDocumentRecord,
        ).where(MemoryDocumentRecord.user_id == query.user_id)

        if query.datasource_ids:
            stmt = stmt.where(
                MemoryDocumentRecord.datasource_id.in_(list(query.datasource_ids))
            )

        if query.source_types:
            stmt = stmt.where(MemoryDocumentRecord.source_type.in_(query.source_types))

        # 对每个 token 构造 (segmented_text LIKE '%token%' OR text LIKE '%token%')，
        # 再把 token 之间用 OR 组合。
        token_predicates = []
        token_match_conditions = []
        for tok in query_tokens:
            token_pattern = f"%{tok}%"
            cond = (
                (MemoryDocumentRecord.segmented_text.ilike(token_pattern))
                | (MemoryDocumentRecord.text.ilike(token_pattern))
            )
            token_predicates.append(cond)
            token_match_conditions.append(cond)

        # 确保至少匹配一个 token
        stmt = stmt.where(or_(*token_predicates))

        match_count_expr = sum(
            case((cond, 1), else_=0) for cond in token_match_conditions
        ).label("match_count")
        stmt = stmt.add_columns(match_count_expr)
        stmt = stmt.order_by(match_count_expr.desc())

        stmt = stmt.limit(query.top_k * 3)

        rows: list[tuple[MemoryDocumentRecord, int]] = list(self._session.execute(stmt))
        if not rows:
            return []

        docs_tokens: list[list[str]] = []
        candidate_records: list[MemoryDocumentRecord] = []
        for record, _ in rows:
            candidate_records.append(record)
            if record.segmented_text:
                tokens = [t for t in record.segmented_text.split() if t and t not in stop_set]
                docs_tokens.append(tokens)
            else:
                tokens = [
                    tok.strip()
                    for tok in jieba.cut((record.text or ""), cut_all=False)
                    if tok.strip() and tok.strip() not in stop_set
                ]
                docs_tokens.append(tokens)

        bm25 = BM25Scorer(config=BM25Config(), docs_tokens=docs_tokens)
        scores = bm25.score(query_tokens)

        results: list[MemorySearchResultDTO] = []

        for (record, _match_count), bm25_score in zip(rows, scores, strict=False):
            if bm25_score <= 0.0:
                continue
            full_text = record.text or ""
            full_lower = full_text.lower()
            query_lower = text_query.lower()
            idx = full_lower.find(query_lower)
            if idx == -1:
                # 若原文中未直接命中整段 query，则尝试先用第一个命中的 token 定位摘要位置。
                for tok in query_tokens:
                    tok_lower = tok.lower()
                    idx = full_lower.find(tok_lower)
                    if idx != -1:
                        break
            if idx == -1:
                # 兜底：返回前若干字符作为摘要
                idx = 0
            snippet_start = max(0, idx - 80)
            snippet_end = min(len(full_text), idx + len(text_query) + 80)
            snippet = full_text[snippet_start:snippet_end]

            try:
                metadata = (
                    json.loads(record.extra_metadata) if record.extra_metadata else None
                )
            except Exception:  # noqa: BLE001
                logger.warning("解析记忆 metadata 失败，忽略该字段", record_id=record.id)
                metadata = None

            results.append(
                MemorySearchResultDTO(
                    id=record.id,
                    document_id=record.id,
                    text=snippet,
                    score=bm25_score,
                    title=record.title,
                    location=record.location,
                    metadata=metadata,
                    datasource_id=record.datasource_id,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[: query.top_k]

    def vector_search(
        self,
        query: MemoryQueryDTO,
        query_embedding: Sequence[float],
    ) -> list[MemorySearchResultDTO]:
        """
        基于 memory_chunks 表中存储的 embedding_json 进行向量相似度检索。
        """

        if not query_embedding:
            return []

        stmt: Select[tuple[MemoryChunkRecord, MemoryDocumentRecord]] = (
            select(MemoryChunkRecord, MemoryDocumentRecord)
            .join(
                MemoryDocumentRecord,
                MemoryDocumentRecord.id == MemoryChunkRecord.document_id,
            )
            .where(
                MemoryChunkRecord.user_id == query.user_id,
                MemoryChunkRecord.embedding_json.is_not(None),
            )
        )

        if query.datasource_ids:
            stmt = stmt.where(
                MemoryChunkRecord.datasource_id.in_(list(query.datasource_ids))
            )

        if query.source_types:
            stmt = stmt.where(MemoryDocumentRecord.source_type.in_(query.source_types))

        rows: list[tuple[MemoryChunkRecord, MemoryDocumentRecord]] = list(
            self._session.execute(stmt)
        )
        if not rows:
            return []

        def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
            if not a or not b:
                return 0.0
            n = min(len(a), len(b))
            dot = sum(a[i] * b[i] for i in range(n))
            na = sqrt(sum(a[i] * a[i] for i in range(n)))
            nb = sqrt(sum(b[i] * b[i] for i in range(n)))
            if na == 0.0 or nb == 0.0:
                return 0.0
            return dot / (na * nb)

        scored: list[MemorySearchResultDTO] = []
        for chunk, doc in rows:
            try:
                emb = (
                    json.loads(chunk.embedding_json or "")
                    if chunk.embedding_json
                    else []
                )
                if not isinstance(emb, list):
                    continue
                emb_floats = [float(x) for x in emb]
            except Exception:  # noqa: BLE001
                logger.warning("解析 chunk embedding_json 失败，跳过该记录", chunk_id=chunk.id)
                continue

            score = _cosine(query_embedding, emb_floats)
            if score <= 0.0:
                continue

            try:
                metadata = (
                    json.loads(doc.extra_metadata) if doc.extra_metadata else None
                )
            except Exception:  # noqa: BLE001
                logger.warning("解析记忆 metadata 失败，忽略该字段", record_id=doc.id)
                metadata = None

            scored.append(
                MemorySearchResultDTO(
                    id=chunk.id,
                    document_id=doc.id,
                    text=chunk.text,
                    score=score,
                    title=doc.title,
                    location=doc.location,
                    metadata=metadata,
                    datasource_id=doc.datasource_id,
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[: query.top_k]

    def count_stats(self) -> MemoryStatusDTO:
        docs_count = self._session.scalar(
            select(func.count(MemoryDocumentRecord.id))
        ) or 0
        chunks_count = self._session.scalar(
            select(func.count(MemoryChunkRecord.id))
        ) or 0
        # 当没有任何向量分块记录时，视为暂不可用向量检索能力，避免对外宣称可用却查不到结果
        vector_available = chunks_count > 0
        return MemoryStatusDTO(
            ready=True,
            documents_count=int(docs_count),
            chunks_count=int(chunks_count),
            keyword_search_available=True,
            vector_search_available=vector_available,
            embedding_dimensions=None,
        )

