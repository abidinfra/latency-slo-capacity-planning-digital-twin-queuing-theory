"""
The money experiment: validate the model's SLO capacity prediction LIVE.

Runs the real system at 0.9 x lam_max (model says: SLO holds) and at
1.1 x lam_max (model says: SLO violated) and reports PASS/FAIL.

  python experiments/slo_test.py --url http://192.168.1.50:8000 \
      --slo 0.1 --lam-max 28.3 --duration 120
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadgen"))
from poisson_loadgen import run_load  # noqa: E402


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--slo", type=float, default=0.1, help="SLO in seconds")
    p.add_argument("--lam-max", type=float, required=True,
                   help="predicted capacity from analyze.py")
    p.add_argument("--duration", type=float, default=120)
    args = p.parse_args()

    print(f"Model prediction: mean latency stays <= {args.slo*1000:.0f} ms "
          f"iff lambda <= {args.lam_max:.2f} req/s\n")

    results = []
    for factor, expect_ok in [(0.9, True), (1.1, False)]:
        rate = factor * args.lam_max
        print(f"--- Running at {factor:.1f} x lam_max = {rate:.2f} req/s "
              f"(model expects SLO {'MET' if expect_ok else 'VIOLATED'}) ---")
        s = await run_load(args.url, rate, args.duration, seed=int(factor * 100))
        met = s["mean_latency"] <= args.slo
        verdict = "CORRECT" if met == expect_ok else "WRONG"
        results.append((factor, rate, s["mean_latency"], expect_ok, met, verdict))
        await asyncio.sleep(5)

    print("\n================ SLO PREDICTION SCORECARD ================")
    print(f"{'load':>10} {'rate':>8} {'mean W':>10} {'predicted':>10} "
          f"{'observed':>9} {'model':>8}")
    for factor, rate, w, exp, met, verdict in results:
        print(f"{factor:>9.1f}x {rate:>8.2f} {w*1000:>8.1f}ms "
              f"{'MET' if exp else 'VIOLATED':>10} "
              f"{'MET' if met else 'VIOLATED':>9} {verdict:>8}")
    if all(r[5] == "CORRECT" for r in results):
        print("\nThe calibrated queueing model correctly predicted real "
              "system behavior on both sides of the capacity boundary.")


if __name__ == "__main__":
    asyncio.run(main())
