"""Module 3 - Product-level & division-level profitability analysis (+ EDA charts)."""
import pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
FIG = "results/figures/"
def classify(pt):
    pm, med = pt.Profit.sum() / pt.Sales.sum(), pt.Sales.sum() / len(pt)   # high-sales = at or above average product sales
    def f(r):
        hs, hm = r.Sales >= med, r.Margin >= pm
        return ("High-profit / high-margin" if hs and hm else "High-sales / low-margin" if hs else
                "Low-sales / low-profit" if not hm else "Low-sales / high-margin (niche)")
    return pt.assign(Segment=pt.apply(f, axis=1))
def run(df, pt, dt):
    pt = classify(pt); pt.to_csv("results/product_segments.csv", index=False)
    p = pt.sort_values("Margin"); fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(p["Product Name"], p.Margin * 100, color=["#c0392b" if m < .5 else "#2e86c1" for m in p.Margin])
    ax.axvline(pt.Profit.sum() / pt.Sales.sum() * 100, ls="--", c="k", lw=1); ax.set_xlabel("Gross margin (%)")
    ax.set_title("Product margin leaderboard (dashed = portfolio margin)"); plt.tight_layout(); plt.savefig(FIG + "margin_leaderboard.png", dpi=150); plt.close()
    fig, ax = plt.subplots(figsize=(7, 4)); x = range(len(dt)); w = .38
    ax.bar([i - w / 2 for i in x], dt.RevShare * 100, w, label="Revenue share"); ax.bar([i + w / 2 for i in x], dt.ProfitShare * 100, w, label="Profit share")
    ax.set_xticks(list(x)); ax.set_xticklabels(dt.Division); ax.set_ylabel("%"); ax.legend(); ax.set_title("Division: revenue vs profit share")
    plt.tight_layout(); plt.savefig(FIG + "division_rev_vs_profit.png", dpi=150); plt.close()
    m = df.groupby("Order Month").agg(S=("Sales", "sum"), P=("Gross Profit", "sum")); fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(m.index, m.S, label="Sales"); ax.plot(m.index, m.P, label="Gross profit"); ax.set_title("Monthly sales and gross profit"); ax.legend()
    plt.tight_layout(); plt.savefig(FIG + "monthly_trend.png", dpi=150); plt.close(); return pt
