from typing import List

from pydantic import BaseModel, Field, computed_field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from app.models.field_validators import *

CODE_TABLE = 1
NUMBER = 2
ALPHABETA = 3
CHINESE_CARACTOR = 4
ANY_CARACTOR = 5
TIME = 6
CONSTANT_STRING = 7
SELF_DEFINE_RULE_TYPE_INT_TO_NAME = {CODE_TABLE: "码表", NUMBER: "数字", ALPHABETA: "英文字母",
                                     CHINESE_CARACTOR: "汉字", ANY_CARACTOR: "任意字符", TIME: "时间",
                                     CONSTANT_STRING: "固定字符串"}


class SegmentRuleDetailModel(BaseModel):
    segment_length: Annotated[int, Field(..., description="编码分段规则长度")]
    name: Annotated[str | None, Field(default=None,
                                      description="编码分段的名称或说明，如果说明不存在，默认为" + NAME_DEFAULT_CONTENT), AfterValidator(
        name_validator)]
    value: str = Field(...,
                       description="编码分段规则具体内容，码表类型时为关联的码表id，时间类型时为时间的格式，固定字符串时为一个固定的字符串，其他为空字符串")
    type: Annotated[int, Field(..., description="编码分段规则类型的编号")]

    @computed_field(description="编码分段规则类型，转化成对应的中文名了，与原本AF的类型名有所区别")
    def type_name(self) -> str:
        return SELF_DEFINE_RULE_TYPE_INT_TO_NAME[int(self.type)]


class RuleDetailModel(BaseModel):
    id: Annotated[str, Field(..., description="编码规则id")]
    name: Annotated[str, Field(..., description="编码规则名称")]
    rule_type: Annotated[
        str, Field(..., description="编码规则类型，CUSTOM是自定义，REGEX是正则", pattern=r"CUSTOM|REGEX")]
    regex: Annotated[
        str, Field(default=None, description="编码规则为正则表达式时的正则表达式"), AfterValidator(regex_validator)]
    custom: List[SegmentRuleDetailModel] = Field(default=None,
                                                 description="当编码规则为自定义时，包含了多条编码分段规则")
    description: Annotated[str | None, Field(default=None,
                                             description="编码规则的详细说明，如果说明不存在，默认为" + DESCRUPTION_DEFAULT_CONTENT), AfterValidator(
        description_validator)]
