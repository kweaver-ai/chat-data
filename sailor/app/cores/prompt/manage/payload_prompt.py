from app.cores.prompt.qa import SELECT_INTERFACE_TEMPLATE, GENERATE_ANSWER_CONCLUSION_TEMPLATE
from app.cores.prompt.text2sql import (
    GENERATE_SQL_TEMPLATE,
    CONSISTENCY_CHECK_TEMPLATE_FIRST,
    CONSISTENCY_CHECK_TEMPLATE_SECOND,
    PARTICIPLE_TEMPLATE
)
from app.cores.prompt.search import (
    ALL_TABLE_TEMPLATE, OLD_ALL_TABLE_TEMPLATE, ALL_TABLE_TEMPLATE_KECC,
    ALL_INTERFACE_TEMPLATE, ALL_INDICATOR_TEMPLATE,
    # ENHANCE_TABLE_TEMPLATE,
    # ALL_TABLE_TEMPLATE_HISTORY_QA_KECC
)
from app.cores.prompt.text2sql import GENERATE_SQL_TEMPLATE, SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME, \
    SAMPLE_GENERATE_PROMPT_TEMPLATE,SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME,SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE
from app.cores.prompt.understand import TABLE_UNDERSTAND_PROMPT, TABLE_UNDERSTAND_ONLY_FOR_TABLE_PROMPT
from app.cores.prompt.recommend import COMMON_FILTER_PROMPT, COMMON_CHECK_PROMPT, COMMON_ALIGN_PROMPT, COMMON_GENERATE_PROMPT
from app.cores.prompt.comprehension import (
    COMPREHENSION_TEMPLATE, COMPREHENSION_RELATION_TEMPLATE, COMPREHENSION_TEMPLATE_YWWD,
    COMPREHENSION_TEMPLATE_ZMZC, COMPREHENSION_TEMPLATE_FMZC, COMPREHENSION_TEMPLATE_FWFW,
    COMPREHENSION_TEMPLATE_FWLY, COMPREHENSION_TEMPLATE_BHKZ, COMPREHENSION_TEMPLATE_CJTD,
    COMPREHENSION_TEMPLATE_TIME, COMPREHENSION_TEMPLATE_LOACL, COMPREHENSION_TEMPLATE_CITY
)

prompt_map = {
    "text2sql": GENERATE_SQL_TEMPLATE,
    "all_table": ALL_TABLE_TEMPLATE,
    "all_interface": ALL_INTERFACE_TEMPLATE,
    "all_indicator": ALL_INDICATOR_TEMPLATE,
    "select_interface": SELECT_INTERFACE_TEMPLATE,
    "conclusion_interface_result": GENERATE_ANSWER_CONCLUSION_TEMPLATE,
    "consistency_check_first": CONSISTENCY_CHECK_TEMPLATE_FIRST,
    "consistency_check_second": CONSISTENCY_CHECK_TEMPLATE_SECOND,
    "participle": PARTICIPLE_TEMPLATE,
    "old_all_table": OLD_ALL_TABLE_TEMPLATE,
    SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME: SAMPLE_GENERATE_PROMPT_TEMPLATE,
    SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME: SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE,
    "table_understand_only_for_table": TABLE_UNDERSTAND_ONLY_FOR_TABLE_PROMPT,
    "table_understand": TABLE_UNDERSTAND_PROMPT,
    'recommend_filter': COMMON_FILTER_PROMPT,
    'recommend_check': COMMON_CHECK_PROMPT,
    'recommend_align': COMMON_ALIGN_PROMPT,
    'recommend_generate': COMMON_GENERATE_PROMPT,
    "comprehension_template": COMPREHENSION_TEMPLATE,
    "comprehension_relation_template": COMPREHENSION_RELATION_TEMPLATE,
    "comprehension_template_ywwd": COMPREHENSION_TEMPLATE_YWWD,  # 数据理解-业务维度
    "comprehension_template_zmzc": COMPREHENSION_TEMPLATE_ZMZC,  # 数据理解-正面支撑
    "comprehension_template_fmzc": COMPREHENSION_TEMPLATE_FMZC,  # 数据理解-负面支撑
    "comprehension_template_fwfw": COMPREHENSION_TEMPLATE_FWFW,  # 数据理解-服务范围
    "comprehension_template_fwly": COMPREHENSION_TEMPLATE_FWLY,  # 数据理解-服务领域
    "comprehension_template_bhkz": COMPREHENSION_TEMPLATE_BHKZ,  # 数据理解-保护控制
    "comprehension_template_cjtd": COMPREHENSION_TEMPLATE_CJTD,  # 数据理解-促进推动
    "comprehension_template_time": COMPREHENSION_TEMPLATE_TIME,  # 数据理解-时间字段理解
    "comprehension_template_local": COMPREHENSION_TEMPLATE_LOACL,  # 数据理解-空间字段理解
    "comprehension_template_city":COMPREHENSION_TEMPLATE_CITY,  # 数据理解-空间范围
    # "comprehension_template_business_objects":COMPREHENSION_TEMPLATE_BUSINESS_OBJECTS #数据理解-业务对象
    "all_table_kecc": ALL_TABLE_TEMPLATE_KECC,  # 基于部门职责的知识增强
    # "enhance_table_template":ENHANCE_TABLE_TEMPLATE,  # 基于历史问答对的知识增强
    # "all_table_history_qa_kecc":ALL_TABLE_TEMPLATE_HISTORY_QA_KECC # 整合基于历史问答对的知识增强和基于部门职责的知识增强
}

payload = [
    {
        "prompt_item_name": "AnyFabric",
        "prompt_item_type_name": "af-sailor",
        "prompt_list": [
            {
                "prompt_name": "text2sql",
                "prompt_desc": "生成SQL",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": GENERATE_SQL_TEMPLATE,
                "variables": [
                    {
                        "var_name": "ddl_and_sample",
                        "field_name": "ddl_and_sample",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "error_code",
                        "field_name": "error_code",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "background",
                        "field_name": "background",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": SAMPLE_GENERATE_PROMPT_TEMPLATE_NAME,
                "prompt_desc": "用于根据结构化数据库表schema生产数据样例的prompt模板",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": SAMPLE_GENERATE_PROMPT_TEMPLATE,
                "variables": [
                    {
                        "var_name": "schema",
                        "field_name": "schema",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "sample_size",
                        "field_name": "sample_size",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "column_detail_info",
                        "field_name": "column_detail_info",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE_NAME,
                "prompt_desc": "用于根据结构化数据库表schema生成数据样例的prompt模板",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": SAMPLE_GENERATE_WITH_SAMPLES_PROMPT_TEMPLATE,
                "variables": [
                    {
                        "var_name": "schema",
                        "field_name": "schema",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "sample_size",
                        "field_name": "sample_size",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "column_detail_info",
                        "field_name": "column_detail_info",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "samples",
                        "field_name": "samples",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "all_table",
                "prompt_desc": "查询整套数据库",
                "prompt_type": "Completion",
                "icon": "2",
                "messages": ALL_TABLE_TEMPLATE,
                "variables": [
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "all_table_kecc",
                "prompt_desc": "查询整套逻辑视图-部门职责知识增强",
                "prompt_type": "Completion",
                "icon": "2",
                "messages": ALL_TABLE_TEMPLATE_KECC,
                "variables": [
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "dept_infosystem_duty",
                        "field_name": "dept_infosystem_duty",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },

            {
                "prompt_name": "old_all_table",
                "prompt_desc": "查询整套数据库适配大模型1.5",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": OLD_ALL_TABLE_TEMPLATE,
                "variables": [
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "all_interface",
                "prompt_desc": "查询整套接口服务",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": ALL_INTERFACE_TEMPLATE,
                "variables": [
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "all_indicator",
                "prompt_desc": "查询指标",
                "prompt_type": "Completion",
                "icon": "4",
                "messages": ALL_INDICATOR_TEMPLATE,
                "variables": [
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "select_interface",
                "prompt_desc": "挑选能够回答问题的接口服务",
                "prompt_type": "Completion",
                "icon": "5",
                "messages": SELECT_INTERFACE_TEMPLATE,
                "variables": [
                    {
                        "var_name": "Dataset",
                        "field_name": "Dataset",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "UserQuestion",
                        "field_name": "UserQuestion",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "conclusion_interface_result",
                "prompt_desc": "调用接口服务获取结果，通过模型总结答案",
                "prompt_type": "Completion",
                "icon": "6",
                "messages": GENERATE_ANSWER_CONCLUSION_TEMPLATE,
                "variables": [
                    {
                        "var_name": "UserQuestion",
                        "field_name": "UserQuestion",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "Answer",
                        "field_name": "Answer",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "consistency_check_first",
                "prompt_desc": "校验问题和sql的一致性，第一阶段",
                "prompt_type": "Completion",
                "icon": "7",
                "messages": CONSISTENCY_CHECK_TEMPLATE_FIRST,
                "variables": [
                    {
                        "var_name": "question",
                        "field_name": "question",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "result",
                        "field_name": "result",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "sql",
                        "field_name": "sql",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "consistency_check_second",
                "prompt_desc": "校验问题和sql的一致性，第二阶段",
                "prompt_type": "Completion",
                "icon": "7",
                "messages": CONSISTENCY_CHECK_TEMPLATE_SECOND,
                "variables": [
                    {
                        "var_name": "question",
                        "field_name": "question",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "result",
                        "field_name": "result",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "participle",
                "prompt_desc": "对文本进行分话",
                "prompt_type": "Completion",
                "icon": "8",
                "messages": PARTICIPLE_TEMPLATE,
                "variables": [
                    {
                        "var_name": "text",
                        "field_name": "text",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "table_understand",
                "prompt_desc": "逻辑视图业务语义自动填充：同时生成整表的业务含义和字段的中文名称、业务含义",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": TABLE_UNDERSTAND_PROMPT,
                "variables": [
                    {
                        "var_name": "user_data",
                        "field_name": "user_data",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "field_ids",
                        "field_name": "field_ids",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "table_understand_only_for_table",
                "prompt_desc": "逻辑视图业务语义自动填充：只生成整表的业务含义",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": TABLE_UNDERSTAND_ONLY_FOR_TABLE_PROMPT,
                "variables": [
                    {
                        "var_name": "user_data",
                        "field_name": "user_data",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "recommend_filter",
                "prompt_desc": "从大量相关与无关的搜索结果中，精准筛选出真正关键的信息",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": COMMON_FILTER_PROMPT,
                "variables": [
                    {
                        "var_name": "input_datas",
                        "field_name": "input_datas",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "recommend_check",
                "prompt_desc": "根据业务含义是否一致、相似来实现业务数据分组聚合",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": COMMON_CHECK_PROMPT,
                "variables": [
                    {
                        "var_name": "input_datas",
                        "field_name": "input_datas",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "recommend_align",
                "prompt_desc": "根据业务含义是否一致、相似来实现业务数据一对一匹配",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": COMMON_ALIGN_PROMPT,
                "variables": [
                    {
                        "var_name": "input_datas",
                        "field_name": "input_datas",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "recommend_generate",
                "prompt_desc": "根据数据业务含义生成相关数据",
                "prompt_type": "Completion",
                "icon": "1",
                "messages": COMMON_GENERATE_PROMPT,
                "variables": [
                    {
                        "var_name": "input_datas",
                        "field_name": "input_datas",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "role_skills",
                        "field_name": "role_skills",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "examples",
                        "field_name": "examples",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "role_tasks",
                        "field_name": "role_tasks",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template",
                "prompt_desc": "数据理解",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_relation_template",
                "prompt_desc": "数据理解，理解各个表之间的可能的复合表达",
                "prompt_type": "Completion",
                "icon": "2",
                "messages": COMPREHENSION_RELATION_TEMPLATE,
                "variables": [
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }

                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_ywwd",
                "prompt_desc": "数据理解——业务维度",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_YWWD,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_zmzc",
                "prompt_desc": "数据理解——正面支撑",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_ZMZC,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_fmzc",
                "prompt_desc": "数据理解——负面支撑",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_FMZC,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_fwfw",
                "prompt_desc": "数据理解——服务范围",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_FWFW,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_fwly",
                "prompt_desc": "数据理解——服务领域",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_FWLY,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_bhkz",
                "prompt_desc": "数据理解——保护控制",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_BHKZ,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_cjtd",
                "prompt_desc": "数据理解——促进推动",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_CJTD,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_time",
                "prompt_desc": "数据理解——时间字段理解",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_TIME,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_local",
                "prompt_desc": "数据理解——空间字段理解",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_LOACL,
                "variables": [
                    {
                        "var_name": "description",
                        "field_name": "description",
                        "optional": False,
                        "field_type": "textarea"
                    },
                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }, {
                        "var_name": "data_dict",
                        "field_name": "data_dict",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            },
            {
                "prompt_name": "comprehension_template_city",
                "prompt_desc": "数据理解——空间范围",
                "prompt_type": "Completion",
                "icon": "3",
                "messages": COMPREHENSION_TEMPLATE_CITY,
                "variables": [

                    {
                        "var_name": "query",
                        "field_name": "query",
                        "optional": False,
                        "field_type": "textarea"
                    }
                ],
                "opening_remarks": ""
            }
            # },
            # {
            #     "prompt_name": "comprehension_template_business_objects",
            #     "prompt_desc": "数据理解——业务对象",
            #     "prompt_type": "Completion",
            #     "icon": "3",
            #     "messages": COMPREHENSION_TEMPLATE_BUSINESS_OBJECTS,
            #     "variables": [
            #         {
            #             "var_name": "description",
            #             "field_name": "description",
            #             "optional": False,
            #             "field_type": "textarea"
            #         },
            #         {
            #             "var_name": "query",
            #             "field_name": "query",
            #             "optional": False,
            #             "field_type": "textarea"
            #         }, {
            #             "var_name": "data_dict",
            #             "field_name": "data_dict",
            #             "optional": False,
            #             "field_type": "textarea"
            #         },
            #         {
            #             "var_name": "subject_domains",
            #             "field_name": "description",
            #             "optional": False,
            #             "field_type": "textarea"
            # #         },
            #     ],
            #     "opening_remarks": ""
            # }
        ]
    }
]
