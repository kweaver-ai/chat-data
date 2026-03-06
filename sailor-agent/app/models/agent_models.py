from enum import Enum

from pydantic import BaseModel

from app.models.config_models import SystemConfigResponse


class agent_input(BaseModel):
    pass


class agent_output(BaseModel):
    pass


class LogsPrefix(Enum):
    AfSailor = "logs-af-sailor-"
    Chat2Plot = "logs-chat2plot-"


# Agent List Models
class AFAgentListReqBody(BaseModel):
    name: str = ""
    list_flag: int = 0
    size: int = 10
    pagination_marker_str: str = ""
    category_ids: list[str] = None


class AgentItem(BaseModel):
    id: str = ""
    key: str = ""
    is_built_in: int = 0
    is_system_agent: int = 0
    name: str = ""
    profile: str = ""
    version: str = ""
    avatar_type: int = 0
    avatar: str = ""
    published_at: int = 0
    published_by: str = ""
    published_by_name: str = ""
    publish_info: dict = {}
    business_domain_id: str = ""
    list_status: str = ""
    af_agent_id: str = ""


class AFAgentListResp(BaseModel):
    entries: list[AgentItem] = []
    pagination_marker_str: str = ""
    is_last_page: bool = False


# Put On Agent Models
class AgentListItem(BaseModel):
    agent_key: str


class PutOnAFAgentReqBody(BaseModel):
    agent_list: list[AgentListItem]


class PutOnAFAgentResp(BaseModel):
    res: dict = {"status": "success"}


# Pull Off Agent Models
class PullOffAFAgentReqBody(BaseModel):
    af_agent_id: str


class UpdateCategoryAFAgentReqBody(BaseModel):
    category_ids: list[str]


class PullOffAFAgentResp(BaseModel):
    res: dict = {"status": "success"}


class AgentDetailCategoryResp(BaseModel):
    entries: list[SystemConfigResponse] = []
