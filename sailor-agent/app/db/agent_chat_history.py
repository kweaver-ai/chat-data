from sqlalchemy import Column, String, Integer, DateTime
from app.db.base import Base


class AgentChatHistory(Base):
    __tablename__ = 'agent_chat_history'
    # __table_args__ = {
    #     'mysql_charset': 'utf8'
    # }
    chat_history_id = Column(Integer, primary_key=True, nullable=False, comment="历史id,雪花")
    id = Column(String, nullable=False, comment="uuid")
    title = Column(String, nullable=False, comment="问答标题")
    session_id = Column(String, nullable=False, comment="session_id")
    product_id = Column(String, nullable=False, comment="product_id")
    created_by_uid = Column(String, nullable=False, comment="创建者id")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")
    deleted_at = Column(Integer, nullable=False, comment="删除时间")