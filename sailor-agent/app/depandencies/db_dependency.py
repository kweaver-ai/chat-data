# -*- coding: utf-8 -*-
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine
from config import get_settings


def get_engine():
    from urllib import parse
    settings = get_settings()
    user = settings.DPQA_MYSQL_USER
    passwd = settings.DPQA_MYSQL_PASSWORD
    host = settings.DPQA_MYSQL_HOST
    # port = config["mysql"]["port"]
    database = settings.DPQA_MYSQL_DATABASE
    dbtype = settings.DB_TYPE
    if dbtype.upper() == "DM8":
        sqlalchemy_database_uri = 'dm+dmPython://{user}:{passwd}@{host}?schema={dbschema}'.format(
            user=user,
            passwd=passwd,  # 特殊字符@处理
            host=host,
            dbschema=database
        )
    else:
        sqlalchemy_database_uri = 'mysql+pymysql://{user}:{passwd}@{host}/{database}?charset=utf8'.format(
            user=user,
            passwd=passwd,  # 特殊字符@处理
            host=host,
            database=database
        )

    # 生产环境不启用 SQLAlchemy echo，避免所有 SQL 及参数直接打到日志中
    _engine = create_engine(
        sqlalchemy_database_uri,
        poolclass=NullPool,
        echo=False,
    )
    return _engine

# 创建全局的SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Session:
    """
    获取数据库会话的依赖注入函数
    用于FastAPI路由中，自动创建和关闭数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    获取数据库会话的函数
    用于非FastAPI路由环境中，需要手动关闭会话
    """
    return SessionLocal()
