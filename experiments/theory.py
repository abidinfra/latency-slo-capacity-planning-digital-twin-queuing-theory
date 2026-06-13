"""
Analytical results for M/M/c and M/M/c/K queues.
These are the "digital twin" equations calibrated with the measured mu-hat.
"""

from math import factorial


def erlang_c(c: int, a: float) -> float:
    """P(wait) for M/M/c with offered load a = lam/mu, requires a/c < 1."""
    rho = a / c
    if rho >= 1:
        return 1.0
    top = (a ** c) / (factorial(c) * (1 - rho))
    return top / (sum((a ** n) / factorial(n) for n in range(c)) + top)


def mmc(lam: float, mu: float, c: int) -> dict:
    """M/M/c (unbounded queue). Returns rho, P_wait, W, Wq, L, Lq."""
    a = lam / mu
    rho = a / c
    if rho >= 1:
        inf = float("inf")
        return {"rho": rho, "P_wait": 1.0, "W": inf, "Wq": inf,
                "L": inf, "Lq": inf}
    C = erlang_c(c, a)
    Wq = C / (c * mu - lam)
    W = Wq + 1 / mu
    return {"rho": rho, "P_wait": C, "W": W, "Wq": Wq,
            "L": lam * W, "Lq": lam * Wq}


def mmck(lam: float, mu: float, c: int, K: int) -> dict:
    """
    M/M/c/K (at most K in system, K >= c). Computed from the birth-death
    state probabilities p_0..p_K — numerically robust for any rho.
    Returns rho, P_block, L, W (over admitted requests), lam_eff.
    """
    a = lam / mu
    # unnormalized state probabilities
    q = []
    for n in range(K + 1):
        if n <= c:
            q.append((a ** n) / factorial(n))
        else:
            q.append((a ** c) / factorial(c) * (a / c) ** (n - c))
    Z = sum(q)
    p = [x / Z for x in q]
    p_block = p[K]
    L = sum(n * p[n] for n in range(K + 1))
    lam_eff = lam * (1 - p_block)
    W = L / lam_eff if lam_eff > 0 else 0.0
    return {"rho": a / c, "P_block": p_block, "L": L, "W": W,
            "lam_eff": lam_eff}


def predicted_W(lam: float, mu: float, c: int, K: int = 0) -> float:
    """Mean sojourn time predicted by the calibrated model."""
    return mmck(lam, mu, c, K)["W"] if K > 0 else mmc(lam, mu, c)["W"]


def slo_capacity(mu: float, c: int, slo_seconds: float, K: int = 0) -> float:
    """
    Invert the model: the largest arrival rate lam such that predicted
    mean latency W(lam) <= slo_seconds. Bisection on (0, c*mu).
    """
    if predicted_W(1e-9, mu, c, K) > slo_seconds:
        return 0.0  # SLO below the bare service time — impossible
    lo, hi = 1e-9, c * mu * (1 - 1e-9) if K == 0 else c * mu * 3
    for _ in range(200):
        mid = (lo + hi) / 2
        if predicted_W(mid, mu, c, K) <= slo_seconds:
            lo = mid
        else:
            hi = mid
    return lo


def min_servers_for_slo(lam: float, mu: float, slo_seconds: float,
                        c_max: int = 64) -> int:
    """Erlang-C driven autoscaling: smallest c meeting the SLO at rate lam."""
    for c in range(1, c_max + 1):
        if lam < c * mu and mmc(lam, mu, c)["W"] <= slo_seconds:
            return c
    return c_max


if __name__ == "__main__":
    print("M/M/2  lam=30 mu=20:", mmc(30, 20, 2))
    print("M/M/2/10 lam=45 mu=20:", mmck(45, 20, 2, 10))
    print("SLO capacity (W<=100ms, c=2, mu=20):",
          round(slo_capacity(20, 2, 0.1), 2), "req/s")
    print("Min servers for lam=70, mu=20, SLO 100ms:",
          min_servers_for_slo(70, 20, 0.1))
