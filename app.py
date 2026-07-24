import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, MultiPoint
from shapely.ops import voronoi_diagram

# ==============================================================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==============================================================================
st.set_page_config(
    page_title="Ernakulam Leptospirosis Intelligence",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        [data-testid="stMetricValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #1e293b !important;
        }
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        .header-container {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            padding: 24px;
            border-radius: 14px;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .header-title { font-size: 30px; font-weight: 800; margin: 0; }
        .header-subtitle { font-size: 15px; color: #93c5fd; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-container">
        <div class="header-title">🩸 Leptospirosis Epidemiological Tracker</div>
        <div class="header-subtitle">Ernakulam District • Custom Block Boundaries & Hotspot Analysis</div>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. DATA LOADING & DYNAMIC BOUNDARY GENERATOR
# ==============================================================================
@st.cache_data
def load_data():
    raw_data = {
        'Health Blocks': [
            'Angamaly', 'Chengamanad', 'Cheranalloor', 'Ezhikkara', 'Kalady',
            'Keechery', 'Kumbalanghi', 'Malayidamthuruth', 'Malippuram', 'Nettoor',
            'Pallarimangalam', 'Pampakuda', 'Pandappilly', 'Pizhala', 'Ramamangalam',
            'Vadavucode', 'Varappetty', 'Varappuzha', 'Vengoor', 'Kochi Corporation'
        ],
        'Number of Cases': [
            12, 4, 8, 2, 8, 7, 3, 20, 3, 2, 4, 4, 5, 0, 5, 10, 7, 4, 13, 11
        ],
        'latitude': [
            10.1960, 10.1517, 10.0461, 10.1412, 10.1685,
            9.8432, 9.8752, 10.0416, 10.0234, 9.9234,
            10.0789, 9.8631, 9.8921, 10.0521, 9.8512,
            9.9723, 10.0214, 10.0762, 10.1821, 9.9674
        ],
        'longitude': [
            76.3860, 76.3685, 76.2891, 76.2185, 76.4385,
            76.4321, 76.2845, 76.3985, 76.2189, 76.3124,
            76.6821, 76.5412, 76.6214, 76.2412, 76.5812,
            76.4412, 76.6512, 76.2612, 76.5512, 76.2426
        ]
    }
    return pd.DataFrame(raw_data)

@st.cache_data
def generate_manual_district_boundaries(df):
    """
    Generates contiguous boundary polygons for each health block 
    and clips them within the overall Ernakulam District boundary envelope.
    """
    points = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    multipoint = MultiPoint(points)
    
    # District envelope buffer
    district_boundary = multipoint.convex_hull.buffer(0.08)
    
    # Voronoi region calculations
    voronoi_regions = voronoi_diagram(multipoint, envelope=district_boundary.envelope)
    
    polygons = []
    for pt in points:
        for poly in voronoi_regions.geoms:
            clipped_poly = poly.intersection(district_boundary)
            if clipped_poly.contains(pt) or clipped_poly.touches(pt):
                polygons.append(clipped_poly)
                break
                
    gdf = gpd.GeoDataFrame(df, geometry=polygons, crs="EPSG:4326")
    gdf['centroid_lat'] = df['latitude']
    gdf['centroid_lon'] = df['longitude']
    return gdf

df_cases = load_data()
gdf_merged = generate_manual_district_boundaries(df_cases)

# ==============================================================================
# 3. SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.header("🕹️ Map Controls & Filters")

map_style = st.sidebar.selectbox(
    "Choose Map Base Layer Style:",
    options=["CartoDB Positron", "CartoDB Dark Matter", "OpenStreetMap"],
    index=0
)

hotspot_threshold = st.sidebar.slider(
    "Hotspot Case Threshold",
    min_value=1,
    max_value=15,
    value=5
)

st.sidebar.markdown("---")
st.sidebar.success("✨ **Custom Manual Boundaries Active**: District & Block boundaries generated successfully!")

# ==============================================================================
# 4. KPI SUMMARY CARDS
# ==============================================================================
col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

total_cases = int(df_cases['Number of Cases'].sum())
total_blocks = len(df_cases)
hotspot_count = int((df_cases['Number of Cases'] > hotspot_threshold).sum())
max_row = df_cases.loc[df_cases['Number of Cases'].idxmax()]

col_kpi1.metric("Total Cumulative Cases", f"{total_cases:,}")
col_kpi2.metric("Total Blocks Monitored", total_blocks)
col_kpi3.metric(f"Hotspots (>{hotspot_threshold} Cases)", hotspot_count, delta=f"{(hotspot_count/total_blocks)*100:.0f}% of total", delta_color="inverse")
col_kpi4.metric("Highest Incidence Cluster", f"{max_row['Number of Cases']} Cases", delta=max_row['Health Blocks'], delta_color="off")

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 5. SIDE-BY-SIDE MAIN LAYOUT
# ==============================================================================
left_col, right_col = st.columns([3, 2])

tile_mapping = {
    "CartoDB Dark Matter": "CartoDB dark_matter",
    "CartoDB Positron": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap"
}

with left_col:
    st.subheader("🗺️ Interactive Spatial Risk Map")
    
    m = folium.Map(
        location=[10.02, 76.40],
        zoom_start=10,
        tiles=tile_mapping[map_style]
    )
    
    # 1. Render Choropleth Polygon Layer
    choropleth = folium.Choropleth(
        geo_data=gdf_merged[['Health Blocks', 'Number of Cases', 'geometry']],
        name="Choropleth Intensity",
        data=gdf_merged,
        columns=["Health Blocks", "Number of Cases"],
        key_on="feature.properties.Health Blocks",
        fill_color="YlOrRd",
        fill_opacity=0.45,
        line_color="#333333",
        line_opacity=0.8,
        line_weight=1.5,
        highlight=True
    ).add_to(m)

    choropleth.geojson.add_child(
        folium.features.GeoJsonTooltip(
            fields=["Health Blocks", "Number of Cases"],
            aliases=["Health Block:", "Reported Cases:"],
            style="font-family: sans-serif; font-size: 12px; padding: 6px;"
        )
    )

    # 2. Render Circle Markers
    for _, row in gdf_merged.iterrows():
        lat = row['centroid_lat']
        lon = row['centroid_lon']
        cases = row['Number of Cases']
        block_name = row['Health Blocks']
        is_hotspot = cases > hotspot_threshold
        
        color_code = "#FF2A6D" if is_hotspot else "#05D5E7"
        fill_code = "#FF0055" if is_hotspot else "#00F5D4"
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=5 + (cases * 0.7),
            color=color_code,
            fill=True,
            fill_color=fill_code,
            fill_opacity=0.85 if is_hotspot else 0.4,
            weight=2 if is_hotspot else 1,
            tooltip=f"<b>{'⚠️ HOTSPOT: ' if is_hotspot else ''}{block_name}</b><br>Cases: {cases}",
            popup=folium.Popup(
                f"<div style='font-family: sans-serif; min-width: 140px;'>"
                f"<h4 style='margin:0; color:{color_code};'>{block_name}</h4>"
                f"<hr style='margin:6px 0; border:0; border-top:1px solid #ccc;'>"
                f"<b>Status:</b> {'⚠️ High Risk Hotspot' if is_hotspot else '✅ Low/Moderate'}<br>"
                f"<b>Reported Cases:</b> <span style='font-size:14px; font-weight:bold;'>{cases}</span>"
                f"</div>", 
                max_width=250
            )
        ).add_to(m)

    st_folium(m, width="100%", height=520)

with right_col:
    st.subheader("📊 Block Case Breakdown")
    
    search_query = st.text_input("🔍 Quick Search Block Name", "")
    
    filtered_df = df_cases.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['Health Blocks'].str.contains(search_query, case=False)]
        
    show_hotspots_only = st.checkbox(f"Filter Hotspots Only (>{hotspot_threshold} Cases)")
    if show_hotspots_only:
        filtered_df = filtered_df[filtered_df['Number of Cases'] > hotspot_threshold]

    st.dataframe(
        filtered_df[['Health Blocks', 'Number of Cases']].sort_values(by="Number of Cases", ascending=False),
        column_config={
            "Health Blocks": st.column_config.TextColumn("Health Block Name"),
            "Number of Cases": st.column_config.ProgressColumn(
                "Infection Count",
                help="Total reported Leptospirosis cases",
                format="%d",
                min_value=0,
                max_value=int(df_cases['Number of Cases'].max())
            )
        },
        use_container_width=True,
        hide_index=True,
        height=430
    )