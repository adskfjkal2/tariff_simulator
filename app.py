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
historical_tariffs = {
    "China": np.linspace(0.1, 0.25, 10),
    "Mexico": np.linspace(0.05, 0.1, 10),
    "Vietnam": np.linspace(0.03, 0.08, 10)
}
years = list(range(2015, 2025))
fig = go.Figure()
for country, values in historical_tariffs.items():
    fig.add_trace(go.Scatter(x=years, y=values, mode='lines', name=country))
fig.update_layout(title="Tariff Trend by Country (2015–2024)", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

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