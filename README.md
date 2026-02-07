# Monitoring Dashboard

A log-based monitoring system that provides real-time analytics for the [E-Commerce Platform](../E-Commerce/). The system reads structured JSONL logs produced by the E-Commerce API gateway and presents aggregated metrics, latency percentiles, error tracking, and traffic analysis through an interactive dashboard.

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
  - [Running Both Services at Once](#running-both-services-at-once)
  - [Running Services Individually](#running-services-individually)
- [How It Connects to E-Commerce](#how-it-connects-to-e-commerce)
- [API Reference](#api-reference)
- [Dashboard Sections](#dashboard-sections)
- [Log Format](#log-format)
- [Configuration](#configuration)
- [Project Structure](#project-structure)

## Architecture

```text
+-------------------+        +-------------------+        +-------------------+
|  E-Commerce       |  JSONL |  Monitoring       |  HTTP  |  Monitoring       |
|  API Gateway      +------->+  FastAPI Backend   +<------+  React Dashboard  |
|  (Port 8001)      |  file  |  (Port 8002)      |        |  (Port 4000)      |
+-------------------+        +-------------------+        +-------------------+
        |
        v
  logs/ecommerce.jsonl
```

The E-Commerce API gateway writes a structured log entry for every request it handles. This dashboard's backend reads that log file, computes aggregated metrics on the fly, and serves them to the React frontend. No database is involved -- everything is derived from the log file at query time.

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher (with npm)
- A running E-Commerce platform (to generate logs), or a sample JSONL log file

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Running Both Services at Once

Use the run script to start both the API and the dashboard with a single command.

Windows:

```bat
run.bat
```

This opens two separate terminal windows. Close each window to stop its service.

Linux / macOS:

```bash
chmod +x run.sh
./run.sh
```

Press `Ctrl+C` to stop both services.

Once running:

- Dashboard: <http://localhost:4000>
- Monitoring API: <http://localhost:8002> (interactive docs at <http://localhost:8002/docs>)

### Running Services Individually

#### Monitoring API

```bash
cd backend
uvicorn main:app --reload --port 8002
```

#### Monitoring Frontend

```bash
cd frontend
npm start
```

The frontend runs on port 4000 (configured in `frontend/.env`), so it can run alongside the E-Commerce frontend on port 3000 without conflict.

## How It Connects to E-Commerce

The monitoring backend reads the log file produced by the E-Commerce API gateway. The path to this file is configured in `backend/.env`:

```ini
LOG_FILE=<absolute path to E-Commerce/logs/ecommerce.jsonl>
```

Make sure this path points to the correct location on your machine. If you move the project, update this path accordingly.

For the dashboard to show meaningful data, the E-Commerce platform must be running and handling requests so that the log file gets populated.

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint                                  | Description                                          |
| ------ | ----------------------------------------- | ---------------------------------------------------- |
| GET    | `/api/health`                             | System health status and log file information        |
| GET    | `/api/metrics?minutes=60`                 | Aggregated metrics for a given time window           |
| GET    | `/api/endpoints?sort_by=p95&order=desc`   | Per-endpoint performance statistics                  |
| GET    | `/api/errors?limit=50`                    | Recent error entries                                 |
| GET    | `/api/traffic?minutes=1440`               | Hourly traffic distribution                          |
| POST   | `/api/upload-log`                         | Upload a log file (JSONL, JSON array, or JSON object)|
| GET    | `/api/debug/sample`                       | Sample of raw and parsed log entries                 |

### Common Query Parameters

| Parameter | Default | Description                                      |
| --------- | ------- | ------------------------------------------------ |
| `minutes` | 60      | Time window in minutes (max 20160 / 14 days)     |
| `limit`   | varies  | Maximum number of results returned               |
| `sort_by` | `count` | Sort field for endpoint stats (`count` or `p95`) |
| `order`   | `desc`  | Sort direction (`asc` or `desc`)                 |

## Dashboard Sections

### Overview

Summary cards showing total requests, average response time, error rate, and latency percentiles (P50, P95, P99). Includes HTTP status code and method distribution charts.

### API Performance

Detailed per-endpoint table with request counts, error rates, average and percentile response times. Highlights the slowest and most active endpoints.

### Errors and Exceptions

Tabular list of recent error responses with timestamp, method, path, status code, and error details.

### Traffic Analysis

Hourly request volume chart with peak traffic identification and breakdown by hour.

The dashboard auto-refreshes every 30 seconds.

## Log Format

The system expects JSONL (one JSON object per line) with these fields:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "method": "GET",
  "path": "/products",
  "status_code": 200,
  "duration_ms": 45.2,
  "action": "view_products",
  "user_id": 123,
  "session_id": "abc1234...",
  "is_authenticated": true,
  "client_ip": "192.168.1.1",
  "level": "INFO",
  "context": {
    "filter_category": "electronics",
    "search_query": "laptop"
  }
}
```

The parser also handles nested structures (`request.method`, `response.status_code`, `timing.duration_ms`) for compatibility with other log formats.

## Configuration

### Environment Variables (`backend/.env`)

| Variable   | Default                  | Description                               |
| ---------- | ------------------------ | ----------------------------------------- |
| `LOG_FILE` | `./data/monitoring.jsonl`| Absolute path to the JSONL log file       |
| `API_KEY`  | `change-me`              | API key for upload endpoint authentication|

### Frontend Port (`frontend/.env`)

| Variable | Default | Description              |
| -------- | ------- | ------------------------ |
| `PORT`   | `4000`  | Development server port  |

## Project Structure

```text
Monitoring_Dashboard/
├── backend/
│   ├── main.py                 # FastAPI application and route definitions
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Log file path and API key
│   ├── models/
│   │   └── data_models.py      # Pydantic response models
│   ├── services/
│   │   ├── storage.py          # Log file read/write operations
│   │   ├── parser.py           # JSONL parsing and field normalization
│   │   └── aggregator.py       # Metric computation (counts, percentiles, rates)
│   ├── utils/
│   │   └── helpers.py          # Shared utility functions
│   └── data/
│       └── monitoring.jsonl    # Local log copy (populated via upload or file watch)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # App shell and routing
│   │   └── Dashboard.tsx       # Main dashboard with all metric panels
│   ├── package.json            # Node dependencies (React 19, Ant Design 6)
│   └── .env                    # PORT=4000
│
├── run.bat                     # Windows launcher (both services)
├── run.sh                      # Linux/macOS launcher (both services)
└── README.md
```
