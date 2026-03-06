# -*- coding: utf-8 -*-
# @Time    : 2025/11/23 14:02
# @Author  : Glen.lv
# @File    : dc_error.py
# @Project : af-sailor

from enum import Enum
from typing import Optional

from pydantic import ValidationError
from app.logs.logger import logger
from app.cores.data_comprehension.dc_model import (BUSINESS_OBJECT, SUPPORTED_DIMENSIONS)
from app.cores.text2sql.t2s_error import Text2SQLError


class AfSailorDependencyErrno(Enum):
    """Error code."""
    CONFIGURATION_CENTER_ERROR = (16, "配置中心异常代码")
    DATA_CATALOG_INFO_ERROR = (17, "获取数据目录详情异常代码")
    DATA_CATALOG_MOUNT_RESOURCE_ERROR = (18, "获取数据目录挂接资源异常代码")
    DEPARTMENT_RESPONSIBILITIES_ERROR = (19, "获取部门职责异常代码")
    DATA_CATALOG_OF_DEPARTMENT_ERROR = (20, "使用基础搜索获取部门所有数据目录异常代码")

    FRONTEND_PARAMS_ERROR = (21, "前端参数查询异常代码")
    INDICATOR_MANAGEMENT_ERROR = (22, "指标管理异常代码")
    DATA_EXPLORE_ERROR = (23, "数据探查报告查询异常代码")

    def __str__(self):
        return f"{self.name}({self.value[0]}): {self.value[1]}"


# Errors_AfSailor = {
#     AfSailorDependencyErrno.CONFIGURATION_CENTER_ERROR: "ConfigurationCenterError",
#     AfSailorDependencyErrno.DATA_CATALOG_ERROR: "DataCataLogError",
#     AfSailorDependencyErrno.FRONTEND_PARAMS_ERROR: "FrontendParamsError",
#     AfSailorDependencyErrno.INDICATOR_MANAGEMENT_ERROR: "IndicatorManagementError",
#     AfSailorDependencyErrno.DATA_EXPLORE_ERROR: "DataExploreError",  # 数据探查异常
# }
class DataCatalogInfoError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.DATA_CATALOG_INFO_ERROR,
        )

class DataCataLogMountResourceError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.DATA_CATALOG_MOUNT_RESOURCE_ERROR,
        )

class DepartmentResponsibilitiesError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.DEPARTMENT_RESPONSIBILITIES_ERROR,
        )

class ConfigurationCenterError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.CONFIGURATION_CENTER_ERROR,
        )


class DataCataLogOfDepartmentError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.DATA_CATALOG_OF_DEPARTMENT_ERROR,
        )




class FrontendParamsError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.FRONTEND_PARAMS_ERROR,
        )


class IndicatorManagementError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.INDICATOR_MANAGEMENT_ERROR,
        )

class DataExploreError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail,
            code=AfSailorDependencyErrno.DATA_EXPLORE_ERROR,
        )


def validate(catalog_id, dimension):
    error_msg = ""
    if not catalog_id:
        error_msg += "catalog_id 参数不能为空! "
        # logger.warning(f"Parameter validation failed: {error_msg}")

    if not dimension:
        error_msg += "dimension 参数不能为空! "
        # logger.warning(f"Parameter validation failed: {error_msg}")

    # 目前算法还不支持“业务对象”维度的理解， 直接返回空， 否则前端会反复重试，拖慢响应时间
    if dimension == BUSINESS_OBJECT:
        error_msg += "暂不支持'业务对象'维度的数据理解! "
        # logger.warning(f"Parameter validation failed: {error_msg}")

    if dimension not in SUPPORTED_DIMENSIONS and dimension is not None and dimension.strip() != "":
        error_msg += f"暂不支持'{dimension}'维度的数据理解!"
        # logger.warning(f"Parameter validation failed: {error_msg}")

    return error_msg


def corr_params(params):
    if params["stopwords"] is None:
        params["stopwords"] = []
    if params["stop_entities"] is None:
        params["stop_entities"] = []
    if params["required_resource"] is None:
        params["required_resource"] = {}
    return params


if __name__ == "__main__":
    # from app.cores.data_comprehension.data_model import TIME_RANGE
    # catalog_id=''
    # dimensions=[BUSINESS_OBJECT, TIME_RANGE, None,'','时间维度']
    # for dimension in dimensions:
    #     print(f'validate(catalog_id,{dimension}) = {validate(catalog_id,dimension)}')

    # err=Text2SQLError(detail="暂不支持该维度的数据理解")
    e = Text2SQLError()
    err = DataExploreError(e)
    print(err)

