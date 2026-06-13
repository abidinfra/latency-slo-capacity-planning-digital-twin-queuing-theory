# Queueing-Theory Digital Twin for Latency SLO Capacity Planning

A real, containerized web service is modeled as an **M/M/c/K queueing
system**. A calibrated analytical model (the "digital twin") **predicts the
maximum request rate the live service can sustain before violating a latency
SLO** — and the prediction is then verified against the real system.

This is the math behind industry capacity planning, admission control, and
autoscaling (SRE / performance engineering).

**Course:** Network Math and Simulations (M.Eng. Computer Networks)

## Headline result (reproduced on every run)

```
================ SLO PREDICTION SCORECARD ================
      load     rate     mean W  predicted  observed    model
      0.9x    25.67     76.7ms        MET       MET  CORRECT
      1.1x    31.37    106.0ms   VIOLATED  VIOLATED  CORRECT
```
The calibrated M/M/2 model predicted λ_max = 28.5 req/s for a 100 ms SLO;
the real system met the SLO just below it and violated it just above it.

## Architecture

```
MacBook (load + analysis)                Home server (system under test)
┌─────────────────────────┐   HTTP /work  ┌────────────────────────────────┐
│ poisson_loadgen.py      │ ────────────► │ docker compose:                │
│  open-loop Poisson λ    │               │  service   :8000  (FastAPI,    │
│ run_sweep / analyze /   │   /stats,     │    M/M/c/K semantics + metrics)│
│ slo_test / autoscaler   │ ◄──────────── │  prometheus:9090               │
│                         │   /metrics    │  grafana   :3000  (dashboards) │
└─────────────────────────┘               └────────────────────────────────┘
```

The service implements **explicit queueing semantics**: c = concurrency
limit (servers), FIFO waiting, K = admission limit (503 beyond it),
exponential service at rate μ per server. So M/M/c/K theory maps 1:1 onto
a real HTTP system.

## Why the load generator is custom (methodology)

`wrk`, `ab`, `hey` are **closed-loop**: workers wait for responses before
sending again, so the offered rate silently drops when the server is slow
("coordinated omission") and arrivals stop being Poisson.
`loadgen/poisson_loadgen.py` is **open-loop**: arrivals are scheduled by
exponential inter-arrival gaps independent of server state — the M in M/M/c.
It also samples `/stats` to measure L (number in system) independently of
latency, enabling a true Little's Law check on real data.

## Repo layout

```
service/        FastAPI target service (app.py, Dockerfile)
loadgen/        open-loop Poisson load generator
experiments/    theory.py, run_sweep.py, analyze.py, slo_test.py, autoscaler.py
monitoring/     prometheus.yml + auto-provisioned Grafana dashboard
docker-compose.yml
results/        sweep data + generated figures
```

## Step-by-step

### A. Home server (system under test)

```bash
git clone <your-repo-url> && cd queueing-digital-twin
docker compose up -d --build
docker compose ps          # all three containers Up
```

Find the server's LAN IP: `ip addr` (e.g. `192.168.1.50`). Verify from the
MacBook: `curl http://192.168.1.50:8000/healthz`.

Open Grafana at `http://192.168.1.50:3000` — the "Queueing Digital Twin —
Live System" dashboard is auto-provisioned (anonymous access enabled).

### B. MacBook (load generation + analysis)

```bash
git clone <your-repo-url> && cd queueing-digital-twin
python3 -m venv venv && source venv/bin/activate
pip install httpx matplotlib numpy

export URL=http://192.168.1.50:8000
```

### C. Experiments

**1. Single run sanity check + Little's Law on real data**
```bash
python loadgen/poisson_loadgen.py --url $URL --rate 30 --duration 120
```

**2. Full λ sweep (default config: c=2, μ=20 → capacity 40 req/s)**
```bash
python experiments/run_sweep.py --url $URL \
    --rates 5,10,15,20,24,28,30,32,34,36 --duration 120 \
    --out results/sweep_c2.json
```
Keep Grafana open during the sweep and screenshot the latency/L/throughput
panels stepping up with each rate.

**3. Calibrate the twin, generate figures, predict SLO capacity**
```bash
python experiments/analyze.py --sweep results/sweep_c2.json --slo 0.1
```
Produces `figA_latency_vs_load.png` (model vs reality),
`figB_littles_law_real.png`, an error table, and prints λ_max.

**4. The money experiment — validate the prediction live**
```bash
python experiments/slo_test.py --url $URL --slo 0.1 \
    --lam-max <value printed by analyze> --duration 120
```

**5. Admission control (M/M/c/K)** — bound the queue, overload it,
compare 503 rate with the blocking formula:
```bash
curl -X POST $URL/config -H 'Content-Type: application/json' -d '{"k": 10}'
python experiments/run_sweep.py --url $URL --rates 30,40,50,60 \
    --duration 120 --out results/sweep_k10.json
python experiments/analyze.py --sweep results/sweep_k10.json   # adds figC
curl -X POST $URL/config -d '{"k": 0}'    # back to unbounded
```

**6. Stretch goal — Erlang-C autoscaler**
```bash
# terminal 1: autoscaler adjusts c live to keep predicted W under the SLO
python experiments/autoscaler.py --url $URL --slo 0.1
# terminal 2: ramp traffic and watch c step up/down in Grafana
python loadgen/poisson_loadgen.py --url $URL --rate 15 --duration 90
python loadgen/poisson_loadgen.py --url $URL --rate 60 --duration 90
python loadgen/poisson_loadgen.py --url $URL --rate 25 --duration 90
```

## Measured validation (sandbox run, c=2, μ=20)

| λ (req/s) | W measured | W predicted | error |
|-----------|-----------|-------------|-------|
| 7.2  | 48.3 ms  | 51.4 ms  | −5.9% |
| 15.6 | 57.8 ms  | 58.5 ms  | −1.2% |
| 23.9 | 78.5 ms  | 76.9 ms  | +2.1% |
| 27.9 | 86.4 ms  | 95.6 ms  | −9.6% |
| 31.4 | 144.7 ms | 126.8 ms | +14.1% |

Little's Law held within a few percent on every run (independent L and W
measurements). M/M/2/6 blocking: measured 0.228 vs theory 0.208 under
overload. Longer runs (≥120 s) tighten all of these.

## Report mapping

- **Theory** → `experiments/theory.py` (Erlang C, M/M/c/K birth–death
  solution, Little's Law); cite Kleinrock Vol. 1 / Bertsekas & Gallager
- **System design** → `service/app.py` (explicit M/M/c/K semantics),
  architecture diagram above
- **Methodology** → open-loop vs closed-loop load generation, warm-up
  discarding, separate client/server machines, μ calibration from measured
  service times
- **Results** → figA/figB/figC + Grafana screenshots + SLO scorecard
- **Discussion** → where the model erred (~±10–15% near saturation):
  service times not perfectly exponential under load, event-loop scheduling
  jitter, network RTT not in the model; real traffic is bursty/self-similar
  (future work: M/G/c, measurement-driven arrival processes)
- **Industry relevance** → capacity planning, SLO-driven admission control,
  concurrency-based autoscaling (e.g. Knative) — this project implements the
  math those systems rely on

## Notes

- Run loadgen and service on **different machines** — co-locating them
  contaminates measurements (CPU contention).
- For best results use Ethernet or sit near the router; Wi-Fi jitter adds
  noise at high rates.
- `POST /config {"mu":..,"c":..,"k":..}` reconfigures the system live —
  no restart needed between experiments.
