import re

DESCRUPTION_DEFAULT_CONTENT = "(未填写说明)"
NAME_DEFAULT_CONTENT = "(未命名)"


def description_validator(v: str) -> str:
    # 任何说明如果为None或者"",默认使用"(未填写说明)"作为默认值
    if not v:
        return DESCRUPTION_DEFAULT_CONTENT
    else:
        return v


def name_validator(v: str) -> str:
    # 任何说明如果为None或者"",默认使用"(未填写说明)"作为默认值
    if not v:
        return NAME_DEFAULT_CONTENT
    else:
        return v


def code_or_id_validator(v: str):
    if not v:
        return None
    else:
        return v


def regex_validator(pattern: str):
    try:
        re.compile(pattern)
        return pattern
    except re.error:
        raise ValueError("正则表达式值不合法。")
