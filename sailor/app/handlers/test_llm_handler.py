import json
from urllib.parse import urljoin

import urllib3
from fastapi import APIRouter

from app.cores.text2sql.t2s_base import API
from config import settings

urllib3.disable_warnings()
test_llm_router = APIRouter()


async def get_model_id(appid: str):
    llm_source_url = "/api/model-factory/v1/llm-source"
    user_quota_url = "/api/model-factory/v1/user-quota/model-list"
    ad_gateway_url = settings.AD_GATEWAY_URL
    llm_name = settings.LLM_NAME
    name2id = {}

    api = API(
        url=urljoin(ad_gateway_url, llm_source_url),
        params={"page": 1, "size": 10000, "series": "all"},
        headers={"appid": appid},
    )
    infos = await api.call_async()
    if infos["res"]["total"] != 0:
        for items in infos["res"]["data"]:
            name2id[items["model_name"]] = items["model_id"]
    try:
        api = API(
            url=urljoin(ad_gateway_url, user_quota_url),
            params={"page": 1, "size": 10000, "order": "create_time", "rule": "desc"},
            headers={"appid": appid},
        )
        infos = await api.call_async()
        if infos["total"] != 0:
            for items in infos["res"]:
                name2id[items["model_name"]] = items["model_id"]
    except Exception as e:
        pass

    return name2id.get(llm_name, None)


async def use_llm(appid: str, model_id: str):
    try:
        prompt_run_stream_url = "/api/model-factory/v1/prompt-run-stream"
        ad_gateway_url = settings.AD_GATEWAY_URL
        api = API(
            method="POST",
            stream=True,
            url=urljoin(ad_gateway_url, prompt_run_stream_url),
            headers={"appid": appid},
            payload={
                "model_id": model_id,
                "messages": "你好",
                "model_para": {
                    "temperature": 1,
                    "top_p": 1,
                    "presence_penalty": 0,
                    "frequency_penalty": 0,
                    "max_tokens": 7
                }
            }
        )
        infos = await api.call_async()
        return {"res": True, "detail": infos}
    except Exception as e:
        infos = json.loads(e.detail)
        infos["res"] = False
        del infos["code"]

        return infos


@test_llm_router.get("/v1/assistant/test-llm")
async def test_llm(appid):
    try:
        llm_id = await get_model_id(appid)
        if llm_id is None:
            return {"res": False, "detail": "模型不存在"}
        else:
            res = await use_llm(appid, llm_id)
            return res
    except Exception as e:
        print("=============")
        print(e)
        return {"res": False, "detail": ""}


if __name__ == '__main__':
    async def main():
        import time
        t = time.time()
        res = await test_llm("O2YJavgYhY0TqNnWRkO")
        print(res)
        print(time.time() - t)


    import asyncio

    asyncio.run(main())
