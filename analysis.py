"""
analysis.py
-----------
All data loading, cleaning and calculation logic for the sales dashboard.
This file has NO Streamlit code, so you can read it, test it, or run it from
the terminal:   python3 analysis.py

Formulas used everywhere in the project
    Revenue        = Quantity x Unit Price x (1 - Discount)
    Product Profit = Revenue - Quantity x Unit Cost
    Profit Margin  = Total Product Profit / Total Revenue x 100
    Orders         = number of DISTINCT Order IDs

Product Profit only subtracts the product cost. Overheads, shipping, marketing
and taxes are not in the dataset, so they are NOT included.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# 1. Column names
# --------------------------------------------------------------------------
# The app uses these standard names internally. If your CSV uses different
# headings (for example "OrderID" or "Sales Channel"), add them to the
# lists below and the loader will rename them automatically.
COLUMN_ALIASES = {
    "order_id": ["order id", "orderid", "order number", "order no", "invoice id"],
    "order_date": ["order date", "date", "orderdate", "invoice date"],
    "region": ["region", "sales region", "market", "territory"],
    "category": ["category", "product category", "product line", "department"],
    "product": ["product", "product name", "item", "sku name"],
    "channel": ["channel", "sales channel", "sales method", "retailer type"],
    "quantity": ["quantity", "qty", "units sold", "units", "quantity sold"],
    "unit_price": ["unit price", "price", "price per unit", "list price"],
    "unit_cost": ["unit cost", "cost", "cost per unit", "cogs per unit"],
    "discount": ["discount", "discount rate", "discount %", "discount pct"],
}
TEXT_COLUMNS = ["region", "category", "product", "channel"]

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "sales_synthetic.csv"

# Discount groups used in the discount analysis (upper bound is inclusive)
DISCOUNT_BINS = [-0.001, 0.0, 0.10, 0.20, 1.0]
DISCOUNT_LABELS = ["No discount", "1-10%", "11-20%", "Over 20%"]


# --------------------------------------------------------------------------
# 2. Loading and cleaning
# --------------------------------------------------------------------------
def _simplify(name: str) -> str:
    """'  Order_ID ' -> 'order id' so headings can be matched loosely."""
    cleaned = "".join(ch.lower() if ch.isalnum() or ch == "%" else " " for ch in str(name))
    return " ".join(cleaned.split())


def standardise_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename the CSV's headings to the standard names. Raises a clear error if any are missing."""
    lookup = {_simplify(col): col for col in raw.columns}
    rename, missing = {}, []
    for standard, aliases in COLUMN_ALIASES.items():
        match = next((lookup[a] for a in aliases if a in lookup), None)
        if match is None:
            missing.append(f"{standard} (looked for: {', '.join(aliases)})")
        else:
            rename[match] = standard
    if missing:
        raise ValueError(
            "These required columns were not found in your CSV:\n- " + "\n- ".join(missing)
            + "\nAdd the heading names to COLUMN_ALIASES in analysis.py."
        )
    return raw.rename(columns=rename)[list(COLUMN_ALIASES)]


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], pd.Series]:
    """
    Clean the raw table step by step.
    Returns: (clean dataframe, cleaning log, missing values per column BEFORE cleaning)
    """
    log: list[dict] = []

    def record(step: str, rows: int, decision: str) -> None:
        log.append({"Step": step, "Rows affected": int(rows), "Decision": decision})

    df = standardise_columns(raw)
    missing_before = df.isna().sum()
    record("Rows loaded", len(df), "Starting point: every row in the CSV.")

    # Text columns: remove stray spaces; blank strings become missing values
    padded_rows = pd.Series(False, index=df.index)
    for col in TEXT_COLUMNS + ["order_id"]:
        text = df[col].astype("string")
        padded_rows |= (text != text.str.strip()).fillna(False)
        df[col] = text.str.strip().replace("", pd.NA)
    n_changed = int(padded_rows.sum())
    record("Trimmed extra spaces in text", n_changed,
           "Values like ' Online Store ' and 'Online Store' must count as one channel.")

    # Dates and numbers: anything that cannot be converted becomes missing
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    for col in ["quantity", "unit_price", "unit_cost", "discount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Discount might be stored as 10 instead of 0.10
    if df["discount"].max() > 1:
        df["discount"] = df["discount"] / 100
        record("Discount rescaled", len(df), "Values looked like percentages (e.g. 10), so they were divided by 100.")

    # Exact duplicate rows are almost certainly accidental double entries
    n_dup = int(df.duplicated().sum())
    df = df.drop_duplicates()
    record("Removed exact duplicate rows", n_dup, "A row repeated in every column was kept only once.")

    # Rows missing something needed to calculate revenue or profit cannot be used
    must_have = ["order_id", "order_date", "quantity", "unit_price", "unit_cost", "discount"]
    n_missing = int(df[must_have].isna().any(axis=1).sum())
    df = df.dropna(subset=must_have)
    record("Dropped rows missing key values", n_missing,
           "Order ID, date, quantity, price, cost and discount are all needed. Guessing them would invent data.")

    # Impossible values
    bad = (df["quantity"] <= 0) | (df["unit_price"] <= 0) | (df["unit_cost"] < 0) | (~df["discount"].between(0, 1))
    n_bad = int(bad.sum())
    df = df[~bad]
    record("Dropped impossible values", n_bad,
           "Quantity or price <= 0, negative cost, or discount outside 0-100%.")

    # Missing labels do not stop revenue being calculated, so keep the row
    n_unknown = int(df[TEXT_COLUMNS].isna().any(axis=1).sum())
    df[TEXT_COLUMNS] = df[TEXT_COLUMNS].fillna("Unknown").astype(str)
    record("Missing labels set to 'Unknown'", n_unknown,
           "Region/category/product/channel gaps keep their revenue; they show up as 'Unknown' instead of vanishing.")

    df = add_metrics(df.reset_index(drop=True))
    record("Rows used for analysis", len(df), "Final clean table.")
    return df, log, missing_before


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add revenue, cost, profit, month and discount-group columns."""
    df = df.copy()
    df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
    df["cost"] = df["quantity"] * df["unit_cost"]
    df["profit"] = df["revenue"] - df["cost"]
    df["month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    df["discount_group"] = pd.cut(df["discount"], bins=DISCOUNT_BINS, labels=DISCOUNT_LABELS)
    return df


def load_data(path: str | Path = DEFAULT_DATA_PATH):
    """Read the CSV and clean it. Returns (clean df, cleaning log, missing-values table)."""
    raw = pd.read_csv(path)
    return clean_data(raw)


# --------------------------------------------------------------------------
# 3. Filtering
# --------------------------------------------------------------------------
def filter_data(df: pd.DataFrame, start, end, regions, categories, channels) -> pd.DataFrame:
    """Apply the sidebar filters. An empty list means 'nothing selected', which returns an empty table."""
    mask = (
        (df["order_date"] >= pd.Timestamp(start))
        & (df["order_date"] <= pd.Timestamp(end))
        & df["region"].isin(regions)
        & df["category"].isin(categories)
        & df["channel"].isin(channels)
    )
    return df[mask]


# --------------------------------------------------------------------------
# 4. Metrics and summary tables
# --------------------------------------------------------------------------
def safe_margin(profit: float, revenue: float) -> float:
    """Profit margin in %, or NaN if revenue is zero (avoids divide-by-zero)."""
    return float(profit / revenue * 100) if revenue else float("nan")


def compute_kpis(df: pd.DataFrame) -> dict:
    revenue, profit = float(df["revenue"].sum()), float(df["profit"].sum())
    return {
        "revenue": revenue,
        "profit": profit,
        "orders": int(df["order_id"].nunique()),
        "units": int(df["quantity"].sum()),
        "margin": safe_margin(profit, revenue),
    }


def summarise(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Revenue, profit, units, orders and margin for each group in `by`."""
    out = (
        df.groupby(by, observed=True)
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"),
             units=("quantity", "sum"), orders=("order_id", "nunique"), lines=("order_id", "size"))
        .reset_index()
    )
    out["margin"] = np.where(out["revenue"] > 0, out["profit"] / out["revenue"] * 100, np.nan)
    return out


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarise(df, "month").sort_values("month")


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarise(df, "category").sort_values("revenue", ascending=False)
    out["revenue_share"] = out["revenue"] / out["revenue"].sum() * 100
    return out


def region_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarise(df, "region").sort_values("revenue", ascending=False)


def channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarise(df, "channel").sort_values("revenue", ascending=False)


def product_summary(df: pd.DataFrame) -> pd.DataFrame:
    return summarise(df, ["product", "category"])


def discount_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = summarise(df, "discount_group")
    out["revenue_share"] = out["revenue"] / out["revenue"].sum() * 100
    return out.sort_values("discount_group")


# --------------------------------------------------------------------------
# 5. Formatting helpers
# --------------------------------------------------------------------------
def money(value: float, symbol: str = "$") -> str:
    """12345678 -> $12.35M, 45600 -> $45.6K, 120 -> $120"""
    if pd.isna(value):
        return "n/a"
    sign, v = ("-" if value < 0 else ""), abs(value)
    if v >= 1e6:
        return f"{sign}{symbol}{v / 1e6:.2f}M"
    if v >= 1e4:
        return f"{sign}{symbol}{v / 1e3:.1f}K"
    return f"{sign}{symbol}{v:,.0f}"


def pct(value: float, digits: int = 1) -> str:
    return "n/a" if pd.isna(value) else f"{value:.{digits}f}%"


# --------------------------------------------------------------------------
# 6. Executive summary (every sentence is built from the filtered data)
# --------------------------------------------------------------------------
MIN_ORDERS_FOR_GROUP = 30  # groups smaller than this are flagged as a small sample
MIN_MARGIN_GAP = 2.0       # margin gaps smaller than this (percentage points) are called "similar"


def known_only(table: pd.DataFrame, column: str) -> pd.DataFrame:
    """Drop the 'Unknown' label so it is never reported as a best/worst performer."""
    return table[table[column] != "Unknown"]


def generate_insights(df: pd.DataFrame, symbol: str = "$") -> list[dict]:
    """
    Return up to 5 findings, each with a 'finding' and a 'recommendation'.
    Wording is careful: the data shows association, not cause.
    """
    insights: list[dict] = []
    if df.empty:
        return insights
    kpi = compute_kpis(df)

    # 1. Category contribution
    cat = known_only(category_summary(df), "category")
    top = cat.iloc[0] if len(cat) else category_summary(df).iloc[0]
    finding = (f"{top['category']} brings in the most revenue: {money(top['revenue'], symbol)} "
               f"({pct(top['revenue_share'])} of the total) at a {pct(top['margin'])} margin "
               f"versus {pct(kpi['margin'])} overall.")
    if len(cat) > 1:
        low = cat.sort_values("margin").iloc[0]
        finding += f" {low['category']} has the lowest margin at {pct(low['margin'])}."
        rec = (f"Keep {top['category']} well stocked, and review pricing and unit cost for "
               f"{low['category']} to see whether its margin can improve.")
    else:
        rec = f"Only {top['category']} is selected; widen the category filter to compare categories."
    insights.append({"title": "Category mix", "finding": finding, "recommendation": rec})

    # 2. Monthly pattern
    monthly = monthly_summary(df)
    if len(monthly) >= 3:
        peak = monthly.loc[monthly["revenue"].idxmax()]
        low = monthly.loc[monthly["revenue"].idxmin()]
        avg = monthly["revenue"].mean()
        finding = (f"Revenue peaked in {peak['month']:%b %Y} at {money(peak['revenue'], symbol)}, about "
                   f"{peak['revenue'] / avg:.1f}x the monthly average; the weakest month was "
                   f"{low['month']:%b %Y} ({money(low['revenue'], symbol)}).")
        rec = ("Plan stock and campaigns ahead of the strongest months, and check whether the weakest "
               "months repeat across years before treating them as a pattern.")
        insights.append({"title": "Monthly pattern", "finding": finding, "recommendation": rec})

    # 3. Regions
    reg = known_only(region_summary(df), "region")
    if len(reg) > 1:
        top_rev = reg.iloc[0]
        best_margin = reg.sort_values("margin", ascending=False).iloc[0]
        worst_margin = reg.sort_values("margin").iloc[0]
        share = pct(top_rev["revenue"] / kpi["revenue"] * 100)
        finding = f"{top_rev['region']} leads on revenue ({money(top_rev['revenue'], symbol)}, {share} of the total)"
        if best_margin["region"] == top_rev["region"]:
            finding += f" and also has the highest margin ({pct(best_margin['margin'])})."
        else:
            finding += f". {best_margin['region']} has the highest margin at {pct(best_margin['margin'])}."
        gap = best_margin["margin"] - worst_margin["margin"]
        if gap < MIN_MARGIN_GAP:
            finding = (f"{top_rev['region']} leads on revenue ({money(top_rev['revenue'], symbol)}, {share} of the total). "
                       f"Margins are very similar across regions ({pct(worst_margin['margin'])} to "
                       f"{pct(best_margin['margin'])}), so scale rather than profitability separates them.")
            rec = (f"Because margins are close, prioritise regions by revenue growth potential and "
                   f"check whether smaller regions such as {reg.iloc[-1]['region']} have room to grow.")
        else:
            finding += f" The lowest margin is in {worst_margin['region']} ({pct(worst_margin['margin'])})."
            rec = (f"Look into pricing, discounts and unit costs in {worst_margin['region']} before adding more "
                   f"volume there, and use {best_margin['region']} as the benchmark.")
        insights.append({"title": "Regional performance", "finding": finding, "recommendation": rec})

    # 4. Channels
    ch = known_only(channel_summary(df), "channel")
    if len(ch) > 1:
        top_rev = ch.iloc[0]
        best_margin = ch.sort_values("margin", ascending=False).iloc[0]
        worst_margin = ch.sort_values("margin").iloc[0]
        finding = (f"{top_rev['channel']} is the largest channel by revenue ({money(top_rev['revenue'], symbol)}). "
                   f"Margin ranges from {pct(worst_margin['margin'])} ({worst_margin['channel']}) "
                   f"to {pct(best_margin['margin'])} ({best_margin['channel']}).")
        rec = (f"Compare discount levels and unit costs in {worst_margin['channel']} with those in "
               f"{best_margin['channel']} to understand the margin gap.")
        insights.append({"title": "Sales channels", "finding": finding, "recommendation": rec})

    # 5. Discounts (association only)
    disc = discount_summary(df)
    if len(disc) > 1:
        best = disc.sort_values("margin", ascending=False).iloc[0]
        worst = disc.sort_values("margin").iloc[0]
        finding = (f"Margin is {pct(best['margin'])} for the '{best['discount_group']}' group and "
                   f"{pct(worst['margin'])} for '{worst['discount_group']}'. A larger discount lowers the "
                   f"price while unit cost stays the same, so a lower margin is expected arithmetically.")
        small = disc[disc["orders"] < MIN_ORDERS_FOR_GROUP]["discount_group"].astype(str).tolist()
        if small:
            finding += f" Small sample (under {MIN_ORDERS_FOR_GROUP} orders): {', '.join(small)}."
        rec = ("This data cannot show whether discounts raised sales volume. Before widening discounts, "
               "run a controlled comparison (e.g. matched products or regions with and without a promotion).")
        insights.append({"title": "Discount groups", "finding": finding, "recommendation": rec})

    return insights


# --------------------------------------------------------------------------
# 7. CSV exports
# --------------------------------------------------------------------------
def export_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Filtered order lines with the calculated columns, using readable headings."""
    out = df[["order_id", "order_date", "region", "channel", "category", "product", "quantity",
              "unit_price", "unit_cost", "discount", "revenue", "cost", "profit"]].copy()
    out["order_date"] = out["order_date"].dt.strftime("%Y-%m-%d")
    out = out.round({"revenue": 2, "cost": 2, "profit": 2})
    out.columns = ["Order ID", "Order Date", "Region", "Channel", "Category", "Product", "Quantity",
                   "Unit Price", "Unit Cost", "Discount", "Revenue", "Product Cost", "Product Profit"]
    return out


def export_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One tidy table with every summary view (category, region, channel, discount group, month)."""
    views = {
        "Category": ("category", category_summary(df)),
        "Region": ("region", region_summary(df)),
        "Channel": ("channel", channel_summary(df)),
        "Discount group": ("discount_group", discount_summary(df)),
        "Month": ("month", monthly_summary(df)),
    }
    parts = []
    for name, (col, table) in views.items():
        part = table[[col, "revenue", "profit", "margin", "units", "orders"]].copy()
        part.insert(0, "Analysis", name)
        part = part.rename(columns={col: "Group"})
        part["Group"] = part["Group"].astype(str).str[:10] if name == "Month" else part["Group"].astype(str)
        parts.append(part)
    out = pd.concat(parts, ignore_index=True).round(2)
    out.columns = ["Analysis", "Group", "Revenue", "Product Profit", "Profit Margin %", "Units Sold", "Orders"]
    return out


# --------------------------------------------------------------------------
# 8. Quick terminal report:  python3 analysis.py
# --------------------------------------------------------------------------
if __name__ == "__main__":
    data, cleaning_log, _ = load_data()
    print(pd.DataFrame(cleaning_log).to_string(index=False))
    print("\nKPIs:", compute_kpis(data))
    print("\n", category_summary(data).round(1).to_string(index=False))
    print("\n", discount_summary(data).round(1).to_string(index=False))
    for item in generate_insights(data):
        print(f"\n[{item['title']}] {item['finding']}\n  -> {item['recommendation']}")
