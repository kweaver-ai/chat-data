# -*- coding: utf-8 -*-
# @Time    : 2025/12/6 17:43
# @Author  : Glen.lv
# @File    : exception_handlers
# @Project : af-sailor
from pydantic import ValidationError
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from app.utils.exception import (SDKRequestException, M3ERequestException, OPENSEARCHRequestException, UnicornException,
                                 NewErrorBase, ErrVal, RequestException)
from app.cores.text2sql.t2s_error import Text2SQLError

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(UnicornException)
    async def unicorn_exception_handler(request: Request, exc: UnicornException):
        return JSONResponse(
            status_code=500,
            content={"Description": exc.name,
                     "ErrorCode": "MF.BeforeRequest.ParametersError",
                     "ErrorDetails": "{}".format(exc.name),
                     "ErrorLink": "",
                     "Solution": "method is not validate"}
        )

    @app.exception_handler(RequestException)
    async def request_exception_handler(request: Request, exc: UnicornException):
        return JSONResponse(
            status_code=400,
            content={"Description": exc.name,
                     "ErrorCode": "MF.BeforeRequest.ParametersError",
                     "ErrorDetails": "{}".format(exc.name),
                     "ErrorLink": "",
                     "Solution": "method is not validate"}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request,
                                           exc: RequestValidationError):
        err = NewErrorBase(status.HTTP_400_BAD_REQUEST, ErrVal.Err_Args_Err,
                           exc.errors()[0])

        # raise_error_log(err)

        return JSONResponse(
            status_code=err.statu_code,
            content=jsonable_encoder(err.err_model.dict()),
        )

    @app.exception_handler(SDKRequestException)
    async def sdk_exception_handler(request: Request, exc: SDKRequestException):
        err = NewErrorBase(exc.status, ErrVal.Err_Args_Err, exc.reason)

        return JSONResponse(
            status_code=err.statu_code,
            content=jsonable_encoder(err.err_model.dict()),
        )

    @app.exception_handler(Text2SQLError)
    async def all_text2sql_exception_handler(request: Request, exc: Text2SQLError):
        """
        处理所有Text2SQL和样例生成异常的异常处理器
        """
        return JSONResponse(
            status_code=exc.status,
            content=jsonable_encoder(exc.json())
        )

    @app.exception_handler(ValidationError)
    async def all_validation_exception_handler(request: Request, exc: ValidationError):
        """
        处理所有参数校验异常的异常处理器
        """
        return JSONResponse(
            status_code=0,
            content=jsonable_encoder(exc.json())
        )

    @app.exception_handler(M3ERequestException)
    async def m3e_exception_handler(request: Request, exc: M3ERequestException):
        err = NewErrorBase(status.HTTP_500_INTERNAL_SERVER_ERROR, ErrVal.Err_Args_Err, exc.reason)

        return JSONResponse(
            status_code=err.statu_code,
            content=jsonable_encoder(err.err_model.dict()),
        )

    @app.exception_handler(OPENSEARCHRequestException)
    async def opensearch_exception_handler(request: Request, exc: OPENSEARCHRequestException):
        err = NewErrorBase(status.HTTP_500_INTERNAL_SERVER_ERROR, ErrVal.Err_Args_Err, exc.reason)

        return JSONResponse(
            status_code=err.statu_code,
            content=jsonable_encoder(err.err_model.dict()),
        )