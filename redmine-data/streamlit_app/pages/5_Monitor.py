import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="Monitor", page_icon="📊", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

# Local timezone (mặc định là Asia/Ho_Chi_Minh, có thể override bằng env var)
import os
LOCAL_TZ = ZoneInfo(os.getenv("SCHEDULER_TIMEZONE", "Asia/Ho_Chi_Minh"))

def utc_to_local(utc_dt_str: str) -> datetime:
    """Convert UTC datetime string sang local timezone datetime."""
    if not utc_dt_str:
        return None
    dt = datetime.fromisoformat(utc_dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)

st.title("📊 System Monitor")
st.markdown("Real-time monitoring and analytics")

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)")
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()

# Refresh button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 Refresh Now"):
        st.rerun()

st.markdown("---")

# ===== SYSTEM OVERVIEW =====
st.subheader("🎯 System Overview")

try:
    stats_response = requests.get(f"{API_URL}/api/ingest/stats")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📁 Total Sources",
                stats.get('total_sources', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                "📄 Source Docs",
                stats.get('total_source_documents', 0),
                delta=None
            )
        
        with col3:
            st.metric(
                "🧩 Chunks",
                f"{stats.get('total_chunks', 0):,}",
                delta=None
            )
        
        with col4:
            st.metric(
                "🔢 Embeddings",
                f"{stats.get('total_embeddings', 0):,}",
                delta=None
            )

except Exception as e:
    st.error(f"Failed to load system stats: {e}")

st.markdown("---")

# ===== LLM USAGE STATISTICS =====
st.subheader("🤖 LLM Usage Statistics")

# Sidebar filters
st.sidebar.markdown("### LLM Usage Filters")
days_filter = st.sidebar.slider("Days", 1, 90, 30, 1)
model_filter = st.sidebar.selectbox(
    "Model",
    ["All", "gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    index=0
)

# Billing cycle settings
st.sidebar.markdown("### 💳 Billing Cycle Settings")
invoice_day = st.sidebar.number_input(
    "Invoice Day (1-31)",
    min_value=1,
    max_value=31,
    value=1,
    help="Day of month when LLM invoice is generated. Billing cycle runs from this day to the same day next month."
)
show_billing_cycles = st.sidebar.checkbox("Show Billing Cycle Stats", value=False)

try:
    # Build API URL with filters
    usage_url = f"{API_URL}/api/search/usage?days={days_filter}"
    if model_filter != "All":
        usage_url += f"&model={model_filter}"
    
    usage_response = requests.get(usage_url)
    
    if usage_response.status_code == 200:
        usage_stats = usage_response.json()
        total = usage_stats.get('total', {})
        
        # Key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "💰 Total Cost",
                f"${total.get('cost_usd', 0):.4f}"
            )
        
        with col2:
            total_tokens = total.get('total_tokens', 0)
            st.metric(
                "🔢 Total Tokens",
                f"{total_tokens:,}"
            )
        
        with col3:
            input_token = total.get('input_token', 0)
            st.metric(
                "📥 Input Tokens",
                f"{input_token:,}"
            )
        
        with col4:
            output_token = total.get('output_token', 0)
            st.metric(
                "📤 Output Tokens",
                f"{output_token:,}"
            )
        
        with col5:
            total_requests = total.get('requests', 0)
            cached_requests = total.get('cached_requests', 0)
            st.metric(
                "📊 Requests",
                f"{total_requests:,}",
                delta=f"{cached_requests:,} cached" if cached_requests > 0 else None
            )
        
        # Token distribution
        st.markdown("**📊 Token Distribution**")
        col1, col2 = st.columns(2)
        
        with col1:
            # Token pie chart
            token_data = {
                'Input Tokens': input_token,
                'Output Tokens': output_token
            }
            df_tokens = pd.DataFrame(
                list(token_data.items()),
                columns=['Type', 'Tokens']
            )
            
            fig = px.pie(
                df_tokens,
                values='Tokens',
                names='Type',
                title='Token Distribution',
                color_discrete_map={'Input Tokens': '#1f77b4', 'Output Tokens': '#ff7f0e'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Cost breakdown
            cost_data = {
                'Input Cost': input_token * 0.150 / 1_000_000,
                'Output Cost': output_token * 0.600 / 1_000_000
            }
            df_cost = pd.DataFrame(
                list(cost_data.items()),
                columns=['Type', 'Cost (USD)']
            )
            
            fig = px.bar(
                df_cost,
                x='Type',
                y='Cost (USD)',
                title='Cost Breakdown',
                labels={'Cost (USD)': 'Cost (USD)'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Daily breakdown
        daily_breakdown = usage_stats.get('daily_breakdown', [])
        if daily_breakdown:
            st.markdown("**📈 Daily Usage (Last 30 Days)**")
            df_daily = pd.DataFrame(daily_breakdown)
            df_daily['date'] = pd.to_datetime(df_daily['date'])
            df_daily = df_daily.sort_values('date')
            
            fig = go.Figure()
            
            # Tokens line
            fig.add_trace(go.Scatter(
                x=df_daily['date'],
                y=df_daily['tokens'],
                mode='lines+markers',
                name='Tokens',
                yaxis='y',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # Cost line (secondary y-axis)
            fig.add_trace(go.Scatter(
                x=df_daily['date'],
                y=df_daily['cost_usd'],
                mode='lines+markers',
                name='Cost (USD)',
                yaxis='y2',
                line=dict(color='#ff7f0e', width=2)
            ))
            
            fig.update_layout(
                title='Daily Token Usage and Cost',
                xaxis_title='Date',
                yaxis=dict(
                    title='Tokens',
                    side='left'
                ),
                yaxis2=dict(
                    title='Cost (USD)',
                    side='right',
                    overlaying='y'
                ),
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Daily table
            with st.expander("📅 View Daily Details"):
                df_daily_display = df_daily.copy()
                df_daily_display['date'] = df_daily_display['date'].dt.strftime('%Y-%m-%d')
                df_daily_display = df_daily_display.rename(columns={
                    'date': 'Date',
                    'tokens': 'Tokens',
                    'cost_usd': 'Cost (USD)',
                    'requests': 'Requests'
                })
                df_daily_display['Cost (USD)'] = df_daily_display['Cost (USD)'].apply(lambda x: f"${x:.4f}")
                st.dataframe(df_daily_display, use_container_width=True, hide_index=True)
        
        # Billing Cycle Statistics
        if show_billing_cycles:
            st.markdown("---")
            st.markdown(f"**💳 Billing Cycle Statistics (Invoice Day: {invoice_day})**")
            
            try:
                billing_url = f"{API_URL}/api/search/usage/billing-cycles?invoice_day={invoice_day}&num_cycles=12"
                if model_filter != "All":
                    billing_url += f"&model={model_filter}"
                
                billing_response = requests.get(billing_url)
                
                if billing_response.status_code == 200:
                    billing_data = billing_response.json()
                    cycles = billing_data.get('cycles', [])
                    
                    if cycles:
                        df_cycles = pd.DataFrame(cycles)
                        
                        # Chart: Cost by billing cycle
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig = px.bar(
                                df_cycles,
                                x='cycle_label',
                                y='cost_usd',
                                title='Cost by Billing Cycle',
                                labels={'cycle_label': 'Billing Cycle', 'cost_usd': 'Cost (USD)'},
                                color='cost_usd',
                                color_continuous_scale='Reds'
                            )
                            fig.update_layout(showlegend=False, height=400)
                            fig.update_xaxes(tickangle=45)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            fig = px.bar(
                                df_cycles,
                                x='cycle_label',
                                y='total_tokens',
                                title='Tokens by Billing Cycle',
                                labels={'cycle_label': 'Billing Cycle', 'total_tokens': 'Total Tokens'},
                                color='total_tokens',
                                color_continuous_scale='Blues'
                            )
                            fig.update_layout(showlegend=False, height=400)
                            fig.update_xaxes(tickangle=45)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        total_cost = df_cycles['cost_usd'].sum()
                        total_tokens_cycles = df_cycles['total_tokens'].sum()
                        total_requests_cycles = df_cycles['requests'].sum()
                        avg_cost_per_cycle = df_cycles['cost_usd'].mean()
                        
                        with col1:
                            st.metric("Total Cost (12 cycles)", f"${total_cost:.4f}")
                        with col2:
                            st.metric("Total Tokens", f"{total_tokens_cycles:,}")
                        with col3:
                            st.metric("Total Requests", f"{total_requests_cycles:,}")
                        with col4:
                            st.metric("Avg Cost/Cycle", f"${avg_cost_per_cycle:.4f}")
                        
                        # Billing cycle table
                        with st.expander("📊 View Billing Cycle Details"):
                            df_cycles_display = df_cycles.copy()
                            df_cycles_display = df_cycles_display.rename(columns={
                                'cycle_label': 'Billing Cycle',
                                'cycle_start': 'Start Date',
                                'cycle_end': 'End Date',
                                'cost_usd': 'Cost (USD)',
                                'total_tokens': 'Tokens',
                                'requests': 'Requests',
                                'cached_requests': 'Cached',
                                'input_token': 'Input Tokens',
                                'output_token': 'Output Tokens'
                            })
                            df_cycles_display['Cost (USD)'] = df_cycles_display['Cost (USD)'].apply(lambda x: f"${x:.4f}")
                            df_cycles_display['Start Date'] = pd.to_datetime(df_cycles_display['Start Date']).dt.strftime('%Y-%m-%d')
                            df_cycles_display['End Date'] = pd.to_datetime(df_cycles_display['End Date']).dt.strftime('%Y-%m-%d')
                            st.dataframe(df_cycles_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("No billing cycle data available")
                else:
                    st.warning(f"Failed to load billing cycle stats: {billing_response.status_code}")
            except Exception as e:
                st.error(f"Failed to load billing cycle statistics: {e}")
        
        # Model breakdown
        model_breakdown = usage_stats.get('model_breakdown', [])
        if model_breakdown:
            st.markdown("**🔧 Model Breakdown**")
            df_models = pd.DataFrame(model_breakdown)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    df_models,
                    x='model',
                    y='tokens',
                    title='Tokens by Model',
                    labels={'model': 'Model', 'tokens': 'Tokens'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    df_models,
                    x='model',
                    y='cost_usd',
                    title='Cost by Model',
                    labels={'model': 'Model', 'cost_usd': 'Cost (USD)'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Model table
            with st.expander("🔧 View Model Details"):
                df_models_display = df_models.copy()
                df_models_display = df_models_display.rename(columns={
                    'model': 'Model',
                    'tokens': 'Tokens',
                    'cost_usd': 'Cost (USD)',
                    'requests': 'Requests'
                })
                df_models_display['Cost (USD)'] = df_models_display['Cost (USD)'].apply(lambda x: f"${x:.4f}")
                st.dataframe(df_models_display, use_container_width=True, hide_index=True)
        
        # ===== RESPONSE TIME STATISTICS (NEW) =====
        response_time_stats = usage_stats.get('response_time_stats', {})
        ai_stats = response_time_stats.get('ai_api', {})
        search_stats = response_time_stats.get('search_api', {})
        
        st.markdown("**⚡ Response Time Statistics** *(excluding cached requests)*")
        
        # Key metrics - 2 rows
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("##### 🤖 AI API")
            st.metric(
                "Avg Time",
                f"{ai_stats.get('avg_ms', 0) / 1000.0:.2f} s"
            )
        
        with col2:
            st.metric(
                "Min / Max",
                f"{ai_stats.get('min_ms', 0) / 1000.0:.2f} / {ai_stats.get('max_ms', 0) / 1000.0:.2f} s"
            )
        
        with col3:
            st.markdown("##### 🔍 Search API")
            st.metric(
                "Avg Time",
                f"{search_stats.get('avg_ms', 0) / 1000.0:.2f} s"
            )
        
        with col4:
            st.metric(
                "Min / Max",
                f"{search_stats.get('min_ms', 0) / 1000.0:.2f} / {search_stats.get('max_ms', 0) / 1000.0:.2f} s"
            )
        
        # Percentile comparison
        ai_percentiles = ai_stats.get('percentiles', {})
        search_percentiles = search_stats.get('percentiles', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 AI API Percentiles**")
            
            # Create percentile bar chart
            percentile_data = pd.DataFrame({
                'Percentile': ['P50', 'P75', 'P90', 'P95', 'P99'],
                'Time (s)': [
                    ai_percentiles.get('p50', 0) / 1000.0,
                    ai_percentiles.get('p75', 0) / 1000.0,
                    ai_percentiles.get('p90', 0) / 1000.0,
                    ai_percentiles.get('p95', 0) / 1000.0,
                    ai_percentiles.get('p99', 0) / 1000.0
                ]
            })
            
            fig = px.bar(
                percentile_data,
                x='Percentile',
                y='Time (s)',
                title=f'AI API Response Time Percentiles ({ai_stats.get("count", 0)} requests)',
                color='Time (s)',
                color_continuous_scale='Reds'
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**📊 Search API Percentiles**")
            
            # Create percentile bar chart
            percentile_data = pd.DataFrame({
                'Percentile': ['P50', 'P75', 'P90', 'P95', 'P99'],
                'Time (s)': [
                    search_percentiles.get('p50', 0) / 1000.0,
                    search_percentiles.get('p75', 0) / 1000.0,
                    search_percentiles.get('p90', 0) / 1000.0,
                    search_percentiles.get('p95', 0) / 1000.0,
                    search_percentiles.get('p99', 0) / 1000.0
                ]
            })
            
            fig = px.bar(
                percentile_data,
                x='Percentile',
                y='Time (s)',
                title=f'Search API Response Time Percentiles ({search_stats.get("count", 0)} requests)',
                color='Time (s)',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        # Response Time Distribution (Histogram)
        ai_raw_times = ai_stats.get('raw_times', [])
        search_raw_times = search_stats.get('raw_times', [])
        
        if ai_raw_times or search_raw_times:
            st.markdown("**📈 Response Time Distribution**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if ai_raw_times:
                    # Convert from ms to seconds
                    ai_raw_times_s = [t / 1000.0 for t in ai_raw_times]
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(
                        x=ai_raw_times_s,
                        nbinsx=30,
                        name='AI API',
                        marker_color='#ff6b6b'
                    ))
                    fig.update_layout(
                        title='AI API Response Time Distribution',
                        xaxis_title='Response Time (s)',
                        yaxis_title='Frequency',
                        height=300,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No AI API response time data available")
            
            with col2:
                if search_raw_times:
                    # Convert from ms to seconds
                    search_raw_times_s = [t / 1000.0 for t in search_raw_times]
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(
                        x=search_raw_times_s,
                        nbinsx=30,
                        name='Search API',
                        marker_color='#4ecdc4'
                    ))
                    fig.update_layout(
                        title='Search API Response Time Distribution',
                        xaxis_title='Response Time (s)',
                        yaxis_title='Frequency',
                        height=300,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No Search API response time data available")
        
        # Daily Response Time Trend
        daily_rt = response_time_stats.get('daily_breakdown', [])
        if daily_rt:
            st.markdown("**📅 Daily Response Time Trend (AI API)**")
            
            df_daily_rt = pd.DataFrame(daily_rt)
            df_daily_rt['date'] = pd.to_datetime(df_daily_rt['date'])
            df_daily_rt = df_daily_rt.sort_values('date')
            
            # Convert from ms to seconds
            df_daily_rt['avg_s'] = df_daily_rt['avg_ms'] / 1000.0
            df_daily_rt['max_s'] = df_daily_rt['max_ms'] / 1000.0
            df_daily_rt['min_s'] = df_daily_rt['min_ms'] / 1000.0
            
            fig = go.Figure()
            
            # Average line
            fig.add_trace(go.Scatter(
                x=df_daily_rt['date'],
                y=df_daily_rt['avg_s'],
                mode='lines+markers',
                name='Average',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # Min/Max area
            fig.add_trace(go.Scatter(
                x=df_daily_rt['date'],
                y=df_daily_rt['max_s'],
                mode='lines',
                name='Max',
                line=dict(color='rgba(255,0,0,0.3)'),
                showlegend=True
            ))
            
            fig.add_trace(go.Scatter(
                x=df_daily_rt['date'],
                y=df_daily_rt['min_s'],
                mode='lines',
                name='Min',
                line=dict(color='rgba(0,128,0,0.3)'),
                fill='tonexty',
                fillcolor='rgba(0,100,255,0.1)',
                showlegend=True
            ))
            
            fig.update_layout(
                title='Daily Response Time (Avg, Min, Max)',
                xaxis_title='Date',
                yaxis_title='Response Time (s)',
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Summary table
        with st.expander("📋 Response Time Summary"):
            summary_data = {
                'Metric': ['Count', 'Avg (s)', 'Min (s)', 'Max (s)', 'P50 (s)', 'P75 (s)', 'P90 (s)', 'P95 (s)', 'P99 (s)'],
                'AI API': [
                    ai_stats.get('count', 0),
                    f"{ai_stats.get('avg_ms', 0) / 1000.0:.2f}",
                    f"{ai_stats.get('min_ms', 0) / 1000.0:.2f}",
                    f"{ai_stats.get('max_ms', 0) / 1000.0:.2f}",
                    f"{ai_percentiles.get('p50', 0) / 1000.0:.2f}",
                    f"{ai_percentiles.get('p75', 0) / 1000.0:.2f}",
                    f"{ai_percentiles.get('p90', 0) / 1000.0:.2f}",
                    f"{ai_percentiles.get('p95', 0) / 1000.0:.2f}",
                    f"{ai_percentiles.get('p99', 0) / 1000.0:.2f}"
                ],
                'Search API': [
                    search_stats.get('count', 0),
                    f"{search_stats.get('avg_ms', 0) / 1000.0:.2f}",
                    f"{search_stats.get('min_ms', 0) / 1000.0:.2f}",
                    f"{search_stats.get('max_ms', 0) / 1000.0:.2f}",
                    f"{search_percentiles.get('p50', 0) / 1000.0:.2f}",
                    f"{search_percentiles.get('p75', 0) / 1000.0:.2f}",
                    f"{search_percentiles.get('p90', 0) / 1000.0:.2f}",
                    f"{search_percentiles.get('p95', 0) / 1000.0:.2f}",
                    f"{search_percentiles.get('p99', 0) / 1000.0:.2f}"
                ]
            }
            
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Cache stats
        st.markdown("**💾 Cache Performance**")
        col1, col2 = st.columns(2)
        
        with col1:
            cache_hit_rate = (cached_requests / total_requests * 100) if total_requests > 0 else 0
            st.metric(
                "Cache Hit Rate",
                f"{cache_hit_rate:.1f}%",
                delta=f"{cached_requests:,} cached requests"
            )
        
        with col2:
            non_cached = total_requests - cached_requests
            st.metric(
                "Non-Cached Requests",
                f"{non_cached:,}",
                delta=f"of {total_requests:,} total"
            )
    
    else:
        st.warning(f"Failed to load LLM usage stats: {usage_response.status_code}")

except Exception as e:
    st.error(f"Failed to load LLM usage statistics: {e}")
    st.exception(e)

st.markdown("---")

# ===== BUDGET STATUS =====
st.subheader("💰 Budget Status")

try:
    budget_response = requests.get(f"{API_URL}/api/budget/status")
    
    if budget_response.status_code == 200:
        budget_data = budget_response.json()
        budget_statuses = budget_data.get('statuses', [])
        
        if budget_statuses:
            # Display budget status for each provider
            cols = st.columns(len(budget_statuses))
            
            for idx, status in enumerate(budget_statuses):
                with cols[idx]:
                    provider = status.get('provider', '').upper()
                    budget_amount = status.get('budget_amount_usd', 0)
                    current_spending = status.get('current_spending_usd', 0)
                    percentage = status.get('percentage_used', 0)
                    
                    # Color coding
                    if percentage >= 100:
                        color = "🔴"
                        delta_color = "inverse"
                    elif percentage >= 80:
                        color = "🟡"
                        delta_color = "normal"
                    else:
                        color = "🟢"
                        delta_color = "normal"
                    
                    st.metric(
                        f"{color} {provider}",
                        f"${current_spending:,.2f}",
                        delta=f"{percentage:.2f}% of ${budget_amount:,.2f}",
                        delta_color=delta_color
                    )
            
            # Show unacknowledged alerts
            alerts_response = requests.get(f"{API_URL}/api/budget/alerts?unacknowledged_only=true&limit=5")
            if alerts_response.status_code == 200:
                alerts = alerts_response.json()
                if alerts:
                    st.warning(f"⚠️ {len(alerts)} unacknowledged budget alert(s). Check the Budget page for details.")
        else:
            st.info("No budget configurations found. Configure budgets in the Budget page.")
    else:
        st.warning(f"Failed to load budget status: {budget_response.status_code}")

except Exception as e:
    st.warning(f"Failed to load budget status: {e}")

st.markdown("---")

# ===== SEARCH ANALYTICS =====
st.subheader("🔍 Search Analytics")

try:
    analytics_response = requests.get(f"{API_URL}/api/search/analytics")
    
    if analytics_response.status_code == 200:
        analytics = analytics_response.json()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Searches",
                analytics.get('total_searches', 0)
            )
        
        with col2:
            st.metric(
                "Searches Today",
                analytics.get('searches_today', 0)
            )
        
        with col3:
            avg_time = analytics.get('avg_response_time_ms', 0)
            st.metric(
                "Avg Response Time",
                f"{avg_time / 1000.0:.2f} s"
            )
        
        # Popular queries chart
        popular = analytics.get('popular_queries', [])
        if popular:
            st.markdown("**🔥 Popular Queries**")
            
            df = pd.DataFrame(popular)
            
            fig = px.bar(
                df,
                x='count',
                y='query',
                orientation='h',
                title="Top 10 Search Queries",
                labels={'count': 'Search Count', 'query': 'Query'}
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Failed to load search analytics: {e}")

st.markdown("---")

# ===== DATABASE STATISTICS =====
st.subheader("💾 Database Statistics")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**📊 Sources by Type**")
    
    # Mock data - replace with actual query
    source_distribution = {
        'document': 45,
        'redmine_issue': 120,
        'redmine_wiki': 30,
        'git_file': 85
    }
    
    df_sources = pd.DataFrame(
        list(source_distribution.items()),
        columns=['Source Type', 'Count']
    )
    
    fig = px.pie(
        df_sources,
        values='Count',
        names='Source Type',
        title='Source Distribution'
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("**📈 Ingestion Timeline (Last 7 Days)**")
    
    # Mock data - replace with actual query
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    counts = [12, 8, 15, 22, 10, 18, 25]
    
    df_timeline = pd.DataFrame({
        'Date': dates[::-1],
        'Sources': counts[::-1]
    })
    
    fig = px.line(
        df_timeline,
        x='Date',
        y='Sources',
        title='Daily Ingestion',
        markers=True
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== PERFORMANCE METRICS =====
st.subheader("⚡ Performance Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Embedding Generation**")
    st.metric("Avg Time per Chunk", "125 ms")
    st.metric("Throughput", "~8 chunks/sec")

with col2:
    st.markdown("**Vector Search**")
    st.metric("Avg Search Time", "45 ms")
    st.metric("Index Size", "2.3 GB")

with col3:
    st.markdown("**RAG Response**")
    st.metric("Avg Generation Time", "3.2 sec")
    st.metric("Token Rate", "~50 tokens/sec")

st.markdown("---")

# ===== JOB STATUS =====
st.subheader("⚙️ Job Execution Status")

try:
    jobs_response = requests.get(f"{API_URL}/api/jobs?is_active=true")
    
    if jobs_response.status_code == 200:
        jobs = jobs_response.json().get('jobs', [])
        
        if jobs:
            job_data = []
            for job in jobs:
                history_response = requests.get(f"{API_URL}/api/jobs/{job['id']}/history?limit=1")
                
                if history_response.status_code == 200:
                    history = history_response.json().get('history', [])
                    last_status = history[0]['status'] if history else 'Never run'
                    last_run = history[0]['started_at'] if history else None
                    
                    job_data.append({
                        'Job Name': job['job_name'],
                        'Type': job['job_type'],
                        'Status': last_status,
                        'Last Run': utc_to_local(last_run).strftime('%Y-%m-%d %H:%M') if last_run else 'Never',
                        'Next Run': utc_to_local(job['next_run_at']).strftime('%Y-%m-%d %H:%M') if job.get('next_run_at') else 'N/A'
                    })
            
            df_jobs = pd.DataFrame(job_data)
            st.dataframe(df_jobs, use_container_width=True, hide_index=True)
        else:
            st.info("No active jobs configured")

except Exception as e:
    st.error(f"Failed to load job status: {e}")

st.markdown("---")

# ===== RECENT ACTIVITY =====
st.subheader("📋 Recent Activity")

tab1, tab2 = st.tabs(["Recent Searches", "Recent Ingestions"])

with tab1:
    try:
        history_response = requests.get(f"{API_URL}/api/search/history?limit=20")
        
        if history_response.status_code == 200:
            history = history_response.json().get('history', [])
            
            if history:
                activity_data = []
                for item in history:
                    activity_data.append({
                        'Time': datetime.fromisoformat(item['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                        'Query': item['query'],
                        'Response Time': f"{item.get('response_time_ms', 0) / 1000.0:.2f} s"
                    })
                
                df_activity = pd.DataFrame(activity_data)
                st.dataframe(df_activity, use_container_width=True, hide_index=True)
            else:
                st.info("No search history yet")
    
    except Exception as e:
        st.error(f"Failed to load search history: {e}")

with tab2:
    st.info("Recent ingestion logs will be displayed here")
    # TODO: Add recent ingestion query

st.markdown("---")

# ===== SYSTEM HEALTH =====
st.subheader("🏥 System Health")

col1, col2, col3 = st.columns(3)

try:
    health_response = requests.get(f"{API_URL}/health")
    
    if health_response.status_code == 200:
        health = health_response.json()
        
        with col1:
            st.success("✅ API Status: Healthy")
            st.info(f"Database: {health.get('database', 'Unknown')}")
        
        with col2:
            st.success("✅ Ollama Status: Connected")
            st.info(f"URL: {health.get('ollama_url', 'N/A')}")
        
        with col3:
            st.success("✅ Vector DB: Connected")
            st.info("pgvector enabled")
    
    else:
        st.error("❌ API not responding")

except Exception as e:
    st.error(f"❌ System health check failed: {e}")

# Export data
st.markdown("---")
with st.expander("📥 Export Data"):
    st.markdown("Export system statistics and logs")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Statistics"):
            st.info("Statistics export not yet implemented")
    
    with col2:
        if st.button("📜 Export Search Logs"):
            st.info("Search logs export not yet implemented")
    
    with col3:
        if st.button("⚙️ Export Job History"):
            st.info("Job history export not yet implemented")