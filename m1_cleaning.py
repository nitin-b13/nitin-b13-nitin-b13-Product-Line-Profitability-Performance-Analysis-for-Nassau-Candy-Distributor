"""Module 1 - Data cleaning & validation (+ factory mapping from the brief)."""
import pandas as pd, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
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

def run():
    df, log = clean(); df.to_csv(ROOT / "data/clean.csv", index=False)
    json.dump(log, open(ROOT / "results/cleaning_log.json", "w"), indent=2); print("M1", log); return df
if __name__ == "__main__": run()
