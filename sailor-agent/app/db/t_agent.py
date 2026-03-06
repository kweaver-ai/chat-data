from sqlalchemy import Column, String, Integer, DateTime
from app.db.base import Base


class TAgent(Base):
    __tablename__ = 't_agent'
    agent_id = Column(Integer, nullable=False, comment="af 智能体id")
    id = Column(String, primary_key=True, nullable=False, comment="智能体id")
    adp_agent_key = Column(String, nullable=False, comment="adp 智能体key")
    category_ids = Column(String(180), nullable=True, comment="分类ID列表，逗号分隔")
    deleted_at = Column(Integer, nullable=False, comment="删除时间")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)