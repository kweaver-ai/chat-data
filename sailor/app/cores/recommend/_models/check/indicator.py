"""
@File: indicator.py
@Date: 2025-01-10
@Author: Danny.gao
@Desc: 
"""

from pydantic import BaseModel, Field
from typing import Optional, List

from app.cores.recommend._models.base import ConfigParams

############################################## 指标一致性校验 Model
class IndicatorParams(BaseModel):
    indicator_id: Optional[str] = None      # 指标的ID
    indicator_name: Optional[str] = None    # 指标的名称
    indicator_desc: Optional[str] = None    # 指标的描述
    indicator_formula: Optional[str] = None # 指标的公式
    indicator_unit: Optional[str] = None    # 指标的单位
    indicator_cycle: Optional[str] = None   # 指标的周期
    indicator_caliber: Optional[str] = None # 指标的口径

    business_domain_id: Optional[str] = None    # 业务流程ID
    business_domain_name: Optional[str] = None  # 业务流程名称
    # business_model_id
    # business_model_name

class CheckIndicatorParams(BaseModel):
    query: List[IndicatorParams]
    config: Optional[ConfigParams] = ConfigParams()

