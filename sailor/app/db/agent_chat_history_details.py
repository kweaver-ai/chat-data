from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.mysql import TEXT
from app.db.base import Base


class AgentChatHistoryDetails(Base):
    __tablename__ = 'agent_chat_history_details'
    # __table_args__ = {
    #     'mysql_charset': 'utf8'
    # }
    chat_history_details_id = Column(Integer, primary_key=True, nullable=False, comment="历史id,雪花")
    id = Column(String, nullable=False, comment="uuid")
    session_id = Column(String, nullable=False, comment="session_id")
    query = Column(String, nullable=False, comment="用户问题")
    answer = Column(TEXT, nullable=False, comment="机器人答案")
    like_status = Column(String, nullable=False, comment="点赞状态")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")
    deleted_at = Column(Integer, nullable=False, comment="删除时间")