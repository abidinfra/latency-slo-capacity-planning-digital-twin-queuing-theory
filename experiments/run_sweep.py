"""
Runs a full lambda sweep against the live service and stores all summaries.
Run this ON THE MACBOOK, pointing at the home server.

Example:
  python experiments/run_sweep.py --url http://192.168.1.50:8000 \
      --rates 5,10,15,20,25,28,30,32,34,36 --duration 120 \
      --out results/sweep_c2.json

Then:  python experiments/analyze.py --sweep results/sweep_c2.json --slo 0.1
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadgen"))
from poisson_loadgen import run_load  # noqa: E402


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--rates", required=True,
                   help="comma-separated arrival rates, e.g. 5,10,15,20")
    p.add_argument("--duration", type=float, default=120,
                   help="seconds per rate point (>=120 recommended)")
    p.add_argument("--gap", type=float, default=5,
                   help="idle seconds between runs (lets the queue drain)")
    p.add_argument("--out", default="results/sweep.json")
    args = p.parse_args()

    rates = [float(r) for r in args.rates.split(",")]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    summaries = []
    for i, rate in enumerate(rates):
        print(f"\n[{i+1}/{len(rates)}] offered rate = {rate} req/s ...")
        s = await run_load(args.url, rate, args.duration, seed=1000 + i)
        summaries.append(s)
        with open(args.out, "w") as f:           # save incrementally
            json.dump(summaries, f, indent=2)
        await asyncio.sleep(args.gap)

    print(f"\nSweep complete -> {args.out}")
    print(f"Next: python experiments/analyze.py --sweep {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
