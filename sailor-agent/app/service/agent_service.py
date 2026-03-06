import uuid
from datetime import datetime
from typing import List

from app.models.agent_models import AgentDetailCategoryResp
from app.service.adp_service import ADPService
from app.db.t_agent import TAgent
from app.logs.logger import logger
from app.service.base_service import BaseService
from sqlalchemy import or_
from app.service.config_service import ConfigService


class AFAgentService(BaseService):
    LISTSTATUS = 1     # 列表模式

    def __init__(self):
        super().__init__()
        self.adp_service = ADPService()

    def get_agent_list(self, req, token):
        """获取智能体列表"""
        try:
            # 构建请求参数
            adp_req = {
                "name": req.name,
                "size": req.size,
                "pagination_marker_str": req.pagination_marker_str
            }

            # 获取已配置的智能体列表
            agent_list = self.get_agent_list_from_db(req.category_ids)
            if not agent_list and req.list_flag==1:
                return {
                    "entries": [],
                    "pagination_marker_str": "",
                    "is_last_page":  True
                }
            agent_keys = []
            agent_key_2_af_agent = {}
            for item in agent_list:
                agent_keys.append(item['adp_agent_key'])
                agent_key_2_af_agent[item['adp_agent_key']] = item['id']

            # 如果是列表模式，添加智能体keys
            if req.list_flag == self.LISTSTATUS:
                adp_req["agent_keys"] = agent_keys
                adp_req["ids"] = []
                adp_req["exclude_agent_keys"] = []
                adp_req["business_domain_ids"] = []

            # 调用ADP服务获取智能体列表
            adp_resp = self.adp_service.agent_list(adp_req, token)

            # 处理返回值
            entries = adp_resp.get("entries", [])
            for item in entries:
                if item.get("key") in agent_key_2_af_agent:
                    item["af_agent_id"] = agent_key_2_af_agent[item.get("key")]
                    item["list_status"] = "put-on"
                else:
                    item["list_status"] = "pull-off"

            return {
                "entries": entries,
                "pagination_marker_str": adp_resp.get("pagination_marker_str", ""),
                "is_last_page": adp_resp.get("is_last_page", True)
            }
        except Exception as e:
            logger.error(f"Get agent list failed: {str(e)}")
            return {
                "entries": [],
                "pagination_marker_str": "",
                "is_last_page": True
            }

    def put_on_agent(self, req):
        """上架智能体"""
        try:
            with self.get_session() as session:
                for item in req.agent_list:
                    # 检查是否已存在
                    existing_agent = session.query(TAgent).filter(
                        TAgent.adp_agent_key == item.agent_key,
                        TAgent.deleted_at == 0
                    ).first()

                    if not existing_agent:
                        # 创建新智能体
                        new_agent = TAgent(
                            agent_id=self._generate_agent_id(),
                            id=str(uuid.uuid4()),
                            adp_agent_key=item.agent_key,
                            deleted_at=0,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(new_agent)

                return {"res": {"status": "success"}}
        except Exception as e:
            logger.error(f"Put on agent failed: {str(e)}")
            return {"res": {"status": "error", "message": str(e)}}

    def pull_off_agent(self, req):
        """下架智能体"""
        try:
            with self.get_session() as session:
                # 软删除智能体
                agent = session.query(TAgent).filter(
                    TAgent.id == req.af_agent_id,
                    TAgent.deleted_at == 0
                ).first()

                if agent:
                    agent.deleted_at = int(datetime.now().timestamp())
                    agent.updated_at = datetime.now()

                return {"res": {"status": "success"}}
        except Exception as e:
            logger.error(f"Pull off agent failed: {str(e)}")
            return {"res": {"status": "error", "message": str(e)}}

    def get_agent_list_from_db(self,category_ids: List[str]) -> List[dict]:
        """从数据库获取智能体列表"""
        try:
            with self.get_session() as session:
                query = session.query(TAgent).filter(TAgent.deleted_at == 0)
                if category_ids and len(category_ids) > 0:
                    # 使用 or_ 连接多个条件，匹配逗号分隔的分类ID列表
                    conditions = []
                    for category_id in category_ids:
                        # 匹配以下三种情况：
                        # 1. 分类ID在开头，如 "1,2,3"
                        # 2. 分类ID在中间，如 "2,1,3"
                        # 3. 分类ID在结尾，如 "2,3,1"
                        conditions.append(TAgent.category_ids == category_id)
                        conditions.append(TAgent.category_ids.like(f'{category_id},%'))
                        conditions.append(TAgent.category_ids.like(f'%,{category_id},%'))
                        conditions.append(TAgent.category_ids.like(f'%,{category_id}'))
                    query = query.filter(or_(*conditions))
                agents = query.all()
                # 将ORM对象转换为字典，避免会话关闭后访问属性时出现问题
                return [{
                    'adp_agent_key': agent.adp_agent_key,
                    'id': agent.id
                } for agent in agents]
        except Exception as e:
            logger.error(f"Get agent list from db failed: {str(e)}")
            return []

    def _generate_agent_id(self):
        """生成智能体ID"""
        # 简单实现，实际项目中可能需要使用雪花算法
        return int(datetime.now().timestamp() * 1000)

    def update_category(self, id: str,category_ids: List[str]):
        """更新智能体分类"""
        try:
            with self.get_session() as session:
                # 查找智能体
                agent = session.query(TAgent).filter(
                    TAgent.id == id,
                    TAgent.deleted_at == 0
                ).first()

                if agent:
                    # 将分类ID列表转换为逗号分隔的字符串
                    category_ids_str = ','.join(category_ids) if category_ids else None
                    # 更新智能体分类和更新时间
                    agent.category_ids = category_ids_str
                    agent.updated_at = datetime.now()
                    self.update_and_commit(agent)

                return {"res": {"status": "success"}}
        except Exception as e:
            logger.error(f"Update agent category failed: {str(e)}")
            return {"res": {"status": "error", "message": str(e)}}
    
    def get_agent_category_detail(self, id: str, token: str) -> AgentDetailCategoryResp:
        """根据id获取智能体分类详情"""

        try:
            with self.get_session() as session:
                # 查找智能体
                agent = session.query(TAgent).filter(
                    TAgent.id == id,
                    TAgent.deleted_at == 0
                ).first()

                if agent:
                    # 初始化ConfigService
                    config_service = ConfigService()
                    # 解析分类ID列表
                    category_ids_str = agent.category_ids
                    category_ids = []
                    if category_ids_str:
                        category_ids = [cid.strip() for cid in category_ids_str.split(',') if cid.strip()]
                    
                    # 获取对应的系统配置（使用批量查询方法）
                    config_responses = []
                    if category_ids:
                        # 将字符串转换为整数
                        category_ids_int = [int(cid) for cid in category_ids]
                        # 调用批量查询方法
                        config_responses = config_service.get_configs_by_ids(category_ids_int)
                    
                    # 返回AgentDetailCategoryResp对象
                    return AgentDetailCategoryResp(entries=config_responses)
                
                # 如果智能体不存在，返回空列表
                return AgentDetailCategoryResp(entries=[])
        except Exception as e:
            logger.error(f"Get agent category detail failed: {str(e)}")
            return AgentDetailCategoryResp(entries=[])
