# Nike Sales Analysis — Independent Portfolio Case Study

An interactive sales dashboard built with **Python, pandas, NumPy, Plotly and Streamlit**.
It answers practical business questions: when does revenue peak, which categories, regions,
products and channels earn the most, and how do discounts relate to profit margin?

> **Synthetic data — not actual Nike sales.**
> This is an independent student project and is **not affiliated with Nike**. Product names are
> generic descriptions, and no real company results are used or claimed.

<!-- Add a screenshot after you run the app:  ![Dashboard](docs/dashboard.png) -->

## What the dashboard shows

| Page | Content |
|---|---|
| Overview | Monthly revenue and profit, revenue share by category, regional and channel performance |
| Products | Top products by revenue and by product profit, plus a sortable product table |
| Discounts | Profit margin and revenue by discount group, with a caution about causation |
| Executive Summary | 3–5 findings and recommendations, **calculated from the filtered data** |
| Data Quality | Cleaning log, missing values, metric definitions, limitations and CSV downloads |

The sidebar has date, region, category and channel filters. **Every KPI, chart and insight updates
with the filters.** Empty selections show a helpful message instead of an error.

## Metric definitions

```
Revenue        = Quantity × Unit Price × (1 − Discount)
Product Profit = Revenue − Quantity × Unit Cost
Profit Margin  = Total Product Profit / Total Revenue × 100
Orders         = number of distinct Order IDs
```

**Limitations:** Product profit only subtracts product cost. Overheads, shipping, marketing and taxes
are not in the dataset, so they are not included. Discount comparisons show *association*, not cause:
a bigger discount lowers the price while unit cost stays the same, so a lower margin is expected
arithmetically, and this data cannot show whether discounts changed sales volume.

## Project structure

```
nike-sales-dashboard/
├── app.py              # Streamlit layout, filters, charts and CSS
├── analysis.py         # Loading, cleaning, metrics, summaries, insight text (no Streamlit)
├── generate_data.py    # Creates the synthetic dataset
├── data/
│   └── sales_synthetic.csv
├── .streamlit/
│   └── config.toml     # Theme colours and settings
├── requirements.txt
└── README.md
```

## Run it on a Mac

```bash
cd nike-sales-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. To stop it press `Ctrl + C`; to leave the virtual environment
run `deactivate`. Next time, only `source venv/bin/activate` and `streamlit run app.py` are needed.

Optional: `python3 generate_data.py` recreates the synthetic CSV, and `python3 analysis.py` prints
the cleaning log and key results in the terminal.

## Using your own dataset

1. Replace `data/sales_synthetic.csv` with your CSV (or change `DATA_PATH` in `app.py`).
2. Needed columns: order id, order date, region, category, product, channel, quantity, unit price,
   unit cost, discount. Common alternative headings are matched automatically; add more names to
   `COLUMN_ALIASES` in `analysis.py` if needed. A clear error lists anything missing.
3. If it is real data, set `DATASET_IS_SYNTHETIC = False` in `app.py` so the "synthetic" labels disappear.
   Keep the "not affiliated with Nike" note unless you have permission to say otherwise.
4. Discounts stored as `10` are converted to `0.10` automatically; the change is shown in the cleaning log.

## Data cleaning decisions

Cleaning is done once in `analysis.clean_data` and listed on the Data Quality page:
extra spaces trimmed, exact duplicate rows removed, rows missing price/cost/quantity/date/discount
dropped (guessing would invent data), impossible values dropped (quantity ≤ 0, negative cost, discount
outside 0–100%), and missing labels such as region kept as `Unknown` so their revenue is not lost.

## Design notes

- Light page, white cards, dark header, blue / teal / orange / purple chart palette.
- Theme colours are in `.streamlit/config.toml`; CSS in `app.py` only styles our own elements.
- KPI cards and the executive summary use CSS container queries, so they adapt to the real content
  width (with the sidebar open or closed). Chart columns wrap under each other when too narrow.
- One font throughout: Arial (Helvetica fallback), set in `.streamlit/config.toml`, charts included. Two weights only: regular and semibold.

## Possible next steps

Add a forecast baseline, compare year over year, include shipping and overhead costs if available,
and test discount effects with a proper experiment design.

## Tech

Python 3.10+, pandas, NumPy, Plotly, Streamlit (tested with Streamlit 1.65).
