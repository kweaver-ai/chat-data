# -*- coding: utf-8 -*-
"""
部门职责查询工具 - 三定职责判定 Prompt
"""

from typing import Optional, List
from data_retrieval.prompts.base import BasePrompt
from datetime import datetime

prompt_template_cn = """
# ROLE：部门职责分析专家

## 任务
根据用户的查询需求和搜索返回的部门职责结果，判定哪些三定职责（sub_dept_duty）与用户查询需求相关。

## 三定职责说明
三定职责是指内设机构的三定职责，是部门职责的细化，通常描述内设机构的具体职责范围和工作内容。

## 判定标准
1. **语义相关性**：三定职责的内容是否与用户查询需求在语义上相关
2. **职责匹配度**：三定职责是否直接或间接回答了用户的查询需求
3. **关键词匹配**：三定职责中是否包含用户查询的关键词或相关概念
4. **业务逻辑相关性**：三定职责是否与用户查询的业务场景相关

## 输出格式
```json
{
    "relevant_duties": [
        {
            "id": "结果项的id（对应输入的id）",
            "relevance_score": 相关性评分（0-100之间的整数，分数越高表示越相关）,
            "relevance_reason": "相关性判定理由，简要说明为什么该三定职责与用户查询相关，不超过100字",
            "sub_dept_duty": "内设机构三定职责（对应输入的sub_dept_duty）",
            "dept_name": "部门名称（对应输入的dept_name）",
            "dept_name_bdsp": "单位名称-大数据服务平台（对应输入的dept_name_bdsp，如果有）",
            "dept_duty": "部门职责（对应输入的dept_duty）",
            "info_system": "对应信息系统-目录链（对应输入的info_system，如果有）",
            "info_system_bdsp": "信息系统名称-大数据服务平台（对应输入的info_system_bdsp，如果有）"
        }
    ],
    "summary": {
        "total_count": 总结果数,
        "relevant_count": 相关三定职责数量,
        "avg_relevance_score": 平均相关性评分
    }
}
```

## 示例
用户查询："企业服务体系建设"

搜索返回结果：
```json
{
    "datas": [
        {
            "id": 669,
            "dept_name": "区经济委员会",
            "dept_name_bdsp": "申浦市泾南区经济委员会",
            "dept_duty": "拟订并落实企业服务政策，建立健全服务企业工作体系和服务网络，服务各类所有制企业，协调解决企业发展中的重大问题",
            "sub_dept_duty": "负责全区企业服务体系建设，指导各镇、街道、固泽工业区和相关园区的企业一体化服务体系、企业服务专员和企业之家建设",
            "duty_items": "指导工作",
            "info_system": "泾南区企业服务平台",
            "info_system_bdsp": "泾南区企业服务平台"
        },
        {
            "id": 670,
            "dept_name": "区经济委员会",
            "dept_name_bdsp": "申浦市泾南区经济委员会",
            "dept_duty": "拟订并落实企业服务政策，建立健全服务企业工作体系和服务网络，服务各类所有制企业，协调解决企业发展中的重大问题",
            "sub_dept_duty": "负责全区招商引资工作，制定招商引资政策，组织招商引资活动",
            "duty_items": "招商引资",
            "info_system": "泾南区企业服务平台",
            "info_system_bdsp": "泾南区企业服务平台"
        }
    ],
    "total_count": 2
}
```

输出：
```json
{
    "relevant_duties": [
        {
            "id": 669,
            "relevance_score": 95,
            "relevance_reason": "三定职责直接包含'企业服务体系建设'，与用户查询高度相关",
            "sub_dept_duty": "负责全区企业服务体系建设，指导各镇、街道、固泽工业区和相关园区的企业一体化服务体系、企业服务专员和企业之家建设",
            "dept_name": "区经济委员会",
            "dept_name_bdsp": "申浦市泾南区经济委员会",
            "dept_duty": "拟订并落实企业服务政策，建立健全服务企业工作体系和服务网络，服务各类所有制企业，协调解决企业发展中的重大问题",
            "info_system": "泾南区企业服务平台",
            "info_system_bdsp": "泾南区企业服务平台"
        }
    ],
    "summary": {
        "total_count": 2,
        "relevant_count": 1,
        "avg_relevance_score": 95
    }
}
```

## 用户查询
{{ query }}

## 搜索返回结果
```json
{{ search_results }}
```

{% if background %}
## 背景知识
{{ background }}
{% endif %}

请根据用户查询需求，判定搜索返回结果中哪些三定职责是相关的，只返回相关的三定职责，不相关的职责不需要返回。给出相关性评分和判定理由（仅JSON，无其他文字）。
"""

prompt_suffix = {
    "cn": "请用中文回答",
    "en": "Please answer in English"
}

prompts = {
    "cn": prompt_template_cn + prompt_suffix["cn"],
    "en": prompt_template_cn + prompt_suffix["en"]
}


class DepartmentDutyJudgePrompt(BasePrompt):
    templates: dict = prompts
    language: str = "cn"
    current_date_time: str = ""
    query: str = ""
    search_results: dict = {}
    background: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now_time = datetime.now()
        self.current_date_time = now_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 将search_results转换为JSON字符串，以便在模板中正确显示
        if isinstance(self.search_results, dict):
            import json
            self.search_results = json.dumps(self.search_results, ensure_ascii=False, indent=2)
