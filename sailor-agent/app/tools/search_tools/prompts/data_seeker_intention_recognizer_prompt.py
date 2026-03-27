# -*- coding: utf-8 -*-
# @Time    : 2025/10/13 14:27
# @Author  : Glen.lv
# @File    : data_seeker_intention_recognizer_prompt
# @Project : af-agent


from typing import Optional, List

from app.tools.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# Role: 用户问题理解、意图识别工具，识别用户问题中提及的实体和关系，对用户问题的意图进行判断。

## Skills：识别用户问题中提及的实体和关系，对用户问题的意图进行判断。


## Rules
1. 你会有一个部门和信息系统列表，每个部门有一个或多个信息系统。
2. 你会有一个对部门和信息系统列表的简单描述，是一些补充信息。
3. 你会有一个主题列表， 是部分数据资源所属的主题，你识别出的主题 `mentioned_subject` 必须在这个列表范围内。
3. 需要根据用户的问题（或者称为查询语句），识别用户问题中提及的实体和关系。
4. 根据用户问题中提及的部门和信息系统，判断用户问题是否在部门和信息系统的范围内, 只能是以下三种情况之一：'用户问题中提及的部门和（或）信息系统在范围内'、'用户问题中未明确提及具体的部门和（或）信息系统'、'用户问题中提及的部门和（或）信息系统不在范围内'。
5. 判断用户问题的意图是'{{intention_generic_demand}}'、'{{intention_specific_demand}}'、'{{intention_out_of_scope}}'这几种意图中的哪一种,如果你认为用户问题的意图不属于以上这些情况，则为未知意图，输出结果中`intent`的值为'{{intention_unknown}}'。
6. 如果用户的问题是指明要具体的部门、信息系统、表和字段，问题中提供的信息可以精准定位到少数具体的部门、信息系统、表和字段，那么输出结果中意图`intent`的值一定是'{{intention_specific_demand}}'。
7. 如果用户的问题比较宽泛，没有知名具体的部门、信息系统、表和字段，那么输出结果中意图`intent`的值为一定是'{{intention_generic_demand}}'。
8. 只有用户的问题提及了具体的部门和信息系统， 并且不在范围内， 同时`is_within_the_scope_of_department_infosystem`的值必须为'用户问题中提及的部门和（或）信息系统不在范围内'。才能判断输出结果中意图`intent`的值为'{{intention_out_of_scope}}'， 如果用户的问题没有明确提及具体的部门或信息系统，那么一定不是'{{intention_out_of_scope}}'。
9. 如果你判断用户问题的意图不是以上这些情况， 则为未知意图，输出结果中`intent`的值为'{{intention_unknown}}'。

## 相关数据

### 部门和信息系统列表
{{ data_scope_dept_infosystem }}

### 部门和信息系统列表的描述
{{ data_scope_dept_infosystem_description }}

### 主题列表，你识别出的主题 `mentioned_subject` 必须在这个范围内。
["知识产权库","专利库"]

{% if background %}
### 背景知识
{{ background }}
{% endif %}

## Final Output (最终输出):
**最终生成的结果**必须为以下的 JSON 格式, 无需包含任何的解释或其他的说明, 直接返回结果，如下所示：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": ["用户问题中提及的时间范围， 如果没有提及，则为空"],
                "mentioned_region": ["用户问题中提及的地域范围， 如果没有提及，则为空"],
                "mentioned_department": ["用户问题中提及的部门名称， 如果没有提及，则为空"],
                "mentioned_info_system": ["用户问题中提及的信息系统名称， 如果没有提及，则为空"],
                "mentioned_subject": ["用户问题中提及的主题名称， 如果没有提及，则为空"],
                "mentioned_topic": ["用户问题中提及的专题需求， 如果没有提及，则为空"],
                "mentioned_tables": ["用户问题中提及的逻辑视图（表）名称， 如果没有提及，则为空"],
                "mentioned_fields": ["用户问题中提及的字段名称， 如果没有提及，则为空"]
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": ["用户问题中提及的部门和信息系统之间的关系， 如果没有提及，则为空字符串"],
                "mentioned_relation_between_info_system_and_tables": ["用户问题中提及的信息系统和逻辑视图（表）之间的关系， 如果没有提及，则为空字符串"],
                "mentioned_relation_between_tables_and_fields": ["用户问题中提及的逻辑视图（表）和字段之间的关系， 如果没有提及，则为空字符串"]
              },
              "is_within_the_scope_of_department_infosystem": "'用户问题中提及的部门和（或）信息系统不在范围内'/'用户问题中提及的部门和（或）信息系统在范围内'/'用户问题中未明确提及具体的部门和（或）信息系统'",
              "intent": "意图分类标签， 是'{{intention_generic_demand}}'、'{{intention_specific_demand}}'、'{{intention_out_of_scope}}'这几种意图中的哪一种,如果你认为用户问题的意图不属于以上这些情况，则为未知意图，意图分类标签即本项`intent`的值为'{{intention_unknown}}'。如果'is_within_the_scope_of_department_infosystem'的值是'用户问题中提及的部门和（或）信息系统不在范围内'，那么意图分类标签即本项`intent`的值是'{{intention_out_of_scope}}'",
              "confidence": "意图判断的置信度， 0-1的小数， 数值越大， 结论越可靠"
        }
    ]
}
```
### 其中判断用户问题是否在部门和信息系统的范围内的项`is_within_the_scope_of_department_infosystem`的值必须是以下三种之一：
1. "用户问题中提及的部门和（或）信息系统在范围内"
2. "用户问题中未明确提及具体的部门和（或）信息系统"
3. "用户问题中提及的部门和（或）信息系统不在范围内"

### 以下举例说明实体、关系、意图的判断方法：
1. 如果用户问题是"全地区的知识产权状况",则Final Output (最终输出)如下：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": [],
                "mentioned_region": ["全地区"],
                "mentioned_department": ["],
                "mentioned_info_system": [],
                "mentioned_subject": [],
                "mentioned_topic": ["知识产权状况"],
                "mentioned_tables": [],
                "mentioned_fields": ["知识产权状况"]
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": [],
                "mentioned_relation_between_info_system_and_tables": [],
                "mentioned_relation_between_tables_and_fields": ["知识产权状况"]
              },
              "is_within_the_scope_of_department_infosystem": "用户问题中未明确提及具体的部门和（或）信息系统",
              "intent": "{{intention_generic_demand}}",
              "confidence": 1
        }
    ]
}
```
2. 如果用户问题是"申请某平台，某表字段1、字段2、字段3数据",则Final Output (最终输出)如下：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": [],
                "mentioned_region": [],
                "mentioned_department": [],
                "mentioned_info_system": ["某平台"],
                "mentioned_subject": [],
                "mentioned_topic": [],
                "mentioned_tables": ["某表"],
                "mentioned_fields": ["字段1","字段2","字段3" ]
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": ["某平台"],
                "mentioned_relation_between_info_system_and_tables": ["某表"],
                "mentioned_relation_between_tables_and_fields": ["某表-字段1"，"某表-字段2"，"某表-字段3"]               
              },
              "is_within_the_scope_of_department_infosystem": "用户问题中提及的部门和（或）信息系统在范围内",
              "intent": "{{intention_specific_demand}}",
              "confidence": 1
        }
    ]
}
```

4. 如果用户问题是"需要全地区的知识产权数据来分析全地区范围内的专利情况等",则Final Output (最终输出)如下：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": [],
                "mentioned_region": ["全地区"],
                "mentioned_department": [],
                "mentioned_info_system": [],
                "mentioned_subject": [],
                "mentioned_topic": ["全地区的知识产权数据,分析全地区范围内的专利情况"],
                "mentioned_tables": [],
                "mentioned_fields": []
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": [],
                "mentioned_relation_between_info_system_and_tables": [],
                "mentioned_relation_between_tables_and_fields": []
              },
              "is_within_the_scope_of_department_infosystem": "用户问题中未明确提及具体的部门和（或）信息系统",
              "intent": "{{intention_generic_demand}}",
              "confidence": 0.95
        }
    ]
}
```

5. 如果用户问题是"申请某部门某系统的某数据",则Final Output (最终输出)如下：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": [],
                "mentioned_region": [],
                "mentioned_department": ["某部门"],
                "mentioned_info_system": ["某系统"],
                "mentioned_subject": [],
                "mentioned_topic": [],
                "mentioned_tables": [],
                "mentioned_fields": []
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": [],
                "mentioned_relation_between_info_system_and_tables": [],
                "mentioned_relation_between_tables_and_fields": []
              },
              "is_within_the_scope_of_department_infosystem": "用户问题中提及的部门和（或）信息系统不在范围内",
              "intent": "{{intention_out_of_scope}}",
              "confidence": 1
        }
    ]
}
```

6. 如果用户问题是"某地区知识产权的数据",则Final Output (最终输出)如下：
```json
{
    "result": [
         {
              "entities": {
                "mentioned_time": [],
                "mentioned_region": [],
                "mentioned_department": ["某部门"],
                "mentioned_info_system": [],
                "mentioned_subject": [],
                "mentioned_topic": [],
                "mentioned_tables": [],
                "mentioned_fields": []
              },
              "relations": {
                "mentioned_relation_between_department_and_info_system": [],
                "mentioned_relation_between_info_system_and_tables": [],
                "mentioned_relation_between_tables_and_fields": []
              },
              "is_within_the_scope_of_department_infosystem": "用户问题中提及的部门和（或）信息系统在范围内",
              "intent": "{{intention_generic_demand}}",
              "confidence": 1
        }
    ]
}
```

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


class DataSeekerIntentionRecognizerPrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    data_scope_dept_infosystem: List[dict] = []
    data_scope_dept_infosystem_description: str = ""
    background: str = ""
    # intention_faq_human_or_house: str = ""
    # intention_faq_enterprise: str = ""
    intention_generic_demand: str = ""
    intention_specific_demand: str = ""
    intention_out_of_scope: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
