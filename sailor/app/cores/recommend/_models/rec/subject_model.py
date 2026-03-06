"""
@File: field_subject.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc:
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 业务对象识别 Model


class RecommendSubjectModelParams(BaseModel):
    query: str

