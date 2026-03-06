# -*- coding: utf-8 -*-
# @Time : 2023/10/27 16:52
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : exception.py
# @Project : mf-models-ie
from enum import Enum
from pydantic import BaseModel
from typing import List
# from common.utils import trim_quotation_marks

Err_Server_Name = "Sailor"


def trim_quotation_marks(s: str) -> str:
    if not s:
        return s
    if s[0] == '"':
        return s[1:-1]

    return s

class ErrModel(BaseModel):
    ErrorCode: str
    Description: str
    Solution: str
    ErrorDetails: List
    ErrorLink: str

class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name

class RequestException(Exception):
    def __init__(self, name: str):
        self.name = name

class SDKRequestException(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason

class M3ERequestException(Exception):
    def __init__(self, reason):
        self.reason = reason

class OPENSEARCHRequestException(Exception):
    def __init__(self, reason):
        self.reason = reason

class NebulaGraphRetrievalException(Exception):
    def __init__(self, reason):
        self.reason = reason


class ErrVal(str, Enum):
    Err_Args_Err = Err_Server_Name + "ArgsErr"  # 请求参数错误
    Err_Service_Permission_Denied_Err = Err_Server_Name + "ServicePermissionDeniedErr"  # 服务权限错误
    Err_Graph_Permission_Denied_Err = Err_Server_Name + "GraphPermissionDeniedErr"  # 图谱权限错误
    Err_VID_LENGTH_Err = Err_Server_Name + "VIDLengthErr"  # vid长度错误
    Err_KGID_Not_Found_Err = Err_Server_Name + "KGIDNotFoundErr"  # 图谱不存在
    Err_KNW_ID_Not_Found_Err = Err_Server_Name + "KNWIDNotFoundErr"  # 网络不存在
    Err_Internal_Err = Err_Server_Name + "InternalErr"  # 内部错误
    Err_Config_Status_Err = Err_Server_Name + "ConfigStatusErr"  # 配置状态
    ErrVClassErr = Err_Server_Name + "VClassErr"  # vertex tag 不存在
    ErrVProErr = Err_Server_Name + "VProErr"  # vertex tag->pro 不存在
    Err_Already_Exists_Err = Err_Server_Name + "AlreadyExistsErr"  # 名字已存在
    Err_VClass_Empty_Err = Err_Server_Name + "VClassErr"  # 没有vclass
    Err_Space_Not_Found_Err = Err_Server_Name + "SpaceNotFoundErr"  # 没有找到space
    Err_Nebula_Internal_Server_Err = Err_Server_Name + "NebulaInternalServerErr"  # 数据库内部错误
    Err_Batch_Exec_Err = Err_Server_Name + "BatchExecErr"  # 所有自定义查询语句执行失败
    Err_MariDB_Internal_Server_Err = Err_Server_Name + "MariDBInternalServerErr"
    Err_Service_Not_Found_Err = Err_Server_Name + "ServiceNotFoundErr"  # 服务不存在
    Err_Service_Not_Edit_Err = Err_Server_Name + "ServiceNotEditErr"  # 服务不可编辑
    Err_Service_Status_Err = Err_Server_Name + "ServiceStatusErr"  # 服务状态错误
    Err_SyntaxErr_Err = Err_Server_Name + "SyntaxErr"  # nebula 查询语句语法错误
    Err_Semantic_Err = Err_Server_Name + "SemanticErr"  # nebula 结构错误
    Err_Snapshot_Not_Found_Err = Err_Server_Name + "SnapshotNotFoundErr"  # 快照id不存在
    Err_StatementTypeIsText = Err_Server_Name + "StatementTypeIsText"  # 查询语句类型为值类型
    Err_Synonym_LexiconID_Err = Err_Server_Name + "SynonymIDErr" #词库id错误


class ErrInfo:
    Err_Mes_Dict = {
        ErrVal.Err_Internal_Err: "Internal Error",
        ErrVal.Err_VID_LENGTH_Err: "VID Length Error",
        ErrVal.Err_Args_Err: "Param Error",
        ErrVal.Err_KGID_Not_Found_Err: "KGid Not Found Error",
        ErrVal.Err_Config_Status_Err: "knowledge_base Config Status Error",
        ErrVal.ErrVClassErr: "knowledge_base Class Error",
        ErrVal.ErrVProErr: "knowledge_base Property Error",
        ErrVal.Err_Already_Exists_Err: "Param Error",
        ErrVal.Err_VClass_Empty_Err: "VClass Empty Error",
        ErrVal.Err_Space_Not_Found_Err: "Space Not Found Error",
        ErrVal.Err_Nebula_Internal_Server_Err: "Nebula Internal Server Error",
        ErrVal.Err_Batch_Exec_Err: "Batch Exec Err",
        ErrVal.Err_MariDB_Internal_Server_Err: "MariDB Internal Server Error",
        ErrVal.Err_Service_Not_Found_Err: "Service Not Found Error",
        ErrVal.Err_Service_Not_Edit_Err: "Service Not Edit Error",
        ErrVal.Err_Service_Status_Err: "Service Status Error",
        ErrVal.Err_SyntaxErr_Err: "Nebula Statement Syntax Error",
        ErrVal.Err_Semantic_Err: "Nebula Semantic Error",
        ErrVal.Err_Snapshot_Not_Found_Err: "Snapshot Not Found Error",
        ErrVal.Err_StatementTypeIsText: "Statement Type is Text",
        ErrVal.Err_Service_Permission_Denied_Err: "Service Permission Denied Error",
        ErrVal.Err_Graph_Permission_Denied_Err: "Graph Permission Denied Error",
        ErrVal.Err_Synonym_LexiconID_Err: "Synonym_ID Error"
    }


class NewErrorBase(Exception):

    def __init__(self, statu_code, err_code: str, cause: str):
        super().__init__()
        self.statu_code = statu_code
        self.err_model = ErrModel(
            ErrorCode=trim_quotation_marks(err_code),
            Description=ErrInfo.Err_Mes_Dict[err_code],
            Solution="",
            ErrorDetails=[{
                'detail': cause
            }],
            ErrorLink="",
        )

