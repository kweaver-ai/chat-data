# -*- coding: utf-8 -*-
# @Time    : 2025/6/5 18:59
# @Author  : Glen.lv
# @File    : models
# @Project : af-sailor

from pydantic import BaseModel
from typing import List, Dict, Optional


class GraphRetrieverParams(BaseModel):
    # ad_appid: str
    # kg_id: str
    datacatalog_ids: List[str] = None

