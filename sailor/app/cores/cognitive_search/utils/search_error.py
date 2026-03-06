from enum import Enum
from typing import Optional
from pydantic import ValidationError


class SearchErrno(Enum):
    """Error code."""
    BASE_ERR = 0
    VIR_ENGINE_ERROR = 1
    CONFIG_CENTER_ERROR = 2
    COGNITIVE_SEARCH_ERROR = 3
    FRONTEND_COLUMN_ERROR = 4
    FRONTEND_COMMON_ERROR = 5
    FRONTEND_SAMPLE_ERROR = 6
    LLM_EXEC_ERROR = 7
    DATA_VIEW_ERROR = 8
    CODE_TABLE_ERROR = 9
    STANDARD_ERROR = 10
    RULE_ERROR = 11
    SAMPLE_PARSE_ERROR = 12
    SAMPLE_GENERATE_ERROR = 13
    NO_PROMPT_TEMPLATE_ERROR = 14
    VALIDATION_ERROR = 15


Errors = {
    SearchErrno.BASE_ERR: "RequestsError",
    SearchErrno.VIR_ENGINE_ERROR: "VirEngineError",
    SearchErrno.CONFIG_CENTER_ERROR: "ConfigCenterError",
    SearchErrno.COGNITIVE_SEARCH_ERROR: "CognitiveSearchError",
    SearchErrno.FRONTEND_COLUMN_ERROR: "FrontendColumnError",
    SearchErrno.FRONTEND_COMMON_ERROR: "FrontendCommonError",
    SearchErrno.FRONTEND_SAMPLE_ERROR: "FrontendSampleError",
    SearchErrno.LLM_EXEC_ERROR: "LLMExecError",
    SearchErrno.DATA_VIEW_ERROR: "DataViewError",
    SearchErrno.CODE_TABLE_ERROR: "CodeTableError",
    SearchErrno.STANDARD_ERROR: "DataStandardError",
    SearchErrno.RULE_ERROR: "RuleError",
    SearchErrno.SAMPLE_PARSE_ERROR: "SampleParseError",
    SearchErrno.SAMPLE_GENERATE_ERROR: "SampleGenerateError",
    SearchErrno.NO_PROMPT_TEMPLATE_ERROR: "NoPromptTemplateError",
    SearchErrno.VALIDATION_ERROR: "ValidationError"
}


class SearchError(Exception):
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


class VirEngineError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.VIR_ENGINE_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class DataViewError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.DATA_VIEW_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class CognitiveSearchError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.COGNITIVE_SEARCH_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendColumnError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.FRONTEND_COLUMN_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class CodeTableError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.CODE_TABLE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class DataStandardError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.STANDARD_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class RuleError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.RULE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendSampleError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.FRONTEND_SAMPLE_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class FrontendCommonError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.FRONTEND_COMMON_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class ConfigCenterError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.CONFIG_CENTER_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class LLMExecError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.LLM_EXEC_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class SampleParseError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.SAMPLE_PARSE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class SampleGenerateError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.SAMPLE_GENERATE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class NoPromptTemplateError(SearchError):
    def __init__(self, e: SearchError):
        super().__init__(
            code=SearchErrno.NO_PROMPT_TEMPLATE_ERROR,
            status=500,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )
