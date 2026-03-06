from typing import List

from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

from app.models.field_validators import description_validator, DESCRUPTION_DEFAULT_CONTENT


class EnumValueModel(BaseModel):
    id: Annotated[str, Field(..., description="码值id")]
    code: Annotated[str, Field(..., description="码值")]
    value: Annotated[str, Field(..., description="码值对应的意义")]
    description: Annotated[str | None, Field(default=None,
                                             description="码值意义的详细说明，如果说明不存在，默认为" + DESCRUPTION_DEFAULT_CONTENT), AfterValidator(
        description_validator)]
    dict_id: Annotated[str, Field(..., description="码值对应的码表的id")]


class CodeTableDetailModel(BaseModel):
    id: Annotated[str, Field(..., description="码表id")]
    code: Annotated[str, Field(..., description="码表code")]
    ch_name: Annotated[str, Field(..., description="码表中文名")]
    en_name: Annotated[str, Field(..., description="码表英文名")]
    enums: Annotated[List[EnumValueModel], Field(..., description="码表的码值列表")]
    description: Annotated[str | None, Field(default=None,
                                             description="码表意义的详细说明，如果说明不存在，默认为" + DESCRUPTION_DEFAULT_CONTENT), AfterValidator(
        description_validator)]
