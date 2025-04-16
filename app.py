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

countries = df["Source Country"].unique()
scenario_tariffs = {}
for country in countries:
    scenario_tariffs[country] = st.sidebar.slider(f"{country} Tariff %", 0, 100, int(df[df["Source Country"] == country]["Tariff Rate (%)"].mean()))

if st.sidebar.button("Run Scenario Simulation"):
    df_scenario = df.copy()
    for country in countries:
        df_scenario.loc[df_scenario["Source Country"] == country, "Tariff Rate (%)"] = scenario_tariffs[country]

    # Compute new Total Cost to Serve
    base_cost = (
        df_scenario["Cost Per Unit (USD)"] +
        df_scenario["Packaging Cost Per Unit (USD)"] +
        df_scenario["Freight Cost Per Unit (USD)"]
    ) * (1 + df_scenario["Tariff Rate (%)"] / 100)
    full_cost = base_cost + df_scenario["Warehouse Cost Per Unit (USD)"] + df_scenario["Indirect Cost Per Unit (USD)"]
    df_scenario["Scenario CTS"] = full_cost * df_scenario["Total Inventory Position"]

    st.subheader("🔁 Scenario Comparison vs Baseline")
    compare_df = df_scenario[["Part Number", "Description", "Source Country", "Tariff Rate (%)", "Total Cost to Serve"]].copy()
    compare_df["New Tariff Rate"] = df_scenario["Tariff Rate (%)"]
    compare_df["New CTS"] = df_scenario["Scenario CTS"]
    compare_df["Delta ($)"] = compare_df["New CTS"] - compare_df["Total Cost to Serve"]
    compare_df["Delta (%)"] = (compare_df["Delta ($)"] / compare_df["Total Cost to Serve"]) * 100

    st.dataframe(compare_df, use_container_width=True)

    fig_bar = px.bar(compare_df.sort_values("Delta ($)", ascending=False),
                     x="Part Number", y="Delta ($)", color="Source Country",
                     title="Parts with Highest Cost Impact")
    st.plotly_chart(fig_bar, use_container_width=True)

### Bubble chart for delta
st.subheader("📍 Scenario Delta Plot: Baseline vs Simulation")

bubble_df = compare_df.copy()
bubble_df["Bubble Size"] = df_scenario["Total Inventory Position"]
bubble_df["Delta ($)"] = bubble_df["Delta ($)"].round(2)

# Plot scenario delta
fig_bubble = go.Figure()

# Add baseline line (Delta = 0)
fig_bubble.add_vline(x=0, line=dict(color="gray", dash="dash"), annotation_text="Baseline", annotation_position="top")

# Add each country group
for country in bubble_df["Source Country"].unique():
    group = bubble_df[bubble_df["Source Country"] == country]
    fig_bubble.add_trace(go.Scatter(
        x=group["Delta ($)"],
        y=group["Part Number"],
        mode="markers",
        name=country,
        marker=dict(
            size=group["Bubble Size"] / 100,  # scale size for readability
            opacity=0.7,
            line=dict(width=1, color="black")
        ),
        hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
    ))

fig_bubble.update_layout(
    title="💥 Scenario Simulation: Cost Change from Baseline",
    xaxis_title="Δ Cost-to-Serve ($)",
    yaxis_title="Part Number",
    height=600,
    showlegend=True
)
st.plotly_chart(fig_bubble, use_container_width=True)
