from textwrap import dedent
from typing import Any, Callable, List, Dict, Optional, OrderedDict

class ToolMultipleResult:

    def __init__(
        self,
        cites: Any = [],
        table: list = [],  # 表名
        df2json: list = [],  # 表数据
        text: list = [],  # 文本
        explain: list = [],  # 解释
        chart: list = [],  # 图表
        new_table: list = [],  # 新表，由于超市和数据应用的 节奏不一样，通过定义一个新表来过度，主要存储包含 title 的表
        new_chart: list = [],  # 新图，同理
        sailor_search_result: list = [],  # 搜索结果
        cache_keys: OrderedDict = OrderedDict[str, Any],
        graph: list = [],  # 图表
        related_info: Any = [],
    ):
        print("=============== 进入 ToolMultipleResult 初始化 ===============")
        if cites:
            cites = []
        if table:
            table = []
        if df2json:
            df2json = []
        if text:
            text = []
        if explain:
            explain = []
        if chart:
            chart = []
        if new_table:
            new_table = []
        if new_chart:
            new_chart = []
        if cache_keys:
            cache_keys = OrderedDict[str, Any]
        if sailor_search_result:
            sailor_search_result = []
        if graph:
            graph = []
        if related_info:
            related_info = []

        self.cites = cites
        self.table = table
        self.df2json = df2json
        self.text = text
        self.explain = explain
        self.chart = chart
        self.new_table = new_table
        self.new_chart = new_chart
        self.cache_keys = cache_keys
        self.sailor_search_result = sailor_search_result
        self.graph = graph
        self.related_info = related_info

    def __repr__(self):
        return dedent(
            f"""
             ToolMultipleResult(
                 cites={self.cites},
                 table={self.table}, 
                 df2json={self.df2json}, 
                 text={self.text}, 
                 explain={self.explain},
                 chart={self.chart},
                 new_table={self.new_table},
                 new_chart={self.new_chart},
                 cache_keys={self.cache_keys},
                 sailor_search_result={self.sailor_search_result},
                 graph={self.graph}
                 related_info={self.related_info}
             )
        """
        )

    def to_ori_json(self):
        return {
            "cites": self.cites,
            "table": self.table,
            "chart": self.chart,
            "df2json": self.df2json,
            "text": self.text,
            "explain": self.explain,
            "new_table": self.new_table,
            "new_chart": self.new_chart,
            "cache_keys": self.cache_keys,
            "sailor_search_result": self.sailor_search_result,
            "graph": self.graph,
            "related_info": self.related_info
        }

    def to_json(self):
        return {
            "result": {
                "status": "answer",
                "res": {
                    "cites": self.cites,
                    "table": self.table,
                    "chart": self.chart,
                    "df2json": self.df2json,
                    "text": self.text,
                    "explain": self.explain,
                    "new_table": self.new_table,
                    "new_chart": self.new_chart,
                    "cache_keys": self.cache_keys,
                    "sailor_search_result": self.sailor_search_result,
                    "graph": self.graph,
                    "related_info": self.related_info
                }
            }
        }