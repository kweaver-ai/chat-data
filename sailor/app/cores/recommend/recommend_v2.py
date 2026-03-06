import jieba
from app.logs.logger import logger
from app.dependencies.opensearch import OpenSearchClient
from app.tools.cluster import greedy_similarity_clustering
from app.utils.stop_word import get_default_stop_words

async def recommendSubjectModel(query: str):
    status, msg, rec_infos, log_infos = False, '', [], {}
    logger.info('智能推荐之API10：主题模型推荐......')
    logger.info(f'INPUT：\nquery: {query}')
    status = True

    client = OpenSearchClient()

    # 首先查询标签
    label_index = "af_subject_model_label_idx"

    stop_word = get_default_stop_words()

    words = jieba.lcut(query)
    words = [wd for wd in words if wd not in stop_word]

    if len(words) == 0:
        msg = "搜索词为空"
        return status, msg, rec_infos, log_infos

    logger.info("搜索词结果为 {}".format(words))

    should_list = [{"wildcard": {"name": "*{}*".format(word)}} for word in words]

    query_body = {
        "query": {
            "bool": {
                "should": should_list,
                "minimum_should_match": 1
            }
        }
    }
    logger.info("搜索query 为 {}".format(query_body))
    # query_body = {'query': {'match': {'name': query}}, "size": 5, "min_score": 2}

    model_score_map = dict()
    resp = client.search(label_index, query_body)
    for _item in resp['hits'].get('hits', []):
        source = _item["_source"]
        _score = _item["_score"]
        model_relate = source["related_model_ids"]

        for model_rel_id in model_relate:
            model_score_map.setdefault(model_rel_id, 0)
            model_score_map[model_rel_id] += _score

    if len(model_score_map)>0:
        model_score_list = [(k, v) for k, v in model_score_map.items()]
        model_score_list.sort(key=lambda x: x[1], reverse=True)

        model_score_list = model_score_list[:5]

        logger.info("recommend model sort result {}".format(model_score_list))

        target_ids = [_it[0] for _it in model_score_list]
        query_info =  {
            "query": {
                "ids": {
                    "values": target_ids  # 核心：指定ID数组
                }
            }
        }

        index_name = "af_subject_model_idx"

        resp = client.search(index_name, query_info)

        logger.info("subject model label query result {}".format(resp))

        for _item in resp['hits'].get('hits', []):
            # logger.info("item {}".format(_item))
            source = _item["_source"]
            rec_infos.append({
                "id": source["id"],
                "business_name": source["business_name"],
                "data_view_id": source.get("data_view_id", ""),
                "display_field_id:": source.get("display_field_id", ""),
                "technical_name:": source.get("technical_name", ""),
                "score": model_score_map.get(source["id"], 0.0)
            })

        rec_infos.sort(key=lambda x: x["score"], reverse=True)

    else:

        index_name = "af_subject_model_idx"
        query_body = {'query': {'match': {'business_name': query}}, "size": 5, "min_score": 2}
        logger.info("subject model query {}".format(query_body))


        resp = client.search(index_name, query_body)

        logger.info("subject model name query result {}".format(resp))

        for _item in resp['hits'].get('hits', []):
            # logger.info("item {}".format(_item))
            source = _item["_source"]
            rec_infos.append({
                "id": source["id"],
                "business_name": source["business_name"],
                "data_view_id": source.get("data_view_id", ""),
                "display_field_id:": source.get("display_field_id", ""),
                "technical_name:": source.get("technical_name", ""),
            })

    logger.info(f'OUTPUT: {rec_infos}')
    return status, msg, rec_infos, log_infos

# 数据标准推荐
async def recommend_code_func(data):
    # 最多推荐数量
    max_size = 3

    table_name = data.table_name
    fields = [field.table_field_name for field in data.table_fields]
    keywords_list = [jieba.lcut(text, cut_all=True) for text in fields]
    standard_codes_tmp = []

    for i, keywords in enumerate(keywords_list):
        query = ''.join(keywords)

        logger.info("搜索词结果为 {}".format(query))

        client = OpenSearchClient()
        query_body = {
            "size": 10,
            "min_score": 0.8,
            "query": {
                "bool": {
                    "must": [],
                    "should": [
                        {
                            "script_score": {
                                "query": {
                                    "multi_match": {
                                        "query": query,
                                        "fields": [
                                            "name_cn^10",
                                            "name_en^10",
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
                    "code",
                    "name_cn",
                    "std_type",
                    "department_ids"
                ]
            }
        }

        logger.info("标准推荐 query {}".format(query_body))

        index_name = "af_sailor_entity_data_element_idx"

        resp = client.search(index_name, query_body)
        codes = []

        for res in resp['hits'].get('hits', []):
            codes.append({
                'std_ch_name': res['_source']['name_cn'],
                'std_code': str(res['_source']['code']),
            })
        codes = codes[:max_size]

        standard_codes_tmp.append({
                'table_field_name': fields[i],
                'rec_stds': codes
            })

    logger.info("标准推荐结果 {}".format(standard_codes_tmp))

    standard_codes = {
        'table_name': table_name,
        'table_fields': standard_codes_tmp
    }

    return {'answers': standard_codes}


async def recommend_check_code_func(datas):
    texts, new_data = [], []
    field_data = []
    field_info = {}

    for idx, item in enumerate(datas):
        new_item = item.dict()
        if 'fields' in new_item:
            new_item.pop('fields')
        else:
            continue
        for field in item.fields:
            field_data.append({
                'id': field.field_id,
                "name": field.field_name
            })
            field_info[field.field_id] = {
                    'id': field.field_id,
                    'standard_id': field.standard_id,
                    'standard_name': field.standard_name,
                    'standard_type': field.standard_type,
                    'name': field.field_name,
                    'desc': field.field_desc,
                    "table_id": item.table_id
                }
    min_sim = 0.5
    cluster_res = greedy_similarity_clustering(field_data, min_sim)
    new_cluster = []
    n_consistent_data_count = 0.0
    n_total_data_count = 0.0
    n_in_count = 0.0
    join_str = '#@#@#'
    group_names = ["standard_name", "standard_type"]
    check_res_rec = []
    for cluster in cluster_res:
        groups = dict()

        for item in cluster:
            field_item_info = field_info[item["id"]]
            key = field_item_info["standard_name"] + "#@#@#" + field_item_info["standard_type"]
            groups.setdefault(key, [])
            groups[key].append({"id": field_item_info["id"], "name": field_item_info["name"]})

        # 找到元素最大的组
        max_group_size = 0
        correct_name = None
        for g_name, group in groups.items():
            if len(group) > max_group_size:
                max_group_size = len(group)
                correct_name = g_name

        res = []
        # 一致的数据
        consistent_data = {
            'correct': True,
            'group': groups[correct_name]
        }
        for k, v in zip(group_names, correct_name.split(join_str)):
            consistent_data[k] = v

        res.append(consistent_data)
        # 不一致的数据
        for g_name, group in groups.items():
            if g_name != correct_name:
                inconsistent_data = {
                    'correct': False,
                    # group_names: g_name,
                    'group': group
                }
                for k, v in zip(group_names, g_name.split(join_str)):
                    inconsistent_data[k] = v
                res.append(inconsistent_data)
        check_res_rec.append(res)
        # 计算一致率
        if len(cluster) > 1:
            n_total_data_count += len(cluster)
            n_in_count += len(consistent_data["group"])

            n_consistent_data_count += len(consistent_data["group"])


    consistency_rate = n_consistent_data_count / n_total_data_count if n_total_data_count > 0 else 0.0
    t_count = n_total_data_count
    in_count = n_in_count

    # 业务侧的设计模板
    reason = f'其中{int(in_count)}个标准化字段名称相同，但{int(t_count - in_count)}个采用的标准依据分类不同。'

    flag = True
    msg = ""
    log_infos = dict()
    rec_infos = dict()
    rec_infos['rate'] = '{:.2f}'.format(consistency_rate)
    rec_infos['reason'] = reason
    rec_infos['rec'] = check_res_rec

    return flag, msg, rec_infos, log_infos


async def recommend_view_func(data):
    text = data.table.name
    fields = [field.name for field in data.fields]
    # 推荐范围：
    # 视图类型：默认元数据视图
    recommend_view_types = data.recommend_view_types
    recommend_view_types = recommend_view_types if recommend_view_types else ['1']
    # terms_musts = [[{'key': 'type', 'values': recommend_view_types}]]
    logger.info(f'推荐视图的视图类型：{recommend_view_types}')

    # new_keywords = [jieba.lcut(text, cut_all=True) for text in stexts]
    # query_word = '|'.join(new_keywords)
    # should_querys.append(query)

    client = OpenSearchClient()
    query = {
	"size": 10,
	"min_score": 2.0,
	"query": {
		"bool": {
			"must": [
				{
					"terms": {
						"type.keyword": recommend_view_types
					}
				}
			],
			"should": [
				{
					"script_score": {
						"query": {
							"multi_match": {
								"query": text,
								"fields": [
									"name^10",
									"description"
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
			"type"
		]
	}
}

    index_name = "af_sailor_entity_form_view_idx"

    resp = client.search(index_name, query)
    view_infos = []

    for res in resp['hits'].get('hits', []):
        view_infos.append({
            'id': res['_source']['id'],
            'name': res['_source']['name'],
            'hit_score': res['_score'],
            'reason': "",
            'type': res['_source']['type']
        })

    return {'answers': {'views': view_infos}}


async def recommend_field_rule_func(datas):
    # new_keywords = [jieba.lcut(text, cut_all=True) for text in stexts]
    # query = '|'.join(new_keywords)
    # should_querys.append(query)
    client = OpenSearchClient()
    rec_infos = []
    for idx, item in enumerate(datas):
        # new_item = item.dict()
        # if 'field' in new_item:
        #     new_item.pop('field')
        fields_rec = []
        for field in item.fields:
            n_text = field.field_name
            query = {
                "size": 3,
                "min_score": 0.75,
                "query": {
                    "bool": {
                        "must": [],
                        "should": [
                            {
                                "script_score": {
                                    "query": {
                                        "multi_match": {
                                            "query": n_text,
                                            "fields": [
                                                "name^10",
                                                "description"
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
                        "org_type",
                        "description",
                        "rule_type",
                        "expression",
                        "department_ids"
                    ]
                }
            }

            index_name = "af_sailor_entity_rule_idx"


            rec_list = []
            resp = client.search(index_name, query)
            for res in resp['hits'].get('hits', []):
                rec_list.append({
                    "rule_id": res["_source"]["id"],
                    "rule_name": res["_source"]["name"]
                })

            fields_rec.append({
                "name": field.field_name,
                "rec": rec_list
            })


        rec_infos.append({
            "table_name": item.table_name,
            "fields": fields_rec
        })

    status = True
    msg = ""
    log_infos = {}
    return  status, msg, rec_infos, log_infos


async def recommend_explore_rule_func(datas):
    client = OpenSearchClient()
    rec_infos = []
    for item in datas:
        table_name = item.view_name
        field_rec_res = []
        for field in item.fields:

            n_text = field.field_name
            query  = {
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
                                                "query": n_text,
                                                "fields": [
                                                    "name^10",
                                                    "description"
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
                            "org_type",
                            "description",
                            "rule_type",
                            "expression"
                        ]
                            }
            }

            index_name = "af_sailor_entity_rule_idx"

            rec_list = []
            resp = client.search(index_name, query)
            for res in resp['hits'].get('hits', []):
                rec_list.append({
                    "rule_id": res["_source"]["id"],
                    "rule_name": res["_source"]["name"]
                })

            field_rec_res.append({
                "field_name": field.field_name,
                "recommend": rec_list
            })
        rec_infos.append({
            "view_name": item.view_name,
            "rec": field_rec_res,
            'generate': '',
            'distinct': '',
            'reason': ''
        })

    status = True
    msg = ""
    log_infos = {}
    return status, msg, rec_infos, log_infos
