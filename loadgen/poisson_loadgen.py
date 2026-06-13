"""
Open-loop Poisson load generator.

WHY NOT wrk / ab / hey?  Those are CLOSED-LOOP: a fixed pool of workers
waits for each response before sending the next request. When the server
slows down, the offered rate silently drops, which destroys the Poisson
arrival assumption and hides queueing collapse ("coordinated omission").
This generator is OPEN-LOOP: arrivals are scheduled by exponential
inter-arrival gaps regardless of how the server is doing -- exactly the
M in M/M/c.

Also samples the server's /stats endpoint every 200 ms to measure the
time-average number in system (L) and reads (service_time_sum, served_count)
deltas to compute an exact service-rate estimate mu-hat.

Usage (from the MacBook, pointing at the home server):
  python loadgen/poisson_loadgen.py --url http://SERVER_IP:8000 \
      --rate 30 --duration 60 --out results/run_r30.csv
"""

import argparse
import asyncio
import csv
import json
import random
import statistics
import time

import httpx

WARMUP_FRAC = 0.15  # discard the first 15% of the run (transient)


async def run_load(url: str, rate: float, duration: float,
                   out_csv: str | None = None, seed: int | None = None,
                   quiet: bool = False) -> dict:
    rng = random.Random(seed)
    records = []          # (t_rel, status, latency_s)
    l_samples = []        # (t_rel, in_system) sampled from /stats
    stop = asyncio.Event()

    limits = httpx.Limits(max_connections=2000, max_keepalive_connections=500)
    # trust_env=False: ignore HTTP(S)_PROXY env vars — we measure the direct
    # LAN path to the server, never a corporate proxy.
    async with httpx.AsyncClient(limits=limits, timeout=30.0,
                                 trust_env=False) as client:

        stats0 = (await client.get(f"{url}/stats")).json()
        t_start = time.perf_counter()

        async def one_request():
            t0 = time.perf_counter()
            try:
                r = await client.get(f"{url}/work")
                status = r.status_code
            except Exception:
                status = -1
            records.append((t0 - t_start, status, time.perf_counter() - t0))

        async def arrival_process():
            tasks = []
            while time.perf_counter() - t_start < duration:
                await asyncio.sleep(rng.expovariate(rate))
                tasks.append(asyncio.create_task(one_request()))
            stop.set()
            await asyncio.gather(*tasks)

        async def l_sampler():
            while not stop.is_set():
                try:
                    s = (await client.get(f"{url}/stats")).json()
                    l_samples.append((time.perf_counter() - t_start,
                                      s["in_system"]))
                except Exception:
                    pass
                await asyncio.sleep(0.2)

        await asyncio.gather(arrival_process(), l_sampler())
        stats1 = (await client.get(f"{url}/stats")).json()

    # ------------------------------------------------------- summarize ----
    t_warm = WARMUP_FRAC * duration
    window = duration - t_warm
    in_win = [r for r in records if r[0] >= t_warm]
    ok = [r for r in in_win if r[1] == 200]
    rejected = [r for r in in_win if r[1] == 503]
    errors = [r for r in in_win if r[1] not in (200, 503)]
    lats = sorted(r[2] for r in ok)
    l_win = [n for t, n in l_samples if t >= t_warm]

    d_served = stats1["served_count"] - stats0["served_count"]
    d_st = stats1["service_time_sum"] - stats0["service_time_sum"]
    mu_hat = d_served / d_st if d_st > 0 else float("nan")

    summary = {
        "offered_rate": rate,
        "duration": duration,
        "sent": len(in_win),
        "ok": len(ok),
        "rejected": len(rejected),
        "errors": len(errors),
        "achieved_rate": len(in_win) / window,
        "throughput": len(ok) / window,
        "reject_prob": len(rejected) / len(in_win) if in_win else 0.0,
        "mean_latency": statistics.fmean(lats) if lats else float("nan"),
        "p50_latency": lats[len(lats) // 2] if lats else float("nan"),
        "p95_latency": lats[int(0.95 * len(lats))] if lats else float("nan"),
        "p99_latency": lats[int(0.99 * len(lats))] if lats else float("nan"),
        "L_measured": statistics.fmean(l_win) if l_win else float("nan"),
        "mu_hat": mu_hat,
        "server_config": stats1["config"],
    }
    # Little's Law cross-check computed from INDEPENDENT measurements:
    summary["littles_lhs_L"] = summary["L_measured"]
    summary["littles_rhs_lamW"] = summary["throughput"] * summary["mean_latency"]

    if out_csv:
        with open(out_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_rel_s", "status", "latency_s"])
            w.writerows(records)

    if not quiet:
        cfg = summary["server_config"]
        print(f"\n=== rate={rate:.1f} req/s for {duration:.0f}s  "
              f"(server: c={cfg['c']}, mu={cfg['mu']}, K={cfg['k']}) ===")
        print(f"  sent={summary['sent']}  ok={summary['ok']}  "
              f"rejected={summary['rejected']}  errors={summary['errors']}")
        print(f"  mean W = {summary['mean_latency']*1000:.1f} ms   "
              f"p95 = {summary['p95_latency']*1000:.1f} ms   "
              f"p99 = {summary['p99_latency']*1000:.1f} ms")
        print(f"  L measured = {summary['L_measured']:.3f}   "
              f"lam_eff x W = {summary['littles_rhs_lamW']:.3f}   (Little's Law)")
        print(f"  mu_hat = {summary['mu_hat']:.2f} req/s per server   "
              f"reject prob = {summary['reject_prob']:.4f}")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--rate", type=float, required=True,
                   help="Poisson arrival rate, requests/second")
    p.add_argument("--duration", type=float, default=60)
    p.add_argument("--out", default=None, help="per-request CSV path")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--json", default=None, help="write summary JSON here")
    args = p.parse_args()
    summary = asyncio.run(run_load(args.url, args.rate, args.duration,
                                   out_csv=args.out, seed=args.seed))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
