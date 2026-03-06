import json


def get_time(
    search_time,
    select_times,
    exec_times,
    answer_search_times,
    answer_conclusion_times,
    answer_exec_text2sql
):
    run_time = {
        "认知搜索": round(search_time, 4),
        "选择接口": round(select_times, 4),
        "执行接口": round(exec_times, 4),
        "搜索总结": round(answer_search_times, 4),
        "接口总结": round(answer_conclusion_times, 4),
        "表格总结": round(answer_exec_text2sql, 4)
    }
    return run_time


class Status:
    search: str = "search"
    invoke: str = "invoke"
    answer: str = "answer"
    ending: str = "ending"
    ending_with_error: str = "ending_with_error"

# 复制了 data（）函数的内容， 改名为 qa_data_reorganize_to_json（）
def qa_data_reorganize_to_json(status, cites=None, detail="", table=None, explain=None, df2json="",
                               related_info=None) -> str | None:
    if table is None:
        table = ""
    if explain is None:
        explain = []
    if cites is None:
        cites = []
    if status == "search":
        return dict_2_data_json({"result": {"status": "search"}})
    elif status == "ending":
        return dict_2_data_json({"result": {"status": "ending"}})
    elif status == "invoke":
        return dict_2_data_json({"result": {"status": "invoke"}})
    elif status == "answer":
        return dict_2_data_json(
            {"result":
                {
                    "status": "answer",
                    "res": {
                        "cites": cites,
                        "table": [table],
                        "df2json": [df2json],
                        "text": [detail],
                        "explain": explain,
                        "related_info": related_info,
                    }
                }
            }
        )
    elif status == "ending_with_error":
        return dict_2_data_json({"result": {"status": "ending", "res": {"cites": [], "text": "token 过期了"}}})

# deprecated
def data(status, cites=None, detail="", table=None, explain=None, df2json=""):
    if table is None:
        table = ""
    if explain is None:
        explain = []
    if cites is None:
        cites = []
    if status == "search":
        return dict_2_data_json({"result": {"status": "search"}})
    elif status == "ending":
        return dict_2_data_json({"result": {"status": "ending"}})
    elif status == "invoke":
        return dict_2_data_json({"result": {"status": "invoke"}})
    elif status == "answer":
        return dict_2_data_json(
            {"result":
                {
                    "status": "answer",
                    "res": {
                        "cites": cites,
                        "table": [table],
                        "df2json": [df2json],
                        "text": [detail],
                        "explain": explain
                    }
                }
            }
        )
    elif status == "ending_with_error":
        return dict_2_data_json({"result": {"status": "ending", "res": {"cites": [], "text": "token 过期了"}}})

def dict_2_data_json(text: dict):
# def shape(text: dict):
    return f'data: {json.dumps(text, ensure_ascii=False)}\n'


def get_text(text):
    return json.loads(text[5:])["result"]["res"]["text"]


def get_table(text):
    return json.loads(text[5:])["result"]["res"].get("table")


def get_path(param):
    url = {
        "service": "http://data-application-service:8156/api/data-application-service/frontend/v1/services/{code}",
        "gateway": "http://data-application-gateway:8157/data-application-gateway{path}",
        "auth_info": "http://data-application-service:8156/api/data-application-service/frontend/v1/services/{code}/auth_info"
    }
    return url[param]
