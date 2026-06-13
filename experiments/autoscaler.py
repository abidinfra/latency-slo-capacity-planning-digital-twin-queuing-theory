"""
Stretch goal: queueing-theory-driven autoscaler.

Every interval, it measures the recent arrival rate from the server's
counters, uses Erlang-C to compute the MINIMUM number of servers c that
keeps predicted mean latency under the SLO, and applies it live via
POST /config. This is the mathematical core of how real autoscalers
(e.g. concurrency-based scaling in Knative) should size capacity.

Run it on the MacBook while a load generator ramps traffic up and down,
and screenshot Grafana showing c stepping up/down with the load:

  python experiments/autoscaler.py --url http://192.168.1.50:8000 --slo 0.1
"""

import argparse
import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(__file__))
from theory import min_servers_for_slo  # noqa: E402


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--slo", type=float, default=0.1)
    p.add_argument("--interval", type=float, default=10,
                   help="seconds between scaling decisions")
    p.add_argument("--c-max", type=int, default=32)
    args = p.parse_args()

    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        prev = (await client.get(f"{args.url}/stats")).json()
        prev_t = time.monotonic()
        print(f"Autoscaler: SLO={args.slo*1000:.0f} ms, "
              f"interval={args.interval}s. Ctrl+C to stop.")
        while True:
            await asyncio.sleep(args.interval)
            cur = (await client.get(f"{args.url}/stats")).json()
            now = time.monotonic()
            lam = ((cur["served_count"] - prev["served_count"])
                   / (now - prev_t))
            mu = cur["config"]["mu"]
            c_now = cur["config"]["c"]
            c_need = min_servers_for_slo(max(lam, 0.01), mu, args.slo,
                                         args.c_max)
            stamp = time.strftime("%H:%M:%S")
            if c_need != c_now:
                await client.post(f"{args.url}/config", json={"c": c_need})
                print(f"[{stamp}] lam={lam:6.1f} req/s -> scale c: "
                      f"{c_now} -> {c_need}")
            else:
                print(f"[{stamp}] lam={lam:6.1f} req/s -> c={c_now} OK")
            prev, prev_t = cur, now


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
