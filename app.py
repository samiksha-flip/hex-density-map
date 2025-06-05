import streamlit as st
import pandas as pd
import pydeck as pdk
import h3
import matplotlib.cm as cm
import matplotlib.colors as colors

# Load your data
df = pd.read_csv("productivity_hex_cord_cumm_3.csv")

# Sidebar filters
selected_pincode = st.sidebar.multiselect("Pincode", df["pincode"].unique(), default=df["pincode"].unique())
selected_hr = st.sidebar.multiselect("Hour", df["hr_order_created"].unique(), default=df["hr_order_created"].unique())
selected_time = st.sidebar.multiselect("Time Category", df["time_category"].unique(), default=df["time_category"].unique())

# Apply filters
filtered_df = df[
    (df["pincode"].isin(selected_pincode)) &
    (df["hr_order_created"].isin(selected_hr)) &
    (df["time_category"].isin(selected_time))
]

# Re-aggregate by hex_mapping
hex_df = filtered_df.groupby("hex_mapping").agg({
    "order_external_id": "sum"
}).reset_index()

# Get hexagon boundary + lat/lng
hex_df["polygon"] = hex_df["hex_mapping"].apply(
    lambda h: [[lng, lat] for lat, lng in h3.cell_to_boundary(h)]
)
hex_df["lat"] = hex_df["hex_mapping"].apply(lambda h: h3.cell_to_latlng(h)[0])
hex_df["lng"] = hex_df["hex_mapping"].apply(lambda h: h3.cell_to_latlng(h)[1])

# Normalize values and apply a color gradient
max_orders = hex_df["order_external_id"].max() or 1
min_orders = hex_df["order_external_id"].min()

norm = colors.Normalize(vmin=min_orders, vmax=max_orders)
colormap = cm.get_cmap("viridis")
  # Options: 'plasma', 'inferno', 'turbo', 'viridis'

def get_color(value):
    rgba = colormap(norm(value))
    return [int(255 * c) for c in rgba[:3]] + [180]  # RGB + alpha

hex_df["fill_color"] = hex_df["order_external_id"].apply(get_color)

# Build polygon data with all fields for hover
polygon_data = [{
    "polygon": row["polygon"],
    "order_count": row["order_external_id"],
    "hex_id": row["hex_mapping"],
    "fill_color": row["fill_color"]
} for _, row in hex_df.iterrows()]

# Pydeck layer
layer = pdk.Layer(
    "PolygonLayer",
    data=polygon_data,
    get_polygon="polygon",
    get_fill_color="fill_color",
    pickable=True,
    stroked=False,
    extruded=True,
    get_elevation="order_count",
    elevation_scale=4,
)

# Map view
view_state = pdk.ViewState(
    latitude=hex_df["lat"].mean() if not hex_df.empty else 28.6139,
    longitude=hex_df["lng"].mean() if not hex_df.empty else 77.2090,
    zoom=10,
    pitch=40,
)

# Tooltip with both order count and hex ID
tooltip = {
    "html": "<b>Orders:</b> {order_count}<br/><b>Hex ID:</b> {hex_id}",
    "style": {"color": "white", "backgroundColor": "black"}
}

# Render map
st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/dark-v9"
))
