# -*- coding: utf-8 -*-
# @Time    : 2025/6/3 16:55
# @Author  : Glen.lv
# @File    : verify_token
# @Project : af-sailor
from fastapi import APIRouter, Request, Body

from app.cores.text2sql.t2s_base import API

from config import settings


def verify_token(request: Request = None):
    # Bearer ory_at_8g0MFkW-Hauhv9ld4KHhACpR2aPVeVra-hHmzdzcqaE.8uazmTE6zpwKs_h7qzGVwDrWALz1s_qr2qK9A8O0MYs
    # token= "ory_at_8g0MFkW-Hauhv9ld4KHhACpR2aPVeVra-hHmzdzcqaE.8uazmTE6zpwKs_h7qzGVwDrWALz1s_qr2qK9A8O0MYs"
    token: str = request.headers.get("Authorization").split(" ")[1]
    print(f"token = {token}")
    api = API(
        data={"token": token},
        method="POST",
        url=f"{settings.HYDRA_URL}/admin/oauth2/introspect",
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    res = api.call()
    return res.get("active", False)
