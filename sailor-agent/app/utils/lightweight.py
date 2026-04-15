"""
轻量级内存搜索引擎工具。

特性：
1. 构建索引（支持覆盖重建）
2. 搜索（精确 / 模糊）
3. 删除索引
4. 使用 jieba 做中文分词
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, Iterable, List, Set

import jieba


def _is_search_token(token: str) -> bool:
    """过滤空 token 和纯符号 token。"""
    if not token:
        return False
    return any(ch.isalnum() or ("\u4e00" <= ch <= "\u9fff") for ch in token)


def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip().lower()


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens: List[str] = []
    for token in jieba.cut(text, cut_all=False):
        normalized = _normalize_text(token)
        if _is_search_token(normalized):
            tokens.append(normalized)
    return tokens


@dataclass
class _IndexedDocument:
    doc_id: str
    text: str
    normalized_text: str
    tokens: Set[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _IndexStore:
    documents: Dict[str, _IndexedDocument] = field(default_factory=dict)
    inverted_index: Dict[str, Set[str]] = field(default_factory=dict)


class LightweightSearchEngine:
    """
    轻量级搜索引擎（内存版）。

    使用方式：
    - build_index: 构建/重建索引
    - search: 精确或模糊检索
    - delete_index: 删除指定索引
    """

    def __init__(self) -> None:
        self._indices: Dict[str, _IndexStore] = {}
        self._lock = RLock()

    def build_index(
        self,
        index_name: str,
        documents: Iterable[Dict[str, Any] | str],
        *,
        id_key: str = "id",
        text_key: str = "text",
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        构建索引。

        参数：
        - index_name: 索引名称
        - documents: 文档列表（每个元素可以是 dict 或 str）
        - id_key/text_key: 当文档为 dict 时用于取值的字段
        - overwrite: True 表示先删除后重建；False 表示增量写入
        """
        normalized_index_name = _normalize_text(index_name)
        if not normalized_index_name:
            raise ValueError("index_name 不能为空")

        docs = list(documents or [])
        if not docs:
            raise ValueError("documents 不能为空")

        with self._lock:
            if overwrite or normalized_index_name not in self._indices:
                self._indices[normalized_index_name] = _IndexStore()

            store = self._indices[normalized_index_name]
            for seq, raw_doc in enumerate(docs):
                indexed_doc = self._build_document(
                    raw_doc=raw_doc,
                    seq=seq,
                    id_key=id_key,
                    text_key=text_key,
                )
                self._upsert_document(store, indexed_doc)

            return {
                "index_name": normalized_index_name,
                "document_count": len(store.documents),
                "term_count": len(store.inverted_index),
                "overwrite": overwrite,
            }

    def search(
        self,
        index_name: str,
        query: str,
        *,
        mode: str = "fuzzy",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        查询索引。

        mode:
        - exact: 精确匹配（query 是文档正文子串）
        - fuzzy: 分词匹配（基于命中词占比评分）
        """
        normalized_index_name = _normalize_text(index_name)
        normalized_query = _normalize_text(query)
        if not normalized_index_name:
            raise ValueError("index_name 不能为空")
        if not normalized_query:
            return []
        if top_k <= 0:
            return []

        with self._lock:
            store = self._indices.get(normalized_index_name)
            if store is None:
                return []

            normalized_mode = _normalize_text(mode) or "fuzzy"
            if normalized_mode == "exact":
                return self._exact_search(store, normalized_query, top_k=top_k)
            if normalized_mode == "fuzzy":
                return self._fuzzy_search(store, normalized_query, top_k=top_k)
            raise ValueError("mode 仅支持 exact 或 fuzzy")

    def delete_index(self, index_name: str) -> bool:
        """删除索引，存在返回 True，不存在返回 False。"""
        normalized_index_name = _normalize_text(index_name)
        if not normalized_index_name:
            return False
        with self._lock:
            return self._indices.pop(normalized_index_name, None) is not None

    def list_indices(self) -> List[str]:
        """查看当前已构建的索引名称。"""
        with self._lock:
            return sorted(self._indices.keys())

    def _build_document(
        self,
        *,
        raw_doc: Dict[str, Any] | str,
        seq: int,
        id_key: str,
        text_key: str,
    ) -> _IndexedDocument:
        if isinstance(raw_doc, str):
            doc_id = f"doc_{seq}"
            text = raw_doc
            metadata: Dict[str, Any] = {}
        elif isinstance(raw_doc, dict):
            doc_id = _normalize_text(raw_doc.get(id_key) or f"doc_{seq}")
            text = str(raw_doc.get(text_key) or "")
            metadata = {
                key: value for key, value in raw_doc.items()
                if key not in {id_key, text_key}
            }
        else:
            raise TypeError("documents 元素仅支持 dict 或 str")

        normalized_text = _normalize_text(text)
        tokens = set(_tokenize(normalized_text))
        return _IndexedDocument(
            doc_id=doc_id,
            text=text,
            normalized_text=normalized_text,
            tokens=tokens,
            metadata=metadata,
        )

    def _upsert_document(self, store: _IndexStore, doc: _IndexedDocument) -> None:
        old_doc = store.documents.get(doc.doc_id)
        if old_doc:
            for token in old_doc.tokens:
                posting = store.inverted_index.get(token)
                if posting:
                    posting.discard(old_doc.doc_id)
                    if not posting:
                        store.inverted_index.pop(token, None)

        store.documents[doc.doc_id] = doc
        for token in doc.tokens:
            store.inverted_index.setdefault(token, set()).add(doc.doc_id)

    def _exact_search(
        self,
        store: _IndexStore,
        query: str,
        *,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for doc in store.documents.values():
            if query in doc.normalized_text:
                score = doc.normalized_text.count(query)
                matches.append(self._render_hit(doc, float(score)))

        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:top_k]

    def _fuzzy_search(
        self,
        store: _IndexStore,
        query: str,
        *,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []

        candidate_ids: Set[str] = set()
        for token in query_tokens:
            candidate_ids.update(store.inverted_index.get(token, set()))

        if not candidate_ids:
            return []

        hits: List[Dict[str, Any]] = []
        token_count = len(query_tokens)
        for doc_id in candidate_ids:
            doc = store.documents.get(doc_id)
            if not doc:
                continue
            overlap = len(query_tokens & doc.tokens)
            if overlap <= 0:
                continue
            score = overlap / token_count
            hits.append(self._render_hit(doc, round(score, 4)))

        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:top_k]

    @staticmethod
    def _render_hit(doc: _IndexedDocument, score: float) -> Dict[str, Any]:
        return {
            "id": doc.doc_id,
            "text": doc.text,
            "score": score,
            "metadata": doc.metadata,
        }
