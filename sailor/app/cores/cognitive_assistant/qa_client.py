from app.handlers.cognitive_assistant_handler import qa_router, QARouter
import json

if __name__ == '__main__':
    from starlette.testclient import TestClient
    from app.utils.password import get_authorization

    inputs = {
        "ad_appid": "OIZ6_KHCKIk-ASpNLg5",
        "af_editions": "catalog",
        "entity2service": {},
        "filter": {
            "online_status": [
                -1
            ],
            "asset_type": [
                -1
            ],
            "data_kind": "0",
            "department_id": [
                -1
            ],
            "end_time": "1800122122",
            "info_system_id": [
                -1
            ],
            "owner_id": [
                -1
            ],
            "publish_status_category": [
                -1
            ],
            "shared_type": [
                -1
            ],
            "start_time": "1600122122",
            "stop_entity_infos": [],
            "subject_id": [
                -1
            ],
            "update_cycle": [
                -1
            ]
        },
        "kg_id": 19457,
        "limit": 100,
        "query": "学生成绩",
        "required_resource": {
            "lexicon_actrie": {
                "lexicon_id": "68"
            },
            "stopwords": {
                "lexicon_id": "69"
            }
        },
        "roles": [
            "normal",
            "data-owner",
            "data-butler",
            "data-development-engineer",
            "tc-system-mgm"
        ],
        "session_id": "3cb26043c7adc9d99cfda80ae7c4cb60",
        "stop_entities": [],
        "stopwords": [],
        "stream": False,
        "subject_id": "08e12c02-e9a8-11ef-9307-8e28d3b0baac",
        "subject_type": "user",
        "if_display_graph": True
    }

    inputs_dip = {
        "af_editions": "catalog",
        "entity2service": {},
        "filter": {
            "online_status": [
                -1
            ],
            "asset_type": [
                -1
            ],
            "data_kind": "0",
            "department_id": [
                -1
            ],
            "end_time": "1800122122",
            "info_system_id": [
                -1
            ],
            "owner_id": [
                -1
            ],
            "publish_status_category": [
                -1
            ],
            "shared_type": [
                -1
            ],
            "start_time": "1600122122",
            "stop_entity_infos": [],
            "subject_id": [
                -1
            ],
            "update_cycle": [
                -1
            ]
        },
        # "kg_id": 11,
        "kg_id": "cognitive_search_data_catalog",
        "limit": 100,
        # "query": "关于测试的数据",
        # "query": "勘测设计",
        "query": "上市公司",
        "required_resource": {
            "lexicon_actrie": {
                "lexicon_id": "68"
            },
            "stopwords": {
                "lexicon_id": "69"
            }
        },
        "roles": [
            "normal",
            "data-owner",
            "data-butler",
            "data-development-engineer",
            "tc-system-mgm"
        ],
        "session_id": "3cb26043c7adc9d99cfda80ae7c4cb60",
        "stop_entities": [],
        "stopwords": [],
        "stream": False,

        "subject_id": "74572b3a-ecfe-11f0-bd2b-62e61f62940-",  # 85 环境，要改成按照外部接口调用，这里改成一个无效id
        "subject_type": "user",
        "if_display_graph": True
    }

    inputs_no_online = {
        "ad_appid": "OR-y8wJLEtkpSfK0Fx2",
        "af_editions": "catalog",
        "entity2service": {},
        "filter": {


            "asset_type": [
                -1
            ],
            "data_kind": "0",
            "department_id": [
                -1
            ],
            "end_time": "1800122122",
            "info_system_id": [
                -1
            ],
            "owner_id": [
                -1
            ],
            "publish_status_category": [
                -1
            ],
            "shared_type": [
                -1
            ],
            "start_time": "1600122122",
            "stop_entity_infos": [],
            "subject_id": [
                -1
            ],
            "update_cycle": [
                -1
            ]
        },
        "kg_id": 16,
        "limit": 100,
        "query": "查询资源目录",
        "required_resource": {
            "lexicon_actrie": {
                "lexicon_id": "1"
            },
            "stopwords": {
                "lexicon_id": "13"
            }
        },
        "roles": [
            "normal",
            "data-owner",
            "data-butler",
            "data-development-engineer",
            "tc-system-mgm"
        ],
        "session_id": "3cb26043c7adc9d99cfda80ae7c4cb60",
        "stop_entities": [],
        "stopwords": [],
        "stream": False,
        "subject_id": "907c1c5a-f572-11ef-b551-e61e42e43094",
        "subject_type": "user",
        "if_display_graph": True
    }

    inputs_kecc = {"ad_appid": "OJIEMT7fcpoGRBykfUF", "af_editions": "resource", "entity2service": {},
              "filter": {"online_status": [-1], "asset_type": [-1], "data_kind": "0", "department_id": [-1],
                         "end_time": "1800122122",
                         "info_system_id": [-1], "owner_id": [-1], "publish_status_category": [-1], "shared_type": [-1],
                         "start_time": "1600122122", "stop_entity_infos": [], "subject_id": [-1], "update_cycle": [-1]},
              "kg_id": 21033, "limit": 100, "query": "知识产权分析",
              "required_resource": {"lexicon_actrie": {"lexicon_id": "22"}, "stopwords": {"lexicon_id": "23"}},
              "roles": ["normal", "data-owner", "data-butler", "data-development-engineer", "tc-system-mgm"],
              "session_id": "3cb26043c7adc9d99cfda80ae7c4cb60", "stop_entities": [], "stopwords": [], "stream": False,
              "subject_id": "bc1e5d48-cfbf-11ee-ac16-f26894970da0", "subject_type": "user"}


    index: int = 1

    inputs_kecc["session_id"] = "986fe7890bc1e4ed7c52e10badaf1b45"

    Authorization = get_authorization("https://10.4.109.85", "liberly", "")

    client = TestClient(qa_router)
    response = client.post(
        QARouter,
        headers={"Authorization": Authorization},
        # json=inputs
        # json=inputs_no_online
        json=inputs_dip
    )
    print(f'response.request={response.request}')
    # assert response.status_code == 200
    print(f"response.status_code = {response.status_code}")
    # print(f"response.json() = {json.dumps(response.json(), indent=4, ensure_ascii=False)}")

