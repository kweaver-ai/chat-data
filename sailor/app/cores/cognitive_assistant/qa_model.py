from typing import List, Dict, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class AFDataServiceParameterModel(BaseModel):
    name: str = Field(..., description="参数名称", example="id")
    type: str = Field(..., description="参数类型", example="int")
    required: str = Field(..., description="参数是否必填", example="yes", choices=["yes", "no"])
    default: str = Field(..., description="参数默认值", example="这是一个默认值")
    operator: str = Field(..., description="参数操作符", example="=")
    description: str = Field(..., description="参数描述", example="这是一个参数的描述")


class AFDataServiceInfoModel(BaseModel):
    name: str = Field(..., description="AF数据服务接口的名称", example="BI探查所示")
    code: str = Field(..., description="AF数据服务接口服务的唯一编码", example="1234567")
    path: str = Field(..., description="AF数据服务接口的URL", example="http://10.4.113.103/BItcss")
    type: str = Field(..., description="AF数据服务接口的URl类型", example="post")
    description: str = Field(..., description="AF数据服务接口的描述", example="这是个用于数据探查接口。")
    parameters: List[AFDataServiceParameterModel] = Field(..., description="AF数据接口服务参数列表")


# props_dict改名为cites——dict, 因为和cite数据结构一样， 差别在于前者是dict，后者而是list
class CognitiveSearchResponseModel(BaseModel):
    props: dict = Field(..., description="AF数据资产")
    props_cn: dict = Field(..., description="AF数据资产：中文")
    cites: list = Field(..., description="以特殊的格式保持所有数据资源目录和接口服务，返回给前端")
    cites_dict: dict = Field(..., description="以字典的形式保持所有数据资源目录和接口服务，后续利用")
    svc_dict: dict = Field(..., description="以字典的形式存储所有的接口服务，后续利用")
    catalog_text2sql: list = Field(..., description="为Text2SQL提供的数据目录")
    view_text2sql: list = Field(..., description="为Text2SQL提供的逻辑视图")
    explanation: list = Field(..., description="存储分析问答型搜索的话术")
    # 含义：select_interface = response[0].get("explanation_service").get("explanation_params")
    select_interface: Union[List, Dict] = Field(..., description="存储分析问答型搜索的可用接口和调用参数，解析自大模型返回话术")
    related_info: list = Field(..., description="扩展元数据， 目前包括部门职责数据（单位-职责-信息系统）")


class AfEdition(object):
    CATALOG: str = "catalog"
    RESOURCE: str = "resource"
    BASE: str = "base"


class ResourceMode(object):
    catalog: str = "数据目录"
    interface: str = "接口服务"
    dataview: str = "逻辑视图"
    indicator: str = "指标分析"


# 需要和 af_agent 保持一致
class QueryIntentionName(Enum):
    INTENTION_GENERIC_DEMAND = "宽泛的需求"
    INTENTION_SPECIFIC_DEMAND = "明确指向的需求"
    INTENTION_OUT_OF_SCOPE = "不在支持范围内"
    INTENTION_UNKNOWN = "未知意图"  # 用作容错，默认意图、未知意图

# 和 af-sailor-agent 中 DataMartQAModel 相比， 少部分字段，多了一个参数 query_intent
class QAParamsModel(BaseModel):
    # 用户信息
    subject_id: str  # 用户id
    subject_type: str  # 用户类型
    roles: Union[List, None] = []  # 用户角色
    # AnyDATA and AnyFabric information
    ad_appid: str  # ad appid
    af_editions: str  # af版本：目录版、资源版

    # Question and resource information
    query: str  # 用户搜索词

    limit: Optional[int] = 5  # 返回结果数量
    stopwords: List = []  # 停止词
    stop_entities: Union[List, None] = []  # 停止实体
    filter: Union[Dict, None] = None  # 筛选项

    kg_id: int  # 认知搜索图谱id
    entity2service: Union[Dict, None] = None  # 图分析实体权重
    required_resource: Union[Dict, None] = None  # 停止词和同义词词库id
    available_option: int = 0  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0

    if_display_graph: Union[bool, None] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户query识别出的意图分类标签

    # 以上是认知搜索参数，以下是问答特有的参数
    stream: Optional[bool] = True  # 是否流式返回
    resources: Union[List, None] = []  # 指定资源问答中的指定资源
    # session_id: str = Field(..., description="会话id")
    # token: str = Field(..., description="会话token")
    direct_qa: Union[bool, None] = False  # 是否直接问答，默认False
    # configs: Union[Dict, None] = None  # af cognitive assistant agent 配置， 在mariadb数据库中

# 和 QAParamsModel 相比， 少了 app_id
class QAParamsModelDIP(BaseModel):
    # 用户信息
    subject_id: Optional[str] = None  # 用户id
    subject_type: Optional[str] = None  # 用户类型
    roles: Union[List, None] = []  # 用户角色
    # AnyFabric information
    af_editions: Optional[str] = None  # af版本：目录版、资源版

    # Question and resource information
    query: str  # 用户搜索词

    limit: Optional[int] = 5  # 返回结果数量
    stopwords: List = []  # 停止词
    stop_entities: Union[List, None] = []  # 停止实体
    filter: Union[Dict, None] = None  # 筛选项

    kg_id: Optional[str] = None  # 认知搜索知识网络id
    entity2service: Union[Dict, None] = None  # 图分析实体权重
    required_resource: Union[Dict, None] = None  # 停止词和同义词词库id
    available_option: int = 0  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0

    if_display_graph: Union[bool, None] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户query识别出的意图分类标签

    # 以上是认知搜索参数，以下是问答特有的参数
    stream: Optional[bool] = True  # 是否流式返回
    resources: Union[List, None] = []  # 指定资源问答中的指定资源
    # session_id: str = Field(..., description="会话id")
    # token: str = Field(..., description="会话token")
    direct_qa: Union[bool, None] = False  # 是否直接问答，默认False
    # configs: Union[Dict, None] = None  # af cognitive assistant agent 配置， 在mariadb数据库中
