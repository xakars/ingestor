# Service Specification: Ingestor Service

## 1. Service Purpose
The **Ingestor Service** is responsible for receiving telemetry data from external clients, such as IoT devices and microservices.

### Key Responsibilities:
* **Request Authentication:** Secure access control via API Key or JWT.
* **Data Validation:** Verification of incoming data structures and payloads.
* **Rate Limiting:** Protection against DDoS attacks and system overloads.
* **Asynchronous Event Publishing:** Efficiently streaming events to Apache Kafka.
* **Fast Client Response:** Implementing a **Fire-and-Forget** pattern to ensure low latency.

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/xakars/ingestor
cd 
```
### 2. Environment Configuration
Copy the example environment file and configure your settings:
```bash
cp .env.example .env
```
### 3. Infrastructure Setup
The service and its dependencies (Kafka, Redis, etc.) are fully containerized. 
To build and start the entire stack in the background:
```bash
docker compose up -d
```
### 4. Monitoring
To follow the service logs and verify the startup process:
```bash
# Show running containers
docker ps

# Follow service logs
docker compose logs -f ingestor 

# View resource usage statistics
docker stats 

# Check keys in Redis
docker compose exec redis redis-cli KEYS "*"

# List active Kafka topics
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```
### 5. Interactive API Documentation
Once the service is running, you can explore and test the endpoints via the Swagger UI:
* **Swagger UI:** http://127.0.0.1:8001/docs

## Development Guide

This section is for developers who want to run the service locally for debugging or feature development.

### 1. Prerequisites
Ensure you have the following installed:
* **Python 3.13+**
* **uv**
* **Docker** (for running infrastructure dependencies)

### 2. Local Environment Setup
We use [uv](https://github.com/astral-sh/uv) for dependency management. To set up your local environment:
```bash
# Install dependencies and create a virtual environment
uv sync

# Activate the environment
source .venv/bin/activate
```

### 3. Run Infrastructure Only
If you want to run the Ingestor code locally but need Kafka and Redis, use the following command:
```bash
docker compose up -d redis kafka
```

### 4. Running the Service
```bash
make run
```
### 5. Linting and Formatting
```bash
# Check for linting errors
make lint

# Format the code
make format
```

### 6. Running Tests
```bash
pytest --cov=app
```

### ⚠️ Important: Environment Configuration
The `.env` file requires different host addresses depending on how you run the application:

| Service | Running inside Docker | Running Locally (Host) |
| :--- | :--- | :--- |
| **Redis Host** | `REDIS_HOST=redis` | `REDIS_HOST=localhost` |
| **Kafka Bootstrap** | `KAFKA_BOOTSTRAP=kafka:9092` | `KAFKA_BOOTSTRAP=localhost:9092` |

> **Tip:** If you are developing locally, it is common to keep the infrastructure (Kafka/Redis) in Docker while running the Python code on your machine.
> In this case, use the **Locally** settings.

