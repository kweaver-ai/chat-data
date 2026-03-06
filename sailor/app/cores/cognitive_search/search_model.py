from dataclasses import dataclass

# import ahocorasick
from pydantic import BaseModel, Field
from typing import Union, Optional, List, Dict, Any
from enum import Enum

from app.cores.cognitive_assistant.qa_model import QueryIntentionName

# EMPTY_RESULT = ({}, "000", "000")
# 分析问答型搜索的空结果, 前3个字段是 res, res_status, explanation_status
# 最后增加一个返回字段， related_info
ANALYSIS_SEARCH_EMPTY_RESULT = ({}, "000", "000", [])
EMPTY_RESULT_LLM_INVOKE_PLUS_RELATED_INFO = ([], [], [], '', [], {})
EMPTY_RESULT_LLM_INVOKE = ([], [], [], '', {})

DEFAULT_FILTER ={
  "online_status": [
    -1
  ],
  "asset_type": [
    -1
  ],
  "data_kind": "0",
  "department_id": [
    -1
  ],
  "end_time": "1800122122",
  "info_system_id": [
    -1
  ],
  "owner_id": [
    -1
  ],
  "publish_status_category": [
    -1
  ],
  "shared_type": [
    -1
  ],
  "start_time": "1600122122",
  "stop_entity_infos": [ ],
  "subject_id": [
    -1
  ],
  "update_cycle": [
    -1
  ]
}

DEAFULT_REQUIRED_RESOURCE = {
            "lexicon_actrie": {
                "lexicon_id": "68"
            },
            "stopwords": {
                "lexicon_id": "69"
            }
        }

# 临时
ALL_ROLES = [
            "normal",
            "data-owner",
            "data-butler",
            "data-development-engineer",
            "tc-system-mgm"
        ]

# 搜索列表的入参数据结构
class AssetSearchParams(BaseModel):
    query: str
    limit: Optional[int] = 5
    stopwords: List
    stop_entities: Optional[List] = None
    filter: Optional[Dict] = None
    ad_appid: str
    kg_id: int
    available_option: Optional[int] = 0
    entity2service: Optional[Dict] = {}
    required_resource: Optional[Dict] = None
    subject_id: Optional[str] = None
    subject_type: Optional[str] = None
    roles: Optional[List] = None
    af_editions: Optional[str] = None

class AssetSearchParamsDIP(BaseModel):
    subject_id: Optional[str] = None  # 用户id
    subject_type: Optional[str] = None  # 用户类型
    af_editions: Optional[str] = None  # af版本：目录版、资源版
    query: str
    limit: Optional[int] = 10
    stopwords: Optional[List] = None
    stop_entities: Optional[List] = None
    filter: Optional[Dict] = None
    kg_id: Optional[str] = None
    entity2service: Optional[Dict] = {}  # 图分析实体权重
    required_resource: Optional[Dict] = None  # 停止词和同义词词库id
    available_option: Optional[int] = 2  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
    roles: Optional[List] = None  # 用户角色
    if_display_graph: Optional[bool] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户qu


# 分析问答型搜索中 search_params 参数的结构
class AnalysisSearchParams(BaseModel):
    subject_id: Optional[str] = None  # 用户id
    subject_type: Optional[str] = None  # 用户类型
    af_editions: Optional[str] = None  # af版本：目录版、资源版
    query: str  # 用户query
    limit: Optional[int] = 5  # 返回结果数量上限
    stopwords: List  # 停止词
    stop_entities: Optional[List] = None  # 停止实体
    filter: Optional[Dict] = None  # 筛选项， 分析问答型搜索暂不支持筛选项， 保留字段
    ad_appid: str  # ad appid
    kg_id: int  # 认知搜索图谱id
    entity2service: Optional[Dict] = None  # 图分析实体权重
    required_resource: Optional[Dict] = None  # 停止词和同义词词库id
    available_option: Optional[int] = 2  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
    roles: Optional[List] = None  # 用户角色
    if_display_graph: Optional[bool] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户query识别出的意图分类标签
    # query_seg_list: Optional[List] = None  # 用户query分词列表

    # 以上是认知搜索参数，以下是问答特有的参数
    # stream: Optional[bool] = True  # 是否流式返回
    # resources: Union[List, None] = []  # 指定资源问答中的指定资源
    # session_id: str = Field(..., description="会话id")
    # token: str = Field(..., description="会话token")
    # direct_qa: Union[bool, None] = False  # 是否直接问答，默认False
    # configs: Union[Dict, None] = None  # af cognitive assistant agent 配置， 在mariadb数据库中

class AnalysisSearchParamsDIP(BaseModel):
    subject_id: Optional[str] = None  # 用户id
    subject_type: Optional[str] = None  # 用户类型
    af_editions: Optional[str] = None  # af版本：目录版、资源版
    query: str  # 用户query
    limit: Optional[int] = 10  # 返回结果数量上限
    stopwords: Optional[List] = None  # 停止词
    stop_entities: Optional[List] = None # 停止实体
    filter: Optional[Dict] = None  # 筛选项， 分析问答型搜索暂不支持筛选项， 保留字段
    kg_id: Optional[str] = None  # 认知搜索知识网络id
    entity2service: Optional[Dict] = {}  # 图分析实体权重
    required_resource: Optional[Dict] = None  # 停止词和同义词词库id
    available_option: Optional[int] = 2  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
    roles: Optional[List] = None  # 用户角色
    if_display_graph: Optional[bool] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户query识别出的意图分类标签

class AnalysisSearchParamsDIPOld(BaseModel):
    subject_id: Optional[str] = None  # 用户id
    subject_type: Optional[str] = None  # 用户类型
    af_editions: Optional[str] = None  # af版本：目录版、资源版
    query: str  # 用户query
    limit: Optional[int] = 5  # 返回结果数量上限
    stopwords: List  # 停止词
    stop_entities: Optional[List] = None  # 停止实体
    filter: Optional[Dict] = None  # 筛选项， 分析问答型搜索暂不支持筛选项， 保留字段
    kg_id: int  # 认知搜索图谱id
    entity2service: Optional[Dict] = None  # 图分析实体权重
    required_resource: Optional[Dict] = None  # 停止词和同义词词库id
    available_option: Optional[int] = 2  # 0（忽略权限，不校验不返回），1（都返回，有字段表示是否有权限），2（只返回有权限的） 认知搜索场景默认为0
    roles: Optional[List] = None  # 用户角色
    if_display_graph: Optional[bool] = False  # 是否显示图谱, 首页智能问数需要显示, 标品不需要
    query_intent: Union[str, None] = QueryIntentionName.INTENTION_UNKNOWN.value  # agent根据用户query识别出的意图分类标签

# 基于历史问答对的知识增强，从历史问答对知识图谱中查询出与用户 query 相关的问答对， 辅助找数问答
# class konwledge_Params(BaseModel):
# class FindHistoryQAParams(BaseModel):
class RetrieverHistoryQAParams(BaseModel):
    query: str
    vec_knn_k_history_qa: Optional[int] = 10
    ad_appid: str
    kg_id_history_qa: str

# class DataSearchModel(BaseModel):
#     """
#     AD图谱信息相关参数
#     """
#     # AnyDATA and AnyFabric information
#     ad_appid: str = Field(..., description="AnyDATA appid")
#     af_editions: str = Field(..., description="AnyFabric version", examples=["catalog", "resource"])

#
#     kg_id: int = Field(..., description="Knowledge graph ID")
#     limit: Optional[int] = Field(default=4, description="Maximum number of search results")
#     stopwords: List = Field(..., description="Stop words")
#     stop_entities: Union[List, None] = Field(..., description="Stop entities")
#     filter: Union[Dict, None] = Field(..., description="Filter conditions")
#     entity2service: Union[Dict, None] = Field(..., description="Cognitive search parameters")
#     required_resource: Union[Dict, None] = Field(..., description="Cognitive search parameters")
#     available_option: int = Field(2, description="Cognitive search parameters", examples=[0, 1, 2])


# 认知搜索中 graph_params 参数
# class graphSearchModel(BaseModel):
class GraphFilterParamsModel(BaseModel):
    """
    图谱查询所需参数,搜索筛选项
    """
    update_cycle: Union[List, None] = Field(default=[-1], description="更新周期")
    shared_type: Union[List, None] = Field(default=[-1], description="共享属性")
    start_time: Union[str, None] = Field(default=0, description="开始时间")
    end_time: Union[str, None] = Field(default=0, description="结束时间")
    asset_type: Union[List, None] = Field(default=[-1], description="资产类型")
    department_id: Union[List, None] = Field(default=[-1], description="部门ID")
    owner_id: Union[List, None] = Field(default=[-1], description="Owner ID")
    info_system: Union[List, None] = Field(default=[-1], description="信息系统id")
    subject_id: Union[List, None] = Field(default=[-1], description="主题id")
    online_status: Union[List, None] = Field(default=[-1], description="在线状态")
    publish_status: Union[List, None] = Field(default=[-1], description="发布状态")
    cate_node_id: Union[List, str, None] = Field(default=[-1], description="分类节点ID")
    resource_type: Union[List, str, None] = Field(default=[-1], description="挂接资源类型")

# 未使用
class DataTypes(Enum):
    """
    Data types
    """
    catalog = "1"  # 目录
    api = "2"  # 接口服务
    view = "3"  # 逻辑视图
    metric = "4"  # 指标


# 认知搜索中 data_params 参数，包含空间名称、实体类型与名称映射等信息的字典
class DataParamsModel(BaseModel):
    entity_rank: dict  # 实体排序权重
    result_types: str  # 返回结果类型， 即中间实体的类型，比如 "resource"
    entity_limit: int  # 实体数量限制, 1000
    entity2service: dict  # 实体到和中心实体的关系以及排序权重
    actrie: Any
    stopwords: List[str]  # 停用词列表
    dropped_words: List[str]  # 被停用词替换后的单词列表?
    entity_types_not_search: List[str]  # 不搜索的实体类型列表
    type2names: dict  # 实体类型到实体名称的映射，# type2names 字典 是前端传来的停用实体,现在已经废弃
    # data_params['type2names'] = {x['class_name']: x['names'] for x in stop_entity_infos}
    indextag2tag: dict  # 实体类型有大写时 转小写
    space_name: str  # 图谱空间名称
    weights_group: list  # 权重组列表

# weights_group
# [
#         [
#             2,
#             [
#                 [
#                     "resource",
#                     2
#                 ]
#             ]
#         ],
#         [
#             1,
#             [
#                 [
#                     "dataowner",
#                     1
#                 ],
#                 [
#                     "datasource",
#                     1
#                 ],
#                 [
#                     "department",
#                     1
#                 ],
#                 [
#                     "info_system",
#                     1
#                 ],
#                 [
#                     "metadataschema",
#                     1
#                 ],
#                 [
#                     "data_explore_report",
#                     1
#                 ],
#                 [
#                     "response_field",
#                     1
#                 ],
#                 [
#                     "field",
#                     1
#                 ],
#                 [
#                     "subdomain",
#                     1
#                 ],
#                 [
#                     "domain",
#                     1
#                 ]
#             ]
#         ],
#         [
#             0,
#             [
#                 [
#                     "dimension_model",
#                     0
#                 ],
#                 [
#                     "indicator_analysis_dimension",
#                     0
#                 ]
#             ]
#         ]
#     ]
# entity_types是dict，实体类型与本体信息的字典
# 每个实体类型是一个dict，包含以下字段：
class EntityType(BaseModel):
    entity_id: str  # 实体类型ID
    name: str  # 实体类型英文名称
    description: str  # 实体类型中文描述
    alias: str  # 实体类型中文别名
    synonym: list  # 实体类型中文同义词列表
    default_tag: str  # 实体类型默认属性
    properties_index: list  # 构建了索引的实体属性列表
    vector_generation: list  # 构建了向量索引的实体属性列表
    primary_key: list  # 实体类型的融合属性列表，主键列表
    properties: list  # 实体属性列表
    search_prop: str  # 搜索属性
    x: float
    y: float
    icon: str
    shape: str
    size: str
    fill_color: str
    stroke_color: str
    text_color: str
    text_position: str
    text_width: str
    index_default_switch: str
    text_type: str
    source_type: str
    model: str
    task_id: str
    icon_color: str
    colour: str


class ResourceEntityTypesModel(BaseModel):
    """
    实体类型集合
    """
    resource: EntityType
    info_system: EntityType
    dimension_model: EntityType
    indicator_analysis_dimension: EntityType
    response_field: EntityType
    field: EntityType
    datasource: EntityType
    metadataschema: EntityType
    dataowner: EntityType
    department: EntityType


# 数据资源搜索结果， 如果 有关联搜索， 返回结果是 nebula 中的数据结构， 如果没有关联搜索， 则返回结果是 opensearch 中的数据结构，
# 因为现在分析问答型搜索，拿到搜索结果后的后续处理，都是按照 opensearch 中的数据结构来做的， 所以加了关联搜索以后，
# 需要把nebula数据结构的结果转成opensearch的数据结构

# 数据模型前缀Graph代表是nebula中的数据结构， 数据结构前缀ES代表是opensearch中的数据结构


class GraphPropertyProp(BaseModel):
    """属性字段"""
    name: str = Field(
        ...,
        description="属性字段英文名称",
        examples=["description"]
    )
    value: str = Field(
        ...,
        description="属性字段值",
        examples=["该表记录了..."]
    )
    alias: str = Field(
        ...,
        description="属性字段显示名称",
        examples=["数据资源描述"]
    )
    type: str = Field(
        ...,
        description="属性字段数据类型",
        examples=["string"]
    )
    disabled: bool
    checked: bool

class GraphProperty(BaseModel):
    """实体的所有属性字段"""
    tag: str = Field(
        ...,
        description="实体类nebula标签",
        examples=["resource"]
    )
    props: List[GraphPropertyProp]

class GraphDefaultProperty(BaseModel):
    """默认属性（显示属性）"""
    name: str = Field(
        ...,
        description="默认属性（显示属性）英文名称",
        examples=["resourcename"]
    )
    value: str = Field(
        ...,
        description="默认属性（显示属性）值",
        examples=["记录表"]
    )
    alias: str = Field(
        ...,
        description="默认属性（显示属性）显示名称",
        examples=["数据资源名称"]
    )

class GraphEntityDetail(BaseModel):
    """实体详情"""
    id: str = Field(
        ...,
        description="实体类id",
        examples=["243eee332fe8192734872297af616037"]
    )
    alias: str =  Field(
        ...,
        description="实体类显示名称",
        examples=["数据资源"]
    )
    color: str = Field(
        ...,
        description="实体类显示颜色",
        examples=["rgba(89,163,255,1)"]
    )
    class_name: str = Field(
        ...,
        description="实体类英文名称",
        examples=["resource"]
    )
    icon: str = Field(
        ...,
        description="实体类图标",
        examples=["graph-layer"]
    )
    default_property: GraphDefaultProperty # 实体的默认属性字段
    tags: List[str] = Field(
        ...,
        description="实体类nebula标签",
        examples=[["resource"]]
    )
    properties: List[GraphProperty] # 实体的所有属性字段
    score: float = Field(
        ...,
        description="排序分数",
        examples=[5.8952832]
    )
    key: List[str] = Field(
        ...,
        description="命中分词列表"

    )

class GraphHitInfo(BaseModel):
    """命中的起点实体信息"""
    prop: str = Field(
        ...,
        description="命中的实体类英文名称",
        examples=["department"]
    )
    value: str = Field(
        ...,
        description="命中的实体值",
    )
    keys: List[str] = Field(
        ...,
        description="命中的关键词列表",
    )
    alias: str = Field(
        ...,
        description="命中的实体类显示名称",
        examples=["部门"]
    )

class GraphStartItem(BaseModel):
    """起始实体以及相关信息"""
    relation: str = Field(
        ...,
        description="起始实体类与数据资源类或数据目录类的关系类名称",
        examples=["包含"]
    )
    class_name: str = Field(
        ...,
        description="起始实体类名称",
        examples=["resource"]
    )
    name: str = Field(
        ...,
        description="起始实体名称",
        examples=["记录表"]
    )
    hit: GraphHitInfo = Field(
        ...,
        description="起始实体命中信息",
    )
    alias: str = Field(
        ...,
        description="起始实体类显示名称",
        examples=["数据资源"]
    )

# 如果有关联搜索（图分析服务），搜索结果 output 返回的数据结构是 GraphHitEntity 的列表
class GraphHitEntity(BaseModel):
    """命中实体信息"""
    starts: List[GraphStartItem]
    entity: GraphEntityDetail
    is_permission: str
    score: int   # 输出结果看起来是 int?

class Subgraph(BaseModel):
    """命中的图谱子图信息-单个子图"""
    starts: List[str] = Field(
        ...,
        description="路径起始实体类id列表",
        examples=[[
                    "243eee332fe8192734872297af616037",
                    "553556d1f35bec7a26e7f923905c37c9",
                    "0454a57e666c9adcbce8fc0e5a37661d"
                ]]
    )
    end: str = Field(
        ...,
        description="路径终点实体类id",
        examples=["243eee332fe8192734872297af616037"]
    )

class QueryCut(BaseModel):
    """分词信息-单个分词"""
    source: str = Field(
        ...,
        description="query分词",
        examples=["总公司"]
    )
    synonym: List[str] = Field(
        ...,
        description="source对应的同义词",
        examples=[["总机构"]]
    )
    is_stopword: bool = Field(
        ...,
        description="source是否为停用词",
        examples=[False]
    )

# 数据目录原始数据的结构
class ESHitModelDataCatalog(BaseModel):
    datacatalogid: Optional[str] = Field(default="", description="数据资源目录ID")
    datacatalogname: Optional[str] = Field(default="", description="数据资源目录名称")
    description_name: Optional[str] = Field(default="", description="数据资源目录描述")
    asset_type: Optional[int] = Field(default=None, description="资产类型")
    code: Optional[str] = Field(default="", description="数据资源目录编码code")
    resource_type: Optional[int] = Field(default=None, description="挂接的数据资源类型 枚举值 1：逻辑视图 2：接口 3:文件资源")
    resource_id: Optional[str] = Field(default="", description="挂接的数据资源id")
    shared_type: Optional[int] = Field(default=None, description="共享属性 1 无条件共享 2 有条件共享 3 不予共享")
    update_cycle: Optional[int] = Field(default=None, description="更新频率 参考数据字典：GXZQ，1不定时 2实时 3每日 4每周 5每月 6每季度 7每半年 8每年 9其他")
    # color: Optional[str] = Field(default="", description="颜色")
    department_id: Optional[str] = Field(default="", description="部门ID")
    department: Optional[str] = Field(default="", description="部门名称")
    department_path_id: Optional[str] = Field(default="", description="部门层级路径ID")
    department_path: Optional[str] = Field(default="", description="部门层级路径")
    info_system_id: Optional[str] = Field(default="", description="信息系统ID")
    info_system_name: Optional[str] = Field(default="", description="信息系统名称")
    subject_nodes: Optional[str] = Field(default="", description="主题nodes")
    subject_id_list: Optional[str] = Field(default="", description="主题id列表")
    customized_cate_nodes: Optional[str] = Field(default="", description="自定义类目nodes")
    customized_cate_node_id_list: Optional[str] = Field(default="", description="自定义类目node_id列表")
    ves_catalog_name: Optional[str] = Field(default="", description="数据源在虚拟化引擎中的技术名称")
    published_at: Optional[int] = Field(default=None, description="发布时间")
    publish_status: Optional[str] = Field(default="", description="发布状态 未发布unpublished 、发布审核中pub-auditing、已发布published、发布审核未通过pub-reject、变更审核中change-auditing、变更审核未通过change-reject")
    publish_status_category: Optional[str] = Field(default="", description="发布状态类别")
    online_time: Optional[int] = Field(default=None, description="上线时间")
    online_status: Optional[str] = Field(default="", description="上线状态 未上线 notline、已上线 online、已下线offline、上线审核中up-auditing、下线审核中down-auditing、上线审核未通过up-reject、下线审核未通过down-reject、已下线（上线审核中）offline-up-auditing、已下线（上线审核未通过）offline-up-reject")


class ESHitModelResource(BaseModel):
    asset_type: Optional[int] = Field(default=None, description="数据资产类型", examples=[1])
    resourceid: Optional[str] = Field(default="", description="数据资源ID", examples=["61bcf5c0-c6e7-4ac7-8017-cc41f262bdc0"])
    resourcename: Optional[str] = Field(default="",description="数据资源名称",examples=["记录表"])
    description: Optional[str] = Field(default="",description="数据资源描述",examples=["记录表"])
    code: Optional[str] = Field(default="",description="数据资源编码code",examples=["SJZYMU20251223/000628"])
    technical_name: Optional[str] = Field(default="",description="数据资源技术名称",examples=["record_table"])
    color: Optional[str] = Field(default="",description="数据资源颜色",examples=["rgba(89,163,255,1)"])
    department: Optional[str] = Field(default="", description="部门")
    department_path: Optional[str] = Field(default="", description="部门层级路径")
    department_id: Optional[str] = Field(default="", description="部门id", examples=["51dcd2b4-7763-11f0-be8e-d6ae8142d007"])
    department_path_id: Optional[str] = Field(default="", description="部门层级路径id", examples=["e5a47c14-fd9b-11ef-84a5-b261ef4a/51dcd2b4-7763-11f0-be8e-d6ae8142d007"])
    owner_id: Optional[str] = Field(default="", description="数据资源owner id", examples=["5b8b5d80-ecdf-11ef-87d1-7208ac3"])
    owner_name: Optional[str] = Field(default="", description="数据资源owner名称", examples=["user1"])
    info_system_uuid: Optional[str] = Field(default="", description="信息系统uuid", examples=["b12b44d3-135e-4590-b34a-8afbb1"])
    info_system_name: Optional[str] = Field(default="", description="信息系统名称")
    subject_id: Optional[str] = Field(default="", description="主题id")
    subject_name: Optional[str] = Field(default="", description="主题名称")
    subject_path: Optional[str] = Field(default="", description="主题路径")
    subject_path_id: Optional[str] = Field(default="", description="主题路径id")
    online_at: Optional[int] = Field(default=None, description="上线时间", examples=[1741664831])
    online_status: Optional[str] = Field(default="", description="上线状态", examples=["online"])
    publish_at: Optional[int] = Field(default=None, description="发布时间", examples=[1741664824])
    publish_status: Optional[str] = Field(default="", description="发布状态", examples=["published"])
    publish_status_category: Optional[str] = Field(default="", description="发布状态类别", examples=["published_category"])

# all_hits 都是 opensearch 的数据结构, all_hits 中存储的是 ESHitModel 的列表
class ESHitModel(BaseModel):
    _id: str  # ES中存储的id
    _score: float  # 排序分
    relation: str  # 实体类与中心点数据资源类的关系
    type: str  # 数据资源类型代码，1 数据目录，2 接口服务，3 逻辑视图，4 指标
    type_alias: str  # 数据资源类型名称，1 数据目录，2 接口服务，3 逻辑视图，4 指标
    name: str  # 数据资源名称
    service_weight: str # 排序分计算权重
    _source: Union[ESHitModelResource, ESHitModelDataCatalog]  # Opensearch中存储的原始数据


# class AnalysisSearchResult(BaseModel):
#     count: int # 命中实体数量
#     entities: Optional[List[GraphHitEntity]] = [] # 命中实体列表
#     answer: str #
#     subgraphs: Optional[List[Subgraph]] = [] # 命中的图谱子图列表
#     query_cuts: Optional[List[QueryCut]] = [] # 分词列表
#     explanation_ind: Optional[str] = "" # 指标的解释话术
#     explanation_formview: Optional[str] = "" # 逻辑视图的解释话术
#     explanation_service: Optional[Dict[str, str]] = {} # 接口服务的解释话术

# output的数据结构
class Output(BaseModel):
    count: int  # 命中实体数量
    entities: Optional[List[Any]] = []  # 命中实体列表
    answer: str  #
    subgraphs: Optional[List[Any]] = []  # 命中的图谱子图列表
    query_cuts: Optional[List[Any]] = []  # 分词列表

class AnalysisSearchResult(BaseModel):
    count: int # 命中实体数量
    entities: Optional[List[Any]] = [] # 命中实体列表
    answer: str #
    subgraphs: Optional[List[Any]] = [] # 命中的图谱子图列表
    query_cuts: Optional[List[Any]] = [] # 分词列表
    explanation_ind: Optional[str] = "" # 指标的解释话术
    explanation_formview: Optional[str] = "" # 逻辑视图的解释话术
    explanation_service: Optional[Dict[str, str]] = {} # 接口服务的解释话术

class AnalysisSearchResponseModel(BaseModel):
    res: AnalysisSearchResult
    status_res: Optional[str] = Field(
        ...,
        description="搜索结果cites是否有效 0 无效， 1 有效；三个标志位分别对应 指标、逻辑视图、接口服务",
        examples=["010"]
    )
    status_explanation: Optional[str] = Field(
        ...,
        description="解释话术是否有效 0 无效， 1 有效；三个标志位分别对应 指标、逻辑视图、接口服务",
        examples=["010"]
    )
    related_info: Optional[List] = Field(
        default=None,
        description="解释话术是否有效 0 无效， 1 有效；三个标志位分别对应 指标、逻辑视图、接口服务",
        examples=["010"]
    )

# class ResourceAssetSearchResponseData(BaseModel):
#     count: int # 命中实体数量
#     entities: Optional[List[GraphHitEntity]] = [] # 命中实体列表
#     answer: str #
#     subgraphs: Optional[List[Subgraph]] = [] # 命中的图谱子图列表
#     query_cuts: Optional[List[QueryCut]] = [] # 分词列表
#     # explanation_ind: Optional[str] = ""
#     # explanation_formview: Optional[str] = ""
#     # explanation_service: Optional[Dict[str, str]] = {}

class ResourceAssetSearchResponseData(BaseModel):
    count: int # 命中实体数量
    entities: Optional[List[Any]] = [] # 命中实体列表
    answer: str #
    subgraphs: Optional[List[Any]] = [] # 命中的图谱子图列表
    query_cuts: Optional[List[Any]] = [] # 分词列表
    # explanation_ind: Optional[str] = ""
    # explanation_formview: Optional[str] = ""
    # explanation_service: Optional[Dict[str, str]] = {}


class AssetSearchResponseModel(BaseModel):
    res: ResourceAssetSearchResponseData
    # res_status: Optional[str] = ""
    # explanation_status: Optional[str] = ""