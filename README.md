# DIP for Data Resource

## Language Selection
[English](./README.md) | [中文](README_CN.md)

## Project Overview

DIP for Data Resource is an AI application for data resources built on the DIP platform, focusing on two core scenarios: "Intelligent Data Discovery" and "Intelligent Data Querying". It helps organizations efficiently find, understand, and analyze data. The platform is committed to solving organizational problems of "poor data quality, difficulty in finding data, and difficulty in using data", and promoting the continuous release of data asset value.

**Intelligent Data Querying**: Beyond BI, an enterprise-level data expert that understands business. Based on scenario analysis knowledge networks and industry engines, it creates data intelligence agents deeply embedded in business scenarios. With AI assistants, it meets the needs of business users for democratized, scenario-based, and exploratory data analysis, fully releasing data value and improving organizational productivity.

**Intelligent Data Discovery**: Through natural language dialogue with the data discovery intelligent agent, the Agent can quickly find the required data resource catalog lists, summarize data content, and summarize application scenarios and other information, helping users quickly understand and locate required data. It helps enterprise users directly transition from the dilemma of "difficulty finding tables and slow understanding" to "findable, understandable, and usable".

## Project Structure

The project consists of three main services:

### 1. Sailor Service (`sailor`)
- **Tech Stack**: Python 3.11, FastAPI
- **Port**: 9797
- **Functionality**: Core data resource service, including cognitive search, text-to-SQL, data classification, and chat functionality
- **Core Features**:
  - Cognitive Search: Intelligent semantic search for data resources
  - Text-to-SQL: Natural language to SQL query conversion
  - Data Classification: Automatic classification of data resources
  - Data Comprehension: Understanding and analyzing data structures
  - Chat System: Conversational interface for data queries
  - Chat-to-Chart: Generate visualization charts from natural language queries
  - Cognitive Assistant: AI-driven data assistant
  - Intelligent Recommendations: Smart data resource recommendations

### 2. Sailor Agent Service (`sailor-agent`)
- **Tech Stack**: Python 3.11, FastAPI
- **Port**: 9595
- **Functionality**: Agent-based advanced AI interaction and Copilot functionality service
- **Core Features**:
  - Agent Framework: Multi-agent system for complex data operations
  - Copilot Service: AI assistant for data operations
  - Advanced Prompt Management: Complex prompt engineering

### 3. Sailor Service (`sailor-service`)
- **Tech Stack**: Go
- **Functionality**: Backend service layer providing business logic and data management
- **Core Features**:
  - Domain Logic: Core business logic implementation
  - Repository Layer: Data access and persistence
  - API Adapters: Integration with external systems

## Core Capabilities

### Cognitive Search
Intelligent semantic search that understands user intent and retrieves relevant data resources, including:
- Logical Views
- Interface Services
- Metrics
- Data Catalogs

### Text-to-SQL
Convert natural language queries into SQL statements, enabling non-technical users to query databases using natural language.

### Data Comprehension
Automatically analyze and understand data structures, schemas, and relationships.

### Intelligent Recommendations
Provide AI-driven relevant data resource recommendations based on user context and history.

### Data Classification
Automatically classify and tag data resources for better organization and discovery.

## Tech Stack

### Backend
- **Python**: FastAPI, LangChain, OpenSearch-py
- **Go**: Backend services and APIs
- **OpenSearch**: Vector search and full-text search
- **Redis**: Caching and session management
- **Kafka**: Message queue for asynchronous processing

### AI/ML
- **LangChain**: LLM orchestration framework
- **Embedding Models**: Vector embeddings for semantic search
- **Large Language Models**: Integration with multiple LLMs (Qwen, Tome, etc.)

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Container orchestration (production environment)
- **Hydra**: OAuth2 authentication

## Quick Start

### Prerequisites

- Python 3.11+
- Go 1.19+
- Docker and Docker Compose
- OpenSearch 2.x
- Redis
- Kafka

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd chat-data
```

2. **Configure environment variables**

Create `.env` files in each service directory with necessary parameters:
- `AF_IP`: AnyFabric service URL
- `OPENSEARCH_HOST`: OpenSearch host
- `OPENSEARCH_PORT`: OpenSearch port
- `REDIS_HOST`: Redis host
- `KAFKA_MQ_HOST`: Kafka host
- `LLM_NAME`: Large language model name
- `ML_EMBEDDING_URL`: Embedding service URL

3. **Install Python dependencies**

Sailor service:
```bash
cd sailor
pip install -r requirements.txt
```

Sailor Agent service:
```bash
cd sailor-agent
pip install -r requirements.txt
```

4. **Build Go service**
```bash
cd sailor-service
go mod download
go build -o app cmd/main.go
```

### Running Services

#### Development Mode

**Sailor service:**
```bash
cd sailor
python main.py
# Service runs on http://localhost:9797
```

**Sailor Agent service:**
```bash
cd sailor-agent
python main.py
# Service runs on http://localhost:9595
```

**Sailor Service (Go):**
```bash
cd sailor-service
./app
```

#### Docker Deployment

For detailed deployment instructions, please refer to `deploy/README.md`.

```bash
cd deploy
docker compose up -d
```

## API Documentation

### Sailor Service Endpoints

- **Cognitive Search**: `/api/v1/cognitive-search/*`
- **Text-to-SQL**: `/api/v1/text2sql/*`
- **Data Comprehension**: `/api/v1/data-comprehension/*`
- **Recommendations**: `/api/v1/recommend/*`
- **Chat**: `/api/v1/chat/*`
- **Classification**: `/api/v1/categorize/*`

### Sailor Agent Service Endpoints

- **Agent Service**: `/api/v1/agent/*`
- **Copilot**: `/api/v1/copilot/*`
- **Assistant**: `/api/v1/assistant/*`

## Configuration

### Key Configuration Parameters

- `MIN_SCORE`: Minimum similarity score for vector search (default: 0.85)
- `OS_VEC_NUM`: Maximum number of results returned by vector search (default: 100)
- `Finally_NUM`: Maximum number of final results returned (default: 30)
- `LLM_NAME`: Large language model to use
- `ML_EMBEDDING_URL`: Embedding service endpoint

## Testing

Run tests for each service:

```bash
# Sailor service tests
cd sailor
pytest tests/

# Sailor agent tests
cd sailor-agent
pytest tests/
```

## Build and Deployment

### Docker Build

```bash
# Build Sailor service
cd sailor
docker build -t sailor:latest .

# Build Sailor Agent service
cd sailor-agent
docker build -t sailor-agent:latest .

# Build Sailor Service (Go)
cd sailor-service
docker build -t sailor-service:latest .
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Specify license here]
