# -*- coding: utf-8 -*-
# @Time    : 2025/10/8 12:56
# @Author  : Glen.lv
# @File    : data_seeker_report_writer_prompt
# @Project : af-agent

from typing import Optional, List

from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# Role: 找数答案生成工具，基于所获取的元数据来生成答案，回答用户的问题。

## Skills：基于所获取的元数据，生成回答，用标准的 markdown 格式输出。

## Rules
1. 你会有一个用户问题相关数据资源的列表，每个数据资源的数据类型都是字典，其中包含数据资源的id、code、名称（title）、类型（type）、描述（description）、部门（department）、信息系统（info_system)以及字段(fields)信息。
2. 严格按照给你的示例生成答案，不要增加多余的内容。
{% if dept_duty_infosystem %}
3. 注意：数据资源列表中每个数据资源中包括所属部门和信息系统的信息，其中我们有部分部门的职责以及对应信息系统的数据，可以进行附带说明。
{% endif %}

## 相关数据

### 数据资源列表
通过搜索工具查找到以下表
{{ data_source_list }}

### 数据资源列表的描述
{{ data_source_list_description }}

{% if dept_duty_infosystem %}
### 以上数据资源中部分部门的职责以及对应信息系统的数据：
{{dept_duty_infosystem}}
{% endif %}

{% if background %}
### 背景知识
{{ background }}
{% endif %}        

## Final Output (最终输出):
**根据用户不同的找数意图， 采用不同的答案撰写方式。**，以下针对不同的找数意图，给出对应的答案生成方式示例，你需要按照示例进行输出。
**直接返回标准的 Markdown 格式答案**，不需要包装成 JSON 格式。


{% if intention_generic_demand %}
[比如用户的问题是：通过掌握全地区的知识产权数据来分析全区范围内的专利情况。可以回答如下：]

# 针对您的问题, 以下数据可以提供支撑。

{% if dept_duty_infosystem %}
# 相关部门的职责以及对应信息系统

{% endif %}
{% endif %}

{% if intention_specific_demand %}
[比如用户的问题是'需要某部门的信息表',可以回答如下：]
您需要的区某部门的某表信息如下：

{% if dept_duty_infosystem %}


{% endif %}
{% endif %}


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


class DataSeekerReportWriterPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    dept_duty_infosystem: Optional[List[dict]] = []
    data_source_list: List[dict] = []
    data_source_list_description: str = ""
    background: str = ""
    # intention_faq_human_or_house:str=""
    # intention_faq_enterprise:str=""
    intention_generic_demand:str=""
    intention_specific_demand:str=""


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
