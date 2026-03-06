from typing import Any, List

from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from app.models.field_validators import description_validator, DESCRUPTION_DEFAULT_CONTENT, code_or_id_validator


class SampleGenerateInput(BaseModel):
    # appid: Annotated[str, Field(..., description="app id")]
    user_id: Annotated[str, Field(..., description="user id")]
    view_id: Annotated[str, Field(..., description="一个虚拟视图的id")]
    samples_size: Annotated[int | None, Field(default=1, description="希望生成样例的数量，1-10条", ge=1, le=50)]
    max_retry: Annotated[int | None, Field(default=2, description="生成样例的重试次数，最多重试10次", ge=1, le=10)]


class ColumnModel(BaseModel):
    column_name: Annotated[str, Field(..., description="生成样例字段名")]
    column_value: Any = Field(..., description="生成样例字段值")
    column_description: Any = Field(default="", description="")


class SampleModel(BaseModel):
    a_sample: Annotated[List[ColumnModel], Field(..., description="一个生成样例")]


class ColumnDetailModel(BaseModel):
    id: Annotated[str, Field(..., description="列uuid")]
    technical_name: Annotated[str, Field(..., description="列技术名称，可理解为字段英文名")]
    business_name: Annotated[str, Field(..., description="列业务名称，可理解为字段中文名")]
    primary_key: Annotated[bool, Field(..., description="是否主键")]
    data_type: Annotated[str, Field(..., description="字段数据类型")]
    data_length: Annotated[int, Field(...,
                                      description="数据长度，这里是指数据库内分配的存储该数据字段的空间，优先级低于数据标准的码表或编码规则的长度")]
    data_accuracy: Annotated[int, Field(..., description="数据精度，小数点后位数，只有在字段数据类型为数字型时有意义")]
    is_nullable: Annotated[str, Field(..., description="是否为空，只能为YES或NO", pattern=r'YES|NO')]
    standard_code: Annotated[str | None, Field(default=None, description="字段所关联数据标准code"), AfterValidator(
        code_or_id_validator)]
    code_table_id: Annotated[
        str | None, Field(..., description="字段所关联码表id,比数据标准内关联的码表优先"), AfterValidator(
            code_or_id_validator)]


class ViewTableDetailModel(BaseModel):
    technical_name: Annotated[str | None, Field(default=None, description="视图技术名称，可理解为视图英文名")]
    business_name: Annotated[str, Field(..., description="视图业务名称，可理解为视图业务名")]
    description: Annotated[str | None, Field(...,
                                             description="视图的说明，如果说明不存在，默认为" + DESCRUPTION_DEFAULT_CONTENT), AfterValidator(
        description_validator)]
