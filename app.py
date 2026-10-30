"""Nassau Candy - product profitability & margin risk dashboard (self-contained: needs data/clean.csv or the raw CSV)."""
import numpy as np, pandas as pd, plotly.express as px, streamlit as st
from pathlib import Path
HERE = ROOT = Path(__file__).resolve().parent

# --- data cleaning (same as modules/m1_cleaning.py; used only if data/clean.csv is missing) ---
COORD = {"Lot's O' Nuts": (32.881893, -111.768036), "Wicked Choccy's": (32.076176, -81.088371),
         "Sugar Shack": (48.11914, -96.18115), "Secret Factory": (41.446333, -90.565487),
         "The Other Factory": (35.1175, -89.971107)}
FACTORY = {"Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts", "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
 "Wonka Bar - Scrumdiddlyumptious": "Lot's O' Nuts", "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
 "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's", "Laffy Taffy": "Sugar Shack", "SweeTARTS": "Sugar Shack",
 "Nerds": "Sugar Shack", "Fun Dip": "Sugar Shack", "Fizzy Lifting Drinks": "Sugar Shack",
 "Everlasting Gobstopper": "Secret Factory", "Hair Toffee": "The Other Factory", "Lickable Wallpaper": "Secret Factory",
 "Wonka Gum": "Secret Factory", "Kazookles": "The Other Factory"}
def clean(src=ROOT / "Nassau_Candy_Distributor.csv"):
    df = pd.read_csv(src); log = {"raw_rows": len(df)}
    df.columns = df.columns.str.strip()
    for c in ["Order Date", "Ship Date"]:
        df[c] = pd.to_datetime(df[c], format="%d-%m-%Y", errors="coerce")
    for c in ["Division", "Product Name", "Region", "Ship Mode", "State/Province", "City", "Country/Region"]:
        df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["Product Name"] = df["Product Name"].str.replace(r"\s*-\s*", " - ", regex=True)  # fixes 'Wonka Bar -Scrumdiddlyumptious'
    df["Division"] = df["Division"].str.title()
    log["missing_units_filled"] = int((df["Units"].isna() | (df["Units"] <= 0)).sum())
    df["Units"] = df["Units"].fillna(df.groupby("Product ID")["Units"].transform("median"))
    log["profit_mismatch_rows"] = int(((df["Sales"] - df["Cost"] - df["Gross Profit"]).abs() > 0.01).sum())
    bad = (df["Sales"] <= 0) | (df["Cost"] < 0) | (df["Units"] <= 0) | ((df["Sales"] - df["Cost"] - df["Gross Profit"]).abs() > 0.01) | df["Order Date"].isna()
    log["invalid_rows_removed"] = int(bad.sum()); df = df[~bad]
    # Same Order ID + Product ID with different Units/Sales are separate line items, so they are NOT dropped.
    log["rows_identical_except_row_id_kept"] = int(df.duplicated(subset=[c for c in df.columns if c != "Row ID"]).sum())
    log["duplicates_removed"] = 0
    df["Ship Lag Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    log["ship_lag_min_max_days"] = [int(df["Ship Lag Days"].min()), int(df["Ship Lag Days"].max())]
    log["note"] = "Ship Date is 2.5-4.5 years after Order Date in every row, so shipping-time analysis is excluded; Order Date drives all time filters."
    df["Factory"] = df["Product Name"].map(FACTORY)
    df["Factory Lat"] = df["Factory"].map(lambda f: COORD[f][0]); df["Factory Lon"] = df["Factory"].map(lambda f: COORD[f][1])
    df["Order Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    log["clean_rows"] = len(df); log["unmapped_products"] = int(df["Factory"].isna().sum())
    return df, log

def _agg(df, keys):
    g = df.groupby(keys).agg(Sales=("Sales", "sum"), Units=("Units", "sum"), Profit=("Gross Profit", "sum"),
                              Cost=("Cost", "sum"), Orders=("Order ID", "nunique")).reset_index()
    g["Margin"] = g.Profit / g.Sales; g["ProfitPerUnit"] = g.Profit / g.Units; g["CostRatio"] = g.Cost / g.Sales
    g["RevShare"] = g.Sales / g.Sales.sum(); g["ProfitShare"] = g.Profit / g.Profit.sum()
    return g
def margin_volatility(df, key):
    m = df.groupby([key, "Order Month"]).agg(S=("Sales", "sum"), P=("Gross Profit", "sum"))
    return (m.P / m.S).groupby(level=0).std().fillna(0)
def product_table(df):
    g = _agg(df, ["Product Name", "Division", "Factory"])
    g["MarginVolatility"] = g["Product Name"].map(margin_volatility(df, "Product Name"))
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)
def division_table(df):
    g = _agg(df, ["Division"]); g["MarginVolatility"] = g["Division"].map(margin_volatility(df, "Division"))
    g["ProfitMinusRevShare"] = g.ProfitShare - g.RevShare        # revenue vs profit imbalance
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)
def classify(pt):
    pm, med = pt.Profit.sum() / pt.Sales.sum(), pt.Sales.sum() / len(pt)   # high-sales = at or above average product sales
    def f(r):
        hs, hm = r.Sales >= med, r.Margin >= pm
        return ("High-profit / high-margin" if hs and hm else "High-sales / low-margin" if hs else
                "Low-sales / low-profit" if not hm else "Low-sales / high-margin (niche)")
    return pt.assign(Segment=pt.apply(f, axis=1))
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


st.set_page_config(page_title="Nassau Candy Profitability", layout="wide")

@st.cache_data
def load():
    for p in [HERE / "data" / "clean.csv", HERE / "clean.csv"]:
        if p.exists(): return pd.read_csv(p, parse_dates=["Order Date", "Ship Date", "Order Month"])
    for p in [HERE / "Nassau_Candy_Distributor.csv", HERE / "data" / "Nassau_Candy_Distributor.csv"]:
        if p.exists(): return clean(p)[0]          # cleans the raw CSV on the fly
    st.error("Data file not found. Add data/clean.csv (or Nassau_Candy_Distributor.csv) to the repo next to app.py."); st.stop()
df = load()
st.sidebar.header("Filters")
lo, hi = df["Order Date"].min().date(), df["Order Date"].max().date()
dr = st.sidebar.date_input("Order date range", (lo, hi), min_value=lo, max_value=hi)
divs = st.sidebar.multiselect("Division", sorted(df.Division.unique()), default=sorted(df.Division.unique()))
thr = st.sidebar.slider("Margin threshold (%)", 0, 90, 55) / 100
q = st.sidebar.text_input("Product search")
if len(dr) != 2: st.info("Select both a start and an end date."); st.stop()
f = df[df["Order Date"].between(pd.Timestamp(dr[0]), pd.Timestamp(dr[1])) & df.Division.isin(divs)]
if q: f = f[f["Product Name"].str.contains(q, case=False, regex=False)]
if f.empty: st.warning("No records match the current filters."); st.stop()
pt = classify(product_table(f)); dt = division_table(f); fl = flag(pt, thr)

st.title("🍬 Nassau Candy – Product Profitability & Margin Risk")
a, b, c, d, e = st.columns(5)
a.metric("Sales", f"${f.Sales.sum():,.0f}"); b.metric("Gross profit", f"${f['Gross Profit'].sum():,.0f}")
c.metric("Gross margin", f"{f['Gross Profit'].sum() / f.Sales.sum():.1%}"); d.metric("Profit / unit", f"${f['Gross Profit'].sum() / f.Units.sum():.2f}")
e.metric("Products below threshold", int((pt.Margin < thr).sum()))
t1, t2, t3, t4 = st.tabs(["Product Profitability", "Division Performance", "Cost vs Margin Diagnostics", "Profit Concentration"])

with t1:
    l, r = st.columns(2)
    p = pt.sort_values("Margin")
    l.plotly_chart(px.bar(p, x="Margin", y="Product Name", orientation="h", color=p.Margin < thr, title="Margin leaderboard",
                          color_discrete_map={True: "#c0392b", False: "#2e86c1"}, labels={"color": "Below threshold"}).update_xaxes(tickformat=".0%"), width="stretch")
    r.plotly_chart(px.pie(pt, names="Product Name", values="Profit", title="Profit contribution by product", hole=.4), width="stretch")
    st.dataframe(pt[["Product Name", "Division", "Factory", "Sales", "Profit", "Margin", "ProfitPerUnit", "RevShare", "ProfitShare", "MarginVolatility", "Segment"]]
                 .style.format({"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Margin": "{:.1%}", "ProfitPerUnit": "${:.2f}", "RevShare": "{:.1%}", "ProfitShare": "{:.1%}", "MarginVolatility": "{:.2%}"}), width="stretch")

with t2:
    l, r = st.columns(2)
    m = dt.melt(id_vars="Division", value_vars=["Sales", "Profit"], var_name="Metric", value_name="USD")
    l.plotly_chart(px.bar(m, x="Division", y="USD", color="Metric", barmode="group", title="Revenue vs profit"), width="stretch")
    r.plotly_chart(px.box(f.assign(Margin=f["Gross Profit"] / f.Sales), x="Division", y="Margin", title="Order-level margin distribution", points=False).update_yaxes(tickformat=".0%"), width="stretch")
    st.dataframe(dt.style.format({"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Cost": "${:,.0f}", "Margin": "{:.1%}", "RevShare": "{:.1%}", "ProfitShare": "{:.1%}", "ProfitMinusRevShare": "{:+.1%}", "CostRatio": "{:.1%}", "ProfitPerUnit": "${:.2f}", "MarginVolatility": "{:.2%}"}), width="stretch")
    mo = f.groupby("Order Month").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum")).reset_index()
    st.plotly_chart(px.line(mo, x="Order Month", y=["Sales", "Profit"], title="Monthly trend"), width="stretch")

with t3:
    l, r = st.columns(2)
    l.plotly_chart(px.scatter(fl, x="Sales", y="Cost", size="Profit", color="Risk", hover_name="Product Name", log_x=True, log_y=True, title="Cost vs sales by product (log scale)",
                              color_discrete_map={"OK": "#2e86c1", "Watch": "#f39c12", "Critical": "#c0392b"}), width="stretch")
    s = f.sample(min(len(f), 3000), random_state=1)
    r.plotly_chart(px.scatter(s, x="Sales", y="Cost", color="Division", hover_name="Product Name", title="Order-level cost vs sales (sample)"), width="stretch")
    st.subheader("Margin-risk flags and recommended actions")
    st.dataframe(fl[fl.Risk != "OK"][["Product Name", "Risk", "Action", "Margin", "CostRatio", "UnitPrice", "UnitCost", "PriceForTarget"]]
                 .style.format({"Margin": "{:.1%}", "CostRatio": "{:.1%}", "UnitPrice": "${:.2f}", "UnitCost": "${:.2f}", "PriceForTarget": "${:.2f}"}), width="stretch")
    st.caption("PriceForTarget = unit price needed to reach the portfolio margin at current unit cost.")

with t4:
    pp = pareto(f.groupby("Product Name")["Gross Profit"].sum()).reset_index(); ps = pareto(f.groupby("Product Name")["Sales"].sum()).reset_index()
    import plotly.graph_objects as go
    fig = go.Figure(); fig.add_bar(x=pp["Product Name"], y=pp.value, name="Profit ($)")
    fig.add_scatter(x=pp["Product Name"], y=pp.cum_share * 100, name="Cumulative profit %", yaxis="y2", mode="lines+markers")
    fig.add_scatter(x=ps["Product Name"], y=ps.cum_share * 100, name="Cumulative revenue %", yaxis="y2", mode="lines+markers")
    fig.update_layout(title="Pareto – profit concentration", yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="%"))
    st.plotly_chart(fig, width="stretch")
    dep = dependency(f); k = st.columns(4)
    k[0].metric("Products for 80% of profit", f"{dep['Product Name']['n80_profit']} of {dep['Product Name']['n']}")
    k[1].metric("Top product share of profit", f"{dep['Product Name']['top1']:.1%}")
    k[2].metric("Top factory share", f"{dep['Factory']['top1']:.1%}", dep["Factory"]["top1_name"])
    k[3].metric("Top state share", f"{dep['State/Province']['top1']:.1%}", dep["State/Province"]["top1_name"])
    st.dataframe(pd.DataFrame(dep).T[["n", "n80_rev", "n80_profit", "top1_name", "top1", "top3", "hhi_profit"]].rename(columns={"n": "Entities", "n80_rev": "# for 80% revenue", "n80_profit": "# for 80% profit", "top1_name": "Top entity", "top1": "Top-1 profit share", "top3": "Top-3 share", "hhi_profit": "HHI"}), width="stretch")
    st.caption("Dependency indicators: a high top-1 share or HHI (>0.25) signals over-reliance on a single product, factory, division, state or region.")
