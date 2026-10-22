"""
generate_data.py
----------------
Creates a SYNTHETIC sales dataset for the dashboard.

Synthetic data -- not actual Nike sales. This project is not affiliated with Nike.
Product names are generic descriptions, not real Nike product names.

Run once:  python3 generate_data.py
Output:    data/sales_synthetic.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ORDERS = 4000
OUTPUT = Path(__file__).parent / "data" / "sales_synthetic.csv"

# (category, product, list price, unit cost as a share of price)
PRODUCTS = [
    ("Footwear", "Road Running Shoe", 130, 0.48),
    ("Footwear", "Court Basketball Shoe", 150, 0.50),
    ("Footwear", "Everyday Sneaker", 100, 0.46),
    ("Footwear", "Trail Running Shoe", 140, 0.52),
    ("Apparel", "Training T-Shirt", 35, 0.40),
    ("Apparel", "Performance Shorts", 45, 0.42),
    ("Apparel", "Fleece Hoodie", 70, 0.50),
    ("Apparel", "Running Jacket", 110, 0.55),
    ("Equipment", "Training Backpack", 60, 0.50),
    ("Equipment", "Sports Water Bottle", 18, 0.45),
    ("Equipment", "Gym Duffel Bag", 55, 0.52),
    ("Equipment", "Training Ball", 30, 0.48),
    ("Accessories", "Sports Socks (3-pack)", 20, 0.38),
    ("Accessories", "Headband", 12, 0.35),
    ("Accessories", "Cap", 28, 0.40),
    ("Accessories", "Training Gloves", 25, 0.44),
]

REGIONS = {  # region: share of orders
    "North America": 0.34, "Europe": 0.27, "Asia Pacific": 0.24,
    "Latin America": 0.09, "Middle East & Africa": 0.06,
}
CHANNELS = ["Online Store", "Retail Store", "Wholesale", "Marketplace"]
CHANNEL_P = [0.38, 0.30, 0.17, 0.15]
# Discount options, with a different mix per channel (rows sum to 1)
DISCOUNTS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]
DISCOUNT_P = {
    "Online Store": [0.38, 0.14, 0.18, 0.12, 0.12, 0.06],
    "Retail Store": [0.50, 0.12, 0.16, 0.10, 0.08, 0.04],
    "Wholesale":    [0.20, 0.10, 0.25, 0.20, 0.15, 0.10],
    "Marketplace":  [0.30, 0.10, 0.15, 0.15, 0.18, 0.12],
}
# Rough seasonality by month (1 = average month)
SEASON = {1: 0.85, 2: 0.80, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.00,
          7: 0.95, 8: 1.00, 9: 1.05, 10: 1.10, 11: 1.40, 12: 1.45}


def build_orders(rng: np.random.Generator) -> pd.DataFrame:
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    # Mild upward trend + seasonality decide how likely each day is
    weights = np.array([SEASON[d.month] * (1 + 0.15 * (d - days[0]).days / len(days)) for d in days])
    order_dates = rng.choice(days, size=N_ORDERS, p=weights / weights.sum())
    regions = rng.choice(list(REGIONS), size=N_ORDERS, p=list(REGIONS.values()))
    channels = rng.choice(CHANNELS, size=N_ORDERS, p=CHANNEL_P)
    return pd.DataFrame({
        "Order ID": [f"ORD-{100000 + i}" for i in range(N_ORDERS)],
        "Order Date": order_dates,
        "Region": regions,
        "Channel": channels,
    })


def build_lines(orders: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for order in orders.itertuples(index=False):
        n_lines = rng.choice([1, 2, 3], p=[0.55, 0.32, 0.13])
        chosen = rng.choice(len(PRODUCTS), size=n_lines, replace=False,
                            p=np.array([14, 10, 12, 6, 14, 10, 8, 5, 5, 6, 3, 3, 8, 4, 5, 3]) / 116)
        discount = rng.choice(DISCOUNTS, p=DISCOUNT_P[order.Channel])
        for idx in chosen:
            category, product, price, cost_share = PRODUCTS[idx]
            qty = int(rng.choice([1, 2, 3, 4, 5], p=[0.55, 0.22, 0.12, 0.07, 0.04]))
            if order.Channel == "Wholesale":
                qty *= int(rng.choice([3, 5, 10]))
            unit_cost = round(price * cost_share * rng.uniform(0.95, 1.05), 2)
            rows.append({
                "Order ID": order[0], "Order Date": order[1], "Region": order[2],
                "Channel": order[3], "Category": category, "Product": product,
                "Quantity": qty, "Unit Price": float(price), "Unit Cost": unit_cost,
                "Discount": float(discount),
            })
    return pd.DataFrame(rows)


def add_quality_issues(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Add a few realistic flaws so the cleaning step in analysis.py has real work to do."""
    df = df.copy()
    df["Order Date"] = pd.to_datetime(df["Order Date"]).dt.strftime("%Y-%m-%d")
    df.loc[rng.choice(df.index, 12, replace=False), "Region"] = np.nan
    df.loc[rng.choice(df.index, 9, replace=False), "Unit Cost"] = np.nan
    df.loc[rng.choice(df.index, 6, replace=False), "Quantity"] = 0
    padded = rng.choice(df.index, 25, replace=False)
    df.loc[padded, "Channel"] = "  " + df.loc[padded, "Channel"] + " "  # stray spaces
    duplicates = df.sample(15, random_state=SEED)
    return pd.concat([df, duplicates], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)


def main() -> None:
    rng = np.random.default_rng(SEED)
    orders = build_orders(rng)
    lines = build_lines(orders, rng)
    final = add_quality_issues(lines, rng)
    OUTPUT.parent.mkdir(exist_ok=True)
    final.to_csv(OUTPUT, index=False)
    print(f"Saved {len(final):,} rows ({final['Order ID'].nunique():,} orders) to {OUTPUT}")


if __name__ == "__main__":
    main()
