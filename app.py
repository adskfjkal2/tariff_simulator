import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------ Sidebar / Input ------------------
st.sidebar.title("Simulation Setup")
selected_product = st.sidebar.selectbox("Choose Product", ["Electronics", "Steel", "Apparel"])
selected_countries = st.sidebar.multiselect("Sourcing Countries", ["China", "Vietnam", "Mexico", "USA", "Germany"], default=["China", "Vietnam"])
volatility = st.sidebar.slider("Tariff Volatility (%)", 0.0, 0.5, 0.15, step=0.01)
runs = st.sidebar.slider("Monte Carlo Simulations", 100, 1000, 500)

# ------------------ Historical Tariffs (Mock) ------------------
def load_historical_tariffs():
    years = list(range(2015, 2025))
    countries = ["China", "Vietnam", "Mexico", "USA", "Germany"]
    data = {country: np.random.uniform(0.05, 0.25, size=len(years)) for country in countries}
    df = pd.DataFrame(data, index=years)
    return df

historical_df = load_historical_tariffs()

# ------------------ Display Historical Timeline ------------------
st.subheader("📈 Historical Tariff Trends (2015–2024)")
st.line_chart(historical_df[selected_countries])

# ------------------ Monte Carlo Simulation ------------------
st.subheader("🔁 Simulated Tariff Impact Distribution")

@st.cache_data
def simulate_tariffs(country, base_tariff, volatility, runs):
    return np.random.normal(loc=base_tariff, scale=volatility, size=runs)

sim_data = []
for country in selected_countries:
    base = historical_df[country].iloc[-1]  # Latest year
    samples = simulate_tariffs(country, base, volatility, runs)
    sim_data.append(pd.DataFrame({
        "Tariff Rate": samples,
        "Country": country
    }))

sim_df = pd.concat(sim_data)

fig = px.violin(sim_df, x="Country", y="Tariff Rate", box=True, points="all", color="Country")
st.plotly_chart(fig)

# ------------------ Country Cards ------------------
st.subheader("🌍 Sourcing Country Summary")
for country in selected_countries:
    latest_tariff = historical_df[country].iloc[-1]
    st.markdown(f"**{country}** – Latest Tariff: `{latest_tariff:.2%}`")
    st.line_chart(historical_df[country])

