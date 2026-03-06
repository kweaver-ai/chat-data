"""
@File: opensearch_utils.py
@Date: 2025-01-16
@Author: Danny.gao
@Desc: 对opensearch输入、输出进行处理的工具类
"""

def format_terms(terms_musts: list[list[dict]]):
    """
    功能：将输入的列表，格式化成opensearch的terms检索条件
    示例：
        1. 输入：
            [
                [
                    {
                        "key": "range_type",
                        "values": [
                            "1",
                            "2"
                        ]
                    }
                ],
                []
            ]
        2. 输出：
            [
                [
                    {
                        "terms": {
                            "range_type.keyword": [
                                "1",
                                "2"
                            ]
                        }
                    }
                ],
                []
            ]
    :param terms_musts:
    :return:
    """
    formats = []
    for musts in terms_musts:
        new_musts = []
        for must in musts:
            key = must.get('key', '')
            values = must.get('values', [])
            must_type = must.get("type", "terms")
            if must_type == "terms":
                if key and values:
                    new_must = {
                        'terms': {
                            f'{key}.keyword': values
                        }
                    }
                    new_musts.append(new_must)
            elif must_type == "wildcard":
                new_must = {
                    'wildcard': {
                        f'{key}': f'*{values}*'
                    }
                }
                new_musts.append(new_must)
        formats.append(new_musts)
    return formats