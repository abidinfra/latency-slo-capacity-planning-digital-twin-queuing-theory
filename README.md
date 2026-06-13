# Latency-SLO Capacity Planning Using Queueing-Theory Digital Twins for Network Services

This project was completed as part of my Master of Engineering (Computer Networks) studies at Toronto Metropolitan University.

The goal was to investigate how queueing theory can be used to predict service performance and estimate capacity limits before a networked application reaches saturation. Instead of relying only on analytical formulas, I deployed a live service on a Rocky Linux server, generated traffic from a separate client machine, collected operational metrics using Prometheus, and visualized system behavior in Grafana.

The project combines mathematical queueing models with real measurements to create a simple digital twin of a network service. The digital twin was then used to estimate the maximum sustainable arrival rate while meeting a latency Service Level Objective (SLO).

## Project Objectives

* Deploy a containerized network service using Docker
* Collect real-time performance metrics with Prometheus
* Visualize queueing behavior using Grafana dashboards
* Validate Little's Law using measured system data
* Compare observed latency against queueing-theory predictions
* Estimate maximum sustainable throughput for a given latency target

## Test Environment

### Server

* Rocky Linux
* Docker & Docker Compose
* FastAPI-based queueing service

### Monitoring

* Prometheus
* Grafana

### Client

* MacBook Air
* Poisson traffic generator

## Key Findings

During testing, the service was configured with two servers and an average service rate of approximately 20 requests per second per server.

The calibrated digital twin estimated a maximum sustainable arrival rate of approximately 29 requests per second for a 100 ms average latency SLO.

Experimental results also showed that latency increased rapidly as utilization approached system capacity, which matched the behavior predicted by queueing theory.

## Repository Structure

* `service/` – FastAPI service implementation
* `loadgen/` – Poisson traffic generator
* `experiments/` – Capacity planning and analysis scripts
* `monitoring/` – Prometheus and Grafana configuration
* `results/` – Generated figures and experiment outputs

## Future Improvements

Possible future work includes:

* M/G/1 and G/G/1 queue models
* Bursty traffic generation
* Kubernetes deployment
* Multi-service digital twin environments
* Automated scaling experiments
