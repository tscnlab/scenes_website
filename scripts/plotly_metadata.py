#!/usr/bin/env python3
"""
Generate interactive Plotly descriptive stats for the SCENES metadata.

Inputs
- data/metadata.csv

Outputs (HTML fragments ready to include in Quarto)
- assets/plots/scene_dist.html
- assets/plots/view_dist.html
- assets/plots/scene_by_lighting.html
- assets/plots/monthly_by_view.html           (if `date` present)
- assets/plots/hist_iso_by_view.html          (if `iso` present)
- assets/plots/hist_ev_by_view.html           (if `ev` present)
- assets/plots/box_iso_by_view.html           (if `iso` present)
- assets/plots/box_ev_by_view.html            (if `ev` present)
- assets/plots/scatter_ev_vs_iso_by_view.html (if `iso` & `ev` present)

Usage
  python scripts/plots_metadata.py

In Quarto, include a plot in a .qmd via:
  ```{=html}
  {{< include assets/plots/scene_dist.html >}}
"""

from pathlib import Path
import pandas as pd
import plotly.express as px

# ---------------- Config ----------------
INPUT_CSV = Path("data/metadata.csv")
OUT_DIR = Path("assets/plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEW_COLORS = {
"Outdoor": "#CD923B",
"Indoor w/ window": "#081A5B",
"Indoor w/o window": "#426E56",
}

# Helper to check column presence
def have(df: pd.DataFrame, *cols) -> bool:
    return all(c in df.columns for c in cols)

# Save helper: lightweight HTML fragment (no <html> wrapper), Plotly JS via CDN
def save_fig(fig, name: str):
    out = OUT_DIR / name
    fig.write_html(out, include_plotlyjs="cdn", full_html=False)
    print(f"wrote {out}")

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing CSV: {INPUT_CSV}")

df = pd.read_csv(INPUT_CSV)


# ---------- Light cleanup ----------
# numeric coercions if columns exist
for col in ["latitude","longitude","iso","ev","aperture","exposure_time","elevation","groundheight","temperature","humidity"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# parse date → month
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

# category order (optional nicer sorting)
if "scene" in df.columns:
    # keep as-is order seen in data (stable)
    order_scene = [s for s in pd.Index(df["scene"].dropna().unique())]
else:
    order_scene = None

# ---------- 1) Scene distribution ----------
if have(df, "scene"):
    fig = px.histogram(
        df, x="scene", color="scene",
        category_orders={"scene": order_scene} if order_scene else None,
        title="Distribution of Scene Types",
        text_auto=True
    )
    fig.update_layout(xaxis_title="Scene", yaxis_title="Count", bargap=0.15, legend_title_text="")
    save_fig(fig, "scene_dist.html")
else:
    print("skip: scene_dist (missing `scene`)")

# ---------- 2) View distribution (uses VIEW_COLORS) ----------
if have(df, "view"):
    fig = px.histogram(
        df, x="view", color="view",
        color_discrete_map=VIEW_COLORS,
        title="Distribution of View Types",
        text_auto=True
    )
    fig.update_layout(xaxis_title="View", yaxis_title="Count", bargap=0.15, legend_title_text="View")
    save_fig(fig, "view_dist.html")
else:
    print("skip: view_dist (missing `view`)")

# ---------- 3) Scene × Lighting grouped ----------
if have(df, "scene", "lighting"):
    fig = px.histogram(
        df, x="scene", color="lighting", barmode="group",
        category_orders={"scene": order_scene} if order_scene else None,
        title="Scene vs Lighting"
    )
    fig.update_layout(xaxis_title="Scene", yaxis_title="Count", bargap=0.2, legend_title="Lighting")
    save_fig(fig, "scene_by_lighting.html")
else:
    print("skip: scene_by_lighting (missing `scene` or `lighting`)")

# ---------- 4) Monthly images by view ----------
if have(df, "month", "view"):
    monthly = (df.dropna(subset=["month"])
                 .groupby(["month","view"]).size().reset_index(name="n"))
    fig = px.line(
        monthly, x="month", y="n", color="view", markers=True,
        color_discrete_map=VIEW_COLORS,
        title="Images per Month (toggle series in legend)"
    )
    fig.update_layout(xaxis_title="", yaxis_title="Images", legend_title="View")
    save_fig(fig, "monthly_by_view.html")
else:
    print("skip: monthly_by_view (missing `date`/`month` or `view`)")

# ---------- 5) Numeric histograms (colored by view when available) ----------
if "iso" in df.columns:
    fig = px.histogram(
        df, x="iso", color=("view" if "view" in df.columns else None),
        nbins=50, title="Distribution of ISO",
        color_discrete_map=VIEW_COLORS if "view" in df.columns else None
    )
    fig.update_layout(xaxis_title="ISO", yaxis_title="Count", bargap=0.05, legend_title="View")
    save_fig(fig, "hist_iso_by_view.html")
else:
    print("skip: hist_iso_by_view (missing `iso`)")

if "ev" in df.columns:
    fig = px.histogram(
        df, x="ev", color=("view" if "view" in df.columns else None),
        nbins=50, title="Distribution of EV",
        color_discrete_map=VIEW_COLORS if "view" in df.columns else None
    )
    fig.update_layout(xaxis_title="EV", yaxis_title="Count", bargap=0.05, legend_title="View")
    save_fig(fig, "hist_ev_by_view.html")
else:
    print("skip: hist_ev_by_view (missing `ev`)")

# ---------- 6) Box plots by view ----------
if have(df, "iso", "view"):
    fig = px.box(df, x="view", y="iso", points=False, title="ISO by View (box plot)",
                 color="view", color_discrete_map=VIEW_COLORS)
    fig.update_layout(xaxis_title="", yaxis_title="ISO", legend_title="View")
    save_fig(fig, "box_iso_by_view.html")
else:
    print("skip: box_iso_by_view (missing `iso` or `view`)")

if have(df, "ev", "view"):
    fig = px.box(df, x="view", y="ev", points=False, title="EV by View (box plot)",
                 color="view", color_discrete_map=VIEW_COLORS)
    fig.update_layout(xaxis_title="", yaxis_title="EV", legend_title="View")
    save_fig(fig, "box_ev_by_view.html")
else:
    print("skip: box_ev_by_view (missing `ev` or `view`)")

# ---------- 7) EV vs ISO scatter ----------
if have(df, "iso", "ev"):
    fig = px.scatter(
        df, x="iso", y="ev",
        color=("view" if "view" in df.columns else None),
        color_discrete_map=VIEW_COLORS if "view" in df.columns else None,
        opacity=0.7, title="EV vs ISO",
        marginal_x="histogram", marginal_y="histogram"
    )
    fig.update_layout(xaxis_title="ISO", yaxis_title="EV", legend_title="View")
    save_fig(fig, "scatter_ev_vs_iso_by_view.html")
else:
    print("skip: scatter_ev_vs_iso_by_view (missing `iso` or `ev`)")

print("\nAll done. Include these in a Quarto page with:")
print("  {{< include assets/plots/view_dist.html >}}  (inside a `{=html}` fenced block)")

if __name__ == "__main__":
    main()



### How to embed these in `stats.qmd`
# Create `stats.qmd` (or edit it) and include whichever plots you like:

