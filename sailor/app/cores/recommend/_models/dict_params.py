"""
@File: config_params.py
@Date:2024-03-13
@Author : Danny.gao
@Desc:
"""

from typing import Optional
from pydantic import BaseModel, Field

from app.cores.recommend._models.base import ConfigParams


class DictParams(BaseModel):
    # 可配参数
    top_n: Optional[float] = 20.0
    min_score: Optional[float] = 0.8
    rec_llm_input_len: Optional[float] = 8000
    rec_llm_output_len: Optional[float] = 8000
    r_default_department_id: Optional[str] = ""

    # query 权重
    dept_layer: Optional[float] = 3.0
    domain_layer: Optional[float] = 3.0
    q_bus_domain_weight: Optional[float] = 0.33
    q_bus_domain_used_weight: Optional[float] = 0.5
    q_bus_domain_unused_weight: Optional[float] = 0.5
    q_dept_weight: Optional[float] = 0.33
    q_dept_used_weight: Optional[float] = 0.5
    q_dept_unused_weight: Optional[float] = 0.5
    q_info_sys_weight: Optional[float] = 0.33
    q_info_sys_used_weight: Optional[float] = 0.5
    q_info_sys_unused_weight: Optional[float] = 0.5
    # sort 权重
    s_bus_domain_weight: Optional[float] = 0.33
    s_bus_domain_used_weight: Optional[float] = 0.5
    s_bus_domain_unused_weight: Optional[float] = 0.5
    s_dept_weight: Optional[float] = 0.33
    s_dept_used_weight: Optional[float] = 0.5
    s_dept_unused_weight: Optional[float] = 0.5
    s_info_sys_weight: Optional[float] = 0.33
    s_info_sys_used_weight: Optional[float] = 0.5
    s_info_sys_unused_weight: Optional[float] = 0.5
    # sort 权重：标准分类
    # r_code_class_weight_list: list[float] = Field([0.009, 0.008, 0.007, 0.006, 0.005, 0.004, 0.01, 0], description='')
    # [0.006, 0.007, 0.008, 0.009, 0.01, 0.005, 0.004, 0]
    r_std_type_weight_0: Optional[float] = 0.006
    r_std_type_weight_1: Optional[float] = 0.007
    r_std_type_weight_2: Optional[float] = 0.008
    r_std_type_weight_3: Optional[float] = 0.009
    r_std_type_weight_4: Optional[float] = 0.001
    r_std_type_weight_5: Optional[float] = 0.005
    r_std_type_weight_6: Optional[float] = 0.004
    r_std_type_weight_99: Optional[float] = 0.0

    ## 标签推荐
    rec_label: Optional[ConfigParams] = ConfigParams()

    ## 业务规则推荐
    rec_field_rule: Optional[ConfigParams] = ConfigParams()

    ## 质量规则推荐
    rec_explore_rule: Optional[ConfigParams] = ConfigParams()
