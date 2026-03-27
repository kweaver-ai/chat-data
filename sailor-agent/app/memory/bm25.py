from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import log
from typing import Final


@dataclass(slots=True)
class BM25Config:
    """
    BM25 配置。

    k1 / b 参数含义参考 OKapi BM25 经典公式：
    - k1: 控制 TF 饱和程度，一般取值 1.2 ~ 2.0；
    - b: 控制文档长度归一化权重，一般取值 0.5 ~ 0.8。

    本实现默认在“候选集”上近似计算统计量，因此非常适合用在
    “向量召回后的重排阶段”，而不是全库倒排索引。
    """

    k1: float = 1.5
    b: float = 0.75
    # 当文档总数小于该阈值时，IDF 计算中使用平滑，避免极端值
    min_doc_count_for_smoothing: int = 1


class BM25Scorer:
    """
    轻量级 BM25 打分器。

    使用方式：
    - 基于一批文本构建实例：BM25Scorer.from_texts(texts, tokenizer)
    - 对同一批文本上的任意 query 调用 score(query) 获得每条文本的 BM25 分数。

    这里的 tokenizer 约定为：将原始字符串拆分为 token 序列的可调用对象，
    便于对中文使用外部分词逻辑（例如 MemoryService._segment_text）。
    """

    _SMOOTH_IDF_EPS: Final[float] = 1e-6

    def __init__(
        self,
        *,
        config: BM25Config,
        docs_tokens: list[list[str]],
    ) -> None:
        self._config = config
        self._docs_tokens = docs_tokens
        self._doc_freqs: dict[str, int] = {}
        self._doc_lengths: list[int] = []
        self._avgdl: float = 0.0
        self._doc_count: int = 0
        self._build_statistics()

    @classmethod
    def from_texts(
        cls,
        texts: Sequence[str],
        *,
        config: BM25Config | None = None,
        tokenizer: callable,
    ) -> "BM25Scorer":
        """
        基于一批原始文本构建 BM25Scorer。

        tokenizer: 接收 str 返回 token 序列（list[str] 或 Iterable[str]）。
        """

        if config is None:
            config = BM25Config()

        docs_tokens: list[list[str]] = []
        for text in texts:
            if not text:
                docs_tokens.append([])
                continue
            tokens_iter = tokenizer(text)
            if isinstance(tokens_iter, list):
                tokens = [t for t in tokens_iter if t]
            else:
                tokens = [t for t in tokens_iter if t]
            docs_tokens.append(tokens)

        return cls(config=config, docs_tokens=docs_tokens)

    def _build_statistics(self) -> None:
        """
        基于 docs_tokens 预计算：
        - 每个文档长度；
        - 每个 term 的 document frequency；
        - 平均文档长度 avgdl。
        """

        self._doc_count = len(self._docs_tokens)
        if self._doc_count == 0:
            self._avgdl = 0.0
            return

        total_len = 0
        df: dict[str, int] = {}

        for tokens in self._docs_tokens:
            length = len(tokens)
            self._doc_lengths.append(length)
            total_len += length
            # 每个文档内部只统计一次 df
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1

        self._doc_freqs = df
        self._avgdl = float(total_len) / float(self._doc_count) if self._doc_count > 0 else 0.0

    def _idf(self, term: str) -> float:
        """
        计算单个 term 的 IDF。

        这里采用一种常见的平滑 IDF 形式，避免极端值：
        idf = log((N - df + 0.5) / (df + 0.5) + eps)
        """

        df = self._doc_freqs.get(term, 0)
        n = max(self._doc_count, self._config.min_doc_count_for_smoothing)
        if df == 0:
            # 未在任何文档出现的 term 直接返回 0
            return 0.0
        # 避免除零和 log(0)
        numerator = max(n - df + 0.5, self._SMOOTH_IDF_EPS)
        denominator = df + 0.5
        return log(numerator / denominator + self._SMOOTH_IDF_EPS)

    def _score_single(self, query_tokens: Sequence[str], doc_index: int) -> float:
        """
        为某一条文档计算给定 query 的 BM25 分数。
        """

        tokens = self._docs_tokens[doc_index]
        if not tokens or not query_tokens:
            return 0.0

        tf_counter = Counter(tokens)
        doc_len = self._doc_lengths[doc_index]
        avgdl = self._avgdl if self._avgdl > 0 else doc_len or 1
        k1 = self._config.k1
        b = self._config.b

        score = 0.0
        for t in query_tokens:
            if not t:
                continue
            tf = tf_counter.get(t, 0)
            if tf == 0:
                continue
            idf = self._idf(t)
            denom = tf + k1 * (1.0 + b * (doc_len / avgdl - 1.0))
            if denom <= 0:
                continue
            score += idf * (tf * (k1 + 1.0) / denom)
        return score

    def score(
        self,
        query_tokens: Iterable[str],
    ) -> list[float]:
        """
        对构建时传入的全部文本，计算单个 query 的 BM25 分数。

        参数 query_tokens 已假定为经过上层分词逻辑处理后的 token 序列，
        便于在调用侧复用同一套分词体系。
        """

        tokens = [t for t in query_tokens if t]
        if not self._docs_tokens or not tokens:
            return [0.0 for _ in range(self._doc_count)]

        return [self._score_single(tokens, idx) for idx in range(self._doc_count)]

