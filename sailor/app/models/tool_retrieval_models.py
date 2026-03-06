from enum import Enum
from typing import List

from pydantic import BaseModel, Field

chinese_name_field = Field(..., description="AF数据服务接口参数的中文名", example="创建人")
english_name_field = Field(..., description="AF数据服务接口参数的英文名", example="created_by_uid")
parameter_description_field = Field(..., description="参数描述", example="这个参数传入创建人的uid")
default_value_field = Field(None, description="默认值", example="1")


class AfDataServiceDataTypeEnum(Enum):
    # AF数据服务接口参数数据类型字段的枚举
    string_type = "string"
    int_type = "int"
    long_type = "long"
    float_type = "float"
    double_type = "double"
    bool_type = "boolean"


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


class AFInterfaceToolModel(BaseModel):
    interface_name: str = Field(..., description="被调用接口的名称")
    params: dict = Field(..., description="被调用接口的参数")


class AFText2SQLToolModel(BaseModel):
    question: str = Field(..., description="一个非SQL的的自然语言问题或者自然语言表述")


class AFKnowledgeSearchToolModel(BaseModel):
    search_str: str = Field(..., description="进行数据目录和接口服务召回的查询文本")


class AFKnowledgeEnhancementToolModel(BaseModel):
    question: str = Field(..., description="自然语言问题或者自然语言表述")


class AfCopilotToolModel(BaseModel):
    query: str = Field(..., description="一个没有歧义和代词的自然语言问题。")


class AfSailorToolModel(BaseModel):
    question: str = Field(..., description="自然语言问题或者自然语言表述。")
    extraneous_information: str = Field(default="",
                                        description="在调用工具的时候需要增加的额外信息或者需要重点强调的信息")

class JsonToPlotToolModel(BaseModel):
    question: str = Field(..., description="自然语言问题或者自然语言表述。")
    # df2json: List[str]  = Field(..., description="其中 str 是用户绘图的 Json 数据，由 dataframe 转过来的")
    chart_type: str = Field(..., description="图表的类型, 输出仅支持三种: 柱状图， 折线图，饼图")
    extraneous_information: str = Field(default="", description="在调用工具的时候需要增加的额外信息或者需要重点强调的信息")