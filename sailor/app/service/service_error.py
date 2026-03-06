from enum import Enum
from typing import Optional


class Errno(Enum):
    """Error code."""
    BASE_ERR = 0
    DATA_CATALOG_ERROR = 1
    CONFIG_CENTER_ERROR = 2

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


class DataCatalogError(BaseError):
    def __init__(self, e: BaseError):
        super().__init__(
            code=Errno.DATA_CATALOG_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )


class ConfigCenterError(BaseError):
    def __init__(self, e: BaseError):
        super().__init__(
            code=Errno.CONFIG_CENTER_ERROR,
            status=e.status,
            reason=e.reason,
            url=e.url,
            detail=e.detail
        )