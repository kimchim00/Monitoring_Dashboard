# Monitoring Dashboard

A log-based monitoring system that provides real-time analytics for web application performance tracking. The system processes JSONL log files and presents metrics through an interactive dashboard interface.

## Overview

This application consists of two main components:

- **Backend**: A FastAPI REST API that handles log ingestion, parsing, and metric computation
- **Frontend**: A React-based dashboard that visualizes performance data and error tracking

## Features

- Real-time metric aggregation with configurable time windows
- HTTP request analytics including response times, status codes, and method distribution
- Per-endpoint performance statistics with P50, P95, and P99 latency metrics
- Error tracking and logging
- Hourly traffic distribution analysis
- User activity tracking (unique users, authenticated requests)
- Auto-refresh capability with 30-second intervals

## Architecture

```
Monitoring_Dashboard/
├── backend/
│   ├── main.py                 # FastAPI application and endpoints
│   ├── models/
│   │   └── data_models.py      # Data transfer objects
│   ├── services/
│   │   ├── storage.py          # Log file I/O operations
│   │   ├── parser.py           # Log parsing and normalization
│   │   └── aggregator.py       # Metric computation
│   ├── utils/
│   │   └── helpers.py          # Utility functions
│   └── data/
│       └── monitoring.jsonl    # Log storage
└── frontend/
    └── src/
        ├── App.tsx
        └── Dashboard.tsx       # Main dashboard component
```

## Requirements

### Backend
- Python 3.9+
- FastAPI

### Frontend
- React 19
- Ant Design 6
- Ant Design Plots

## Installation

### Backend Setup

```bash
cd backend
pip install fastapi uvicorn python-dateutil
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start Backend Server

```bash
cd backend
uvicorn main:app --reload --port 8002
```

The API will be available at `http://localhost:8002`.

### Start Frontend Development Server

```bash
cd frontend
npm start
```

The dashboard will be available at `http://localhost:3000`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health status and log file information |
| `/api/metrics` | GET | Aggregated metrics for specified time window |
| `/api/endpoints` | GET | Per-endpoint performance statistics |
| `/api/errors` | GET | Recent error entries |
| `/api/traffic` | GET | Hourly traffic distribution |
| `/api/upload-log` | POST | Upload log file (JSONL, JSON array, or JSON object) |
| `/api/debug/sample` | GET | Sample of raw and parsed log entries |

### Query Parameters

- `minutes`: Time window in minutes (default: 60, max: 20160)
- `limit`: Maximum number of results (varies by endpoint)
- `sort_by`: Sort field for endpoints (count or p95)
- `order`: Sort order (asc or desc)

## Log Format

The system accepts logs in JSONL format with the following fields:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "method": "GET",
  "path": "/api/users",
  "status_code": 200,
  "duration_ms": 45.2,
  "user_id": 123,
  "is_authenticated": true,
  "level": "INFO"
}
```

Nested structures are also supported for fields like `request.method`, `response.status_code`, and `timing.duration_ms`.

## Dashboard Sections

### Overview
Displays summary statistics including total requests, average response time, error rate, and latency percentiles. Shows HTTP status code and method distributions with recent error list.

### API Performance
Shows detailed endpoint statistics with request counts, error rates, and response times. Lists slowest and most popular endpoints.

### Errors and Exceptions
Tabular view of recent errors with timestamp, method, path, status code, and error details.

### Traffic Analysis
Visualizes request distribution across hours with peak traffic identification and hourly breakdown.

## Configuration

### Environment Variables

- `LOG_FILE`: Path to the log file (default: `./data/monitoring.jsonl`)