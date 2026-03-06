from sqlalchemy import Column, String, DateTime, BigInteger, Integer
from app.db.base import Base


class SystemConfig(Base):
    __tablename__ = 't_system_config'
    config_id = Column('f_id', BigInteger, primary_key=True, nullable=False, comment="配置id,雪花")
    config_key = Column('f_config_key', String(25), nullable=False, comment="配置键")
    config_value = Column('f_config_value', String(50), nullable=False, comment="配置值")
    config_group = Column('f_config_group', String(50), nullable=False, comment="配置分组")
    config_group_type = Column('f_config_group_type', Integer, nullable=False, default=0, comment="配置分组类型0问数分类")
    config_desc = Column('f_config_desc', String(255), nullable=True, comment="配置描述")
    created_at = Column('f_created_at', DateTime, nullable=False, comment="创建时间")
    updated_at = Column('f_updated_at', DateTime, nullable=False, comment="更新时间")
    deleted_at = Column('f_deleted_at', BigInteger, nullable=False, default=0, comment="删除时间")
    created_by = Column('f_created_by', String(50), nullable=True, comment="创建人")
    updated_by = Column('f_updated_by', String(50), nullable=True, comment="更新人")
