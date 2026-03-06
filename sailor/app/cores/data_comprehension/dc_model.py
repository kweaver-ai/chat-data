# -*- coding: utf-8 -*-
# @Time    : 2025/3/15 15:14
# @Author  : Glen.lv
# @File    : data_model
# @Project : af-sailor

def create_empty_data_comprehension_response(dimension: str, error_str: str = None):
    """创建空响应的工厂函数"""
    return {"dimension": dimension, "answer": [], "error": error_str}


# 提取常量
ALL_DIMENSIONS = 'all'
BUSINESS_OBJECT = "业务对象"
TIME_RANGE = "时间范围"
TIME_FIELD = "时间字段理解"
SPACE_RANGE = "空间范围"
SPACE_FIELD = "空间字段理解"
BUSINESS_DIMENSION = "业务维度"
COMPLEX_EXPRESSION = "复合表达"
SERVICE_SCOPE = "服务范围"
SERVICE_FIELD = "服务领域"
POSITIVE_SUPPORT = "正面支撑"
NEGATIVE_SUPPORT = "负面支撑"
PROTECTION_CONTROL = "保护控制"
PROMOTION_DRIVE = "促进推动"

SUPPORTED_DIMENSIONS = [BUSINESS_OBJECT, TIME_RANGE, TIME_FIELD, SPACE_RANGE, SPACE_FIELD, BUSINESS_DIMENSION,
                        COMPLEX_EXPRESSION, SERVICE_SCOPE, SERVICE_FIELD, POSITIVE_SUPPORT, NEGATIVE_SUPPORT,
                        PROTECTION_CONTROL, PROMOTION_DRIVE]

# 提取模板名称
TEMPLATE_ALL_DIMENSIONS = 'comprehension_template'
TEMPLATE_TIME_FIELD = "comprehension_template_time"
TEMPLATE_SPACE_RANGE = "comprehension_template_city"
TEMPLATE_SPACE_FIELD = "comprehension_template_local"
TEMPLATE_BUSINESS_DIMENSION = "comprehension_template_ywwd"
TEMPLATE_COMPLEX_EXPRESSION = "comprehension_relation_template"
TEMPLATE_SERVICE_SCOPE = "comprehension_template_fwfw"
TEMPLATE_SERVICE_FIELD = "comprehension_template_fwly"
TEMPLATE_POSITIVE = "comprehension_template_zmzc"
TEMPLATE_NEGATIVE = "comprehension_template_fmzc"
TEMPLATE_PROTECTION = "comprehension_template_bhkz"
TEMPLATE_PROMOTION = "comprehension_template_cjtd"

# 引入命名变量
PROMPT_MAP = {
    TIME_FIELD: TEMPLATE_TIME_FIELD,
    SPACE_RANGE: TEMPLATE_SPACE_RANGE,
    SPACE_FIELD: TEMPLATE_SPACE_FIELD,
    BUSINESS_DIMENSION: TEMPLATE_BUSINESS_DIMENSION,
    COMPLEX_EXPRESSION: TEMPLATE_COMPLEX_EXPRESSION,
    SERVICE_SCOPE: TEMPLATE_SERVICE_SCOPE,
    SERVICE_FIELD: TEMPLATE_SERVICE_FIELD,
    POSITIVE_SUPPORT: TEMPLATE_POSITIVE,
    NEGATIVE_SUPPORT: TEMPLATE_NEGATIVE,
    PROTECTION_CONTROL: TEMPLATE_PROTECTION,
    PROMOTION_DRIVE: TEMPLATE_PROMOTION
}


# prompt_map = {
#         "时间字段理解": "comprehension_template_time",
#         "空间范围": "comprehension_template_city",
#         "空间字段理解": "comprehension_template_local",
#         "业务维度": "comprehension_template_ywwd",
#         "复合表达": "comprehension_relation_template",
#         "服务范围": "comprehension_template_fwfw",
#         "服务领域": "comprehension_template_fwly",
#         "正面支撑": "comprehension_template_zmzc",
#         "负面支撑": "comprehension_template_fmzc",
#         "保护控制": "comprehension_template_bhkz",
#         "促进推动": "comprehension_template_cjtd"
#         }
