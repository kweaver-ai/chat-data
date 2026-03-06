# -*- coding: utf-8 -*-
# @Time : 2023/12/19 15:12
# @Author : Jack.li
# @Email : jack.li@aishu.cn
# @File : __init__.py.py
# @Project : copilot

from app.utils.view_data_generator import (
    generate_form_view_from_data_view_id,
    generate_form_views_from_data_view_ids
)

__all__ = [
    'generate_form_view_from_data_view_id',
    'generate_form_views_from_data_view_ids',
]