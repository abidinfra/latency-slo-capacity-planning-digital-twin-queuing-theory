"""
Analyzes a sweep: calibrates mu-hat from measured service times, overlays
the M/M/c (or M/M/c/K) digital-twin prediction on the REAL measurements,
verifies Little's Law on real data, and computes the SLO capacity.

  python experiments/analyze.py --sweep results/sweep_c2.json --slo 0.1
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from theory import mmc, mmck, predicted_W, slo_capacity  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", required=True, help="sweep JSON from run_sweep")
    p.add_argument("--slo", type=float, default=0.1,
                   help="mean-latency SLO in seconds (default 0.1 = 100 ms)")
    p.add_argument("--outdir", default="results")
    args = p.parse_args()

    runs = json.load(open(args.sweep))
    os.makedirs(args.outdir, exist_ok=True)
    cfg = runs[-1]["server_config"]
    c, K = int(cfg["c"]), int(cfg["k"])

    # ---- calibration: pooled mu-hat across all runs --------------------
    mu_hat = float(np.mean([r["mu_hat"] for r in runs]))
    print(f"Server config: c={c}, K={K or 'inf'}")
    print(f"Calibrated service rate mu_hat = {mu_hat:.3f} req/s per server "
          f"(configured: {cfg['mu']})")

    lams = np.array([r["achieved_rate"] for r in runs])
    W_meas = np.array([r["mean_latency"] for r in runs])
    L_meas = np.array([r["L_measured"] for r in runs])
    thr = np.array([r["throughput"] for r in runs])
    rej = np.array([r["reject_prob"] for r in runs])

    lam_grid = np.linspace(max(lams.min() * 0.5, 0.1),
                           min(lams.max() * 1.1,
                               c * mu_hat * (0.99 if K == 0 else 1.5)), 250)
    W_pred = [predicted_W(l, mu_hat, c, K) for l in lam_grid]

    # ---- fig A: latency vs offered load, prediction vs reality ----------
    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=130)
    ax.plot(lam_grid, np.array(W_pred) * 1000, color="tab:blue",
            label=f"Digital twin prediction (M/M/{c}"
                  f"{'/'+str(K) if K else ''}, mu_hat={mu_hat:.1f})")
    ax.plot(lams, W_meas * 1000, "o", color="tab:red", ms=7,
            label="REAL measurements (MacBook -> server)")
    ax.axhline(args.slo * 1000, color="gray", ls="--", lw=1,
               label=f"SLO = {args.slo*1000:.0f} ms")
    ax.set_xlabel("Arrival rate λ (req/s)")
    ax.set_ylabel("Mean latency W (ms)")
    ax.set_title("Calibrated queueing model vs real system")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "figA_latency_vs_load.png"))
    plt.close(fig)

    # ---- fig B: Little's Law on real data -------------------------------
    fig, ax = plt.subplots(figsize=(5.8, 5.4), dpi=130)
    lamW = thr * W_meas
    lim = max(lamW.max(), L_meas.max()) * 1.08
    ax.plot([0, lim], [0, lim], color="gray", label="L = λW")
    ax.plot(lamW, L_meas, "o", color="tab:green", ms=7,
            label="Real runs (independent measurements)")
    ax.set_xlabel("λ_eff · W   (throughput × mean latency)")
    ax.set_ylabel("L   (sampled in-system average)")
    ax.set_title("Little's Law verified on a REAL system")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "figB_littles_law_real.png"))
    plt.close(fig)

    # ---- fig C: rejection probability (only meaningful when K > 0) ------
    if K > 0:
        fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=130)
        rej_pred = [mmck(l, mu_hat, c, K)["P_block"] for l in lam_grid]
        ax.plot(lam_grid, rej_pred, color="tab:blue", label="Predicted P_block")
        ax.plot(lams, rej, "o", color="tab:red", ms=7, label="Measured 503 rate")
        ax.set_xlabel("Arrival rate λ (req/s)")
        ax.set_ylabel("Rejection probability")
        ax.set_title(f"Admission control: M/M/{c}/{K} blocking, theory vs real")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(args.outdir, "figC_rejection_vs_load.png"))
        plt.close(fig)

    # ---- SLO capacity prediction ----------------------------------------
    lam_max = slo_capacity(mu_hat, c, args.slo, K)
    print(f"\n=== SLO capacity prediction ===")
    print(f"SLO: mean latency <= {args.slo*1000:.0f} ms")
    print(f"Predicted maximum sustainable arrival rate: "
          f"lam_max = {lam_max:.2f} req/s "
          f"(utilization rho = {lam_max/(c*mu_hat):.2f})")
    print(f"Validate it live:")
    print(f"  python experiments/slo_test.py --url <URL> --slo {args.slo} "
          f"--lam-max {lam_max:.2f}")

    # ---- model error table ----------------------------------------------
    print("\nlambda   W_measured   W_predicted   error")
    for lam, w in zip(lams, W_meas):
        wp = predicted_W(lam, mu_hat, c, K)
        print(f"{lam:6.1f}   {w*1000:8.1f} ms   {wp*1000:8.1f} ms   "
              f"{100*(w-wp)/wp:+6.1f}%")
    print(f"\nFigures written to {args.outdir}/")


if __name__ == "__main__":
    main()
