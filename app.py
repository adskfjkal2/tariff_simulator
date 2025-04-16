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

# Ensure df_scenario exists so chart can always be drawn
df_scenario = df.copy()
df_scenario["Scenario CTS"] = df["Total Cost to Serve"]  # Same as baseline initially


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

# Determine whether a real scenario has been run
scenario_triggered = (
    "Scenario CTS" in df_scenario.columns
    and not df_scenario["Scenario CTS"].equals(df["Total Cost to Serve"])
)

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

    # ------------------ Combined Bubble Chart: Baseline + Scenario ------------------
    st.subheader("📍 Cost Impact Bubble Chart: Baseline + Scenario")

    # Create baseline trace (always visible)
    baseline_df = df.copy()
    baseline_df["Delta ($)"] = 0
    baseline_df["Delta (%)"] = 0
    baseline_df["Part Number"] = df["Part Number"]

    # Check if scenario has been run
    # scenario_triggered = False
    if "Scenario CTS" in df_scenario.columns:
        scenario_triggered = not df_scenario["Scenario CTS"].equals(df["Total Cost to Serve"])
        df_scenario["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
        df_scenario["Delta (%)"] = (df_scenario["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
        df_scenario["Part Number"] = df["Part Number"]

    # Compute bubble sizes based on selection
    if size_option == "Total Inventory":
        baseline_size = df["Total Inventory Position"]
        scenario_size = df["Total Inventory Position"] if scenario_triggered else None
    elif size_option == "Δ Cost ($)":
        baseline_size = pd.Series([1]*len(df))  # ensure bubbles are visible
        scenario_size = df_scenario["Delta ($)"].abs() if scenario_triggered else None
    elif size_option == "Δ Cost (%)":
        baseline_size = pd.Series([1]*len(df))
        scenario_size = (df_scenario["Delta (%)"].abs() * 100) if scenario_triggered else None

    # Combine sizes to normalize
    combined_size = pd.concat([baseline_size] + ([scenario_size] if scenario_triggered else []))
    sizeref = 2. * combined_size.max() / (40.0 ** 2)

    # Create figure
    fig_both = go.Figure()
    fig_both.add_vline(x=0, line=dict(color="gray", dash="dash"), annotation_text="Baseline", annotation_position="top")

    # Add baseline trace per country
    for country in df["Source Country"].unique():
        baseline_group = baseline_df[baseline_df["Source Country"] == country].copy()
        baseline_group["Bubble Size"] = baseline_size[baseline_group.index]

        fig_both.add_trace(go.Scatter(
            x=baseline_group["Delta ($)"],
            y=baseline_group["Part Number"],
            mode="markers",
            name=f"{country} (Baseline)",
            marker=dict(
                size=baseline_group["Bubble Size"],
                sizemode="area",
                sizeref=sizeref,
                sizemin=5,
                opacity=0.4,
                symbol="circle",
                line=dict(width=1, color='black')
            ),
            hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
        ))

    # If scenario exists, add matching trace
    if scenario_triggered:
        for country in df["Source Country"].unique():
            scenario_group = df_scenario[df_scenario["Source Country"] == country].copy()
            scenario_group["Bubble Size"] = scenario_size[scenario_group.index]

            fig_both.add_trace(go.Scatter(
                x=scenario_group["Delta ($)"],
                y=scenario_group["Part Number"],
                mode="markers",
                name=f"{country} (Scenario)",
                marker=dict(
                    size=scenario_group["Bubble Size"],
                    sizemode="area",
                    sizeref=sizeref,
                    sizemin=5,
                    opacity=0.9,
                    symbol="circle",  # 👈 force all to use circles
                    line=dict(width=1, color="black")
                ),
                hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
            ))

    fig_both.update_layout(
        title=f"💥 Cost Change from Baseline (Bubble Size: {size_option})",
        xaxis_title="Δ Cost-to-Serve ($)",
        yaxis_title="Part Number",
        height=650,
        showlegend=True
    )

    st.plotly_chart(fig_both, use_container_width=True)
    st.caption("🔵 Bubbles = Baseline & Scenario. Hover for delta.")


# ------------------ Combined Animated Bubble Chart ------------------
st.subheader("📍 Cost Impact Bubble Chart: Baseline + Scenario")

# Compute deltas and scenario stats if simulation was run
bubble_df = df_scenario.copy()
bubble_df["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
bubble_df["Delta (%)"] = (bubble_df["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
bubble_df["Part Number"] = df["Part Number"]

# Set bubble sizes
if size_option == "Total Inventory":
    baseline_size = df["Total Inventory Position"]
    scenario_size = df["Total Inventory Position"] if scenario_triggered else None
elif size_option == "Δ Cost ($)":
    baseline_size = pd.Series([1]*len(df))
    scenario_size = bubble_df["Delta ($)"].abs() if scenario_triggered else None
elif size_option == "Δ Cost (%)":
    baseline_size = pd.Series([1]*len(df))
    scenario_size = bubble_df["Delta (%)"].abs() * 100 if scenario_triggered else None

combined_size = pd.concat([baseline_size] + ([scenario_size] if scenario_triggered else []))
sizeref = 2. * combined_size.max() / (40.0 ** 2)

# Assign consistent color per country
country_list = sorted(df["Source Country"].unique())
color_map = px.colors.qualitative.Set2
country_colors = {country: color_map[i % len(color_map)] for i, country in enumerate(country_list)}

fig_both = go.Figure()
fig_both.add_vline(x=0, line=dict(color="gray", dash="dash"), annotation_text="Baseline", annotation_position="top")

# Plot baseline trace
for country in country_list:
    base = df[df["Source Country"] == country].copy()
    base["Delta ($)"] = 0
    base["Bubble Size"] = baseline_size[base.index]
    base["Part Number"] = df["Part Number"]

    fig_both.add_trace(go.Scatter(
        x=base["Delta ($)"],
        y=base["Part Number"],
        mode="markers+text",
        name=f"{country} (Baseline)",
        marker=dict(
            size=base["Bubble Size"],
            sizemode="area",
            sizeref=sizeref,
            sizemin=5,
            opacity=0.4,
            color=country_colors[country],
            line=dict(width=1, color='black')
        ),
        text=None,
        hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
    ))

# Plot scenario trace (animated into view)
if scenario_triggered:
    for country in country_list:
        group = bubble_df[bubble_df["Source Country"] == country].copy()
        group["Bubble Size"] = scenario_size[group.index]

        fig_both.add_trace(go.Scatter(
            x=group["Delta ($)"],
            y=group["Part Number"],
            mode="markers",
            name=f"{country} (Scenario)",
            marker=dict(
                size=group["Bubble Size"],
                sizemode="area",
                sizeref=sizeref,
                sizemin=5,
                opacity=0.9,
                color=country_colors[country],
                line=dict(width=1, color="black")
            ),
            hovertemplate="<b>%{y}</b><br>Δ: $%{x}<extra></extra>"
        ))

        # Add average Δ line per country (subtle)
        avg_delta = group["Delta ($)"].mean()
        fig_both.add_vline(
            x=avg_delta,
            line=dict(color=country_colors[country], width=1, dash="dot"),
            opacity=0.3,
            layer="below",
            annotation_text=f"{country} Avg",
            annotation_position="top left",
            annotation_font=dict(size=10)
        )

# Final chart styling
fig_both.update_layout(
    title=f"💥 Baseline vs Scenario (Bubble Size: {size_option})",
    xaxis_title="Δ Cost-to-Serve ($)",
    yaxis_title="Part Number",
    height=700,
    showlegend=True,
    transition={"duration": 500}  # subtle animation
)

st.plotly_chart(fig_both, use_container_width=True)

if not scenario_triggered:
    st.caption("👀 Run a scenario to compare with baseline.")
else:
    st.caption("🔵 Bubbles = Baseline & Scenario. Dotted line = Avg Δ by country.")
