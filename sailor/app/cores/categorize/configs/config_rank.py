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


class Params(BaseModel):
    index: str = Field(..., description='opensearch检索的索引', example='entity_index')
    vector_search: VectorParams = Field(..., description='向量检索参数')
    includes: list = Field(['id', 'name'], description='opensearch检索结果返回字段')


PROPS = {
    'index': 'entity_subject_property',
    'vector_search': {
        'field': 'path-vector',
        'min_score': 0,
        'size': 20
    },
    'includes': ['id', 'name', 'path', 'path_id', 'standard_id']
}


rank_params = Params(**PROPS)


if __name__ == '__main__':
    pass