import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ Tariff Reference ------------------
product_tariffs = {
    "Steel Coils (7208.38)": {"China": 0.25},
    "IC Chips (8542.31)": {"Taiwan": 0.15},
    "Aluminum Sheets (7606.12)": {"EU": 0.10}
}

# ------------------ Sidebar Inputs ------------------
st.sidebar.title("Simulation Setup")

selected_material = st.sidebar.selectbox("Raw Material Input", list(product_tariffs.keys()))
source_options = list(product_tariffs[selected_material].keys())
selected_countries = st.sidebar.multiselect("Sourcing Countries", source_options, default=source_options)

volatility = st.sidebar.slider("Tariff Volatility (±%)", 0.0, 0.5, 0.15)
runs = st.sidebar.slider("Monte Carlo Simulations", 1000, 20000, 5000, step=1000)

st.sidebar.markdown("### Supply Chain Parameters")
adu = st.sidebar.number_input("Avg Daily Use (ADU)", min_value=100, value=500)
plt = st.sidebar.number_input("Planned Lead Time (Days)", min_value=1, value=30)
cover_days = st.sidebar.number_input("Delivery Quantity (Days of Cover)", min_value=1, value=15)
ots = st.sidebar.slider("On-Time Shipping Rate (%)", 80, 100, 95)
ppm = st.sidebar.number_input("Defect Rate (PPM)", min_value=0, value=500)

# ------------------ Historical Tariff (Static) ------------------
def get_historical_tariffs(country):
    # Made-up realistic trend for now, replace with real-world data when ready
    base = product_tariffs[selected_material][country]
    years = list(range(2015, 2025))
    trend = np.linspace(base * 0.8, base * 1.2, len(years))  # Simulate past 10 years
    noise = np.random.normal(0, 0.005, len(years))
    return pd.Series(np.clip(trend + noise, 0.01, 0.5), index=years)

# ------------------ Simulation Function ------------------
@st.cache_data
def simulate_costs(country, base_tariff, adu, plt, cover, ots, ppm, volatility, runs):
    demand = np.random.normal(loc=adu, scale=adu * 0.1, size=runs)
    lead_times = np.random.normal(loc=plt, scale=(1 - ots / 100) * 10, size=runs)
    shipment_qty = demand * cover
    defects = shipment_qty * (ppm / 1_000_000)

    tariffs = np.random.normal(loc=base_tariff, scale=volatility, size=runs)
    purchase_cost = shipment_qty * 10  # mock $10/unit
    tariff_cost = purchase_cost * tariffs
    freight = shipment_qty * 2  # $2/unit freight
    warehousing = shipment_qty * 0.5
    indirect = shipment_qty * 0.25

    total_cts = purchase_cost + tariff_cost + freight + warehousing + indirect

    return pd.DataFrame({
        "Country": country,
        "Purchase": purchase_cost,
        "Tariffs": tariff_cost,
        "Freight": freight,
        "Warehousing": warehousing,
        "Indirect": indirect,
        "Total CTS": total_cts
    })

# ------------------ Run Simulation ------------------
st.subheader("🔁 Tariff Scenario Simulation")

historical_df = pd.DataFrame({country: get_historical_tariffs(country) for country in selected_countries})
st.subheader("📈 Historical Tariff Trends")
st.line_chart(historical_df)

all_results = []
for country in selected_countries:
    base_tariff = product_tariffs[selected_material][country]
    result = simulate_costs(country, base_tariff, adu, plt, cover_days, ots, ppm, volatility, runs)
    all_results.append(result)

final_df = pd.concat(all_results)

# ------------------ Results: Violin + Cost Breakdown ------------------
st.subheader("🎻 Simulated Cost-to-Serve Distribution")
st.plotly_chart(
    px.violin(final_df, x="Country", y="Total CTS", box=True, points="all", color="Country"),
    use_container_width=True
)

summary = final_df.groupby("Country")["Total CTS"].agg(
    P50="median", P90=lambda x: np.percentile(x, 90), P95=lambda x: np.percentile(x, 95)
)
st.subheader("📊 Cost Exposure Summary (P-Values)")
st.dataframe(summary)

# ------------------ (Planned): Save Scenario / Compare Button ------------------
# You can add st.session_state + st.button() to save "snapshots" for compare view
