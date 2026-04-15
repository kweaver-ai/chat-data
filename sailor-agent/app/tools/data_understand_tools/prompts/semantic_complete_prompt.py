from typing import Optional, List

from app.tools.prompts.base import BasePrompt
from app.utils.model_types import ModelType4Prompt
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

## 背景信息（可选）
如果以下内容不为空，请将其作为补充上下文用于判断与补全；如果为空请忽略。
```text
{{background}}
```

输出检测结果（仅JSON，无其他文字）。
"""

# DeepSeek V3.2：任务专用、强约束、无长示例（减 token、降跑偏）
prompt_template_cn_deepseek_v32 = """
[任务] 语义补全质量检测。你的唯一合法输出：一个 UTF-8 JSON 对象（从根对象起可被标准解析器完整解析，无包裹层）。

## 硬约束（任一违反即错误）
1. 禁止 Markdown（含 ```）、禁止前后任何非 JSON 文本、禁止 `//` 与 `#` 注释、禁止尾随逗号。
2. 禁止输出思考过程、步骤说明、自我检查或与任务无关的寒暄。
3. `views` 数组顺序与长度必须与输入一致：每个输入视图对应**恰好一个**输出元素，禁止增删视图。
4. `view_id`、`view_tech_name`、`field_id` 必须与输入**逐字相同**（含大小写、空格；`field_id` 可能为短数字字符串，禁止改写）。
5. 顶层每个视图的 `view_business_name`、`desc`：若该视图**不需要**视图级补全（`view_need_completion.need_completion` 为 false），则必须与输入**完全一致**（原文复制，含空串）；若需要补全（true），则顶层填**最终采用值**（与 `suggested_business_name` / `suggested_description` 一致）。
6. `fields_need_completion` **只列**需处理的字段；ACCURATE 字段**不得**出现（后处理会补 `fields_accurate`）。
7. `issue_type` 只能是 MISSING、INACCURATE、INCOMPLETE 三者之一。
8. `field_role` 为输入中的值（含 null）；若规则要求补全角色则必须额外给出整数 `suggested_field_role`（1–8）。
9. 禁止编造输入中不存在的视图/字段；禁止复述整段输入或粘贴 `fields` 全量列表。

## 执行顺序（内部推理，勿输出）
① 按视图遍历 `fields` → 决定是否进入 `fields_need_completion`。② 判定视图级名称/描述。③ 填各视图 `summary` 与根 `summary`。④ 用 `field_comment`（若有）辅助判断。

## 计数（必须自洽，用整数）
- 视图内：`total_fields` = 该视图输入 `fields` 的长度；`need_completion_count` = 本视图 `fields_need_completion` 的长度；`accurate_count` = `total_fields - need_completion_count`（不得为负）。
- 根：`total_views` = `views` 长度；`total_fields` = 各视图 `total_fields` 之和；`need_completion_count` / `accurate_count` 同理为各视图之和。

## 字段描述 issue（简判）
- MISSING：空/null/占位（无、待补充、N/A、暂无描述等）
- INACCURATE：与语义明显不符、过短(<10 字且无实质信息)、仅重复技术名、与类型明显矛盾
- INCOMPLETE：有字但缺业务含义/取值或典型使用场景（在输入信息足以推断时）
- 否则 ACCURATE → 不写入 `fields_need_completion`

## 字段级补全触发
- `field_business_name` 空/null/非中文 → 必须 `suggested_business_name`（简洁中文）。
- `field_role` 空/null → 必须 `suggested_field_role`（1–8）。
- 字段需 issue 且需要改写描述时 → 必须 `suggested_description`（MISSING 几乎必给）。

## 角色编码（整数 1–8）
1 业务主键 2 关联标识 3 业务状态 4 时间 5 业务指标 6 业务特征 7 审计 8 技术

## 视图级补全
- 视图 `view_business_name` 空/null/非中文 → `view_need_completion.need_completion=true` 且按需 `suggested_business_name`。
- 视图 `desc` 触发 MISSING/INACCURATE/INCOMPLETE → 按需 `suggested_description`。
- `need_completion` 为 false 时，`view_need_completion` 可仅含键 `need_completion` 且值为 false（勿嵌套多余键）。
- `need_completion=true` 时必填：`current_business_name`、`current_description`、`issue_type`、`issue_reason`，以及按需的 `suggested_*`。

## `fields_need_completion` 单条
必填：`field_id`、`field_tech_name`、`field_business_name`、`field_role`、`issue_type`、`current_description`（与输入 `field_desc` 一致）、`issue_reason`（**一句短因**，建议≤40字）。
按需：`suggested_description`、`suggested_business_name`、`suggested_field_role`。

## 根结构键名（须齐全）
根级含 `views`（数组）与 `summary`（对象）。每个 view 须含：`view_id`,`view_tech_name`,`view_business_name`,`desc`,`view_need_completion`,`fields_need_completion`,`summary`。

## 用户输入
{{input_data}}

## 背景（空则忽略）
{{background}}
"""

prompt_template_en_deepseek_v32 = """
[Task] Semantic completion quality check. Your only valid output: one JSON object (single root object, parseable as JSON, no wrapper).

## Hard constraints
1. No markdown (no ```), no text before/after JSON, no comments, no trailing commas.
2. No chain-of-thought, no step lists, no self-check narration.
3. `views` must mirror the input 1:1 in order and length—no extra/missing views.
4. `view_id`, `view_tech_name`, `field_id` must match input **verbatim** (including empty strings; `field_id` may be short numeric strings).
5. Top-level per-view `view_business_name` and `desc`: if `view_need_completion.need_completion` is false, copy **exactly** from input; if true, set to the **final** values (same as `suggested_*` you provide).
6. `fields_need_completion` contains **only** non-ACCURATE fields; omit ACCURATE fields entirely.
7. `issue_type` must be exactly one of: MISSING, INACCURATE, INCOMPLETE.
8. Echo `field_role` from input (including null); when rules require filling role, add integer `suggested_field_role` in 1–8.
9. Do not invent views/fields; do not paste the full input or full `fields` arrays.

## Counts (must be consistent integers)
Per view: `total_fields` = input `fields` length; `need_completion_count` = length of `fields_need_completion`; `accurate_count` = `total_fields - need_completion_count` (≥0).
Root: `total_views` = len(views); `total_fields` / `need_completion_count` / `accurate_count` = sums across views.

## Field issues, business names, roles, view-level fixes
Same criteria as the Chinese template: MISSING/INACCURATE/INCOMPLETE vs ACCURATE; non-Chinese/empty field business name → `suggested_business_name`; empty role → `suggested_field_role`; weak view name/desc → `view_need_completion` with suggestions. For MISSING issues that need a rewrite, provide `suggested_description`. Keep `issue_reason` to one short sentence (≤ ~40 Chinese chars equivalent).

## Root keys
Root contains `views` (array) and `summary` (object). Each view must include: `view_id`,`view_tech_name`,`view_business_name`,`desc`,`view_need_completion`,`fields_need_completion`,`summary`.

## User input
{{input_data}}

## Background (optional)
{{background}}
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}

prompts_deepseek_v32 = {
    "cn": prompt_template_cn_deepseek_v32.strip() + "\n\n" + prompt_suffix["cn"] + " 输出：仅 JSON。",
    "en": prompt_template_en_deepseek_v32.strip() + "\n\n" + prompt_suffix["en"] + " Output: JSON only.",
}


class SemanticCompletePrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    input_data: list = []
    background: str = ""
    model_type: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _use_deepseek_v32_prompt(model_type: str) -> bool:
        mt = (model_type or "").lower().strip()
        if not mt:
            return False
        if mt == ModelType4Prompt.DEEPSEEK_V32.value:
            return True
        return mt.startswith("deepseek-v3.2") or mt.startswith("deepseek-v3-2")

    def custom_template(self) -> str:
        if self._use_deepseek_v32_prompt(self.model_type):
            return prompts_deepseek_v32.get(self.language) or prompts_deepseek_v32["cn"]
        return self.get_prompt(self.language)
