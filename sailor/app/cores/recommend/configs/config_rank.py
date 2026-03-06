"""
@File: config_recall.py
@Date:2024-03-12
@Author : Danny.gao
@Desc:
"""

from pydantic import BaseModel, Field

from app.cores.recommend.common import ad_opensearch_connector


class IndexParams(BaseModel):
    index: str = Field(..., description='opensearch检索的索引', example='entity_index')
    query_field: str = Field(..., description='需要解析的字段名称', example='business_model_id')
    includes: list = Field(['id', 'name'], description='opensearch检索结果返回字段')


class VectorParams(BaseModel):
    index: str = Field(..., description='opensearch检索的索引', example='entity_index')
    field: str = Field('name-vector', description='类型为knn vector的字段')
    min_score: float = Field(1.75, description='检索得分阈值')
    size: int = Field(3, description='opensearch检索返回条数')
    includes: list = Field(['id', 'name'], description='opensearch检索结果返回字段')


class Params(BaseModel):
    entity_type: str = Field(..., description='实体类型')
    table2model: IndexParams = None
    model2domain: IndexParams = None
    domain2dept: IndexParams = None
    dept2self: IndexParams = None
    std_type: list = Field(..., description='排序结果按照此类型进行排序')
    # 表单推荐：不推荐字段个数=0的表单
    filter_num_search: VectorParams = None


RECOMMEND_TABLE_PROPS = {
    'entity_type': 'entity_form',
    'model2domain': {
        'index': 'entity_business_model',
        'query_field': 'business_model_id',
        'includes': ['id', 'name', 'domain_id']
    },
    'domain2dept': {
        'index': 'entity_domain_flow',
        'query_field': 'domain_id',
        'includes': ['id', 'name', 'path_id', 'department_id', 'business_system']
    },
    'dept2self': {
        'index': 'entity_department',
        'query_field': 'department_id',
        'includes': ['id', 'name', 'path_id']
    },
    'std_type': [],
    'filter_num_search': {
        'index': 'entity_field',
        'field': 'business_form_id',
        'min_score': 1,
        'size': 1,
        'includes': ['id', 'name', 'business_form_id']
    }
}

RECOMMEND_FLOW_PROPS = {
    'entity_type': 'entity_flowchart',
    'std_type': []
}

RECOMMEND_CODE_PROPS = {
    'entity_type': 'entity_data_element',
    # 国家4/地方3/行业2/企业1/团体0/国际5/国外6/其他99
    'std_type': [0.006, 0.007, 0.008, 0.009, 0.01, 0.005, 0.004, 0]
}

RECOMMEND_CHECK_CODE_PROPS = {
    'entity_type': 'entity_field',
    'table2model': {
        'index': 'entity_form',
        'query_field': 'business_form_id',
        'includes': ['id', 'name', 'business_model_id']
    },
    'model2domain': {
        'index': 'entity_business_model',
        'query_field': 'business_model_id',
        'includes': ['id', 'name', 'domain_id']
    },
    'domain2dept': {
        'index': 'entity_domain_flow',
        'query_field': 'domain_id',
        'includes': ['id', 'name', 'path_id', 'department_id', 'business_system']
    },
    'dept2self': {
        'index': 'entity_department',
        'query_field': 'department_id',
        'includes': ['id', 'name', 'path_id']
    },
    'std_type': []
}

RECOMMEND_CHECK_INDICATOR_PROPS = {
    'entity_type': 'entity_business_indicator',
    'std_type': []
}

RECOMMEND_VIEW_PROPS = {
    'entity_type': 'entity_form_view_field',
    'field_num_distance': 3,
    'filed_vector_search': {
        'index': 'entity_form_view_field',
        'field': 'name-vector',
        'min_score': 1.95,
        'size': 1,
        'includes': ['id', 'name', 'form_view_id']
    },
    'std_type': []
}

RECOMMEND_LABEL_PROPS = {
    'entity_type': 'entity_label',
    'std_type': []
}

RECOMMEND_FIELD_RULE_PROPS = {
    'entity_type': 'entity_rule',
    'std_type': []
}

RECOMMEND_EXPLORE_RULE_PROPS = {
    'entity_type': 'entity_rule',
    'std_type': []
}

RECOMMEND_FIELD_SUBJECT_PROPS = {
    'entity_type': 'entity_subject_property',
    'std_type': []
}

rank_table_params = Params(**RECOMMEND_TABLE_PROPS)
rank_flow_params = Params(**RECOMMEND_FLOW_PROPS)
rank_code_params = Params(**RECOMMEND_CODE_PROPS)
rank_view_params = Params(**RECOMMEND_VIEW_PROPS)
rank_label_params = Params(**RECOMMEND_LABEL_PROPS) #1
rank_field_rule_params = Params(**RECOMMEND_FIELD_RULE_PROPS)   #5
rank_explore_rule_params = Params(**RECOMMEND_EXPLORE_RULE_PROPS)   #6 + 生成

rank_check_code_params = Params(**RECOMMEND_CHECK_CODE_PROPS)   #3
rank_check_indicator_params = Params(**RECOMMEND_CHECK_INDICATOR_PROPS) #4

rank_field_subject_params = Params(**RECOMMEND_FIELD_SUBJECT_PROPS) #2 + 对齐



if __name__ == '__main__':
    print(rank_table_params.model2domain.index)
    print(rank_table_params.model2domain.includes)