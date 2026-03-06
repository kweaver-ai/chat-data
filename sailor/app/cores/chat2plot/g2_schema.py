import copy
from enum import Enum
from typing import Any, Type

import jsonref
import pydantic

from app.cores.chat2plot.dictionary_helper import (
    flatten_single_element_allof,
    remove_field_recursively,
)


class ChartType(str, Enum):
    PIE = "Pie"
    LINE = "Line"
    COLUMN = "Column"


class G2PlotConfig(pydantic.BaseModel):
    chart_type: ChartType = pydantic.Field(
        description="The type of the chart. Use scatter plots as little as possible unless explicitly specified by the user. Choose 'scalar' if we need only single scalar."
    )

    xField: str | None = pydantic.Field(
        None, description="X-axis for the chart except pie chart. Set None if you choose to draw pie chart."
    )
    yField: str | None = pydantic.Field(None,
                                        description="Y-Field or measure value for the chart except pie chart. Set None if you choose to draw pie chart.",
                                        )
    colorField: str | None = pydantic.Field(
        None,
        description="color-Field for the pie chart.",
    )
    angleField: str | None = pydantic.Field(
        None,
        description="angle-Field for the pie chart.",
    )
    color: str | None = pydantic.Field(
        None,
        description="Column name used as grouping variables that will produce different colors.",
    )
    limit: int | None = pydantic.Field(
        None, description="Limit a number of data to top-N items"
    )


def get_schema_of_chart_config(
        target_schema: Type[pydantic.BaseModel],
        inlining_refs: bool = True,
        remove_title: bool = True,
        as_function: bool = False,
) -> dict[str, Any]:
    defs = jsonref.loads(
        target_schema.model_json_schema()) if inlining_refs else target_schema.model_json_schema()  # type: ignore

    if remove_title:
        defs = remove_field_recursively(defs, "title")

    defs = flatten_single_element_allof(defs)

    defs = copy.deepcopy(defs)

    if as_function:
        return {
            "name": "generate_chart",
            "description": "Generate the chart with given parameters",
            "parameters": defs,
        }

    return defs  # type: ignore
