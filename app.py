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



# ------------------ Load Tariff Data ------------------
tariff_data_path = "Tariff Rate by Year (1).csv"
@st.cache_data
def load_tariff_data():
    return pd.read_csv(tariff_data_path)

historical_df = load_tariff_data()

# ------------------ Landing Section ------------------
st.title("📊 Tariff Impact & Supply Chain Simulator")

# ------------------ Sidebar: Scenario Builder ------------------
st.sidebar.title("🧪 Scenario Builder")
st.sidebar.markdown("Adjust tariffs by source country")

# Sidebar: Tariff sliders by country
countries = sorted(df["Source Country"].unique())
scenario_tariffs = {
    country: st.sidebar.slider(f"{country} Tariff %", 0, 100, int(df[df["Source Country"] == country]["Tariff Rate (%)"].mean()))
    for country in countries
}

# Sidebar: Bubble size and grouping selectors
st.sidebar.markdown("### Bubble Size Metric")
size_option = st.sidebar.selectbox("Choose what bubble size represents:", [
    "Total Inventory", "Δ Cost ($)", "Δ Cost (%)"
])

# Sidebar: NEW grouping option
st.sidebar.markdown("### Group Data By")
group_by_option = st.sidebar.radio("View data grouped by:", ["Part Number", "Part Name", "Commodity"])
group_field = {
    "Part Number": "Part Number",
    "Part Name": "Description",  # Renaming 'Description' to 'Part Name'
    "Commodity": "Commodity"
}[group_by_option]


# Always group data to build compare_df (used in bar chart, table, bubble chart)
group_cols = [group_field, "Source Country"]

compare_df = df_scenario.groupby(group_cols).agg({
    "Scenario CTS": "sum",
    "Total Cost to Serve": "sum",
    "Total Inventory Position": "sum",
    "Tariff Rate (%)": "mean"
}).reset_index()

compare_df["Delta ($)"] = compare_df["Scenario CTS"] - compare_df["Total Cost to Serve"]
compare_df["Delta (%)"] = (compare_df["Delta ($)"] / compare_df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)

# This powers bubble chart and bar chart
bubble_df = compare_df.copy()

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

    # Use selected group_field for grouping
    group_cols = [group_field, "Source Country"]

    # ------------------ Scenario Comparison Table ------------------
    compare_df = df_scenario.groupby(group_cols).agg({
        "Scenario CTS": "sum",
        "Total Cost to Serve": "sum",
        "Total Inventory Position": "sum"
    }).reset_index()

    compare_df["Delta ($)"] = compare_df["Scenario CTS"] - compare_df["Total Cost to Serve"]
    compare_df["Delta (%)"] = (compare_df["Delta ($)"] / compare_df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)


    # # st.subheader("🔁 Scenario Comparison vs Baseline")
    # compare_df = df_scenario[["Part Number", "Description", "Source Country"]].copy()
    # compare_df["New Tariff Rate"] = df_scenario["Tariff Rate (%)"]
    # compare_df["New CTS"] = df_scenario["Scenario CTS"]
    # compare_df["Total Cost to Serve"] = df["Total Cost to Serve"]
    # compare_df["Delta ($)"] = compare_df["New CTS"] - compare_df["Total Cost to Serve"]
    # compare_df["Delta (%)"] = (compare_df["Delta ($)"] / compare_df["Total Cost to Serve"]) * 100

    # st.dataframe(compare_df, use_container_width=True)

    # ------------------ Bar Chart of Δ ------------------
    fig_bar = px.bar(compare_df.sort_values("Delta ($)", ascending=False),
                 x=group_field, y="Delta ($)", color="Source Country",
                 title=f"{group_by_option}s with Highest Cost Impact")


# ------------------ Combined Animated Bubble Chart ------------------
# st.subheader("📍 Cost Impact Bubble Chart: Baseline + Scenario")


# Determine whether a real scenario has been run
scenario_triggered = (
    "Scenario CTS" in df_scenario.columns
    and not df_scenario["Scenario CTS"].equals(df["Total Cost to Serve"]))

# ------------------ Grouping Logic ------------------
if group_field != "Part Number":
    grouped_df = df_scenario.groupby([group_field, "Source Country"]).agg({
        "Scenario CTS": "sum",
        "Total Cost to Serve": "sum",
        "Total Inventory Position": "sum"
    }).reset_index()

    grouped_df["Delta ($)"] = grouped_df["Scenario CTS"] - grouped_df["Total Cost to Serve"]
    grouped_df["Delta (%)"] = (grouped_df["Delta ($)"] / grouped_df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)

    bubble_df = grouped_df.rename(columns={group_field: "Group Label"})
else:
    df_scenario["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
    df_scenario["Delta (%)"] = (df_scenario["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
    bubble_df = df_scenario.copy()
    bubble_df["Group Label"] = df_scenario["Part Number"]


# # === New: Add toggle to group by Part or Commodity ===
# group_by_option = st.sidebar.radio("Group bubble chart by:", ["Part Number", "Commodity"])
# group_field = "Part Number" if group_by_option == "Part Number" else "Commodity"

# # Group data accordingly
# if group_field == "Commodity":
#     grouped_df = df_scenario.groupby("Commodity").agg({
#         "Scenario CTS": "sum",
#         "Total Cost to Serve": "sum",
#         "Total Inventory Position": "sum",
#         "Source Country": lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"
#     }).reset_index()

#     grouped_df["Delta ($)"] = grouped_df["Scenario CTS"] - grouped_df["Total Cost to Serve"]
#     grouped_df["Delta (%)"] = (grouped_df["Delta ($)"] / grouped_df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
#     bubble_df = grouped_df
#     bubble_df[group_field] = bubble_df["Commodity"]
# else:
#     # Keep default part-level granularity
#     bubble_df = df_scenario.copy()
#     bubble_df["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
#     bubble_df["Delta (%)"] = (bubble_df["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)
#     bubble_df[group_field] = df["Part Number"]

# Compute deltas and scenario stats if simulation was run
bubble_df = compare_df.copy()
bubble_df["Group Label"] = bubble_df[group_field]

# bubble_df = df_scenario.copy()
# bubble_df["Delta ($)"] = df_scenario["Scenario CTS"] - df["Total Cost to Serve"]
# bubble_df["Delta (%)"] = (bubble_df["Delta ($)"] / df["Total Cost to Serve"]).replace([np.inf, -np.inf], 0).fillna(0)

# bubble_df["Part Number"] = df["Part Number"]

# Update axis and bubble grouping dynamically
y_values = bubble_df[group_field]
# In all go.Scatter calls, use:
y=y_values
# Also update y-axis label in layout:
yaxis_title=group_field

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

# Build the chart 
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
    height=500,
    showlegend=True,
    transition={"duration": 1000}  # subtle animation
)

st.plotly_chart(fig_both, use_container_width=True)

if not scenario_triggered:
    st.caption("👀 Run a scenario to compare with baseline.")
else:
    st.caption("🔵 Bubbles = Baseline & Scenario. Dotted line = Avg Δ by country.")


#=== Container-based Fixed Dashboard ===

# Simulation status
scenario_triggered = (
    "Scenario CTS" in df_scenario.columns
    and not df_scenario["Scenario CTS"].equals(df["Total Cost to Serve"])
)


# st.subheader("📍 Bubble Chart: Baseline + Scenario")
# st.plotly_chart(fig_both, use_container_width=True)

# Create the 2x2 grid containers
top_row = st.container()
bottom_row = st.container()

# ---------------- TOP ROW ----------------
with top_row:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Baseline Supply Chain Inputs")
        st.dataframe(df, use_container_width=True, height=400)

    with col2:
        if scenario_triggered and 'fig_bar' in locals():
            st.subheader("📦 Delta table")
            st.dataframe(compare_df, use_container_width=True)
        else:
            st.info("Run a scenario to view Delta table.")

# ---------------- BOTTOM ROW ----------------
with bottom_row:
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("🔁 Scenario Comparison Bar Chart")
        if scenario_triggered and 'fig_bar' in locals():
            st.plotly_chart(fig_bar, use_container_width=True, height=400)
        else:
            st.info("Run a scenario to view comparison bar chart.")

    with col4:
        st.subheader("🧭 Placeholder")
        st.markdown("Reserved for future modules or simulation results.")
