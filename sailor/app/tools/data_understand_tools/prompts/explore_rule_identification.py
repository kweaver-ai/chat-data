from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：数据质量专家，数据质量规则识别专家

## 任务
从库表列表中识别每个表和字段的数据质量规则，分析数据质量约束条件和校验规则。

## 数据质量规则类型

### 1. 完整性规则（Completeness）
- **非空约束（NOT NULL）**：字段不能为空，属性值不能为空，计算表中的空值数据
- **必填字段（Required）**：业务上必须填写的字段
- **完整性检查**：关键字段的完整性要求

### 2. 准确性规则（Accuracy）
- **格式校验**：数据格式要求（如：邮箱格式、手机号格式、身份证格式等）
- **范围校验**：数值范围、日期范围等
- **精度校验**：小数位数、字符串长度等
- **类型校验**：数据类型匹配
- **长度约束**：属性值必须满足约定的长度范围

**内置规则 - 长度约束**：
- 字段级规则，属性值必须满足约定的长度范围
- 区间是闭合空间（包含边界值），如 [min_length, max_length]
- 返回不在长度约束范围内的记录
- 规则表达式：LENGTH_RANGE
- 规则值：格式为 [min_length, max_length]，如 [1, 50] 表示长度在1到50之间（包含1和50）
- 返回结果：不符合长度约束的记录列表

### 3. 一致性规则（Consistency）
- **唯一性约束（UNIQUE）**：字段值必须唯一
- **记录唯一**：记录不重复，返回记录不唯一的记录
- **主键约束（PRIMARY KEY）**：主键唯一性
- **外键约束（FOREIGN KEY）**：参照完整性
- **业务一致性**：业务逻辑一致性要求

**内置规则 - 记录唯一**：
- 字段级规则，记录不重复
- 返回记录不唯一的记录（即重复的记录）
- 规则表达式：UNIQUE
- 返回结果：重复记录列表，包含重复的记录及其出现次数

### 4. 时效性规则（Timeliness）
- **时间范围**：数据的时间有效性范围
- **过期检查**：数据是否过期
- **时效性要求**：数据的时效性要求

### 5. 有效性规则（Validity）
- **枚举值约束**：字段值必须在指定的枚举值范围内
- **正则表达式**：符合特定模式的数据
- **业务规则**：符合业务逻辑的数据

### 6. 合理性规则（Reasonableness）
- **数值合理性**：数值是否在合理范围内
- **逻辑合理性**：数据逻辑是否合理
- **业务合理性**：是否符合业务常识

## 识别方法

### 基于字段类型和约束
- **数据类型**：通过数据类型判断（如varchar长度、decimal精度等）
- **字段约束**：通过字段约束判断（如NOT NULL、UNIQUE等）
- **字段名称**：通过字段名称判断（如包含id、time、status等关键词）

### 基于字段描述和业务含义
- **字段描述**：通过字段描述判断质量要求
- **业务含义**：结合业务含义判断质量规则
- **样例数据**：通过样例数据推断质量规则

### 基于表结构和关系
- **主键外键**：识别主键和外键约束
- **表关系**：识别表之间的关联关系
- **业务规则**：识别业务逻辑规则

## 输出格式
```json
{
    "tables": [
        {
            "table_id": "表ID",
            "table_name": "表名",
            "quality_rules": [
                {
                    "rule_id": "规则ID",
                    "rule_name": "规则名称",
                    "rule_type": "规则类型（完整性/准确性/一致性/时效性/有效性/合理性）",
                    "rule_category": "规则分类（如：非空约束/格式校验/唯一性约束等）",
                    "target_field": "目标字段（字段ID或字段名）",
                    "rule_description": "规则描述",
                    "rule_expression": "规则表达式（如：NOT NULL、REGEX、RANGE等）",
                    "rule_value": "规则值（如：枚举值列表、范围值等）",
                    "severity": "严重程度（HIGH/MEDIUM/LOW）",
                    "confidence": "识别置信度（0-1）"
                }
            ],
            "table_level_rules": [
                {
                    "rule_id": "规则ID",
                    "rule_name": "规则名称",
                    "rule_type": "规则类型",
                    "rule_description": "规则描述",
                    "rule_expression": "规则表达式",
                    "severity": "严重程度",
                    "confidence": "识别置信度"
                }
            ],
            "summary": {
                "total_fields": "该表总字段数",
                "total_rules": "规则总数",
                "completeness_rules": "完整性规则数",
                "accuracy_rules": "准确性规则数",
                "consistency_rules": "一致性规则数",
                "timeliness_rules": "时效性规则数",
                "validity_rules": "有效性规则数",
                "reasonableness_rules": "合理性规则数"
            }
        }
    ],
    "summary": {
        "total_tables": "总表数",
        "total_rules": "规则总数",
        "rule_type_distribution": {
            "完整性": "规则数量",
            "准确性": "规则数量",
            "一致性": "规则数量",
            "时效性": "规则数量",
            "有效性": "规则数量",
            "合理性": "规则数量"
        },
        "severity_distribution": {
            "HIGH": "高严重程度规则数",
            "MEDIUM": "中等严重程度规则数",
            "LOW": "低严重程度规则数"
        }
    }
}
```

## 示例
输入：
```json
[
    {
        "table_id": "t001",
        "table_name": "user_info",
        "table_business_name": "用户信息表",
        "table_description": "存储用户基本信息，包括用户ID、姓名、联系方式等",
        "fields": [
            {"field_id": "f001", "field_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_description": "用户唯一标识，主键"},
            {"field_id": "f002", "field_name": "user_name", "field_business_name": "用户名", "field_type": "varchar(50)", "field_description": "用户名称，必填"},
            {"field_id": "f003", "field_name": "phone", "field_business_name": "手机号", "field_type": "varchar(11)", "field_description": "用户手机号码，11位数字"},
            {"field_id": "f004", "field_name": "email", "field_business_name": "邮箱", "field_type": "varchar(100)", "field_description": "用户邮箱地址"},
            {"field_id": "f005", "field_name": "age", "field_business_name": "年龄", "field_type": "int", "field_description": "用户年龄"},
            {"field_id": "f006", "field_name": "status", "field_business_name": "状态", "field_type": "varchar(10)", "field_description": "用户状态：active/inactive/deleted"},
            {"field_id": "f007", "field_name": "create_time", "field_business_name": "创建时间", "field_type": "datetime", "field_description": "用户创建时间"}
        ]
    },
    {
        "table_id": "t002",
        "table_name": "order_detail",
        "table_business_name": "订单明细表",
        "table_description": "存储订单详细信息，包括订单ID、商品信息、金额等",
        "fields": [
            {"field_id": "f008", "field_name": "order_id", "field_business_name": "订单ID", "field_type": "varchar(32)", "field_description": "订单唯一标识，主键"},
            {"field_id": "f009", "field_name": "user_id", "field_business_name": "用户ID", "field_type": "varchar(32)", "field_description": "下单用户ID，外键关联user_info表"},
            {"field_id": "f010", "field_name": "product_id", "field_business_name": "商品ID", "field_type": "varchar(32)", "field_description": "商品唯一标识，外键关联product表"},
            {"field_id": "f011", "field_name": "amount", "field_business_name": "订单金额", "field_type": "decimal(10,2)", "field_description": "订单总金额，必须大于0"},
            {"field_id": "f012", "field_name": "order_status", "field_business_name": "订单状态", "field_type": "varchar(20)", "field_description": "订单状态：pending/paid/shipped/completed/cancelled"},
            {"field_id": "f013", "field_name": "create_time", "field_business_name": "创建时间", "field_type": "datetime", "field_description": "订单创建时间"},
            {"field_id": "f014", "field_name": "update_time", "field_business_name": "更新时间", "field_type": "datetime", "field_description": "订单更新时间"}
        ]
    }
]
```

输出：
```json
{
    "tables": [
        {
            "table_id": "t001",
            "table_name": "user_info",
            "quality_rules": [
                {
                    "rule_id": "r001",
                    "rule_name": "用户ID非空且唯一",
                    "rule_type": "一致性",
                    "rule_category": "主键约束",
                    "target_field": "user_id",
                    "rule_description": "用户ID是主键，必须非空且唯一",
                    "rule_expression": "PRIMARY KEY",
                    "rule_value": null,
                    "severity": "HIGH",
                    "confidence": 0.98
                },
                {
                    "rule_id": "r002",
                    "rule_name": "用户名必填",
                    "rule_type": "完整性",
                    "rule_category": "非空约束",
                    "target_field": "user_name",
                    "rule_description": "用户名是必填字段，不能为空",
                    "rule_expression": "NOT NULL",
                    "rule_value": null,
                    "severity": "HIGH",
                    "confidence": 0.95
                },
                {
                    "rule_id": "r003",
                    "rule_name": "手机号格式校验",
                    "rule_type": "准确性",
                    "rule_category": "格式校验",
                    "target_field": "phone",
                    "rule_description": "手机号必须是11位数字",
                    "rule_expression": "REGEX",
                    "rule_value": "^1[3-9]\\d{9}$",
                    "severity": "HIGH",
                    "confidence": 0.92
                },
                {
                    "rule_id": "r004",
                    "rule_name": "邮箱格式校验",
                    "rule_type": "准确性",
                    "rule_category": "格式校验",
                    "target_field": "email",
                    "rule_description": "邮箱必须符合邮箱格式",
                    "rule_expression": "REGEX",
                    "rule_value": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                    "severity": "MEDIUM",
                    "confidence": 0.90
                },
                {
                    "rule_id": "r005",
                    "rule_name": "年龄范围校验",
                    "rule_type": "合理性",
                    "rule_category": "数值合理性",
                    "target_field": "age",
                    "rule_description": "年龄应该在合理范围内（0-150）",
                    "rule_expression": "RANGE",
                    "rule_value": "[0, 150]",
                    "severity": "MEDIUM",
                    "confidence": 0.85
                },
                {
                    "rule_id": "r006",
                    "rule_name": "状态枚举值约束",
                    "rule_type": "有效性",
                    "rule_category": "枚举值约束",
                    "target_field": "status",
                    "rule_description": "状态字段值必须在指定枚举值范围内",
                    "rule_expression": "ENUM",
                    "rule_value": ["active", "inactive", "deleted"],
                    "severity": "HIGH",
                    "confidence": 0.95
                }
            ],
            "table_level_rules": [],
            "summary": {
                "total_fields": 7,
                "total_rules": 6,
                "completeness_rules": 1,
                "accuracy_rules": 2,
                "consistency_rules": 1,
                "timeliness_rules": 0,
                "validity_rules": 1,
                "reasonableness_rules": 1
            }
        },
        {
            "table_id": "t002",
            "table_name": "order_detail",
            "quality_rules": [
                {
                    "rule_id": "r007",
                    "rule_name": "订单ID非空且唯一",
                    "rule_type": "一致性",
                    "rule_category": "主键约束",
                    "target_field": "order_id",
                    "rule_description": "订单ID是主键，必须非空且唯一",
                    "rule_expression": "PRIMARY KEY",
                    "rule_value": null,
                    "severity": "HIGH",
                    "confidence": 0.98
                },
                {
                    "rule_id": "r008",
                    "rule_name": "用户ID外键约束",
                    "rule_type": "一致性",
                    "rule_category": "外键约束",
                    "target_field": "user_id",
                    "rule_description": "用户ID必须存在于user_info表中",
                    "rule_expression": "FOREIGN KEY",
                    "rule_value": "user_info.user_id",
                    "severity": "HIGH",
                    "confidence": 0.95
                },
                {
                    "rule_id": "r009",
                    "rule_name": "商品ID外键约束",
                    "rule_type": "一致性",
                    "rule_category": "外键约束",
                    "target_field": "product_id",
                    "rule_description": "商品ID必须存在于product表中",
                    "rule_expression": "FOREIGN KEY",
                    "rule_value": "product.product_id",
                    "severity": "HIGH",
                    "confidence": 0.95
                },
                {
                    "rule_id": "r010",
                    "rule_name": "订单金额必须大于0",
                    "rule_type": "合理性",
                    "rule_category": "数值合理性",
                    "target_field": "amount",
                    "rule_description": "订单金额必须大于0",
                    "rule_expression": "RANGE",
                    "rule_value": "(0, +∞)",
                    "severity": "HIGH",
                    "confidence": 0.90
                },
                {
                    "rule_id": "r011",
                    "rule_name": "订单状态枚举值约束",
                    "rule_type": "有效性",
                    "rule_category": "枚举值约束",
                    "target_field": "order_status",
                    "rule_description": "订单状态必须在指定枚举值范围内",
                    "rule_expression": "ENUM",
                    "rule_value": ["pending", "paid", "shipped", "completed", "cancelled"],
                    "severity": "HIGH",
                    "confidence": 0.95
                }
            ],
            "table_level_rules": [
                {
                    "rule_id": "r012",
                    "rule_name": "订单时间逻辑校验",
                    "rule_type": "合理性",
                    "rule_description": "订单更新时间必须大于等于创建时间",
                    "rule_expression": "update_time >= create_time",
                    "severity": "MEDIUM",
                    "confidence": 0.85
                }
            ],
            "summary": {
                "total_fields": 7,
                "total_rules": 6,
                "completeness_rules": 0,
                "accuracy_rules": 0,
                "consistency_rules": 3,
                "timeliness_rules": 0,
                "validity_rules": 1,
                "reasonableness_rules": 2
            }
        }
    ],
    "summary": {
        "total_tables": 2,
        "total_rules": 12,
        "rule_type_distribution": {
            "完整性": 1,
            "准确性": 2,
            "一致性": 4,
            "时效性": 0,
            "有效性": 2,
            "合理性": 3
        },
        "severity_distribution": {
            "HIGH": 9,
            "MEDIUM": 3,
            "LOW": 0
        }
    }
}
```

## 用户输入
```json
{{input_data}}
```

输出质量规则识别结果（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class ExploreRuleIdentificationPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
