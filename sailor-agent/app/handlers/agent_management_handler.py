from fastapi import APIRouter, Request, Body, Depends

from app.service.agent_service import AFAgentService
from app.models.agent_models import AFAgentListReqBody, PutOnAFAgentReqBody, PullOffAFAgentReqBody, PullOffAFAgentResp, \
    AFAgentListResp, PutOnAFAgentResp, UpdateCategoryAFAgentReqBody, AgentDetailCategoryResp
from app.utils.get_token import get_token

AgentManagementRouter = APIRouter()
agent_service = AFAgentService()


@AgentManagementRouter.post(
    "/agent/list",
    summary="获取智能体列表",
    description="根据条件查询智能体列表，支持分页",
    response_model=AFAgentListResp,
    responses={
        200: {
            "description": "成功获取智能体列表",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/AFAgentListResp"
                    }
                }
            }
        }
    }
)
async def get_agent_list(
    request: Request,
    req_body: AFAgentListReqBody = Body(..., description="智能体列表查询条件"),
    token: str = Depends(get_token)
):
    """获取智能体列表
    
    根据条件查询智能体列表，支持分页。
    
    Args:
        request: HTTP请求对象
        req_body: 智能体列表查询条件
        token: 认证令牌
    
    Returns:
        AFAgentListResp: 智能体列表响应
    """
    try:
        resp = agent_service.get_agent_list(req_body, token)
        return resp
    except Exception as e:
        return {"entries": [], "pagination_marker_str": "", "is_last_page": True}


@AgentManagementRouter.put(
    "/agent/put-on",
    summary="上架智能体",
    description="将智能体上架，使其可以被使用",
    response_model=PutOnAFAgentResp,
    responses={
        200: {
            "description": "智能体上架成功",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/PutOnAFAgentResp"
                    }
                }
            }
        }
    }
)
async def put_on_agent(
    request: Request,
    req_body: PutOnAFAgentReqBody = Body(..., description="上架智能体请求参数"),
    token: str = Depends(get_token)
):
    """上架智能体
    
    将智能体上架，使其可以被使用。
    
    Args:
        request: HTTP请求对象
        req_body: 上架智能体请求参数
        token: 认证令牌
    
    Returns:
        PutOnAFAgentResp: 上架智能体响应
    """
    try:
        resp = agent_service.put_on_agent(req_body)
        return resp
    except Exception as e:
        return {"res": {"status": "error", "message": str(e)}}


@AgentManagementRouter.put(
    "/agent/pull-off",
    summary="下架智能体",
    description="将智能体下架，使其不可被使用",
    response_model=PullOffAFAgentResp,
    responses={
        200: {
            "description": "智能体下架成功",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/PullOffAFAgentResp"
                    }
                }
            }
        }
    }
)
async def pull_off_agent(
    request: Request,
    req_body: PullOffAFAgentReqBody = Body(..., description="下架智能体请求参数"),
    token: str = Depends(get_token)
):
    """下架智能体
    
    将智能体下架，使其不可被使用。
    
    Args:
        request: HTTP请求对象
        req_body: 下架智能体请求参数
        token: 认证令牌
    
    Returns:
        PullOffAFAgentResp: 下架智能体响应
    """
    try:
        resp = agent_service.pull_off_agent(req_body)
        return resp
    except Exception as e:
        return {"res": {"status": "error", "message": str(e)}}


@AgentManagementRouter.put(
    "/agent/update-category/{id}",
    summary="分类智能体",
    description="将智能体分类，使其分类",
    response_model=PullOffAFAgentResp,
    responses={
        200: {
            "description": "智能体下架成功",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/PullOffAFAgentResp"
                    }
                }
            }
        }
    }
)
async def update_category(
        request: Request,id: str,
        req_body: UpdateCategoryAFAgentReqBody = Body(..., description="智能体分类请求参数"),
        token: str = Depends(get_token)
):
    """更新智能体分类

    将智能体分类，使其分类管理。

    Args:
        request: HTTP请求对象
        req_body: 分类智能体请求参数
        token: 认证令牌

    Returns:
        PullOffAFAgentResp: 分类智能体响应
        :param agent_id:
    """
    try:
        resp = agent_service.update_category(id, req_body.category_ids)
        return resp
    except Exception as e:
        return {"res": {"status": "error", "message": str(e)}}


@AgentManagementRouter.get(
    "/agent/category/detail/{id}",
    summary="获取智能体详情",
    description="根据智能体id查询智能体分类详情",
    response_model=AgentDetailCategoryResp,
    responses={
        200: {
            "description": "成功获取智能体分类详情",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/AgentDetailCategoryResp"
                    }
                }
            }
        },
        404: {
            "description": "智能体不存在"
        }
    }
)
async def get_agent_category_detail(
    request: Request,
    id: str,
    token: str = Depends(get_token)
):
    """获取智能体分类详情
    
    根据智能体id查询智能体分类详情。
    
    Args:
        request: HTTP请求对象
        id: 智能体key
        token: 认证令牌
    
    Returns:
        AgentDetailCategoryResp: 智能体分类详情响应
    """
    try:
        resp = agent_service.get_agent_category_detail(id, token)
        if resp:
            return resp
        return {"detail": "Agent not found"}
    except Exception as e:
        return {"detail": str(e)}
