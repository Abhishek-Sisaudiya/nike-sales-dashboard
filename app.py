"""
app.py
------
Streamlit dashboard: "Nike Sales Analysis - Independent Portfolio Case Study".
Run with:  streamlit run app.py

All calculations live in analysis.py. This file only handles layout, filters and charts.
Independent project, not affiliated with Nike.
"""

from contextlib import contextmanager
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis as an

# --------------------------------------------------------------------------
# Settings you may want to change
# --------------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "data" / "sales_synthetic.csv"
DATASET_IS_SYNTHETIC = True  # set to False if you replace the CSV with real data
CURRENCY = "$"

PAGES = ["Overview", "Products", "Discounts", "Executive Summary", "Data Quality"]

# Chart colours (blue, teal, orange, purple) + extras for datasets with more groups
BLUE, TEAL, ORANGE, PURPLE = "#2563EB", "#0D9488", "#F97316", "#7C3AED"
COLORWAY = [BLUE, TEAL, ORANGE, PURPLE, "#64748B", "#DB2777", "#CA8A04", "#0891B2"]
INK, MUTED, GRID = "#111827", "#5B6572", "#E9ECF1"
CHART_FONT = "Arial, Helvetica, sans-serif"

st.set_page_config(
    page_title="Nike Sales Analysis - Portfolio Case Study",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# --------------------------------------------------------------------------
# Styling. Only our own class names plus two small, stable Streamlit hooks:
#   - the main container padding (so the banner clears Streamlit's top bar)
#   - containers created with key="card_..." (a documented Streamlit feature)
# We never set widths or margins on Streamlit's layout, so the page fills the
# whole width when the sidebar is closed.
# --------------------------------------------------------------------------
CSS = """
<style>
/* Font: Arial/Helvetica everywhere. Streamlit widgets get it from .streamlit/config.toml;
   our own elements below simply inherit it. Weights used: 400 (regular) and 600 (semibold). */

[data-testid="stMainBlockContainer"] {
    padding: 3.25rem clamp(1rem, 2.2vw, 2.25rem) 2rem !important;
}

/* Columns drop under each other when they would be narrower than ~21rem.
   This follows the real content width, so it also works with the sidebar open. */
[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
[data-testid="stColumn"] { min-width: min(100%, 21rem); }

/* ---------- header banner ---------- */
/* ---------- header banner ---------- */
.hero {
    background: linear-gradient(120deg, #EAF5FF, #ADD8E6);
    border: 1px solid #B8D9EC;
    border-left: 5px solid #2563EB;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
    font-family: Arial, Helvetica, sans-serif;
}

.hero-title {
    font-family: Arial, Helvetica, sans-serif;
    font-size: clamp(22px, 2.4vw, 30px);
    font-weight: 600;
    line-height: 1.4;
    color: #15324F;
    margin: 0;
    overflow-wrap: anywhere;
}

.hero-title span {
    font-weight: 400;
    color: #45627D;
}

.hero-sub {
    margin-top: 8px;
    font-size: 14px;
    line-height: 1.6;
    color: #36556F;
}

.badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
}

.badge {
    background: #F5FAFF;
    border: 1px solid #BED7E8;
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 400;
    line-height: 1.5;
    color: #36556F;
}

.badge.warn {
    background: #FFF4E6;
    border-color: #F5CBA0;
    color: #944512;
}

@media (max-width: 600px) {
    .hero {
        padding: 18px;
    }

    .hero-title {
        font-size: 22px;
    }

    .hero-title span {
        display: block;
        margin-top: 5px;
        font-size: 16px;
    }
}

/* ---------- KPI cards (container queries follow the real content width) ---------- */
.kpi-wrap { container-type: inline-size; margin: .85rem 0 .25rem; }
.kpi-grid { display: grid; gap: .75rem; grid-template-columns: repeat(5, minmax(0, 1fr)); }
.kpi {
    background: #fff; border: 1px solid #E3E7ED; border-left: 4px solid var(--c);
    border-radius: 10px; padding: .75rem .9rem; min-width: 0;
}
.kpi-label { font-size: .8rem; font-weight: 400; color: #5B6572; }
.kpi-value { font-size: clamp(1.3rem, 2cqw, 1.6rem); font-weight: 600; line-height: 1.25; color: #111827; }
.kpi-note { font-size: .72rem; color: #7A8594; }
@container (max-width: 860px) {
    .kpi-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .kpi { grid-column: span 2; }
    .kpi:nth-child(n+4) { grid-column: span 3; }
}
@container (max-width: 480px) {
    .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .kpi, .kpi:nth-child(n+4) { grid-column: span 1; }
    .kpi:last-child { grid-column: span 2; }
}
.filter-note { font-size: .82rem; line-height: 1.5; color: #5B6572; margin: .35rem 0 .1rem; }

/* ---------- chart cards ---------- */
[class*="st-key-card_"] { background: #fff; }
.card-title { font-size: 1rem; font-weight: 600; line-height: 1.3; color: #111827; }
.card-sub { font-size: .8rem; line-height: 1.45; color: #5B6572; margin-top: .1rem; }
.card-note { font-size: .78rem; line-height: 1.45; color: #5B6572; padding-bottom: .6rem; }

/* ---------- executive summary ---------- */
.insight-wrap { container-type: inline-size; }
.insight {
    background: #fff; border: 1px solid #E3E7ED; border-left: 4px solid var(--c);
    border-radius: 10px; padding: .9rem 1.1rem; margin-bottom: .7rem;
}
.insight-title { font-size: 1rem; font-weight: 600; color: #111827; margin-bottom: .4rem; }
.insight-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.insight-label { font-size: .8rem; font-weight: 600; color: #5B6572; margin-bottom: .15rem; }
.insight-text { font-size: .9rem; line-height: 1.55; color: #1F2937; }
@container (max-width: 720px) { .insight-cols { grid-template-columns: 1fr; gap: .7rem; } }

/* ---------- misc ---------- */
.callout {
    background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 10px; line-height: 1.5;
    padding: .7rem .95rem; font-size: .88rem; color: #7C2D12; margin: .25rem 0 .75rem;
}
.callout b { font-weight: 600; }
.side-brand { font-size: 1.1rem; font-weight: 600; line-height: 1.25; color: #111827; }
.side-sub { font-size: .8rem; color: #5B6572; margin-bottom: .2rem; }
.side-label { font-size: .85rem; font-weight: 600; color: #111827; margin: .2rem 0 -.3rem; }
.footer { font-size: .76rem; color: #7A8594; padding: .4rem 0 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def h(text) -> str:
    """Make text safe for HTML. Also escapes '$' so Streamlit does not treat it as a math formula."""
    return escape(str(text)).replace("$", "&#36;")


# --------------------------------------------------------------------------
# Data loading (cached)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning data...")
def get_data(path: str, modified_time: float):
    """modified_time is only here so the cache refreshes when the CSV file changes."""
    return an.load_data(path)


try:
    data, cleaning_log, missing_before = get_data(str(DATA_PATH), DATA_PATH.stat().st_mtime)
except FileNotFoundError:
    st.error(f"Data file not found: {DATA_PATH}. Run `python3 generate_data.py` or add your CSV there.")
    st.stop()
except ValueError as err:
    st.error(f"The dataset could not be read.\n\n{err}")
    st.stop()

if data.empty:
    st.error("The dataset has no usable rows after cleaning. See analysis.py > clean_data.")
    st.stop()

DATA_MIN, DATA_MAX = data["order_date"].min().date(), data["order_date"].max().date()
OPTIONS = {
    "region": sorted(data["region"].unique()),
    "category": sorted(data["category"].unique()),
    "channel": sorted(data["channel"].unique()),
}

# --------------------------------------------------------------------------
# Sidebar: navigation and filters
# --------------------------------------------------------------------------
STATE_KEYS = {"region": "f_regions", "category": "f_categories", "channel": "f_channels"}


def reset_filters() -> None:
    st.session_state["f_dates"] = (DATA_MIN, DATA_MAX)
    for field, key in STATE_KEYS.items():
        st.session_state[key] = list(OPTIONS[field])


st.session_state.setdefault("f_dates", (DATA_MIN, DATA_MAX))
for field, key in STATE_KEYS.items():
    # keep only values that still exist in the data (safe if the CSV changed)
    st.session_state[key] = [v for v in st.session_state.get(key, OPTIONS[field]) if v in OPTIONS[field]]

with st.sidebar:
    st.markdown('<div class="side-brand">Sales Analysis</div>'
                '<div class="side-sub">Independent portfolio case study</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-label">Pages</div>', unsafe_allow_html=True)
    page = st.radio("Page", PAGES, key="page", label_visibility="collapsed")

    st.markdown('<div class="side-label">Filters</div>', unsafe_allow_html=True)
    picked = st.date_input("Order date", key="f_dates", min_value=DATA_MIN, max_value=DATA_MAX)
    # Each list sits in a collapsed expander so the sidebar stays short; the page shows what is selected.
    for label, field, placeholder in [("Region", "region", "Choose regions"),
                                      ("Category", "category", "Choose categories"),
                                      ("Channel", "channel", "Choose channels")]:
        with st.expander(label):
            st.multiselect(label, OPTIONS[field], key=STATE_KEYS[field], placeholder=placeholder,
                           label_visibility="collapsed")
    st.button("Reset filters", on_click=reset_filters, width="stretch")

# The date picker returns 1 date while the user is still choosing the end date
if isinstance(picked, (tuple, list)) and len(picked) == 2:
    start, end = picked
elif isinstance(picked, (tuple, list)) and len(picked) == 1:
    start = end = picked[0]
else:
    start = end = picked

df = an.filter_data(
    data, start, end,
    st.session_state["f_regions"], st.session_state["f_categories"], st.session_state["f_channels"],
)

with st.sidebar:
    st.download_button(
        "Download filtered data (CSV)",
        data=an.export_rows(df).to_csv(index=False).encode("utf-8") if not df.empty else b"",
        file_name="filtered_sales_data.csv", mime="text/csv",
        disabled=df.empty, width="stretch", key="dl_side",
    )
    st.caption("Synthetic data, not actual Nike sales. Not affiliated with Nike."
               if DATASET_IS_SYNTHETIC else "Independent project, not affiliated with Nike.")

# --------------------------------------------------------------------------
# Header banner + KPI cards (shown on every page)
# --------------------------------------------------------------------------
badges = ""
if DATASET_IS_SYNTHETIC:
    badges += '<span class="badge warn">Synthetic data — not actual Nike sales</span>'
badges += '<span class="badge">Independent project — not affiliated with Nike</span>'
badges += '<span class="badge">Product profit excludes overheads, shipping and taxes</span>'

st.markdown(
    '<div class="hero">'
    '<div class="hero-title" role="heading" aria-level="1">Nike Sales Analysis <span>— Independent Portfolio Case Study</span></div>'
    '<div class="hero-sub">Revenue, profit and discount analysis by month, category, region, product and channel.</div>'
    f'<div class="badges">{badges}</div></div>',
    unsafe_allow_html=True,
)

# Empty selections: explain, then stop (nothing below can be calculated)
missing_filters = [label for label, key in
                   [("region", "f_regions"), ("category", "f_categories"), ("channel", "f_channels")]
                   if not st.session_state[key]]
if missing_filters:
    st.warning(f"Please select at least one {', '.join(missing_filters)} in the sidebar to see results.")
    st.stop()
if df.empty:
    st.warning("No orders match the current filters. Widen the date range or use 'Reset filters' in the sidebar.")
    st.stop()

kpi = an.compute_kpis(df)
kpi_cards = [
    ("Total Revenue", an.money(kpi["revenue"], CURRENCY), "Qty × Price × (1 − Discount)", BLUE),
    ("Product Profit", an.money(kpi["profit"], CURRENCY), "Revenue − product cost", TEAL),
    ("Total Orders", f"{kpi['orders']:,}", "Distinct Order IDs", ORANGE),
    ("Units Sold", f"{kpi['units']:,}", "Sum of quantity", PURPLE),
    ("Profit Margin", an.pct(kpi["margin"]), "Profit ÷ Revenue", BLUE),
]
cards_html = "".join(
    f'<div class="kpi" style="--c:{color}"><div class="kpi-label">{h(label)}</div>'
    f'<div class="kpi-value">{h(value)}</div><div class="kpi-note">{h(note)}</div></div>'
    for label, value, note, color in kpi_cards
)
st.markdown(f'<div class="kpi-wrap"><div class="kpi-grid">{cards_html}</div></div>', unsafe_allow_html=True)

def describe(key: str, field: str) -> str:
    """'all', or the chosen names (if 3 or fewer), or a count."""
    chosen = st.session_state[key]
    if len(chosen) == len(OPTIONS[field]):
        return "all"
    return ", ".join(chosen) if len(chosen) <= 3 else f"{len(chosen)} of {len(OPTIONS[field])}"


st.markdown(
    f'<div class="filter-note">Showing {len(df):,} order lines from {start:%d %b %Y} to {end:%d %b %Y}. '
    f'Region: {h(describe("f_regions", "region"))}. Category: {h(describe("f_categories", "category"))}. '
    f'Channel: {h(describe("f_channels", "channel"))}.</div>',
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Chart helpers
# --------------------------------------------------------------------------
@contextmanager
def card(key: str, title: str, subtitle: str = ""):
    """A white bordered card with a title. Use:  with card('trend', 'Title', 'Subtitle'): ..."""
    with st.container(border=True, key=f"card_{key}"):
        sub = f'<div class="card-sub">{h(subtitle)}</div>' if subtitle else ""
        st.markdown(f'<div class="card-title">{h(title)}</div>{sub}', unsafe_allow_html=True)
        yield


def style(fig: go.Figure, height: int, legend: bool = True) -> go.Figure:
    """Apply one consistent look to every Plotly chart."""
    fig.update_layout(
        height=height, margin=dict(l=4, r=8, t=34 if legend else 8, b=4),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=CHART_FONT, size=12, color=INK), colorway=COLORWAY,
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="", font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", bordercolor="#CBD2DC", font=dict(family=CHART_FONT, size=12, color=INK)),
    )
    fig.update_xaxes(showline=True, linecolor="#CBD2DC", ticks="outside", tickcolor="#CBD2DC", automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, automargin=True)
    return fig


def money_axis(fig: go.Figure, axis: str = "y", title: str = "") -> None:
    """Show tick labels as $100k, $1M ... and add an axis title that names the currency."""
    update = fig.update_yaxes if axis == "y" else fig.update_xaxes
    update(tickprefix=CURRENCY, tickformat="~s", title_text=title)


def show(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=key)


def category_colors(names) -> dict:
    return {name: COLORWAY[i % len(COLORWAY)] for i, name in enumerate(names)}


def margin_caption(table: pd.DataFrame, label: str) -> str:
    items = ", ".join(f"{row[label]} {an.pct(row['margin'])}" for _, row in table.iterrows())
    return f'<div class="card-note">Profit margin: {h(items)}.</div>'


# --------------------------------------------------------------------------
# Chart builders (each takes the filtered data and returns a figure)
# --------------------------------------------------------------------------
def fig_monthly(data_: pd.DataFrame) -> go.Figure:
    m = an.monthly_summary(data_)
    fig = go.Figure()
    fig.add_bar(
        x=m["month"], y=m["revenue"], name="Revenue", marker_color=BLUE, opacity=0.9,
        customdata=m[["orders"]], hovertemplate=f"Revenue: {CURRENCY}%{{y:,.0f}}<br>Orders: %{{customdata[0]:,}}<extra></extra>",
    )
    fig.add_scatter(
        x=m["month"], y=m["profit"], name="Product profit", mode="lines+markers",
        line=dict(color=TEAL, width=3), marker=dict(size=6),
        customdata=m[["margin"]], hovertemplate=f"Product profit: {CURRENCY}%{{y:,.0f}}<br>Margin: %{{customdata[0]:.1f}}%<extra></extra>",
    )
    style(fig, 330)
    money_axis(fig, "y", f"Amount ({CURRENCY})")
    fig.update_xaxes(tickformat="%b %Y", title_text="Order month", hoverformat="%B %Y")
    fig.update_layout(hovermode="x unified", bargap=0.25)
    return fig


def fig_category(data_: pd.DataFrame) -> go.Figure:
    c = an.category_summary(data_)
    colors = category_colors(c["category"])
    fig = go.Figure(go.Pie(
        labels=c["category"], values=c["revenue"], hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=[colors[x] for x in c["category"]], line=dict(color="white", width=2)),
        textinfo="percent", textfont=dict(size=12, color="white"),
        customdata=c[["profit", "margin", "units"]],
        hovertemplate=(f"<b>%{{label}}</b><br>Revenue: {CURRENCY}%{{value:,.0f}} (%{{percent}})"
                       f"<br>Profit: {CURRENCY}%{{customdata[0]:,.0f}}<br>Margin: %{{customdata[1]:.1f}}%"
                       "<br>Units: %{customdata[2]:,}<extra></extra>"),
    ))
    style(fig, 330, legend=True)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, title_text=""),
        margin=dict(l=4, r=4, t=8, b=4),
        annotations=[dict(text=f"<b>{an.money(c['revenue'].sum(), CURRENCY)}</b><br>revenue", x=0.5, y=0.5,
                          showarrow=False, font=dict(size=15, color=INK))],
    )
    return fig


def fig_grouped(table: pd.DataFrame, label: str, height: int) -> go.Figure:
    """Horizontal revenue + profit bars. Horizontal keeps long names readable."""
    t = table.sort_values("revenue")  # smallest first, so the largest ends up on top
    fig = go.Figure()
    for name, col, color in [("Product profit", "profit", TEAL), ("Revenue", "revenue", BLUE)]:
        fig.add_bar(
            y=t[label], x=t[col], name=name, orientation="h", marker_color=color,
            text=[an.money(v, CURRENCY) for v in t[col]], textposition="outside", cliponaxis=False,
            textfont=dict(size=11, color=MUTED),
            customdata=t[["margin", "orders", "units"]],
            hovertemplate=(f"<b>%{{y}}</b><br>{name}: {CURRENCY}%{{x:,.0f}}<br>Margin: %{{customdata[0]:.1f}}%"
                           "<br>Orders: %{customdata[1]:,}<br>Units: %{customdata[2]:,}<extra></extra>"),
        )
    style(fig, height)
    money_axis(fig, "x", f"Amount ({CURRENCY})")
    fig.update_xaxes(range=[0, t["revenue"].max() * 1.3], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False, title_text="")
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.05)
    # reverse legend order so it reads Revenue, Product profit like the bars (top to bottom)
    fig.update_layout(legend=dict(traceorder="reversed"))
    return fig


def fig_top_products(table: pd.DataFrame, column: str, color: str, name: str, n: int) -> go.Figure:
    top = table.nlargest(n, column).sort_values(column)  # largest on top
    fig = go.Figure(go.Bar(
        y=top["product"], x=top[column], orientation="h", marker_color=color,
        text=[an.money(v, CURRENCY) for v in top[column]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=MUTED),
        customdata=top[["category", "margin", "units", "orders"]],
        hovertemplate=(f"<b>%{{y}}</b> (%{{customdata[0]}})<br>{name}: {CURRENCY}%{{x:,.0f}}"
                       "<br>Margin: %{customdata[1]:.1f}%<br>Units: %{customdata[2]:,}"
                       "<br>Orders: %{customdata[3]:,}<extra></extra>"),
    ))
    style(fig, max(260, 34 * len(top) + 70), legend=False)
    money_axis(fig, "x", f"{name} ({CURRENCY})")
    fig.update_xaxes(range=[0, top[column].max() * 1.25], showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False, title_text="")
    return fig


def fig_discount_margin(table: pd.DataFrame) -> go.Figure:
    t = table.copy()
    t["group"] = t["discount_group"].astype(str)
    fig = go.Figure(go.Bar(
        x=t["group"], y=t["margin"], marker_color=ORANGE,
        text=[an.pct(v) for v in t["margin"]], textposition="outside", cliponaxis=False,
        customdata=t[["orders", "revenue", "profit"]],
        hovertemplate=(f"<b>%{{x}}</b><br>Margin: %{{y:.1f}}%<br>Orders: %{{customdata[0]:,}}"
                       f"<br>Revenue: {CURRENCY}%{{customdata[1]:,.0f}}<br>Profit: {CURRENCY}%{{customdata[2]:,.0f}}<extra></extra>"),
    ))
    style(fig, 320, legend=False)
    fig.update_yaxes(title_text="Profit margin (%)", ticksuffix="%", range=[0, max(t["margin"].max() * 1.2, 10)])
    fig.update_xaxes(title_text="Discount group")
    return fig


def fig_discount_money(table: pd.DataFrame) -> go.Figure:
    t = table.copy()
    t["group"] = t["discount_group"].astype(str)
    fig = go.Figure()
    for name, col, color in [("Revenue", "revenue", PURPLE), ("Product profit", "profit", TEAL)]:
        fig.add_bar(
            x=t["group"], y=t[col], name=name, marker_color=color,
            customdata=t[["revenue_share", "orders"]],
            hovertemplate=(f"<b>%{{x}}</b><br>{name}: {CURRENCY}%{{y:,.0f}}"
                           "<br>Share of revenue: %{customdata[0]:.1f}%<br>Orders: %{customdata[1]:,}<extra></extra>"),
        )
    style(fig, 320)
    money_axis(fig, "y", f"Amount ({CURRENCY})")
    fig.update_xaxes(title_text="Discount group")
    fig.update_layout(barmode="group", bargap=0.3)
    return fig


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def page_overview() -> None:
    left, right = st.columns([3, 2], gap="medium")
    with left:
        with card("trend", "Monthly revenue and profit", f"Revenue (bars) and product profit (line) per order month, in {CURRENCY}"):
            show(fig_monthly(df), "trend")
    with right:
        with card("category", "Revenue by category", "Share of total revenue; hover for profit and margin"):
            show(fig_category(df), "category")

    regions, channels = an.region_summary(df), an.channel_summary(df)
    height = 70 + 56 * max(len(regions), len(channels), 3)  # same height keeps the two cards level
    left, right = st.columns(2, gap="medium")
    with left:
        with card("region", "Regional performance", f"Revenue and product profit by region, in {CURRENCY}"):
            show(fig_grouped(regions, "region", height), "region")
            st.markdown(margin_caption(regions, "region"), unsafe_allow_html=True)
    with right:
        with card("channel", "Sales channel performance", f"Revenue and product profit by channel, in {CURRENCY}"):
            show(fig_grouped(channels, "channel", height), "channel")
            st.markdown(margin_caption(channels, "channel"), unsafe_allow_html=True)


def page_products() -> None:
    summary = an.product_summary(df)
    top_n = st.radio("Number of products to show", [5, 8, 10], index=1, horizontal=True, key="top_n")
    left, right = st.columns(2, gap="medium")
    with left:
        with card("top_rev", f"Top {min(top_n, len(summary))} products by revenue", f"Revenue in {CURRENCY}; hover for category and margin"):
            show(fig_top_products(summary, "revenue", BLUE, "Revenue", top_n), "top_rev")
    with right:
        with card("top_profit", f"Top {min(top_n, len(summary))} products by product profit", f"Product profit in {CURRENCY}; hover for category and margin"):
            show(fig_top_products(summary, "profit", TEAL, "Product profit", top_n), "top_profit")

    with card("product_table", "All products", "Click a column heading to sort. Orders can overlap between products because one order may contain several products."):
        table = summary.sort_values("revenue", ascending=False).rename(columns={
            "product": "Product", "category": "Category", "revenue": "Revenue", "profit": "Product profit",
            "margin": "Margin %", "units": "Units", "orders": "Orders"})[
            ["Product", "Category", "Revenue", "Product profit", "Margin %", "Units", "Orders"]]
        st.dataframe(
            table, hide_index=True, width="stretch", height="content",
            column_config={
                "Revenue": st.column_config.NumberColumn(format="dollar"),
                "Product profit": st.column_config.NumberColumn(format="dollar"),
                "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


def page_discounts() -> None:
    disc = an.discount_summary(df)
    left, right = st.columns(2, gap="medium")
    with left:
        with card("disc_margin", "Profit margin by discount group", "Discount groups compared on product profit margin"):
            show(fig_discount_margin(disc), "disc_margin")
    with right:
        with card("disc_money", "Revenue and profit by discount group", f"Amounts in {CURRENCY}; hover for share of revenue"):
            show(fig_discount_money(disc), "disc_money")

    small = disc[disc["orders"] < an.MIN_ORDERS_FOR_GROUP]["discount_group"].astype(str).tolist()
    note = ("A bigger discount lowers the selling price while unit cost stays the same, so a lower "
            "margin in heavily discounted groups is expected arithmetically. These charts show association only; "
            "they cannot show whether discounts caused higher or lower sales, because that would need a controlled comparison.")
    if small:
        note += f" Small sample (under {an.MIN_ORDERS_FOR_GROUP} orders): {', '.join(small)}."
    st.markdown(f'<div class="callout"><b>How to read this.</b> {h(note)}</div>', unsafe_allow_html=True)

    with card("disc_table", "Discount group table", "Orders are counted separately within each discount group."):
        table = disc.assign(discount_group=disc["discount_group"].astype(str)).rename(columns={
            "discount_group": "Discount group", "revenue": "Revenue", "profit": "Product profit",
            "margin": "Margin %", "revenue_share": "Share of revenue %", "units": "Units", "orders": "Orders"})[
            ["Discount group", "Revenue", "Product profit", "Margin %", "Share of revenue %", "Units", "Orders"]]
        st.dataframe(
            table, hide_index=True, width="stretch",
            column_config={
                "Revenue": st.column_config.NumberColumn(format="dollar"),
                "Product profit": st.column_config.NumberColumn(format="dollar"),
                "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
                "Share of revenue %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


def page_summary() -> None:
    insights = an.generate_insights(df, CURRENCY)
    st.markdown('<div class="card-title" style="margin:.4rem 0 .5rem">Executive summary</div>'
                '<div class="card-sub" style="margin-bottom:.6rem">Every sentence below is calculated from the currently filtered data, '
                'so it changes when you change the filters.</div>', unsafe_allow_html=True)
    colors = [BLUE, TEAL, ORANGE, PURPLE, BLUE]
    html = ""
    for item, color in zip(insights, colors):
        html += (f'<div class="insight" style="--c:{color}"><div class="insight-title">{h(item["title"])}</div>'
                 f'<div class="insight-cols"><div><div class="insight-label">Finding</div>'
                 f'<div class="insight-text">{h(item["finding"])}</div></div>'
                 f'<div><div class="insight-label">Recommendation</div>'
                 f'<div class="insight-text">{h(item["recommendation"])}</div></div></div></div>')
    st.markdown(f'<div class="insight-wrap">{html}</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout">Recommendations are practical suggestions based on patterns in this dataset. '
                'They describe associations, not proven causes, and product profit excludes overheads, shipping and taxes.</div>',
                unsafe_allow_html=True)


def page_quality() -> None:
    with card("about", "About this dataset"):
        label = "Synthetic data — not actual Nike sales. " if DATASET_IS_SYNTHETIC else ""
        st.markdown(h(f"{label}This project is an independent portfolio case study and is not affiliated with Nike. "
                      f"File: {DATA_PATH.name}. After cleaning: {len(data):,} order lines, {data['order_id'].nunique():,} orders, "
                      f"{data['order_date'].min():%d %b %Y} to {data['order_date'].max():%d %b %Y}."),
                    unsafe_allow_html=True)

    with card("cleaning", "Cleaning decisions", "Applied once to the full file, before any filters"):
        st.table(pd.DataFrame(cleaning_log).set_index("Step"))

    left, right = st.columns([2, 3], gap="medium")
    with left:
        with card("missing", "Missing values before cleaning", "Columns with no gaps are not listed"):
            gaps = missing_before[missing_before > 0]
            if gaps.empty:
                st.write("No missing values were found.")
            else:
                st.dataframe(gaps.rename("Missing cells").rename_axis("Column").reset_index(),
                             hide_index=True, width="stretch")
    with right:
        with card("definitions", "Metric definitions and limits"):
            st.markdown(
                "- **Revenue** = Quantity × Unit Price × (1 − Discount)\n"
                "- **Product Profit** = Revenue − Quantity × Unit Cost\n"
                "- **Profit Margin** = Total Product Profit ÷ Total Revenue × 100\n"
                "- **Orders** = number of distinct Order IDs\n\n"
                "Product profit only subtracts product cost. Overheads, shipping, marketing and taxes are not in the data, "
                "so they are not included. Order counts for a category, product or channel can overlap when one order contains "
                "several items, so they should not be added together. Discount findings show association, not cause."
            )

    with card("download", "Download the filtered analysis", "Both files follow the current sidebar filters"):
        c1, c2 = st.columns(2)
        c1.download_button("Order lines with calculated columns (CSV)", an.export_rows(df).to_csv(index=False).encode("utf-8"),
                           "filtered_sales_data.csv", "text/csv", width="stretch", key="dl_rows")
        c2.download_button("Summary tables (CSV)", an.export_summary(df).to_csv(index=False).encode("utf-8"),
                           "filtered_sales_summary.csv", "text/csv", width="stretch", key="dl_summary")
        st.caption("Preview of the filtered order lines (first 100 rows, key columns; the download has every column)")
        preview_cols = ["Order ID", "Order Date", "Region", "Channel", "Category", "Product", "Quantity", "Revenue", "Product Profit"]
        st.dataframe(an.export_rows(df)[preview_cols].head(100), hide_index=True, width="stretch")


PAGE_FUNCTIONS = {
    "Overview": page_overview,
    "Products": page_products,
    "Discounts": page_discounts,
    "Executive Summary": page_summary,
    "Data Quality": page_quality,
}
PAGE_FUNCTIONS[page]()

st.markdown(
    '<div class="footer">Independent portfolio case study, not affiliated with Nike. '
    + ("Synthetic data, not actual Nike sales. " if DATASET_IS_SYNTHETIC else "")
    + "Built with Python, pandas, NumPy, Plotly and Streamlit.</div>",
    unsafe_allow_html=True,
)
