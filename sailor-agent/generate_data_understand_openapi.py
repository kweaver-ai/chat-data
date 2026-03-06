# -*- coding: utf-8 -*-
"""
生成数据理解工具的 OpenAPI JSON 文档
"""
import asyncio
import json
from app.routers import API_V1_STR
from app.routers.agent_temp_router import ToolRouter

# 导入所有数据理解工具
from app.tools.data_understand_tools.sensitive_data_detect_tools import SensitiveDataDetectTool
from app.tools.data_understand_tools.business_object_identification_tools import BusinessObjectIdentificationTool
from app.tools.data_understand_tools.data_classification_detect_tools import DataClassificationDetectTool
from app.tools.data_understand_tools.explore_rule_identification_tools import ExploreRuleIdentificationTool
from app.tools.data_understand_tools.semantic_complete_tool import SemanticCompleteTool

# 数据理解工具映射
DATA_UNDERSTAND_TOOLS_MAPPING = {
    "sensitive_data_detect": SensitiveDataDetectTool,
    "business_object_identification": BusinessObjectIdentificationTool,
    "data_classification_detect": DataClassificationDetectTool,
    "explore_rule_identification": ExploreRuleIdentificationTool,
    "semantic_completion": SemanticCompleteTool,
}


async def generate_data_understand_openapi_doc():
    """生成数据理解工具的 OpenAPI 文档"""
    
    # OpenAPI 文档基础结构
    openapi_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Sailor Agent - Data Understand Tools",
            "description": "数据理解工具 API 文档，包括敏感字段检测、业务对象识别、数据分类分级、质量规则识别、语义补全等功能",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "本地开发服务器"
            },
            {
                "url": "http://af-sailor-agent:9595",
                "description": "生产环境"
            }
        ],
        "paths": {}
    }
    
    # 基础路径
    base_path = f"{API_V1_STR}{ToolRouter}"
    
    # 遍历所有数据理解工具，获取它们的 schema
    for tool_name, tool_class in DATA_UNDERSTAND_TOOLS_MAPPING.items():
        if hasattr(tool_class, 'get_api_schema'):
            try:
                # 调用静态方法获取 schema
                schema = await tool_class.get_api_schema()
                
                # 构建完整路径
                full_path = f"{base_path}/{tool_name}"
                
                # 将 schema 添加到 paths 中
                openapi_doc["paths"][full_path] = schema
                
                print(f"✓ 已添加工具: {tool_name} -> {full_path}")
            except Exception as e:
                print(f"✗ 获取工具 {tool_name} 的 schema 失败: {e}")
                import traceback
                traceback.print_exc()
    
    return openapi_doc


async def main():
    """主函数"""
    print("=" * 60)
    print("开始生成数据理解工具的 OpenAPI 文档...")
    print("=" * 60)
    
    openapi_doc = await generate_data_understand_openapi_doc()
    
    # 输出为 JSON 文件
    output_file = "data_understand_openapi.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_doc, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ OpenAPI 文档已生成: {output_file}")
    print(f"✓ 共包含 {len(openapi_doc['paths'])} 个 API 端点")
    print("=" * 60)
    
    # 列出所有生成的端点
    print("\n生成的 API 端点列表:")
    for path in sorted(openapi_doc['paths'].keys()):
        summary = openapi_doc['paths'][path].get('post', {}).get('summary', 'N/A')
        print(f"  - {path}: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
