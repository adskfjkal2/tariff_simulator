import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ------------------ Load Data ------------------
data_path = "simInput.xlsx"  # Excel file in same folder
@st.cache_data
def load_data():
    return pd.read_excel(data_path)

df = load_data()

# ------------------ Load Historical Tariff Data ------------------
tariff_data_path = "Tariff Rate by Year (1).csv"
@st.cache_data
def load_tariff_data():
    return pd.read_csv(tariff_data_path)

historical_df = load_tariff_data()

# ------------------ Landing Section ------------------
st.title("📊 Tariff Impact & Supply Chain Simulator")
st.markdown("""
Welcome to the simulation dashboard. Here you can:
- Explore historical tariffs
- View part-level baseline data
- Model what-if scenarios (e.g. tariff changes, supplier switches)
- Compare baseline vs scenario cost exposure
""")

# ------------------ Historical Tariff View ------------------
st.subheader("📈 Historical Tariff Education")
years = sorted(historical_df["Year"].unique())
selected_year = st.slider("Select Year", min_value=years[0], max_value=years[-1], value=years[-1])

year_df = historical_df[historical_df["Year"] == selected_year]
fig_heat = px.density_heatmap(
    year_df,
    x="Country",
    y="Material",
    z="Tariff Rate (%)",
    color_continuous_scale="Reds",
    title=f"Tariff Heatmap by Country & Material in {selected_year}"
)
st.plotly_chart(fig_heat, use_container_width=True)

# ------------------ Input & Baseline ------------------
st.subheader("📦 Baseline Supply Chain Inputs")
st.dataframe(df, use_container_width=True)

# ------------------ Scenario Builder ------------------
st.sidebar.title("🧪 Scenario Builder")
st.sidebar.markdown("Adjust tariffs by source country")

# Sidebar: Tariff sliders by country
countries = sorted(df["Source Country"].unique())
scenario_tariffs = {
    country: st.sidebar.slider(f"{country} Tariff %", 0, 100, int(df[df["Source Country"] == country]["Tariff Rate (%)"].mean()))
    for country in countries
}

# Sidebar: Bubble size selector
st.sidebar.markdown("### Bubble Size Metric")
size_option = st.sidebar.selectbox("Choose what bubble size represents:", [
    "Total Inventory",
    "Δ Cost ($)",
    "Δ Cost (%)"
])

# ------------------ Bubble Plot: Baseline (Always Visible) ------------------
st.subheader("📍 Scenario Delta Plot: Baseline vs Simulation")

# Create baseline version (everything at delta = 0)
baseline_df = df.copy()
baseline_df["Delta ($)"] = 0
baseline_df["Delta (%)"] = 0
baseline_df["Part Number"] = df["Part Number"]

# Compute dynamic bubble size based on sidebar option
if size_option == "Total Inventory":
    baseline_df["Bubble Size"] = df["Total Inventory Position"]
elif size_option == "Δ Cost ($)":
    baseline_df["Bubble Size"] = 0  # no delta yet
elif size_option == "Δ Cost (%)":
    baseline_df["Bubble Size"] = 0

# Compute size scaling for both baseline + scenario
sizeref = 2. * df["Total Inventory Position"].max() / (40.0 ** 2)  # 40px max

# Create baseline bubble chart
fig_zero = go.Figure()
fig_zero.add_vline(x=0, line=dict(color="gray", dash="dash"), annotation_text="Baseline", annotation_position="top")

for country in baseline_df["Source Country"].unique():
    group = baseline_df[baseline_df["Source Country"] == country]
    fig_zero.add_trace(go.Scatter(
        x=group["Delta ($)"],
        y=group["Part Number"],
        mode="markers",
        name=country,
        marker=dict(
            size=group["Bubble Size"],
            sizemode="area",
            sizeref=sizeref,
            sizemin=5,
            opacity=0.7,
            line=dict(width=1, color='black')
        ),
        hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
    ))

fig_zero.update_layout(
    title="💥 Baseline: All Parts at Zero Delta",
    xaxis_title="Δ Cost vs Baseline ($)",
    yaxis_title="Part Number",
    height=600,
    showlegend=True
)
st.plotly_chart(fig_zero, use_container_width=True)

# ------------------ Scenario Simulation ------------------
if st.sidebar.button("Run Scenario Simulation"):
    # Copy baseline and apply updated tariffs
    df_scenario = df.copy()
    for country in countries:
        df_scenario.loc[df_scenario["Source Country"] == country, "Tariff Rate (%)"] = scenario_tariffs[country]

    # Recompute Scenario Total Cost to Serve (CTS)
    base_cost = (
        df_scenario["Cost Per Unit (USD)"] +
        df_scenario["Packaging Cost Per Unit (USD)"] +
        df_scenario["Freight Cost Per Unit (USD)"]
    ) * (1 + df_scenario["Tariff Rate (%)"] / 100)

    full_cost = base_cost + df_scenario["Warehouse Cost Per Unit (USD)"] + df_scenario["Indirect Cost Per Unit (USD)"]
    df_scenario["Scenario CTS"] = full_cost * df_scenario["Total Inventory Position"]

    # ------------------ Scenario Comparison Table ------------------
    st.subheader("🔁 Scenario Comparison vs Baseline")
    compare_df = df_scenario[["Part Number", "Description", "Source Country"]].copy()
    compare_df["New Tariff Rate"] = df_scenario["Tariff Rate (%)"]
    compare_df["New CTS"] = df_scenario["Scenario CTS"]
    compare_df["Total Cost to Serve"] = df["Total Cost to Serve"]
    compare_df["Delta ($)"] = compare_df["New CTS"] - compare_df["Total Cost to Serve"]
    compare_df["Delta (%)"] = (compare_df["Delta ($)"] / compare_df["Total Cost to Serve"]) * 100

    st.dataframe(compare_df, use_container_width=True)

    # ------------------ Bar Chart of Δ ------------------
    fig_bar = px.bar(compare_df.sort_values("Delta ($)", ascending=False),
                     x="Part Number", y="Delta ($)", color="Source Country",
                     title="Parts with Highest Cost Impact")
    st.plotly_chart(fig_bar, use_container_width=True)

    # ------------------ Updated Delta Bubble Chart ------------------
    st.subheader("📍 Scenario Delta Plot: Updated After Simulation")

    bubble_df = df_scenario.copy()
    bubble_df["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
    bubble_df["Delta (%)"] = (bubble_df["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
    bubble_df["Part Number"] = df["Part Number"]

    # Compute size dynamically again based on selection
    if size_option == "Total Inventory":
        bubble_df["Bubble Size"] = df["Total Inventory Position"]
    elif size_option == "Δ Cost ($)":
        bubble_df["Bubble Size"] = bubble_df["Delta ($)"].abs()
    elif size_option == "Δ Cost (%)":
        bubble_df["Bubble Size"] = bubble_df["Delta (%)"].abs() * 100  # percent scaled

    sizeref = 2. * bubble_df["Bubble Size"].max() / (40.0 ** 2)

    fig_bubble = go.Figure()
    fig_bubble.add_vline(x=0, line=dict(color="gray", dash="dash"), annotation_text="Baseline", annotation_position="top")

    for country in bubble_df["Source Country"].unique():
        group = bubble_df[bubble_df["Source Country"] == country]
        fig_bubble.add_trace(go.Scatter(
            x=group["Delta ($)"],
            y=group["Part Number"],
            mode="markers",
            name=country,
            marker=dict(
                size=group["Bubble Size"],
                sizemode="area",
                sizeref=sizeref,
                sizemin=5,
                opacity=0.7,
                line=dict(width=1, color="black")
            ),
            hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
        ))

    fig_bubble.update_layout(
        title=f"💥 Simulation Impact: Cost Change from Baseline (Bubble Size: {size_option})",
        xaxis_title="Δ Cost-to-Serve ($)",
        yaxis_title="Part Number",
        height=600,
        showlegend=True
    )

    st.plotly_chart(fig_bubble, use_container_width=True)
