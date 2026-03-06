from enum import Enum
from typing import Optional
from pydantic import ValidationError


class T2SErrno(Enum):
    """Error code."""
    BASE_ERR = (0, "通用异常代码")
    VIR_ENGINE_ERROR = (1, "虚拟化引擎异常代码")
    CONFIG_CENTER_ERROR = (2, "配置中心异常代码")
    COGNITIVE_SEARCH_ERROR = (3, "认知搜索异常代码")
    FRONTEND_COLUMN_ERROR = (4, "前端字段、信息项查询异常代码")
    FRONTEND_COMMON_ERROR = (5, "前端通用异常代码")
    FRONTEND_SAMPLE_ERROR = (6, "前端数据样例查询异常代码")
    LLM_EXEC_ERROR = (7, "LLM执行异常代码")
    DATA_VIEW_ERROR = (8, "逻辑视图查询异常代码")
    CODE_TABLE_ERROR = (9, "代码表查询异常代码")
    STANDARD_ERROR = (10, "数据标准查询异常代码")
    RULE_ERROR = (11, "规则查询异常代码")
    SAMPLE_PARSE_ERROR = (12, "数据样例解析异常代码")
    SAMPLE_GENERATE_ERROR = (13, "数据样例生成异常代码")
    NO_PROMPT_TEMPLATE_ERROR = (14, "无提示模板异常代码")
    VALIDATION_ERROR = (15, "参数校验异常代码")

    def __str__(self):
        return f"{self.name}({self.value[0]}): {self.value[1]}"


Errors = {
    T2SErrno.BASE_ERR: "RequestsError",
    T2SErrno.VIR_ENGINE_ERROR: "VirEngineError",
    T2SErrno.CONFIG_CENTER_ERROR: "ConfigCenterError",
    T2SErrno.COGNITIVE_SEARCH_ERROR: "CognitiveSearchError",
    T2SErrno.FRONTEND_COLUMN_ERROR: "FrontendColumnError",
    T2SErrno.FRONTEND_COMMON_ERROR: "FrontendCommonError",
    T2SErrno.FRONTEND_SAMPLE_ERROR: "FrontendSampleError",
    T2SErrno.LLM_EXEC_ERROR: "LLMExecError",
    T2SErrno.DATA_VIEW_ERROR: "DataViewError",
    T2SErrno.CODE_TABLE_ERROR: "CodeTableError",
    T2SErrno.STANDARD_ERROR: "DataStandardError",
    T2SErrno.RULE_ERROR: "RuleError",
    T2SErrno.SAMPLE_PARSE_ERROR: "SampleParseError",
    T2SErrno.SAMPLE_GENERATE_ERROR: "SampleGenerateError",
    T2SErrno.NO_PROMPT_TEMPLATE_ERROR: "NoPromptTemplateError",
    T2SErrno.VALIDATION_ERROR: "ValidationError"
}


class Text2SQLError(Exception):
    code: Enum
    status: int
    reason: Optional[str]
    url: Optional[str]
    detail: Optional[dict]

    def __init__(
            self,
            status=0,
            code: Enum = 0,
            reason="",
            url="",
            detail: dict = None
    ):
        super().__init__()
        self.code = code
        self.status = status
        self.reason = reason
        self.url = url
        self.detail = detail

    def __str__(self):
        return f"\n" \
               f"- Code: {self.code}\n" \
               f"- Status: {self.status}\n" \
               f"- Reason: {self.reason}\n" \
               f"- URL: {self.url} \n" \
               f"- Detail: {self.detail}\n"

    def json(self):
        """Return json format of error."""
        return {
            "code": self.code,
            "status": self.status,
            "reason": self.reason,
            "url": self.url,
            "detail": self.detail
        }


class VirEngineError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.VIR_ENGINE_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class DataViewError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.DATA_VIEW_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class CognitiveSearchError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.COGNITIVE_SEARCH_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendColumnError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.FRONTEND_COLUMN_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class CodeTableError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.CODE_TABLE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class DataStandardError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.STANDARD_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class RuleError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.RULE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendSampleError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.FRONTEND_SAMPLE_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendCommonError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.FRONTEND_COMMON_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class ConfigCenterError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.CONFIG_CENTER_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class LLMExecError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.LLM_EXEC_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class SampleParseError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.SAMPLE_PARSE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class SampleGenerateError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.SAMPLE_GENERATE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class NoPromptTemplateError(Text2SQLError):
    def __init__(self, e: Text2SQLError):
        super().__init__(
            code=T2SErrno.NO_PROMPT_TEMPLATE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )

if __name__ == "__main__":
    e = Text2SQLError()
    err = VirEngineError(e)
    print(err)
    err1=DataViewError(e)
    print(err1)
