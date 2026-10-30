"""Module 4 - Profit concentration (Pareto) & dependency indicators."""
import pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def pareto(s):
    s = s.sort_values(ascending=False); c = s.cumsum() / s.sum()
    return pd.DataFrame({"value": s, "cum_share": c, "rank": range(1, len(s) + 1)})
def n_for(s, t=.8): return int((s.sort_values(ascending=False).cumsum() / s.sum() < t).sum() + 1)
def hhi(s): sh = s / s.sum(); return float((sh ** 2).sum())
def dependency(df):
    out = {}
    for key in ["Product Name", "Factory", "Division", "State/Province", "Region"]:
        sales, prof = df.groupby(key)["Sales"].sum(), df.groupby(key)["Gross Profit"].sum()
        out[key] = dict(n=len(prof), n80_rev=n_for(sales), n80_profit=n_for(prof), top1=prof.max() / prof.sum(), top1_name=prof.idxmax(),
                        top3=prof.nlargest(3).sum() / prof.sum(), hhi_profit=hhi(prof))
    return out
def run(df):
    dep = dependency(df); pd.DataFrame(dep).T.to_csv("results/dependency.csv")
    ps, pp = pareto(df.groupby("Product Name")["Sales"].sum()), pareto(df.groupby("Product Name")["Gross Profit"].sum())
    fig, ax = plt.subplots(figsize=(8, 4.5)); ax.plot(ps["rank"] / len(ps) * 100, ps.cum_share * 100, marker="o", label="Revenue")
    ax.plot(pp["rank"] / len(pp) * 100, pp.cum_share * 100, marker="s", label="Gross profit"); ax.axhline(80, ls="--", c="grey")
    ax.set_xlabel("% of products (ranked)"); ax.set_ylabel("Cumulative %"); ax.set_title("Pareto: revenue and profit concentration"); ax.legend()
    plt.tight_layout(); plt.savefig("results/figures/pareto.png", dpi=150); plt.close(); return dep
