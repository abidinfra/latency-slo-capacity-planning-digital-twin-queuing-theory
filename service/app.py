"""
Target service for the queueing digital twin.

Implements an HTTP service with EXPLICIT M/M/c/K semantics so that
queueing theory maps cleanly onto a real running system:

  - c "servers"  : a concurrency limit. At most c requests are in service
                   at once; the rest wait in a FIFO queue (asyncio.Condition
                   wakes waiters in arrival order).
  - K capacity   : max requests IN SYSTEM (waiting + in service). Arrivals
                   beyond K are rejected with HTTP 503 -> this is admission
                   control / tail-drop, exactly like a bounded listen queue.
                   K = 0 means unbounded (pure M/M/c).
  - service time : exponential with rate MU per server (models work being
                   done; swap in real CPU work as an extension).

Exposes Prometheus metrics at /metrics and a JSON snapshot at /stats.
Config is changeable at runtime via POST /config (used by the autoscaler
experiment), no restart needed.

Run locally:   uvicorn app:app --host 0.0.0.0 --port 8000
Env vars:      MU (default 20 req/s per server), C (default 2), K (default 0)
"""

import asyncio
import os
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge,
                               Histogram, generate_latest)

# ----------------------------------------------------------------- state ----
state = {
    "mu": float(os.getenv("MU", "20")),  # service rate PER server (req/s)
    "c": int(os.getenv("C", "2")),       # number of parallel servers
    "k": int(os.getenv("K", "0")),       # max in system; 0 = unbounded
}

busy = 0                 # requests currently in service
in_system = 0            # in service + waiting (the queueing-theory "n")
served_count = 0         # cumulative completions
service_time_sum = 0.0   # cumulative pure service time (for exact mu-hat)
cond: asyncio.Condition | None = None

# --------------------------------------------------------------- metrics ----
LAT_BUCKETS = (.005, .01, .02, .03, .05, .075, .1, .15, .2, .3, .5,
               .75, 1.0, 1.5, 2.0, 3.0, 5.0)
ARRIVALS = Counter("arrivals_total", "Requests that arrived at /work")
SERVED = Counter("served_total", "Requests completed successfully")
REJECTED = Counter("rejected_total", "Requests rejected (system full, 503)")
IN_SYSTEM = Gauge("in_system", "Requests in system (waiting + in service)")
BUSY = Gauge("busy_servers", "Requests currently in service")
LATENCY = Histogram("request_latency_seconds",
                    "Total time in system (sojourn time W)",
                    buckets=LAT_BUCKETS)
SERVICE_TIME = Histogram("service_time_seconds",
                         "Pure service time (no queueing)",
                         buckets=LAT_BUCKETS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cond
    cond = asyncio.Condition()
    yield


app = FastAPI(title="queueing-digital-twin-target", lifespan=lifespan)


# ------------------------------------------------------------- endpoints ----
@app.get("/work")
async def work():
    """The modeled request: admission check -> FIFO queue -> exponential
    service. This endpoint IS the queueing system."""
    global busy, in_system, served_count, service_time_sum
    t0 = time.perf_counter()
    ARRIVALS.inc()

    # --- admission control (the "K" in M/M/c/K) ---
    k = state["k"]
    if k > 0 and in_system >= k:
        REJECTED.inc()
        return JSONResponse({"status": "rejected", "reason": "system_full"},
                            status_code=503)

    in_system += 1
    IN_SYSTEM.set(in_system)

    # --- wait for one of the c servers (FIFO via Condition) ---
    async with cond:
        while busy >= state["c"]:
            await cond.wait()
        busy += 1
        BUSY.set(busy)

    # --- exponential service ---
    st = random.expovariate(state["mu"])
    await asyncio.sleep(st)

    async with cond:
        busy -= 1
        BUSY.set(busy)
        cond.notify(1)

    in_system -= 1
    IN_SYSTEM.set(in_system)
    served_count += 1
    service_time_sum += st
    SERVED.inc()
    SERVICE_TIME.observe(st)
    LATENCY.observe(time.perf_counter() - t0)
    return {"status": "ok", "service_time_s": round(st, 6)}


@app.get("/stats")
async def stats():
    """JSON snapshot used by the load generator to sample L and to compute
    an exact mu-hat from (service_time_sum, served_count) deltas."""
    return {
        "in_system": in_system,
        "busy": busy,
        "served_count": served_count,
        "service_time_sum": service_time_sum,
        "config": dict(state),
        "ts": time.time(),
    }


@app.get("/config")
async def get_config():
    return dict(state)


@app.post("/config")
async def set_config(req: Request):
    """Update mu / c / k at runtime, e.g. {"c": 4}. Used by the
    queueing-theory autoscaler experiment."""
    body = await req.json()
    for key in ("mu", "c", "k"):
        if key in body:
            state[key] = float(body[key]) if key == "mu" else int(body[key])
    async with cond:
        cond.notify_all()  # wake waiters if c increased
    return dict(state)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
