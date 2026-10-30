"""Module 2 - Profitability metric calculation (product + division level)."""
import pandas as pd
def _agg(df, keys):
    g = df.groupby(keys).agg(Sales=("Sales", "sum"), Units=("Units", "sum"), Profit=("Gross Profit", "sum"),
                              Cost=("Cost", "sum"), Orders=("Order ID", "nunique")).reset_index()
    g["Margin"] = g.Profit / g.Sales; g["ProfitPerUnit"] = g.Profit / g.Units; g["CostRatio"] = g.Cost / g.Sales
    g["RevShare"] = g.Sales / g.Sales.sum(); g["ProfitShare"] = g.Profit / g.Profit.sum()
    return g
def margin_volatility(df, key):
    m = df.groupby([key, "Order Month"]).agg(S=("Sales", "sum"), P=("Gross Profit", "sum"))
    return (m.P / m.S).groupby(level=0).std().fillna(0)          # std-dev of monthly margin (fraction)
def product_table(df):
    g = _agg(df, ["Product Name", "Division", "Factory"])
    g["MarginVolatility"] = g["Product Name"].map(margin_volatility(df, "Product Name"))
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)
def division_table(df):
    g = _agg(df, ["Division"]); g["MarginVolatility"] = g["Division"].map(margin_volatility(df, "Division"))
    g["ProfitMinusRevShare"] = g.ProfitShare - g.RevShare        # revenue vs profit imbalance
    return g.sort_values("Profit", ascending=False).reset_index(drop=True)
def run(df):
    p, d = product_table(df), division_table(df)
    p.to_csv("results/product_metrics.csv", index=False); d.to_csv("results/division_metrics.csv", index=False); return p, d
