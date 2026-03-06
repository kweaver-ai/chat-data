from enum import Enum
from typing import Optional


class Errno(Enum):
    """Error code."""
    BASE_ERR = 0
    VIR_ENGINE_ERROR = 1
    CONFIG_CENTER_ERROR = 2
    COGNITIVE_SEARCH_ERROR = 3
    FRONTEND_COLUMN_ERROR = 4
    FRONTEND_COMMON_ERROR = 5
    FRONTEND_SAMPLE_ERROR = 6
    LLM_EXEC_ERROR = 7


class BaseError(Exception):
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
