from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from app.models.field_validators import description_validator, DESCRUPTION_DEFAULT_CONTENT

DATA_TYPE_NAME_TO_NUMBER = {"数字型": "0", "字符型": "1", "日期型": "2", "日期时间型": "3", "时间戳型": "4",
                            "布尔型": "5", "二进制": "6", "其他类型": "99", "未知类型": "-1"}


class StandardDetailModel(BaseModel):
    id: Annotated[str, Field(..., description="数据标准的数据库id")]
    code: Annotated[str, Field(..., description="数据标准的真正唯一键id，逻辑视图里的字段详情里通过这个关联数据标准")]
    name_en: Annotated[str, Field(..., description="数据标准的英文名")]
    name_cn: Annotated[str, Field(..., description="数据标准的中文名")]
    synonym: Annotated[str, Field(default=None, description="数据标准的同义词")]
    data_length: Annotated[int, Field(default=None, description="数据标准的长度")]
    data_precision: Annotated[int, Field(default=None, description="数据标准为数字型时小数点后的位数")]
    dict_id: Annotated[str, Field(default=None, description="数据标准对应码表时码表的id")]
    rule_id: Annotated[str, Field(default=None, description="数据标准对应编码规则时编码规则的id")]
    description: Annotated[str | None, Field(default=None,
                                             description="数据标准的说明，如果说明不存在，默认为" + DESCRUPTION_DEFAULT_CONTENT), AfterValidator(
        description_validator)]
    data_type: Annotated[int, Field(default=None, description="数据标准的类型代号")]
    data_type_name: Annotated[
        str, Field(..., description="数据标准的数据类型的名称，如果关联了码表或编码规则则忽略此信息")]
    std_type_name: Annotated[str, Field(..., description="数据标准的类型名称")]
