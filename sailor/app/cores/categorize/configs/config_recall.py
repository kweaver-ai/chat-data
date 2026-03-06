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
    size: int = Field(3, description='opensearch检索返回条数')

class KeywordParams(BaseModel):
    fields: list = Field(['name^10', 'description'], description='关键字检索的字段')
    min_score: float = Field(1.75, description='检索得分阈值')
    size: int = Field(100, description='opensearch检索返回条数')


class Params(BaseModel):
    index: str = Field(..., description='opensearch检索的索引', example='entity_index')
    top_n: float = Field(..., description='召回条数')
    vector_search: VectorParams = Field(..., description='向量检索参数')
    keyword_search: KeywordParams = Field(..., description='关键字检索参数')
    includes: list = Field(['id', 'name'], description='opensearch检索结果返回字段')
    opensearch_must: List[dict] = Field([], description='opensearch 查询时必须需满足的条件')


PROPS = {
    'index': 'entity_subject_property',
    'top_n': 3.,
    'vector_search': {
        'field': 'name-vector',
        'min_score': 1.9,
        'size': 20
    },
    'keyword_search': {
        'fields': ["name^10", 'description'],
        'min_score': 0.75,
        'size': 10
    },
    'includes': ['id', 'name', 'path', 'path_id', 'standard_id'],
    'opensearch_must': []
}


recall_params = Params(**PROPS)


if __name__ == '__main__':
    pass