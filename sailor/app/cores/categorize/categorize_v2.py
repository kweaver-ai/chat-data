"""
@File: recommend.py
@Date:2024-03-11
@Author : Danny.gao
@Desc: 推荐接口
"""

import math

from app.logs.logger import logger
from app.dependencies.opensearch import OpenSearchClient
# from app.cores.categorize.models import categorize_recall, categorize_rank, categorize_filter
from app.tools.similarity import levenshtein_similarity


async def data_categorize_func(data):
    props = {}
    logger.info('API：数据分类分级接口......')

    # texts
    view_id = data.view_id
    view_name = data.view_business_name
    view_technical_name = data.view_technical_name
    subject_id = data.subject_id
    view_fields = data.view_fields
    fields = [field.view_field_business_name for field in view_fields]

    client = OpenSearchClient()
    prop_infos = []
    for field in view_fields:
        query_body = {
            "size": 10,
            "min_score": 0.75,
            "query": {
                "bool": {
                    "must": [],
                    "should": [
                        {
                            "script_score": {
                                "query": {
                                    "multi_match": {
                                        "query": field.view_field_business_name,
                                        "fields": [
                                            "name^10",
                                            "description"
                                            "path"
                                        ]
                                    }
                                },
                                "script": {
                                    "source": "_score"
                                }
                            }
                        }
                    ]
                }
            },
            "_source": {
                "includes": [
                    "id",
                    "name",
                    "path",
                    "path_id",
                    "standard_id"
                ]
            }
        }

        logger.info("data categorize query {}".format(query_body))

        index_name = "af_sailor_entity_subject_property_idx"

        resp = client.search(index_name, query_body)

        subjects = []

        for _source in resp['hits'].get('hits', []):

            path = _source["_source"]["path"]

            similarity_score = levenshtein_similarity(field.view_field_business_name, path)
            subjects.append({
                'subject_id': _source["_source"].get('id', ''),
                'subject_name': _source["_source"].get('name', ''),
                'score': _source["_score"] + similarity_score*10
            })
        subjects.sort(key=lambda x: x["score"], reverse=True)
        prop_infos.append({
            'view_field_id': field.view_field_id,
            'rel_subjects': subjects
        })
    props = {
        'view_id': view_id,
        'view_fields': prop_infos
    }

    logger.info(f'OUTPUT: {props}')
    return {'answers': props}





