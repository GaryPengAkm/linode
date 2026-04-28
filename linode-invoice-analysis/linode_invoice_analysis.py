import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import numpy as np
import calendar  # Used to automatically calculate the number of days in a month

# --- Page Configuration ---
st.set_page_config(page_title="Linode invoice Comprehensive Analysis System", layout="wide")

# --- Custom CSS to make Tabs Larger, Bolder, and Black ---
st.markdown("""
    <style>
    /* Target the text inside the Streamlit tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 24px !important;       /* Larger text */
        font-weight: 900 !important;      /* Bolder text */
        color: #000000 !important;        /* Pure Black color */
    }
    
    /* Make the active tab's bottom border black as well for consistency */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom-color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Linode Invoice Analysis System ")

# --- Traffic Quota Mapping (Unit: GB) ---
PLAN_QUOTAS = {
    "Nanode 1GB": 1000, "Linode 2GB": 2000, "Linode 4GB": 4000, "Linode 8GB": 5000,
    "Linode 16GB": 8000, "Linode 24GB": 5000, "Linode 32GB": 16000, "Linode 48GB": 6000,
    "Linode 64GB": 20000, "Linode 90GB": 7000, "Dedicated 4GB": 4000, "Dedicated 8GB": 5000, 
    "Dedicated 16GB": 6000, "Dedicated 32GB": 7000, "Dedicated 64GB": 8000, "Dedicated 96GB": 9000, 
    "Dedicated 128GB": 10000, "Premium 4GB": 4000, "Premium 8GB": 5000, "Premium 16GB": 6000,
    "Premium 32GB": 7000, "Premium 64GB": 8000, "Premium 96GB": 9000, "Premium 128GB": 10000, 
    "Premium 256GB": 11000
}

def process_billing_file(file):
    """Parse the billing CSV file and extract model, region, and time info."""
    try:
        content = file.getvalue().decode('utf-8-sig', errors='ignore').splitlines()
        header_idx = 0
        # Find the header row dynamically
        for i, line in enumerate(content):
            if "Description" in line and ("From" in line or "Quantity" in line):
                header_idx = i
                break
        
        file.seek(0)
        df = pd.read_csv(file, encoding='utf-8-sig', skiprows=header_idx)
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # Keep empty Quantity values as NaN for proper logic handling later
        if 'Quantity' in df.columns:
            df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
        
        # Filter for instance rows only
        mask = df['Description'].str.startswith(('Nanode','Linode', 'Dedicated', 'Premium', 'G8'), na=False)
        inst_df = df[mask].copy()
        
        if not inst_df.empty:
            # Extract Model and Region from Description
            inst_df['Model'] = inst_df['Description'].apply(lambda x: x.split(' - ')[0].strip() if ' - ' in x else "Unknown")
            if 'Region' in inst_df.columns:
                inst_df['Region'] = inst_df['Region'].fillna("Unknown").str.strip()
            else:
                inst_df['Region'] = inst_df['Description'].apply(lambda x: x.split(' - ')[1].strip() if ' - ' in x else "Unknown")
            
            # Convert to datetime objects
            inst_df['From_DT'] = pd.to_datetime(inst_df['From'])
            inst_df['To_DT'] = pd.to_datetime(inst_df['To'])
            
            return df, inst_df
        return df, None
    except Exception as e:
        st.error(f"File parsing failed: {e}")
        return None, None

def get_hourly_stats(df, group_col, selected_items):
    """Calculate hourly active instances based on 'From' and 'To' times."""
    if df.empty: return pd.DataFrame()
    start_min, end_max = df['From_DT'].min().floor('H'), df['To_DT'].max().ceil('H')
    hourly_range = pd.date_range(start=start_min, end=end_max, freq='H')
    
    summary_data = []
    for hour in hourly_range:
        row = {'Time': hour}
        # Check if the machine was active during this specific hour
        current_online = df[(df['From_DT'] <= hour) & (df['To_DT'] > hour)]
        total_count = 0
        for item in selected_items:
            count = len(current_online[current_online[group_col] == item])
            row[item] = count
            total_count += count
        row['Total'] = total_count
        summary_data.append(row)
    return pd.DataFrame(summary_data)

def get_daily_avg_stats(hourly_df, items):
    """Calculate daily average machines (Sum of hours / 24, rounded down)."""
    if hourly_df.empty:
        return pd.DataFrame()
    
    df = hourly_df.copy()
    # Truncate time to the day level
    df['Date'] = df['Time'].dt.floor('D')
    
    cols_to_calc = [item for item in items if item in df.columns]
    if 'Total' in df.columns:
        cols_to_calc.append('Total')
        
    # Sum all active hours per day
    daily_sum = df.groupby('Date')[cols_to_calc].sum()
    
    # Core logic: sum of 24 hours divided by 24, rounded down
    daily_avg = np.floor(daily_sum / 24).astype(int)
    
    # Format back for plotting
    daily_avg = daily_avg.reset_index().rename(columns={'Date': 'Time'})
    return daily_avg

def draw_step_chart(df, items, title, y_label, start_dt, end_dt):
    """Draw an interactive step chart with optimized hover text."""
    fig = go.Figure()
    
    # Unified hover template: Shows only the name and value to keep it clean
    sub_hover_fmt = "<b>%{fullData.name}</b>: %{y}<extra></extra>"

    for item in items:
        if item in df.columns:
            fig.add_trace(go.Scatter(
                x=df['Time'], 
                y=df[item], 
                name=item, 
                mode='lines', 
                line=dict(shape='hv', width=1.5),
                hovertemplate=sub_hover_fmt
            ))
            
    fig.add_trace(go.Scatter(
        x=df['Time'], 
        y=df['Total'], 
        name="📈 Total", 
        mode='lines', 
        line=dict(shape='hv', width=3, dash='dash', color='black'),
        hovertemplate=sub_hover_fmt
    ))
    
    # Dynamic date format based on time range
    diff = (end_dt - start_dt).total_seconds()
    date_tick_format = "%m-%d %H:%M" if diff <= 172800 else "%Y-%m-%d"
    
    fig.update_layout(
        title=title,
        height=450,
        template="plotly_white",
        hovermode="x unified",  # Unified hover showing date once at the top
        xaxis=dict(
            tickformat=date_tick_format,
            hoverformat="%Y-%m-%d %H:%M",  # Force full Date/Time display on hover
            nticks=15,
            showgrid=True
        ),
        yaxis=dict(title=y_label)
    )
    return fig

def analyze_traffic_logic(df, inst_df, days_in_month):
    """Calculate Free Quota vs Actual Overage based on run hours."""
    total_hours = days_in_month * 24
    
    def calculate_row(row):
        model = row['Model']
        base_quota = PLAN_QUOTAS.get(model, 0)
        
        # Full Month: Quantity is NaN or 0
        if pd.isna(row['Quantity']) or row['Quantity'] == 0:
            return base_quota, "Full Month", 0
        else:
            # Partial Month: Prorated by run hours
            weighted_quota = (row['Quantity'] / total_hours) * base_quota
            return weighted_quota, "Partial Month", row['Quantity']

    inst_data = inst_df.copy()
    res = inst_data.apply(calculate_row, axis=1, result_type='expand')
    inst_data['Quota_GB'] = res[0]
    inst_data['Run_Type'] = res[1]
    inst_data['Used_Hours'] = res[2]

    # Detect Overage Traffic (Priority: Overage keyword, fallback: Transfer keyword)
    overage_mask = df['Description'].str.contains("Network Transfer Overage", case=False, na=False)
    overage_df = df[overage_mask]
    if overage_df.empty:
        overage_df = df[df['Description'].str.startswith("Network Transfer", na=False)]
    
    total_overage_gb = overage_df['Quantity'].fillna(0).sum()
    return inst_data, total_overage_gb

# --- Sidebar ---
st.sidebar.header("1. Data Import")
uploaded_file = st.sidebar.file_uploader("Upload Linode Bill (CSV)", type="csv")

if uploaded_file:
    full_df, instance_df = process_billing_file(uploaded_file)
    if instance_df is not None:
        
        # Create Tabs
        tab_qty, tab_traffic = st.tabs(["📉 Machine Quantity Stats", "🌐 Network Traffic Stats"])

        with tab_qty:
            all_models = sorted(instance_df['Model'].unique().tolist())
            all_regions = sorted(instance_df['Region'].unique().tolist())
            st.sidebar.divider()
            st.sidebar.subheader("2. Filter Configuration")
            selected_models = st.sidebar.multiselect("Model Filter", all_models, default=all_models)
            selected_regions = st.sidebar.multiselect("Region Filter", all_regions, default=all_regions)
            
            min_t, max_t = instance_df['From_DT'].min(), instance_df['To_DT'].max()
            c1, c2 = st.sidebar.columns(2)
            with c1: d_s = st.date_input("Start Date", min_t.date())
            with c2: d_e = st.date_input("End Date", max_t.date())
            start_dt = datetime.combine(d_s, time(0, 0))
            end_dt = datetime.combine(d_e, time(23, 59))
            
            if st.sidebar.button("🚀 Generate Cross-Statistics Charts", use_container_width=True, type="primary"):
                filtered_raw = instance_df[(instance_df['Model'].isin(selected_models)) & (instance_df['Region'].isin(selected_regions))]
                if not filtered_raw.empty:
                    # 1. Calculate base hourly data
                    df_m = get_hourly_stats(filtered_raw, 'Model', selected_models)
                    df_r = get_hourly_stats(filtered_raw, 'Region', selected_regions)
                    
                    # 2. Slice based on selected time range
                    final_m = df_m[(df_m['Time'] >= start_dt) & (df_m['Time'] <= end_dt)]
                    final_r = df_r[(df_r['Time'] >= start_dt) & (df_r['Time'] <= end_dt)]
                    
                    # --- Chart 1: Hourly Model Distribution ---
                    st.plotly_chart(draw_step_chart(final_m, selected_models, "Quantity Stats by Machine Type (Hourly Change)", "Online Quantity", start_dt, end_dt), use_container_width=True)
                    
                    # --- Chart 2: Daily Average Calculation ---
                    daily_avg_m = get_daily_avg_stats(final_m, selected_models)
                    if not daily_avg_m.empty:
                        st.plotly_chart(draw_step_chart(daily_avg_m, selected_models, "Daily Average Machine Quantity by Type (Rounded Down)", "Average Online Quantity", start_dt, end_dt), use_container_width=True)
                    
                    # --- Chart 3: Hourly Region Distribution ---
                    st.plotly_chart(draw_step_chart(final_r, selected_regions, "Quantity Stats by Region (Hourly Change)", "Online Quantity", start_dt, end_dt), use_container_width=True)
                else:
                    st.error("❌ No matching data found.")

        with tab_traffic:
            st.header("📊 Account Network Traffic Accounting (TB)")
            
            # Automatically identify the billing month and its length
            most_frequent_month = instance_df['From_DT'].dt.month.mode()[0]
            most_frequent_year = instance_df['From_DT'].dt.year.mode()[0]
            _, days_in_month = calendar.monthrange(most_frequent_year, most_frequent_month)
            
            st.success(f"📅 **Billing Period Identified**: This bill belongs to **{most_frequent_year}-{most_frequent_month:02d}**.")
            st.info(f"💡 **Auto-Accounting Reference**: This month has a total of **{days_in_month}** days.")
            
            if st.button("🔍 Start Traffic Analysis", type="primary", use_container_width=True):
                processed_inst, overage_gb = analyze_traffic_logic(full_df, instance_df, days_in_month)
                total_free_gb = processed_inst['Quota_GB'].sum()
                def to_tb(gb): return gb / 1000

                st.subheader("💡 Overall Analysis Summary")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Account Free Quota", f"{to_tb(total_free_gb):.2f} TB")
                m2.metric("Billed Overage Traffic", f"{to_tb(overage_gb):.2f} TB")
                m3.metric("Total Actual Traffic Consumed This Month", f"{to_tb(total_free_gb + overage_gb):.2f} TB")
                
                st.divider()
                cl, cr = st.columns(2)
                with cl:
                    st.subheader("✅ Full-Month Running Machines")
                    full_res = processed_inst[processed_inst['Run_Type'] == "Full Month"].groupby('Model').agg(
                        Quantity=('Model', 'count'),
                        Total_Free_Quota_TB=('Quota_GB', lambda x: to_tb(x.sum()))
                    )
                    st.table(full_res.style.format("{:.2f}", subset=['Total_Free_Quota_TB']))
                with cr:
                    st.subheader("⏳ Partial-Month Running Machines")
                    part_res = processed_inst[processed_inst['Run_Type'] == "Partial Month"].groupby('Model').agg(
                        Total_Used_Hours=('Used_Hours', 'sum'),
                        Prorated_Free_Quota_TB=('Quota_GB', lambda x: to_tb(x.sum()))
                    )
                    st.table(part_res.style.format({
                        "Total_Used_Hours": "{:.2f}", 
                        "Prorated_Free_Quota_TB": "{:.2f}"
                    }))
else:
    st.info("💡 Please upload the Linode billing CSV file in the left sidebar.")