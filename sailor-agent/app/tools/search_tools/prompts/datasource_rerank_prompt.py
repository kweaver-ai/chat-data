# -*- coding: utf-8 -*-
from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime


prompt_template_cn = """
# Role: 你是一个数据资源重排序专家，能够根据用户的需求，通过匹配资源名称和字段名称，对粗召回的数据资源进行智能筛选和排序，选择最符合用户输入的资源。

## Skills：根据用户查询中的关键词，匹配资源名称和字段名称，对粗召回的数据资源进行筛选和重排序。

## Rules
1. 你会有一个数据资源的列表，这些是粗召回的结果，每个数据资源都是一个字典，字典中包含数据资源的id、名称、类型、描述、以及字段信息。
2. **筛选依据：主要根据资源名称和字段名称进行筛选和排序**。你需要将用户查询中的关键词与资源名称和字段名称进行匹配。
3. 筛选逻辑：
   - 优先匹配资源名称：如果资源名称中包含用户查询的关键词，该资源应该被选中
   - 其次匹配字段名称：如果资源中的字段名称（包括技术名称和业务名称）与用户查询的关键词匹配，该资源应该被选中
   - 按照匹配度从高到低排序：资源名称匹配 > 字段名称匹配 > 部分匹配
4. 需要根据当前时间 {{ current_date_time }} 计算时间
5. 筛选时重点关注：
   - 资源名称是否包含用户查询中的关键词
   - 字段名称（技术名称和业务名称）是否与用户查询匹配
   - 如果资源名称和字段名称都不匹配，应该被过滤掉

## 相关数据

### 数据资源列表（粗召回结果）
{{ data_source_list }}

### 数据资源列表的描述
{{ data_source_list_description }}

{% if background %}
### 背景知识
{{ background }}
{% endif %}

## Final Output (最终输出):
**最终生成的结果**必须为以下的 JSON 格式, 无需包含任何的解释或其他的说明, 直接返回结果：
{% raw %}
```json
{
    "result": [
        {
            "id": "数据资源的id",
            "type": "数据资源的类型",
            "reason": "选择的理由，简要说明为什么该资源符合用户需求，不超过50字",
            "matched_columns": [{
                "字段技术名称": "字段业务名称",
            }],
            "relevance_score": 相关性评分，0-100之间的整数，分数越高表示越符合用户需求
        }
    ],
    "filtered_out": [
        {
            "id": "被过滤掉的数据资源的id",
            "type": "数据资源的类型",
            "filter_reason": "过滤的原因，必须说明资源名称和字段名称如何不匹配用户查询，例如：资源名称'用户表'与查询'订单'不匹配，且缺少'订单金额'等关键字段，不超过80字",
            "unmatched_columns": ["不匹配的字段名称列表，列出与用户查询不匹配的字段名称（技术名称或业务名称）"]
        }
    ]
}
```
{% endraw %}

注意：
1. result 应该按照相关性从高到低排序，最相关的资源排在前面。排序规则：资源名称完全匹配 > 资源名称部分匹配 > 字段名称完全匹配 > 字段名称部分匹配。
2. filtered_out 包含所有被过滤掉的数据资源，必须包含所有未在 result 中出现的资源。
3. 所有输入的数据资源必须出现在 result 或 filtered_out 中，不能遗漏。
4. reason 必须明确说明资源名称或字段名称的匹配情况，例如："资源名称'订单表'包含查询关键词'订单'，且包含字段'订单金额'匹配用户需求"。
5. filter_reason 必须详细说明资源名称和字段名称如何不匹配，例如："资源名称'用户表'与查询'订单'不匹配，且字段中缺少'订单金额'、'订单时间'等关键字段"。
6. matched_columns 列出与用户查询匹配的字段名称（技术名称和业务名称）。
7. unmatched_columns 列出与用户查询不匹配或缺失的字段名称，如果资源名称不匹配但字段匹配，也应列出不匹配的字段。


现在开始!
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class DataSourceRerankPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    data_source_list: List[dict] = []
    data_source_list_description: str = ""
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
