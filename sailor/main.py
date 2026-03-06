# -*- coding: utf-8 -*-
# @Time : 2023/12/19 14:18
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : main.py
# @Project : copilot
import os
import sys

root_path = os.getcwd()
sys.path.append(root_path)

import uvicorn

from config import settings
from app import create_app
from app.utils.exception_handlers import register_exception_handlers

app = create_app()
register_exception_handlers(app)

if __name__ == '__main__':
    if settings.IF_DEBUG:
        workers = 1
    else:
        workers = 4
    uvicorn.run(
        app=app,
        host='0.0.0.0',
        port=9797,
        # reload=False,
        workers=workers
    )
