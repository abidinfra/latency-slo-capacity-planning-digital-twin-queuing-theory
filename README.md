# Latency-SLO Capacity Planning Using Queueing-Theory Digital Twins for Network Services

A queueing-theory-based digital twin used to analyze latency behavior, validate service-level objectives (SLOs), and estimate network service capacity limits using real measurements collected from a live deployment.

## Architecture

```mermaid
flowchart LR
    subgraph client["🖥️  Client"]
        Client["Client Node<br/><sub>MacBook Air</sub>"]
        LoadGen["Traffic Generator<br/><sub>Poisson Distribution</sub>"]
    end

    subgraph server["🐧  Rocky Linux Server"]
        Service["FastAPI Queueing Service<br/><sub>Docker Container</sub>"]
        Prom["Prometheus<br/><sub>Metrics Collection</sub>"]
        Graf["Grafana<br/><sub>Visualization Dashboard</sub>"]
    end

    Client --> LoadGen
    LoadGen -->|HTTP Requests| Service
    Service -->|Metrics| Prom
    Prom --> Graf

    classDef hardware fill:#F1EFE8,stroke:#5F5E5A,stroke-width:1px,color:#2C2C2A;
    classDef app fill:#E1F5EE,stroke:#0F6E56,stroke-width:1px,color:#04342C;
    classDef obs fill:#EEEDFE,stroke:#534AB7,stroke-width:1px,color:#26215C;

    class Client hardware;
    class LoadGen,Service app;
    class Prom,Graf obs;

    style client fill:#FAFAF7,stroke:#B4B2A9,stroke-width:1px,color:#5F5E5A;
    style server fill:#FAFAF7,stroke:#B4B2A9,stroke-width:1px,color:#5F5E5A;
```

## Key Results

| Metric                  | Value               |
| ----------------------- | ------------------- |
| Servers (c)             | 2                   |
| Service Rate (μ̂)       | 20.323 req/s/server |
| Capacity                | 40.65 req/s         |
| SLO Target              | 100 ms              |
| Predicted λmax          | 28.97 req/s         |
| Little's Law Validation | Successful          |

## Technology Stack

### Infrastructure
- Rocky Linux 9
- Docker
- Docker Compose

### Monitoring
- Prometheus
- Grafana

### Application
- FastAPI
- Python

### Performance Engineering
- Queueing Theory (M/M/c)
- Little's Law
- SLO Capacity Planning

## Repository Structure

```text
service/        FastAPI queueing service
loadgen/        Poisson traffic generator
experiments/    Analysis and capacity-planning scripts
monitoring/     Prometheus and Grafana configuration
results/        Experimental outputs and figures
```

## Sample Outputs

* Latency vs Load Curve
* Little's Law Validation
* SLO Capacity Prediction
* Real-Time Grafana Dashboard
