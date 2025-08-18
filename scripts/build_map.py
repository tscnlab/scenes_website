"""
Builds an interactive Folium map (data/map.html) from SCENES metadata.

- Reads Excel at data/20250630_SCENES_metadata_integrated_modified.xlsx 
  (or falls back to data/metadata.csv if Excel is missing).
- Writes cleaned data/metadata.csv for use in Quarto pages.
- Saves Folium map to data/map.html with cluster markers + legend.
"""

import re
from pathlib import Path
import warnings

import pandas as pd
import folium
from folium.plugins import MarkerCluster

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]  
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

EXCEL_PATH = DATA / "20250630_SCENES_metadata_integrated_modified.xlsx"
CSV_PATH   = DATA / "metadata.csv"
MAP_HTML   = DATA / "map.html"

VIEW_COLORS = {
    "Outdoor": "#CD923B",
    "Indoor w/ window": "#081A5B",
    "Indoor w/o window": "#426E56",
}

def extract_parentheses_content(s):
    """Extract text inside parentheses, e.g. 'Scene (Outdoor)' -> 'Outdoor'."""
    s = "" if pd.isna(s) else str(s).strip()
    m = re.search(r"\((.*?)\)", s)
    return m.group(1).strip() if m else ""

def load_metadata():
    if EXCEL_PATH.exists():
        print(f"Reading Excel: {EXCEL_PATH}")
        try:
            df = pd.read_excel(EXCEL_PATH) 
        except ImportError:
            raise ImportError(
                "openpyxl is required to read .xlsx. Install with:\n  pip install openpyxl"
            )
    elif CSV_PATH.exists():
        print(f"Reading CSV: {CSV_PATH}")
        df = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError(
            f"No metadata file found.\n"
            f"Expected one of:\n  {EXCEL_PATH}\n  {CSV_PATH}"
        )
    return df

def clean_metadata(df):
    df = df.copy()

    if "scene" in df.columns:
        df["scene"] = df["scene"].apply(extract_parentheses_content)
    if "lighting" in df.columns:
        df["lighting"] = df["lighting"].apply(extract_parentheses_content)

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")


    for col in ["location", "date", "time", "scene"]:
        if col not in df.columns:
            df[col] = ""

    return df

def build_map(df):
    m = folium.Map(
        location=[df["latitude"].mean(), df["longitude"].mean()],
        zoom_start=2,
    )
    mc = MarkerCluster().add_to(m)

    for r in df.itertuples(index=False):
        view = getattr(r, "view", "")
        color = VIEW_COLORS.get(view, "gray")

        lat, lon = getattr(r, "latitude"), getattr(r, "longitude")
        if pd.isna(lat) or pd.isna(lon):
            continue

        popup = (
            f"<b>Location:</b> {getattr(r, 'location','')}<br>"
            f"<b>View:</b> {view}<br>"
            f"<b>Scene:</b> {getattr(r, 'scene','')}<br>"
            f"<b>Date:</b> {getattr(r, 'date','')} {getattr(r, 'time','')}"
        )

        folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            popup=popup,
        ).add_to(mc)

    legend_items = "".join(
        f'''
        <div style="display:flex; align-items:center; gap:4px; margin:1px 0;">
          <svg viewBox="0 0 100 100" style="width:1.2em; height:1.2em; flex:0 0 auto;">
            <!-- hollow circle: stroke in category color, transparent center -->
            <circle cx="50" cy="50" r="40" fill="none" stroke="{c}" stroke-width="20"></circle>
        </svg>
          <span>{label}</span>
        </div>
        '''
        for label, c in VIEW_COLORS.items()
    )

    legend_html = f"""
    <div style="
        position: fixed; bottom: 20px; left: 20px;  /* tighter to corner */
        border: 0px solid #666; border-radius: 3px;
        background: rgba(255, 255, 255, 0.4); /* semi-transparent */
        padding: 4px 4px; z-index: 999;
        font: 8px/1.2 Arial, sans-serif; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    ">
      <b>View Legend</b>
      {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m

def main():
    df_raw = load_metadata()
    df = clean_metadata(df_raw)

    df.to_csv(CSV_PATH, index=False)
    print(f"Wrote CSV: {CSV_PATH}")

    m = build_map(df)
    m.save(MAP_HTML.as_posix())
    print(f"Wrote map: {MAP_HTML}")

if __name__ == "__main__":
    main()
