from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryDocumentRecord(Base):
    """
    长期记忆文档表（MySQL 版本）。

    - user_id 用于用户级隔离；
    - source_type 区分 session/profile/event 等不同类型记忆；
    - text 建议存摘要后的文本，尽量控制长度；
    - metadata 使用 TEXT 存 JSON 字符串，便于后续迁移；
    - segmented_text 存放 jieba 分词后的 token 串，用于关键词检索。
    """

    __tablename__ = "t_memory_documents"
    __table_args__ = {
        "comment": (
            "长期记忆文档表：按 user_id 隔离；source_type 区分画像/业务规则等类型；"
            "text 存摘要文本；metadata 存 JSON；segmented_text 存分词结果供关键词检索。"
        ),
    }

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # 具体数据源实例标识，例如业务知识网络 ID、数据库实例 ID 等
    datasource_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # 原代码中列名为 metadata，这里保持列名不变，Python 属性避免与保留名冲突
    extra_metadata: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)
    segmented_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class MemoryChunkRecord(Base):
    """
    记忆分块表，承载向量信息。

    - embedding_json 以 JSON 字符串形式存储向量；
    - keyword_score_hint 预留给关键词检索的简单评分。
    """

    __tablename__ = "t_memory_chunks"
    __table_args__ = {
        "comment": (
            "记忆向量分块表：与文档一对一或按块切片；embedding_json 存向量 JSON；"
            "keyword_score_hint 预留关键词评分；按 user_id 与 document_id 关联检索。"
        ),
    }

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    datasource_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_score_hint: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

