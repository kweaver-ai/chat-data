from .search_tools import (AfSailorTool, DataSourceFilterTool, DataSourceFilterToolV2, DataViewExploreTool,
                           DataViewSampleDataTool, DepartmentDutyQueryTool, DataSourceRerankTool,
                           CustomSearchStrategyTool, KnSelectTool)
from .data_understand_tools import (BusinessObjectIdentificationTool, DataClassificationDetectTool
, ExploreRuleIdentificationTool, SemanticCompleteTool, SensitiveDataDetectTool)

from .query_mind import (
    Text2SQLTool,
    Text2MetricTool,
    Json2PlotTool,
    GetMetadataTool,
    MetricSearchTool,
    KnowledgeItemTool,
    SQLHelperTool,
)
from .sandbox_tools.toolkit import ExecuteCodeTool, CreateFileTool, ReadFileTool, ListFilesTool
from .basic_tools import IntentRouterTool
from .memory_tools import MemorySearchTool, MemoryWriteTool
from .todo_list import TodoListTool, TaskManagerTool

_TOOLS_MAPPING = {
    "af_sailor": AfSailorTool,
    "datasource_filter": DataSourceFilterTool,
    "datasource_filter_v2": DataSourceFilterToolV2,
    "data_view_explore": DataViewExploreTool,
    "data_view_sample_data": DataViewSampleDataTool,
    "datasource_rerank": DataSourceRerankTool,
    "department_duty_query": DepartmentDutyQueryTool,
    "custom_search_strategy": CustomSearchStrategyTool,
    "kn_select": KnSelectTool,
    "business_object_identification": BusinessObjectIdentificationTool,
    "data_classification_detect": DataClassificationDetectTool,
    "explore_rule_identification": ExploreRuleIdentificationTool,
    "semantic_complete": SemanticCompleteTool,
    "sensitive_data_detect": SensitiveDataDetectTool,
    "text2sql": Text2SQLTool,
    "text2metric": Text2MetricTool,
    "metric_search": MetricSearchTool,
    "json2plot": Json2PlotTool,
    "get_metadata": GetMetadataTool,
    "knowledge_item": KnowledgeItemTool,
    "sql_helper": SQLHelperTool,
    "execute_code": ExecuteCodeTool,
    "create_file": CreateFileTool,
    "read_file": ReadFileTool,
    "list_files": ListFilesTool,
    "intent_router": IntentRouterTool,
    "memory_search": MemorySearchTool,
    "memory_write": MemoryWriteTool,
    "todo_list": TodoListTool,
    "task_manager": TaskManagerTool,
}