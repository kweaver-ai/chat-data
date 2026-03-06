# -*- coding: utf-8 -*-
# @Time : 2024/1/26 9:10
# @Author : KaiNing.Zhang
import hashlib
import hmac
import json
import time
import uuid
import requests
from fastapi import Request


def init_token(app_id, app_secret, method, path, body="", qs=""):
    map_method = {
        "get": "GET",
        "post": "POST",
        "GET": "GET",
        "POST": "POST",
    }
    if isinstance(body, dict):
        body_dumps = json.dumps(body)
    else:
        body_dumps = ""
    if isinstance(qs, dict):
        qs = {k: qs[k] for k in sorted(qs)}
        qs = "&".join([f"{key}={value}" for key, value in qs.items()])
    else:
        qs = ""
    method = map_method[method]  # HTTP 请求方法
    ## zknzkn
    try:
        timestamp = requests.get("http://10.4.109.142:8502").json()
    except Exception:
        timestamp = int(time.time())  # 请求时间戳
    nonce = str(uuid.uuid4())  # 请求随机串
    message = f"""{method}\n{timestamp}\n{nonce}\n{path}\n{qs}\n{body_dumps}\n"""
    signature = hmac.new(app_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    authorization = f"ANYFABRIC-HMAC-SHA256 appid={app_id},timestamp={timestamp},nonce={nonce},signature={signature}"
    return authorization


def get_token(request: Request):
    """获取请求头中的token"""
    token = request.headers.get("Authorization", "")
    if not token:
        token = request.headers.get("authorization", "")
    return token


if __name__ == '__main__':

    appId = ""
    appSecret = ""
    mode = "POST"
    paths = "/data-application-gateway/cssjybg"
    body_ = {"id": 1}
    auth = init_token(appId, appSecret, mode, paths, body_)
    headers = {"Authorization": auth}
    url = "http://10.4.113.103/data-application-gateway/cssjybg"
    res = requests.post(url, json={"id": 1}, headers=headers, verify=False)
    print(res.json())
