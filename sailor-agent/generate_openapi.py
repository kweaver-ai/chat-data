# -*- coding: utf-8 -*-
"""
生成完整的 OpenAPI JSON 文档
"""
import asyncio
import json
from app.tools import _TOOLS_MAPPING
from app.routers import API_V1_STR
from app.routers.agent_temp_router import ToolRouter


async def generate_openapi_doc():
    """生成完整的 OpenAPI 文档"""
    
    # OpenAPI 文档基础结构
    openapi_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Sailor Agent",
            "description": "Sailor Agent数据分析员",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "本地开发服务器"
            }
        ],
        "paths": {}
    }
    
    # 基础路径
    base_path = f"{API_V1_STR}{ToolRouter}"
    
    # 遍历所有工具，获取它们的 schema
    for tool_name, tool_class in _TOOLS_MAPPING.items():
        # 搜索工具
        if tool_name not in ["datasource_rerank"]:
            continue
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
    
    return openapi_doc


async def main():
    """主函数"""
    print("开始生成 OpenAPI 文档...")
    openapi_doc = await generate_openapi_doc()
    
    # 输出为 JSON 文件
    output_file = "openapi.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_doc, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ OpenAPI 文档已生成: {output_file}")
    print(f"✓ 共包含 {len(openapi_doc['paths'])} 个 API 端点")
    
    # 也输出到控制台
    print("\n" + "="*50)
    print("OpenAPI 文档内容:")
    print("="*50)
    print(json.dumps(openapi_doc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
