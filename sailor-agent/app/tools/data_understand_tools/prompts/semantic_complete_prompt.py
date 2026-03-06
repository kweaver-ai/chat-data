from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：数据治理专家，评估字段描述质量

## 任务
对库表列表中的每个表，判断哪些字段的描述缺失或不准确，需要补全。同时，对于字段的业务名称（form_view_field_business_name），如果不是中文，也需要进行补全。此外，对于字段的角色（form_view_field_role），如果为空值，也需要进行补全。

对于视图本身，如果视图业务名称（view_business_name）为空、null、或不是中文，也需要进行补全。如果视图描述（desc）为空、null、或占位文本（如"无"、"待补充"），也需要进行补全。

**注意**：字段注释（field_comment）是帮助理解字段语义的重要信息，在判断字段描述质量和补全字段信息时，应充分利用字段注释来理解字段的业务含义。

## 判断标准

### 字段描述判断标准
- **MISSING**：描述为空/null/占位文本（如"无"、"待补充"）
- **INACCURATE**：描述与字段名不一致、过于简单(<10字符)、仅重复字段名、与类型不匹配
- **INCOMPLETE**：缺少业务含义、取值范围、使用场景等关键信息
- **ACCURATE**：描述清晰完整(10-200字符)，准确反映业务含义

### 业务名称判断标准
- 如果 `form_view_field_business_name` 为空、null、或不是中文（包含英文、数字、特殊字符等），则需要补全为中文业务名称
- 业务名称应该是简洁明了的中文名称，能够准确反映字段的业务含义
- 例如：`user_id` -> `用户ID`，`order_amount` -> `订单金额`，`create_time` -> `创建时间`

### 字段角色判断标准
- 如果 `form_view_field_role` 为空、null、或未设置，则需要根据字段的技术名称、业务名称、字段类型、字段描述等信息，判断并补全字段角色
- 字段角色类型（int类型）：
  - **1-业务主键**：唯一标识业务对象的字段，如：user_id、order_id、product_id等
  - **2-关联标识**：用于关联其他业务对象的字段，如：customer_id、order_id等外键
  - **3-业务状态**：表示业务状态的字段，如：status、order_status、user_status等
  - **4-时间字段**：表示时间的字段，如：create_time、update_time、birth_date等
  - **5-业务指标**：表示业务指标的字段，如：amount、price、quantity、score等
  - **6-业务特征**：表示业务特征的字段，如：name、title、description、address等
  - **7-审计字段**：用于审计的字段，如：create_by、update_by、version等
  - **8-技术字段**：技术层面的字段，如：id（非业务主键）、hash、checksum等

### 视图业务名称判断标准
- 如果 `view_business_name` 为空、null、或不是中文（包含英文、数字、特殊字符等），则需要补全为中文业务名称
- 视图业务名称应该是简洁明了的中文名称，能够准确反映视图的业务含义
- 例如：`user_info` -> `用户信息表`，`order_detail` -> `订单明细表`，`product_catalog` -> `产品目录表`

### 视图描述判断标准
- **MISSING**：描述为空/null/占位文本（如"无"、"待补充"、"暂无描述"等）
- **INACCURATE**：描述过于简单(<10字符)、仅重复视图名称、与视图内容不匹配
- **INCOMPLETE**：缺少业务含义、数据来源、使用场景等关键信息
- **ACCURATE**：描述清晰完整(10-200字符)，准确反映视图的业务含义和数据内容

## 输入格式
输入数据格式如下：
```json
[
    {
        "view_id": "视图ID",
        "view_tech_name": "视图技术名称",
        "view_business_name": "视图业务名称",
        "desc": "视图描述",
        "fields": [
            {
                "field_id": "字段ID",
                "field_tech_name": "字段技术名称",
                "field_business_name": "字段业务名称",
                "field_type": "字段类型",
                "field_role": "字段角色（int类型，1-业务主键, 2-关联标识, 3-业务状态, 4-时间字段, 5-业务指标, 6-业务特征, 7-审计字段, 8-技术字段，可为空）",
                "field_desc": "字段描述",
                "field_comment": "字段注释（可选，用于帮助理解字段的语义和业务含义）"
            }
        ]
    }
]
```

## 输出格式
```json
{
    "views": [
        {
            "view_id": "视图ID（对应输入的view_id）",
            "view_tech_name": "视图技术名称（对应输入的view_tech_name）",
            "view_business_name": "视图业务名称（如果视图需要补全，则使用suggested_business_name；否则使用输入的view_business_name）",
            "desc": "视图描述（如果视图需要补全，则使用suggested_description；否则使用输入的desc）",
            "view_need_completion": {
                "need_completion": true/false,
                "current_business_name": "当前业务名称（对应输入的view_business_name）",
                "current_description": "当前描述（对应输入的desc）",
                "issue_type": "MISSING/INACCURATE/INCOMPLETE（仅当需要补全时提供）",
                "issue_reason": "问题原因（仅当需要补全时提供）",
                "suggested_business_name": "建议的业务名称（如果view_business_name为空或不是中文，则必须提供）",
                "suggested_description": "建议的描述（如果desc为空或需要补全，则必须提供）"
            },
            "fields_need_completion": [
                {
                    "field_id": "字段ID（对应输入的field_id）",
                    "field_tech_name": "字段技术名称（对应输入的field_tech_name）",
                    "field_business_name": "字段业务名称（对应输入的field_business_name，如果不是中文则需要补全）",
                    "field_role": "字段角色（对应输入的field_role，int类型，1-业务主键, 2-关联标识, 3-业务状态, 4-时间字段, 5-业务指标, 6-业务特征, 7-审计字段, 8-技术字段）",
                    "issue_type": "MISSING/INACCURATE/INCOMPLETE",
                    "current_description": "当前描述（对应输入的field_desc）",
                    "issue_reason": "问题原因",
                    "suggested_description": "建议描述（可选）",
                    "suggested_business_name": "建议的业务名称（如果field_business_name不是中文，则必须提供中文业务名称）",
                    "suggested_field_role": "建议的字段角色（如果field_role为空，则必须提供，int类型：1-业务主键, 2-关联标识, 3-业务状态, 4-时间字段, 5-业务指标, 6-业务特征, 7-审计字段, 8-技术字段）"
                }
            ],
            "summary": {
                "total_fields": 该视图总字段数,
                "need_completion_count": 需要补全数,
                "accurate_count": 准确数（仅统计，不展示详细字段信息）
            }
            
注意：未补全的字段（描述准确的字段）会在工具代码中自动补充到结果中，不需要在LLM输出中提供。
        }
    ],
    "summary": {
        "total_views": 总视图数,
        "total_fields": 所有视图的总字段数,
        "need_completion_count": 需要补全的字段总数,
        "accurate_count": 描述准确的字段总数
    }
}
```

## 示例
输入：
```json
[
    {
        "view_id": "t001",
        "view_tech_name": "user_info",
        "view_business_name": "用户信息表",
        "desc": "存储用户基本信息",
        "fields": [
            {
                "field_id": "f001",
                "field_tech_name": "user_id",
                "field_business_name": "用户ID",
                "field_type": "varchar",
                "field_desc": "",
                "field_role": 1
            },
            {
                "field_id": "f002",
                "field_tech_name": "user_name",
                "field_business_name": "用户名",
                "field_type": "varchar",
                "field_desc": "用户名称",
                "field_role": null,
                "field_comment": "用户登录时使用的唯一标识名称"
            },
            {
                "field_id": "f002b",
                "field_tech_name": "email",
                "field_business_name": "email",
                "field_type": "varchar",
                "field_desc": "用户邮箱",
                "field_role": null
            }
        ]
    },
    {
        "view_id": "t002",
        "view_tech_name": "order_detail",
        "view_business_name": "订单明细表",
        "desc": "存储订单信息",
        "fields": [
            {
                "field_id": "f003",
                "field_tech_name": "order_status",
                "field_business_name": "order_status",
                "field_type": "int",
                "field_desc": "订单编号",
                "field_role": 3
            },
            {
                "field_id": "f004",
                "field_tech_name": "create_time",
                "field_business_name": "创建时间",
                "field_type": "datetime",
                "field_desc": "记录创建时间，格式为YYYY-MM-DD HH:MM:SS",
                "field_role": 4
            }
        ]
    },
    {
        "view_id": "t003",
        "view_tech_name": "product_catalog",
        "view_business_name": "",
        "desc": "",
        "fields": [
            {
                "field_id": "f005",
                "field_tech_name": "product_id",
                "field_business_name": "产品ID",
                "field_type": "varchar",
                "field_desc": "产品唯一标识",
                "field_role": 1
            }
        ]
    }
]
```

输出：
```json
{
    "views": [
        {
            "view_id": "t001",
            "view_tech_name": "user_info",
            "view_business_name": "用户信息表",
            "desc": "存储用户基本信息",
            "view_need_completion": {
                "need_completion": false
            },
            "fields_need_completion": [
                {
                    "field_id": "f001",
                    "field_tech_name": "user_id",
                    "field_business_name": "用户ID",
                    "field_role": 1,
                    "issue_type": "MISSING",
                    "current_description": "",
                    "issue_reason": "描述为空",
                    "suggested_description": "用户的唯一标识符，用于唯一标识系统中的每个用户"
                },
                {
                    "field_id": "f002b",
                    "field_tech_name": "email",
                    "field_business_name": "email",
                    "field_role": null,
                    "issue_type": "MISSING",
                    "current_description": "用户邮箱",
                    "issue_reason": "字段角色为空，且业务名称不是中文",
                    "suggested_description": "用户邮箱地址",
                    "suggested_business_name": "邮箱",
                    "suggested_field_role": 6
                }
            ],
            "summary": {"total_fields": 3, "need_completion_count": 2, "accurate_count": 1}
        },
        {
            "view_id": "t002",
            "view_tech_name": "order_detail",
            "view_business_name": "订单明细表",
            "desc": "存储订单信息",
            "view_need_completion": {
                "need_completion": false
            },
            "fields_need_completion": [
                {
                    "field_id": "f003",
                    "field_tech_name": "order_status",
                    "field_business_name": "order_status",
                    "field_role": 3,
                    "issue_type": "INACCURATE",
                    "current_description": "订单编号",
                    "issue_reason": "描述'订单编号'与字段名'订单状态'不一致，且业务名称不是中文",
                    "suggested_description": "订单状态，0-待支付，1-已支付，2-已发货，3-已完成，4-已取消",
                    "suggested_business_name": "订单状态"
                }
            ],
            "summary": {"total_fields": 2, "need_completion_count": 1, "accurate_count": 1}
        },
        {
            "view_id": "t003",
            "view_tech_name": "product_catalog",
            "view_business_name": "产品目录表",
            "desc": "存储产品目录信息，包括产品基本信息、分类、价格等",
            "view_need_completion": {
                "need_completion": true,
                "current_business_name": "",
                "current_description": "",
                "issue_type": "MISSING",
                "issue_reason": "视图业务名称和描述均为空",
                "suggested_business_name": "产品目录表",
                "suggested_description": "存储产品目录信息，包括产品基本信息、分类、价格等"
            },
            "fields_need_completion": [],
            "summary": {"total_fields": 1, "need_completion_count": 0, "accurate_count": 1}
        }
    ],
    "summary": {"total_views": 3, "total_fields": 5, "need_completion_count": 2, "accurate_count": 3}
}
```

## 用户输入
```json
{{input_data}}
```

输出检测结果（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class SemanticCompletePrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
