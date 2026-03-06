# -*- coding: utf-8 -*-
from app.db.system_config import SystemConfig
from app.models.config_models import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse, SystemConfigListResponse, GroupedSystemConfigResponse
from datetime import datetime
from app.service.base_service import BaseService
from app.utils.id_generator import generate_snowflake_id


class ConfigService(BaseService):
    """配置服务类，继承自基础服务类，使用统一的session管理"""

    def create_config(self, config_data: SystemConfigCreate) -> SystemConfigResponse:
        """创建配置"""
        config = SystemConfig(
            config_id=generate_snowflake_id(),
            config_key=config_data.config_key,
            config_value=config_data.config_value,
            config_group=config_data.config_group,
            config_group_type=config_data.config_group_type,
            config_desc=config_data.config_desc,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=0,
            created_by=config_data.created_by,
            updated_by=config_data.updated_by
        )
        created_config = self.add_and_commit(config)
        return SystemConfigResponse(
            config_id=str(created_config.config_id),
            config_key=created_config.config_key,
            config_value=created_config.config_value,
            config_group=created_config.config_group,
            config_group_type=created_config.config_group_type,
            config_desc=created_config.config_desc,
            created_at=created_config.created_at.isoformat() if created_config.created_at else None,
            updated_at=created_config.updated_at.isoformat() if created_config.updated_at else None,
            deleted_at=int(created_config.deleted_at),
            created_by=created_config.created_by,
            updated_by=created_config.updated_by
        )

    def get_config_by_key(self, config_key: str) -> SystemConfigResponse:
        """根据配置键获取配置"""
        with self.get_session() as session:
            config = session.query(SystemConfig).filter(
                SystemConfig.config_key == config_key,
                SystemConfig.deleted_at == 0
            ).first()
            if config:
                return SystemConfigResponse(
                    config_id=str(config.config_id),
                    config_key=config.config_key,
                    config_value=config.config_value,
                    config_group=config.config_group,
                    config_group_type=config.config_group_type,
                    config_desc=config.config_desc,
                    created_at=config.created_at.isoformat() if config.created_at else None,
                    updated_at=config.updated_at.isoformat() if config.updated_at else None,
                    deleted_at=int(config.deleted_at),
                    created_by=config.created_by,
                    updated_by=config.updated_by
                )
            return None

    def get_config_by_id(self, config_id: int) -> SystemConfigResponse:
        """根据配置id获取配置"""
        with self.get_session() as session:
            config = session.query(SystemConfig).filter(
                SystemConfig.config_id == config_id,
                SystemConfig.deleted_at == 0
            ).first()
            if config:
                return SystemConfigResponse(
                    config_id=str(config.config_id),
                    config_key=config.config_key,
                    config_value=config.config_value,
                    config_group=config.config_group,
                    config_group_type=config.config_group_type,
                    config_desc=config.config_desc,
                    created_at=config.created_at.isoformat() if config.created_at else None,
                    updated_at=config.updated_at.isoformat() if config.updated_at else None,
                    deleted_at=int(config.deleted_at),
                    created_by=config.created_by,
                    updated_by=config.updated_by
                )
            return None
    
    def get_configs_by_ids(self, config_ids: list[int]) -> list[SystemConfigResponse]:
        """根据配置id列表批量获取配置"""
        with self.get_session() as session:
            configs = session.query(SystemConfig).filter(
                SystemConfig.config_id.in_(config_ids),
                SystemConfig.deleted_at == 0
            ).all()
            
            config_responses = []
            for config in configs:
                config_response = SystemConfigResponse(
                    config_id=str(config.config_id),
                    config_key=config.config_key,
                    config_value=config.config_value,
                    config_group=config.config_group,
                    config_group_type=config.config_group_type,
                    config_desc=config.config_desc,
                    created_at=config.created_at.isoformat() if config.created_at else None,
                    updated_at=config.updated_at.isoformat() if config.updated_at else None,
                    deleted_at=int(config.deleted_at),
                    created_by=config.created_by,
                    updated_by=config.updated_by
                )
                config_responses.append(config_response)
            
            return config_responses

    def list_configs(self, config_key: str = None, config_group: str = None, config_group_type: int = None, size: int = 10, pagination_marker_str: str = None) -> SystemConfigListResponse:
        """获取配置列表"""
        # 构建基础查询
        with self.get_session() as session:
            query = session.query(SystemConfig).filter(SystemConfig.deleted_at == 0)

            if config_key:
                query = query.filter(SystemConfig.config_key.like(f"%{config_key}%"))
            if config_group:
                query = query.filter(SystemConfig.config_group == config_group)
            if config_group_type is not None:
                query = query.filter(SystemConfig.config_group_type == config_group_type)

            # 使用通用分页方法
            pagination_result = self.paginate_query(
                query=query,
                page_size=size,
                pagination_marker=pagination_marker_str,
                order_by_field=SystemConfig.config_id
            )
            
            # Convert SQLAlchemy models to SystemConfigResponse objects
            config_responses = []
            for config in pagination_result["entries"]:
                config_response = SystemConfigResponse(
                    config_id=str(config.config_id),
                    config_key=config.config_key,
                    config_value=config.config_value,
                    config_group=config.config_group,
                    config_group_type=config.config_group_type,
                    config_desc=config.config_desc,
                    created_at=config.created_at.isoformat() if config.created_at else None,
                    updated_at=config.updated_at.isoformat() if config.updated_at else None,
                    deleted_at=int(config.deleted_at),
                    created_by=config.created_by,
                    updated_by=config.updated_by
                )
                config_responses.append(config_response)
            
            return SystemConfigListResponse(
                entries=config_responses,
                pagination_marker_str=pagination_result["pagination_marker_str"],
                is_last_page=pagination_result["is_last_page"]
            )

    def update_config(self, config_id: int, config_data: SystemConfigUpdate) -> SystemConfigResponse:
        """更新配置"""
        with self.get_session() as session:
            config = session.query(SystemConfig).filter(
                SystemConfig.config_id == config_id,
                SystemConfig.deleted_at == 0
            ).first()
            if not config:
                return None

            update_data = config_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(config, field, value)
            config.updated_at = datetime.now()

            updated_config = self.merge_and_commit(config)
            return SystemConfigResponse(
                config_id=str(updated_config.config_id),
                config_key=updated_config.config_key,
                config_value=updated_config.config_value,
                config_group=updated_config.config_group,
                config_group_type=updated_config.config_group_type,
                config_desc=updated_config.config_desc,
                created_at=updated_config.created_at.isoformat() if updated_config.created_at else None,
                updated_at=updated_config.updated_at.isoformat() if updated_config.updated_at else None,
                deleted_at=int(updated_config.deleted_at),
                created_by=updated_config.created_by,
                updated_by=updated_config.updated_by
            )

    def delete_config(self, config_id: int, updated_by: str) -> bool:
        """删除配置（软删除）"""
        with self.get_session() as session:
            config = session.query(SystemConfig).filter(
                SystemConfig.config_id == config_id,
                SystemConfig.deleted_at == 0
            ).first()
            if not config:
                return False

            config.deleted_at = int(datetime.now().timestamp())
            config.updated_by = updated_by
            config.updated_at = datetime.now()

            self.merge_and_commit(config, refresh=False)
            return True

    def get_grouped_configs(self,config_group_type:int) -> GroupedSystemConfigResponse:
        """获取分组的配置列表，用于前端展示"""
        with self.get_session() as session:
            query = session.query(SystemConfig).filter(SystemConfig.deleted_at == 0,
                                                       SystemConfig.config_group_type==config_group_type)
            configs = query.all()
            
            # 动态按配置分组组织数据
            grouped_configs = {}
            
            for config in configs:
                if config.config_group not in grouped_configs:
                    grouped_configs[config.config_group] = []
                # Convert SQLAlchemy model to SystemConfigResponse object
                config_response = SystemConfigResponse(
                    config_id=str(config.config_id),
                    config_key=config.config_key,
                    config_value=config.config_value,
                    config_group=config.config_group,
                    config_group_type=config.config_group_type,
                    config_desc=config.config_desc,
                    created_at=config.created_at.isoformat() if config.created_at else None,
                    updated_at=config.updated_at.isoformat() if config.updated_at else None,
                    deleted_at=int(config.deleted_at),
                    created_by=config.created_by,
                    updated_by=config.updated_by
                )
                grouped_configs[config.config_group].append(config_response)
            
            return GroupedSystemConfigResponse(data=grouped_configs)
