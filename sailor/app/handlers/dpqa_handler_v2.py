# -*- coding:utf-8 -*-
import sys

from fastapi import APIRouter, Request, Body, Path
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from app.cores.af_agents.models import AgentQAModel
from app.cores.af_agents.service import AgentService

from app.cores.prompt.manage.api_base import API
from app.routers.agent_temp_router import *

from config import settings

dpqa_v2 = APIRouter()


"""
转发adp 问答接口
"""

@dpqa_v2.post(
    AgentV2Router,
    summary="智能体问答接口",
    description="转发adp问答接口，支持流式响应",
    responses={
        200: {
            "description": "流式响应成功",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": "data: {\"message\": \"Hello\", \"done\": false}\n\n"
                    }
                }
            }
        },
        401: {
            "description": "未授权访问",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "example": "Unauthorized"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def dpqa_chat_v2(
    request: Request,
    adp_agent_key: str = Path(..., description="ADB智能体ID"),
    params=Body(..., description="问答请求参数")
):
    """智能体问答接口
    
    该接口用于转发ADB智能体的问答请求，并支持流式响应。
    
    Args:
        request: HTTP请求对象
        adp_agent_key: ADB智能体的唯一标识
        params: 问答请求参数，包含问题、会话ID等信息
    
    Returns:
        StreamingResponse: 流式响应，包含智能体的回答内容
    """
    if not verify_token(request):  # 验证token
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})

    authorization = request.headers.get('Authorization')
    agent_server = AgentService()

    params["agent_key"] = adp_agent_key

    new_params = AgentQAModel.model_validate(params)

    return StreamingResponse(agent_server.stream(new_params, authorization), media_type="text/event-stream")


def verify_token(request: Request = None):
    token: str = request.headers.get("Authorization").split(" ")[1]
    api = API(
        data={"token": token},
        method="POST",
        url="{}/admin/oauth2/introspect".format(settings.HYDRA_URL),
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    res = api.call()
    return res.get("active", False)


if __name__ == "__main__":
    # verify_token()
    param = {
        "id": "a67c0673-9080-4213-b3d7-4ab606678146",
        "stream": True,
        "session_id": "",
        "config": {
            "data_indicators": [],
            "data_views": [],
            "configs": {"task_desc": "", "knowledge": ["", "", "", "", ""], "remark": "",
                        "preset_question": []},
            "tools": [{"id": "1", "tool_desc": "", "tool_config": ""},
                      {"id": "2", "tool_desc": "", "tool_config": ""},
                      {"id": "3", "tool_desc": "", "tool_config": ""}],
            "work_mode": [{"id": "2", "mode_desc": "", "mode_config": ""}]
        },
        "que": "你好",
        "chat_history": ["你好"],
        "is_debug": True,
        "user_name": "liberly",
        "user_id": "e3e51a0a-0f30-11ef-a09c-62fb8b52b81d"
    }
    # async def main(param):
    #     print(await dpqa_chat(param))

    import  asyncio
    asyncio.run(main(param))
