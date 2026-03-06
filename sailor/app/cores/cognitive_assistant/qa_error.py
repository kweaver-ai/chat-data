from enum import Enum

from app.cores.text2sql.t2s_error import Text2SQLError


class Errno(Enum):
    """Error code."""
    BASE_ERR = 0
    LLM_EXEC_ERROR = 1
    FRONTEND_COLUMN_ERROR = 2
    FRONTEND_PARAMS_ERROR = 3
    VIR_ENGINE_ERROR = 4
    INDICATOR_MANAGEMENT_ERROR = 5
    DATA_CATALOG_ERROR = 6
    CONFIGURATION_CENTER_ERROR = 7


Errors = {
    Errno.BASE_ERR: "RequestsError",
    Errno.LLM_EXEC_ERROR: "LLMExecError",
    Errno.FRONTEND_COLUMN_ERROR: "FrontendColumnError",
    Errno.FRONTEND_PARAMS_ERROR: "FrontendParamsError",
    Errno.VIR_ENGINE_ERROR: "VirEngineError",
    Errno.INDICATOR_MANAGEMENT_ERROR: "IndicatorManagementError",
    Errno.DATA_CATALOG_ERROR: "DataCataLogError",
    Errno.CONFIGURATION_CENTER_ERROR: "ConfigurationCenterError",
}


class LLMExecError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.LLM_EXEC_ERROR,
        )


class FrontendColumnError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.FRONTEND_COLUMN_ERROR,
        )


class ConfigurationCenterError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.CONFIGURATION_CENTER_ERROR,
        )


class DataCataLogError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.DATA_CATALOG_ERROR,
        )


class FrontendParamsError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.FRONTEND_PARAMS_ERROR,
        )


class IndicatorManagementError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.INDICATOR_MANAGEMENT_ERROR,
        )


class VirEngineError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=Errno.VIR_ENGINE_ERROR,
        )


def validate(params):
    error_dict = {
        "error": "Sailor.QA.ParameterError",
        "description": "Parameter check error",
        "details": "",
        "solution": "Check the input parameter format as prompted",
        "link": ""
    }
    if not isinstance(params["stream"], bool):
        error_dict["details"] = "stream must be bool"
    elif not isinstance(params["query"], str) or params["query"] == "":
        error_dict["details"] = "query must be a string and cannot be empty"
    elif not isinstance(params["limit"], int):
        error_dict["details"] = "limit must be a int and cannot be empty"
    elif not isinstance(params["stopwords"], list) and params["stopwords"] is not None:
        error_dict["details"] = "stopwords must be a list or None"
    elif not isinstance(params["stop_entities"], list) and params["stop_entities"] is not None:
        error_dict["details"] = "stop_entities must be a list or None"
    elif not isinstance(params["filter"], dict) and params["filter"] is not None:
        error_dict["details"] = "filter must be a dict or None"
    # elif not isinstance(params["ad_appid"], str) or params["ad_appid"] == "":
    #     error_dict["details"] = "ad_appid must be a string and cannot be empty"
    elif not isinstance(params["kg_id"], int):
        error_dict["details"] = "kg_id must be a int and cannot be empty"
    elif not isinstance(params["required_resource"], dict) and params["required_resource"] is not None:
        error_dict["details"] = "required_resource must be a dict and cannot be empty"
    if error_dict["details"] != "":
        return error_dict
    return None # 显式返回 None 表示验证过程没有发现错误

def validate_dip(params):
    error_dict = {
        "error": "Sailor.QA.ParameterError",
        "description": "Parameter check error",
        "details": "",
        "solution": "Check the input parameter format as prompted",
        "link": ""
    }
    if not isinstance(params["stream"], bool):
        error_dict["details"] = "stream must be bool"
    elif not isinstance(params["query"], str) or params["query"] == "":
        error_dict["details"] = "query must be a string and cannot be empty"
    elif not isinstance(params["limit"], int):
        error_dict["details"] = "limit must be a int and cannot be empty"
    elif not isinstance(params["stopwords"], list) and params["stopwords"] is not None:
        error_dict["details"] = "stopwords must be a list or None"
    elif not isinstance(params["stop_entities"], list) and params["stop_entities"] is not None:
        error_dict["details"] = "stop_entities must be a list or None"
    elif not isinstance(params["filter"], dict) and params["filter"] is not None:
        error_dict["details"] = "filter must be a dict or None"
    # elif not isinstance(params["ad_appid"], str) or params["ad_appid"] == "":
    #     error_dict["details"] = "ad_appid must be a string and cannot be empty"
    elif not isinstance(params["kg_id"], str):
        error_dict["details"] = "kg_id must be a str and cannot be empty"
    elif not isinstance(params["required_resource"], dict) and params["required_resource"] is not None:
        error_dict["details"] = "required_resource must be a dict and cannot be empty"
    if error_dict["details"] != "":
        return error_dict
    return None # 显式返回 None 表示验证过程没有发现错误


def corr_params(params):
    """qa接口入参按需补全，如果没有传入的话，设置初始值为空列表或空字典：stopwords、stop_entities、required_resource"""
    if params.get("stopwords") is None:
        params["stopwords"] = []
    if params.get("stop_entities") is None:
        params["stop_entities"] = []
    if params.get("required_resource") is None:
        params["required_resource"] = {}
    return params
