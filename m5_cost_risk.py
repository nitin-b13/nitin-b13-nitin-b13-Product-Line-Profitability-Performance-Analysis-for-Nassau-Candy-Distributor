"""Module 5 - Cost structure diagnostics & margin-risk flags (reprice / renegotiate / discontinue)."""
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def flag(pt, threshold=0.55, target=None):
    pt = pt.copy(); target = target or pt.Profit.sum() / pt.Sales.sum()
    pt["UnitPrice"] = pt.Sales / pt.Units; pt["UnitCost"] = pt.Cost / pt.Units
    pt["PriceForTarget"] = pt.UnitCost / (1 - target)
    pt["Risk"] = np.where(pt.Margin < 0.20, "Critical", np.where(pt.Margin < threshold, "Watch", "OK"))
    def act(r):
        if r.Risk == "OK": return "Maintain"
        if r.CostRatio > .8 and r.RevShare < .02: return "Discontinuation review (reprice first)"
        if r.RevShare >= .02: return "Cost renegotiation / modest repricing"
        return "Repricing"
    pt["Action"] = pt.apply(act, axis=1); return pt
def run(pt):
    f = flag(pt); f.to_csv("results/margin_risk_flags.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 5)); col = f.Risk.map({"OK": "#2e86c1", "Watch": "#f39c12", "Critical": "#c0392b"})
    ax.scatter(f.Sales, f.Cost, s=f.Profit / 60 + 20, c=col, alpha=.8); ax.set_xscale("log"); ax.set_yscale("log")
    lim = [f.Sales.min(), f.Sales.max()]; ax.plot(lim, lim, "k--", lw=1)
    for _, r in f.iterrows():
        if r.Risk != "OK" or r.Sales > 20000: ax.annotate(r["Product Name"].replace("Wonka Bar - ", ""), (r.Sales, r.Cost), fontsize=7)
    ax.set_xlabel("Sales ($, log)"); ax.set_ylabel("Cost ($, log)"); ax.set_title("Cost vs sales (below dashed line = profitable; bubble = profit)")
    plt.tight_layout(); plt.savefig("results/figures/cost_vs_sales.png", dpi=150); plt.close(); return f
