# -*- coding: utf-8 -*-
from sqlalchemy.orm import sessionmaker, Session
from app.depandencies.db_dependency import get_engine
from app.logs.logger import logger
from contextlib import contextmanager


class BaseService:
    """
    基础服务类，统一管理SQLAlchemy ORM的session
    提供session的创建、提交、刷新和关闭的统一管理
    """
    def __init__(self):
        """初始化基础服务，创建Session类"""
        self.engine = get_engine()
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """
        上下文管理器，用于获取和管理数据库会话
        自动处理会话的创建、提交和关闭
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database operation failed: {str(e)}")
            raise
        finally:
            session.close()

    def add_and_commit(self, model_instance, refresh=True):
        """
        添加模型实例到数据库并提交
        :param model_instance: 模型实例
        :param refresh: 是否刷新实例，获取最新数据
        :return: 模型实例
        """
        with self.get_session() as session:
            session.add(model_instance)
            if refresh:
                session.refresh(model_instance)
            return model_instance

    def bulk_add_and_commit(self, model_instances, refresh=False):
        """
        批量添加模型实例到数据库并提交
        :param model_instances: 模型实例列表
        :param refresh: 是否刷新实例，获取最新数据
        :return: 模型实例列表
        """
        with self.get_session() as session:
            session.add_all(model_instances)
            if refresh:
                for instance in model_instances:
                    session.refresh(instance)
            return model_instances

    def update_and_commit(self, model_instance, refresh=True):
        """
        更新模型实例并提交
        :param model_instance: 模型实例
        :param refresh: 是否刷新实例，获取最新数据
        :return: 模型实例
        """
        return self.merge_and_commit(model_instance, refresh)

    def merge_and_commit(self, model_instance, refresh=True):
        """
        合并模型实例到会话并提交
        用于处理分离的模型实例，处理主键冲突等情况
        :param model_instance: 模型实例
        :param refresh: 是否刷新实例，获取最新数据
        :return: 模型实例
        """
        with self.get_session() as session:
            merged_instance = session.merge(model_instance)
            if refresh:
                session.refresh(merged_instance)
            return merged_instance

    def delete_and_commit(self, model_instance):
        """
        删除模型实例并提交
        :param model_instance: 模型实例
        :return: None
        """
        with self.get_session() as session:
            session.delete(model_instance)
            return None

    def paginate_query(self, query, page_size: int, pagination_marker: str = None, order_by_field=None):
        """
        通用分页查询方法
        :param query: SQLAlchemy查询对象
        :param page_size: 每页大小
        :param pagination_marker: 分页标记
        :param order_by_field: 排序字段
        :return: (查询结果列表, 下一页分页标记, 是否最后一页)
        """
        with self.get_session() as session:
            # 如果没有指定排序字段，使用id字段
            if order_by_field is None:
                order_by_field = query.column_descriptions[0]['expr'].id
            
            # 应用排序
            query = query.order_by(order_by_field)
            
            # 如果有分页标记，使用标记过滤
            if pagination_marker:
                try:
                    marker_value = int(pagination_marker)
                    query = query.filter(order_by_field > marker_value)
                except (ValueError, TypeError):
                    # 如果标记无效，从头开始查询
                    pass
            
            # 查询总数量
            total_count = query.count()
            
            # 查询分页数据
            if page_size > 0:
                query = query.limit(page_size + 1)  # 查询多一条，用于判断是否有下一页
            
            results = session.execute(query).scalars().all()
            
            # 处理分页结果
            has_next_page = len(results) > page_size if page_size > 0 else False
            if has_next_page:
                results = results[:page_size]
            
            # 生成下一页分页标记
            next_marker = str(results[-1].__dict__[order_by_field.name]) if results and has_next_page else ""
            
            return {
                "entries": results,
                "pagination_marker_str": next_marker,
                "is_last_page": not has_next_page
            }
