# Latency-SLO Capacity Planning Using Queueing-Theory Digital Twins for Network Services

A queueing-theory-based digital twin used to analyze latency behavior, validate service-level objectives (SLOs), and estimate network service capacity limits using real measurements collected from a live deployment.

## Architecture

<svg width="880" height="520" viewBox="0 0 880 520" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M1 1 L9 5 L1 9" fill="none" stroke="#8b8b85" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M1 1 L9 5 L1 9" fill="none" stroke="#1d9e75" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <marker id="ah3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M1 1 L9 5 L1 9" fill="none" stroke="#7f77dd" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
    <style>
      .title  { font-size: 15px; font-weight: 600; }
      .sub    { font-size: 12px; font-weight: 400; }
      .tier   { font-size: 11px; font-weight: 600; letter-spacing: 1.5px; }
      .grp    { font-size: 12px; font-weight: 600; letter-spacing: .5px; }
      .edge   { font-size: 11px; font-weight: 500; }
      .hint   { font-size: 11px; font-weight: 400; }
      .canvas { fill: none; }
      .tier-txt { fill: #adaca4; }
      .grp-txt  { fill: #8b8b85; }
      .grp-box  { fill: none; stroke: #d3d1c7; stroke-dasharray: 5 4; }
      .edge-txt { fill: #6b6a64; }
      .hint-txt { fill: #c2c1b9; }
      .ln       { stroke: #b4b2a9; }
      .ln2      { stroke: #5dcaa5; }
      .ln3      { stroke: #afa9ec; }
      .n-hw   { fill: #f1efe8; stroke: #888780; }
      .n-hw-t { fill: #2c2c2a; }  .n-hw-s { fill: #5f5e5a; }
      .n-app   { fill: #e1f5ee; stroke: #1d9e75; }
      .n-app-t { fill: #04342c; } .n-app-s { fill: #0f6e56; }
      .n-obs   { fill: #eeedfe; stroke: #7f77dd; }
      .n-obs-t { fill: #26215c; } .n-obs-s { fill: #534ab7; }
      @media (prefers-color-scheme: dark) {
        .tier-txt { fill: #6f6e69; }
        .grp-txt  { fill: #9c9a92; }
        .grp-box  { stroke: #44443f; }
        .edge-txt { fill: #b4b2a9; }
        .hint-txt { fill: #57564f; }
        .ln  { stroke: #5f5e5a; }
        .ln2 { stroke: #1d9e75; }
        .ln3 { stroke: #534ab7; }
        .n-hw   { fill: #2c2c2a; stroke: #888780; }
        .n-hw-t { fill: #f1efe8; } .n-hw-s { fill: #b4b2a9; }
        .n-app   { fill: #062e26; stroke: #1d9e75; }
        .n-app-t { fill: #9fe1cb; } .n-app-s { fill: #5dcaa5; }
        .n-obs   { fill: #221d4d; stroke: #7f77dd; }
        .n-obs-t { fill: #cecbf6; } .n-obs-s { fill: #afa9ec; }
      }
    </style>
  </defs>

  <text class="tier tier-txt" x="120" y="40" text-anchor="middle">CLIENT</text>
  <text class="tier tier-txt" x="760" y="40" text-anchor="middle">ROCKY LINUX SERVER</text>

  <rect class="grp-box" x="40" y="60" width="200" height="400" rx="16"/>

  <rect class="n-hw" x="68" y="120" width="144" height="70" rx="10" stroke-width="1.2"/>
  <text class="title n-hw-t" x="140" y="152" text-anchor="middle">Client Node</text>
  <text class="sub n-hw-s" x="140" y="172" text-anchor="middle">MacBook Air</text>

  <rect class="n-app" x="68" y="300" width="144" height="70" rx="10" stroke-width="1.2"/>
  <text class="title n-app-t" x="140" y="328" text-anchor="middle">Traffic Generator</text>
  <text class="sub n-app-s" x="140" y="348" text-anchor="middle">Poisson arrivals</text>

  <line class="ln" x1="140" y1="190" x2="140" y2="298" stroke-width="1.4" marker-end="url(#ah)"/>

  <rect class="grp-box" x="560" y="60" width="280" height="400" rx="16"/>

  <rect class="n-app" x="608" y="100" width="184" height="74" rx="10" stroke-width="1.2"/>
  <text class="title n-app-t" x="700" y="130" text-anchor="middle">FastAPI Service</text>
  <text class="sub n-app-s" x="700" y="150" text-anchor="middle">Queueing · Docker container</text>

  <rect class="n-obs" x="608" y="232" width="184" height="74" rx="10" stroke-width="1.2"/>
  <text class="title n-obs-t" x="700" y="262" text-anchor="middle">Prometheus</text>
  <text class="sub n-obs-s" x="700" y="282" text-anchor="middle">Metrics collection</text>

  <rect class="n-obs" x="608" y="364" width="184" height="74" rx="10" stroke-width="1.2"/>
  <text class="title n-obs-t" x="700" y="394" text-anchor="middle">Grafana</text>
  <text class="sub n-obs-s" x="700" y="414" text-anchor="middle">Visualization dashboard</text>

  <line class="ln3" x1="700" y1="174" x2="700" y2="230" stroke-width="1.6" marker-end="url(#ah3)"/>
  <text class="edge edge-txt" x="714" y="206" text-anchor="start">scrape</text>
  <line class="ln3" x1="700" y1="306" x2="700" y2="362" stroke-width="1.6" marker-end="url(#ah3)"/>
  <text class="edge edge-txt" x="714" y="338" text-anchor="start">query</text>

  <path class="ln2" d="M212 335 H 400 V 137 H 606" fill="none" stroke-width="1.8" marker-end="url(#ah2)"/>
  <rect x="334" y="222" width="132" height="24" rx="6" fill="#e1f5ee" stroke="#5dcaa5" stroke-width="0.8"/>
  <text class="edge n-app-s" x="400" y="238" text-anchor="middle">HTTP requests</text>

  <text class="hint hint-txt" x="440" y="498" text-anchor="middle">Poisson-distributed load → containerized queueing service → metrics pipeline</text>
</svg>
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
