from __future__ import annotations

from collections.abc import Iterable, Sequence
from functools import lru_cache

import jieba
from sqlalchemy.exc import ProgrammingError

from app.depandencies.db_dependency import get_db_session
from app.logs.logger import logger
from app.utils.stop_word import get_default_stop_words
from app.memory.db_models import MemoryChunkRecord, MemoryDocumentRecord
from app.memory.embedding_backend import ADPEmbeddingBackend
from app.memory.bm25 import BM25Config
from app.memory.models import (
    MemoryDocumentDTO,
    MemoryListQueryDTO,
    MemoryListResultDTO,
    MemoryQueryDTO,
    MemorySearchResultDTO,
    MemoryStatusDTO,
)
from app.memory.repository import MemoryRepository
from app.memory.search_strategies import HybridSearcher


class MemoryService:
    """
    记忆服务层，对上提供统一的搜索 / 写入接口。

    - 是否需要搜索/写入由 LLM 决策，本服务不做语义层面的“要不要”判断；
    - 内部自动根据底层能力选择向量+关键词混合检索或退回纯关键词检索。
    """

    def __init__(self) -> None:
        # embedding 后端为轻量对象，可以按实例维度持有
        self._embedding_backend = ADPEmbeddingBackend()
        # BM25 与融合相关配置，后续可通过配置文件或环境变量注入
        self._bm25_config = BM25Config()
        self._vector_weight: float = 0.7
        self._bm25_weight: float = 0.3
        self._vector_candidate_size: int = 64

    @staticmethod
    def _ensure_memory_tables(bind) -> None:
        """
        在新环境中自动创建记忆相关表。
        """
        try:
            logger.warning("记忆模块检测到缺少表，尝试自动创建 memory_documents / memory_chunks")
            MemoryDocumentRecord.__table__.create(bind=bind, checkfirst=True)
            MemoryChunkRecord.__table__.create(bind=bind, checkfirst=True)
        except Exception:  # noqa: BLE001
            logger.exception("自动创建记忆相关表失败")

    def _with_repo(self, fn):
        session = get_db_session()
        try:
            repo = MemoryRepository(session)
            result = fn(repo)
            # 统一在服务层提交事务，保证记忆写入真正落库
            session.commit()
            return result
        except ProgrammingError as exc:
            msg = str(getattr(exc, "orig", exc))
            if "t_memory_documents" in msg or "t_memory_chunks" in msg:
                bind = session.get_bind()
                self._ensure_memory_tables(bind)
                # 建表后重试一次
                repo = MemoryRepository(session)
                result = fn(repo)
                session.commit()
                return result
            session.rollback()
            raise
        except Exception:
            # 其它异常场景统一回滚，避免脏事务
            session.rollback()
            raise
        finally:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                logger.warning("关闭记忆模块数据库会话失败", exc_info=True)

    @staticmethod
    @lru_cache(maxsize=1)
    def _memory_stop_words() -> set[str]:
        """
        获取停用词集合。

        - 用于分词阶段过滤高频无意义词，提升 BM25/Sparse 检索质量。
        - 使用 lru_cache 避免每次写入/检索重复构建集合。
        """
        return get_default_stop_words()

    @staticmethod
    def _segment_text(text: str) -> str:
        """
        使用 jieba 对文本进行分词，返回空格分隔的 token 串。
        """

        if not text:
            return ""
        stop_set = MemoryService._memory_stop_words()
        tokens = [
            tok.strip()
            for tok in jieba.cut(text, cut_all=False)
            if tok.strip() and tok.strip() not in stop_set
        ]
        return " ".join(tokens)

    def _prepare_docs_with_segmentation(
        self,
        docs: Iterable[MemoryDocumentDTO],
    ) -> list[MemoryDocumentDTO]:
        result: list[MemoryDocumentDTO] = []
        for doc in docs:
            text = doc.text or ""
            segmented = self._segment_text(text)
            doc.segmented_text = segmented
            result.append(doc)
        return result

    def upsert_documents(self, docs: Iterable[MemoryDocumentDTO]) -> None:
        docs_list = list(docs)
        if not docs_list:
            return
        docs_list = self._prepare_docs_with_segmentation(docs_list)

        def _inner(repo: MemoryRepository) -> None:
            logger.info("批量写入记忆文档：count=%d", len(docs_list))
            repo.upsert_documents(docs_list)

        self._with_repo(_inner)

    def upsert_documents_with_embeddings(
        self,
        docs: Iterable[MemoryDocumentDTO],
    ) -> None:
        """
        写入记忆文档的同时，为每条文档生成 embedding 并存入 MySQL。

        当前实现为“一文一向量”，向量基于全文 text 生成；
        如需更细粒度切片，可在上层拆分 text，再多次调用本方法。
        """

        docs_list = [d for d in docs if d.text.strip()]
        if not docs_list:
            return

        docs_list = self._prepare_docs_with_segmentation(docs_list)
        texts: list[str] = [d.text for d in docs_list]
        embeddings: list[list[float]] = self._embedding_backend.embed_texts(texts)
        if not embeddings:
            logger.warning("embedding 服务返回空结果，退回仅写入文档")
            self.upsert_documents(docs_list)
            return

        def _inner(repo: MemoryRepository) -> None:
            logger.info(
                "批量写入记忆文档及向量：count=%d has_embeddings=%d",
                len(docs_list),
                len(embeddings),
            )
            repo.upsert_documents(docs_list)
            repo.upsert_chunks_with_embeddings(docs_list, embeddings)

        self._with_repo(_inner)

    def delete_documents(self, ids: list[str]) -> None:
        if not ids:
            return

        def _inner(repo: MemoryRepository) -> None:
            logger.info("批量删除记忆文档：count=%d", len(ids))
            # 当前模型未显式设置外键级联，先删向量块再删 t_memory_documents 行，避免孤儿 chunk
            repo.delete_chunks_by_document_ids(ids)
            repo.delete_documents(ids)

        self._with_repo(_inner)

    def list_user_memories(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        query: str | None = None,
        source_types: Sequence[str] | None = None,
    ) -> MemoryListResultDTO:
        """
        分页列出当前用户的记忆文档，供管理界面使用。
        """

        def _inner(repo: MemoryRepository) -> MemoryListResultDTO:
            dto = MemoryListQueryDTO(
                user_id=user_id,
                page=page,
                page_size=page_size,
                query=query,
                source_types=list(source_types) if source_types else None,
            )
            return repo.list_documents(dto)

        return self._with_repo(_inner)

    def search(self, query: MemoryQueryDTO) -> list[MemorySearchResultDTO]:
        """
        对外统一搜索接口：内部自动融合关键词检索与向量检索。
        """

        def _inner(repo: MemoryRepository) -> list[MemorySearchResultDTO]:
            searcher = HybridSearcher(
                repo,
                bm25_config=self._bm25_config,
                vector_weight=self._vector_weight,
                bm25_weight=self._bm25_weight,
                vector_candidate_size=self._vector_candidate_size,
            )
            # 向量查询直接在此处完成 embedding 生成与融合
            query_embedding: Sequence[float] | None = []
            if query.query.strip():
                embeddings = self._embedding_backend.embed_texts([query.query])
                if embeddings:
                    query_embedding = embeddings[0]

            has_embedding = bool(query_embedding)
            logger.info(
                "记忆搜索：user_id=%s has_embedding=%s query_preview=%s",
                query.user_id,
                has_embedding,
                (query.query[:100] if query.query else ""),
            )

            return searcher.hybrid_search(query, query_embedding)

        return self._with_repo(_inner)

    def status(self) -> MemoryStatusDTO:
        def _inner(repo: MemoryRepository) -> MemoryStatusDTO:
            searcher = HybridSearcher(repo)
            return searcher.status()

        return self._with_repo(_inner)

