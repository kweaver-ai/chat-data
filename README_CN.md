# DIP for Data Resource

## 语言选择

[English](README.md) | [中文](./README_CN.md)

## 项目简介

  DIP for Data Resource是基于DIP平台打造的面向数据资源的AI应用，聚焦“智能找数、智能问数”两大核心场，帮助组织高效查找、理解和分析数据。致力于解决组织“数据质量差、找数难、用数难”的问题，推动数据资产价值的持续释放。

  智能问数：超越 BI，懂业务的企业级数据专家，依托场景分析知识网络与行业引擎，打造深植业务场景的数据智能体，以AI助手满足业务用户平民化、场景化、探索式数据分析需求，充分释放数据价值，提升组织生产力。

  智能找数：通过自然语言与找数智能体对话，Agent能够快速查找所需的数据资源目录清单、汇总数据内容并总结应用场景等信息，辅助用户快速理解及定位需求数据。帮助企业用户从“找表难、理解慢”的困境中，直接跨越到“找得到、读得懂、用得上”。

## 项目结构

项目包含三个主要服务：

### 1. Sailor 服务 (`sailor`)
- **技术栈**: Python 3.11, FastAPI
- **端口**: 9797
- **功能**: 核心数据资源服务，包括认知搜索、文本转SQL、数据分类和聊天功能
- **核心功能**:
  - 认知搜索：智能语义搜索数据资源
  - 文本转SQL：自然语言转SQL查询
  - 数据分类：自动分类数据资源
  - 数据理解：理解和分析数据结构
  - 聊天系统：数据查询的对话界面
  - 聊天转图表：从自然语言查询生成可视化图表
  - 认知助手：AI驱动的数据助手
  - 智能推荐：智能数据资源推荐

### 2. Sailor Agent 服务 (`sailor-agent`)
- **技术栈**: Python 3.11, FastAPI
- **端口**: 9595
- **功能**: 基于代理的高级AI交互和Copilot功能服务
- **核心功能**:
  - 代理框架：用于复杂数据操作的多代理系统
  - Copilot服务：数据操作的AI助手
  - 高级提示词管理：复杂的提示词工程

### 3. Sailor Service (`sailor-service`)
- **技术栈**: Go
- **功能**: 提供业务逻辑和数据管理的后端服务层
- **核心功能**:
  - 领域逻辑：核心业务逻辑实现
  - 仓储层：数据访问和持久化
  - API适配器：与外部系统集成

## 核心能力

### 认知搜索
智能语义搜索，理解用户意图并检索相关数据资源，包括：
- 逻辑视图
- 接口服务
- 指标
- 数据目录

### 文本转SQL
将自然语言查询转换为SQL语句，使非技术用户能够使用自然语言查询数据库。

### 数据理解
自动分析和理解数据结构、模式和关系。

### 智能推荐
基于用户上下文和历史记录，提供AI驱动的相关数据资源推荐。

### 数据分类
自动分类和标记数据资源，以便更好地组织和发现。

## 技术栈

### 后端
- **Python**: FastAPI, LangChain, OpenSearch-py
- **Go**: 后端服务和API
- **OpenSearch**: 向量搜索和全文搜索
- **Redis**: 缓存和会话管理
- **Kafka**: 异步处理的消息队列

### AI/ML
- **LangChain**: LLM编排框架
- **嵌入模型**: 用于语义搜索的向量嵌入
- **大语言模型**: 集成多种LLM（Qwen、Tome等）

### 基础设施
- **Docker**: 容器化
- **Kubernetes**: 容器编排（生产环境）
- **Hydra**: OAuth2认证

## 快速开始

### 前置要求

- Python 3.11+
- Go 1.19+
- Docker 和 Docker Compose
- OpenSearch 2.x
- Redis
- Kafka

### 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd chat-data
```

2. **配置环境变量**

在每个服务目录中创建 `.env` 文件，配置必要的参数：
- `AF_IP`: AnyFabric服务URL
- `OPENSEARCH_HOST`: OpenSearch主机
- `OPENSEARCH_PORT`: OpenSearch端口
- `REDIS_HOST`: Redis主机
- `KAFKA_MQ_HOST`: Kafka主机
- `LLM_NAME`: 大语言模型名称
- `ML_EMBEDDING_URL`: 嵌入服务URL

3. **安装Python依赖**

Sailor服务：
```bash
cd sailor
pip install -r requirements.txt
```

Sailor Agent服务：
```bash
cd sailor-agent
pip install -r requirements.txt
```

4. **构建Go服务**
```bash
cd sailor-service
go mod download
go build -o app cmd/main.go
```

### 运行服务

#### 开发模式

**Sailor服务:**
```bash
cd sailor
python main.py
# 服务运行在 http://localhost:9797
```

**Sailor Agent服务:**
```bash
cd sailor-agent
python main.py
# 服务运行在 http://localhost:9595
```

**Sailor Service (Go):**
```bash
cd sailor-service
./app
```

#### Docker部署

详细部署说明请参考 `deploy/README.md`。

```bash
cd deploy
docker compose up -d
```

## API文档

### Sailor服务端点

- **认知搜索**: `/api/v1/cognitive-search/*`
- **文本转SQL**: `/api/v1/text2sql/*`
- **数据理解**: `/api/v1/data-comprehension/*`
- **推荐**: `/api/v1/recommend/*`
- **聊天**: `/api/v1/chat/*`
- **分类**: `/api/v1/categorize/*`

### Sailor Agent服务端点

- **代理服务**: `/api/v1/agent/*`
- **Copilot**: `/api/v1/copilot/*`
- **助手**: `/api/v1/assistant/*`

## 配置说明

### 关键配置参数

- `MIN_SCORE`: 向量搜索的最小相似度分数（默认：0.85）
- `OS_VEC_NUM`: 向量搜索返回的最大结果数（默认：100）
- `Finally_NUM`: 最终返回的最大结果数（默认：30）
- `LLM_NAME`: 使用的大语言模型
- `ML_EMBEDDING_URL`: 嵌入服务端点

## 测试

运行各服务的测试：

```bash
# Sailor服务测试
cd sailor
pytest tests/

# Sailor agent测试
cd sailor-agent
pytest tests/
```

## 构建和部署

### Docker构建

```bash
# 构建Sailor服务
cd sailor
docker build -t sailor:latest .

# 构建Sailor Agent服务
cd sailor-agent
docker build -t sailor-agent:latest .

# 构建Sailor Service (Go)
cd sailor-service
docker build -t sailor-service:latest .
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m '添加新功能'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 许可证

[在此指定许可证]
