"""
@File: config_recall.py
@Date:2024-03-12
@Author : Danny.gao
@Desc:
"""

from typing import List
from pydantic import BaseModel, Field


class VectorParams(BaseModel):
    field: str = Field('name-vector', description='类型为knn vector的字段')
    min_score: float = Field(1.75, description='检索得分阈值')
    size: int = Field(100, description='opensearch检索返回条数')


class KeywordParams(BaseModel):
    fields: list = Field(['name^10', 'description'], description='关键字检索的字段')
    min_score: float = Field(1.75, description='检索得分阈值')
    size: int = Field(100, description='opensearch检索返回条数')


class Params(BaseModel):
    index: str = Field(..., description='opensearch检索的索引', example='entity_index')
    vector_search: VectorParams = Field(..., description='向量检索参数')
    keyword_search: KeywordParams = Field(..., description='关键字检索参数')
    includes: list = Field(['id', 'name'], description='opensearch检索结果返回字段')
    opensearch_must: List[dict] = Field([], description='opensearch 查询时必须需满足的条件')


RECOMMEND_TABLE_PROPS = {
    'index': 'entity_form',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['id', 'name', 'business_model_id'],
    'opensearch_must': []
}

RECOMMEND_FLOW_PROPS = {
    'index': 'entity_flowchart',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description', 'business_model_id'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['id', 'name'],
    'opensearch_must': []
}

RECOMMEND_CODE_PROPS = {
    'index': 'entity_data_element',
    'vector_search': {
        'field': 'name_cn-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ['name_cn^10', 'name_en^10', 'description'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['code', 'name_cn', 'std_type', 'department_ids'],
    'opensearch_must': []
}

RECOMMEND_CHECK_CODE_PROPS = {
    'index': 'entity_field',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['id', 'name', 'business_form_id', 'business_form_name', 'standard_id'],
    'opensearch_must': []
    # 'opensearch_must': [
    #     {
    #         "exists": {
    #             "field": "standard_id"
    #         }
    #     }
    # ]
}

RECOMMEND_CHECK_INDICATOR_PROPS = {
    'index': 'entity_business_indicator',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['id', 'name', 'description', 'calculation_formula', 'unit', 'statistics_cycle',
                 'statistical_caliber', 'business_model_id'],
    'opensearch_must': []
}

RECOMMEND_VIEW_PROPS = {
    'index': 'entity_form_view',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.95,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0.95,
        'size': 10
    },
    'includes': ['id', 'name', 'type'],
    'opensearch_must': []
}

RECOMMEND_LABEL_PROPS = {
    'index': 'entity_label',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'category_description', 'category_name'],
        'min_score': 0,
        'size': 10
    },
    'includes': ['id', 'name', 'category_id', 'category_name', 'category_range_type'],
    'opensearch_must': []
}

RECOMMEND_FIELD_RULE_PROPS = {
    'index': 'entity_rule',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0,
        'size': 10
    },
    'includes': ['id', 'name', 'org_type', 'description', 'rule_type', 'expression', "department_ids"],
    'opensearch_must': []
}

RECOMMEND_EXPLORE_RULE_PROPS = {
    'index': 'entity_rule',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0,
        'size': 10
    },
    'includes': ['id', 'name', 'org_type', 'description', 'rule_type', 'expression'],
    'opensearch_must': []
}

RECOMMEND_FIELD_SUBJECT_PROPS = {
    'index': 'entity_subject_property',
    'vector_search': {
        'field': 'name-vector',
        'min_score': 0.75,
        'size': 10
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0,
        'size': 10
    },
    'includes': ['id', 'name', 'org_type', 'description', 'rule_type', 'expression'],
    'opensearch_must': []
}

recall_table_params = Params(**RECOMMEND_TABLE_PROPS)
recall_flow_params = Params(**RECOMMEND_FLOW_PROPS)
recall_code_params = Params(**RECOMMEND_CODE_PROPS)
recall_view_params = Params(**RECOMMEND_VIEW_PROPS)
recall_label_params = Params(**RECOMMEND_LABEL_PROPS)   #1
recall_field_rule_params = Params(**RECOMMEND_FIELD_RULE_PROPS) #5
recall_explore_rule_params = Params(**RECOMMEND_EXPLORE_RULE_PROPS) #6 + 生成

recall_check_code_params = Params(**RECOMMEND_CHECK_CODE_PROPS) #3 + 校验
recall_check_indicator_params = Params(**RECOMMEND_CHECK_INDICATOR_PROPS) #4 + 校验

recall_field_subject_params = Params(**RECOMMEND_FIELD_SUBJECT_PROPS) #2 + 对齐


if __name__ == '__main__':
    print(recall_table_params.index)
    print(recall_table_params.vector_search)
    print(recall_table_params.vector_search.field)
    print(recall_table_params.vector_search.min_score)
    print(recall_table_params.vector_search.size)