from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


# 当前阶段聚焦“问数”场景，只区分：
# - business_rule：指标口径 / 业务规则 / 统计口径等与“怎么算”相关的知识
# - profile：用户画像 / 偏好（保留，便于后续扩展个性化问数体验）
MemorySourceType = Literal["business_rule", "profile"]


@dataclass(slots=True)
class MemoryDocumentDTO:
    """
    记忆文档 DTO，对应一条可检索的长期记忆。
    text 不宜过长，建议在写入前做摘要。
    """

    id: str
    user_id: str
    source_type: MemorySourceType
    text: str
    title: str | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 具体数据源实例标识，例如业务知识网络 ID、数据库实例 ID 等
    datasource_id: str | None = None
    # 分词后的文本（使用 jieba 分词得到的 token 串），用于关键词检索
    segmented_text: str | None = None


@dataclass(slots=True)
class MemoryChunkDTO:
    """
    分块级记忆 DTO，目前用于承载向量信息，后续可扩展为多粒度切片。
    """

    id: str
    document_id: str
    user_id: str
    text: str
    embedding: list[float] | None = None
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] | None = None
    datasource_id: str | None = None


@dataclass(slots=True)
class MemoryQueryDTO:
    """
    统一的记忆检索请求。
    是否使用向量/关键词由服务层与底层能力自动决定，上层无需关心。
    """

    user_id: str
    query: str
    top_k: int = 8
    source_types: list[MemorySourceType] | None = None
    # 支持按具体数据源实例过滤；为空则不按数据源限制
    datasource_ids: list[str] | None = None
    # 预留更细粒度过滤条件，例如按时间范围、location 前缀等
    filters: dict[str, Any] | None = None


@dataclass(slots=True)
class MemorySearchResultDTO:
    """记忆检索结果，包含简单打分。"""

    id: str
    document_id: str
    text: str
    score: float
    title: str | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None
    datasource_id: str | None = None


@dataclass(slots=True)
class MemoryStatusDTO:
    """记忆后端状态，用于可观测性与调试。"""

    ready: bool
    documents_count: int = 0
    chunks_count: int = 0
    vector_search_available: bool = False
    keyword_search_available: bool = True
    embedding_dimensions: int | None = None


@dataclass(slots=True)
class MemoryDocumentListItemDTO:
    """
    记忆列表项 DTO，用于前端分页展示。

    相比 MemoryDocumentDTO：
    - text 只返回摘要片段（由仓储层裁剪），避免单条过长；
    - 保留 created_at/updated_at 便于排序与前端展示。
    """

    id: str
    user_id: str
    source_type: MemorySourceType
    text_snippet: str
    title: str | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    datasource_id: str | None = None


@dataclass(slots=True)
class MemoryListQueryDTO:
    """
    记忆列表查询请求，主要用于管理端分页浏览。
    """

    user_id: str
    page: int = 1
    page_size: int = 20
    query: str | None = None
    source_types: list[MemorySourceType] | None = None
    datasource_ids: list[str] | None = None


@dataclass(slots=True)
class MemoryListResultDTO:
    """
    记忆列表分页结果。
    """

    items: list[MemoryDocumentListItemDTO]
    total: int

