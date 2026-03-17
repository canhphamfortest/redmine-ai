import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="Budget", page_icon="💰", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

st.title("💰 Budget Management")
st.markdown("Configure and monitor LLM usage budgets with alerts")

# Initialize session state
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "status"  # "status", "config", "alerts"

# Sidebar navigation
st.sidebar.markdown("### Navigation")
view_mode = st.sidebar.selectbox(
    "View",
    ["Budget Status", "Configuration", "Alerts"],
    index=0 if st.session_state.view_mode == "status" else 1 if st.session_state.view_mode == "config" else 2
)

if view_mode == "Budget Status":
    st.session_state.view_mode = "status"
elif view_mode == "Configuration":
    st.session_state.view_mode = "config"
else:
    st.session_state.view_mode = "alerts"

# ===== BUDGET STATUS =====
if st.session_state.view_mode == "status":
    st.subheader("📊 Budget Status Dashboard")
    
    try:
        response = requests.get(f"{API_URL}/api/budget/status")
        
        if response.status_code == 200:
            data = response.json()
            statuses = data.get('statuses', [])
            
            if not statuses:
                st.info("No budget configurations found. Create a budget config in the Configuration tab.")
            else:
                # Display status for each provider
                for status in statuses:
                    provider = status.get('provider', '').upper()
                    budget_amount = status.get('budget_amount_usd', 0)
                    current_spending = status.get('current_spending_usd', 0)
                    remaining = status.get('remaining_budget_usd', 0)
                    percentage = status.get('percentage_used', 0)
                    cycle_start = status.get('billing_cycle_start', '')
                    cycle_end = status.get('billing_cycle_end', '')
                    thresholds = status.get('alert_thresholds', [])
                    
                    with st.container():
                        st.markdown(f"### {provider} Budget")
                        
                        # Progress bar with color coding
                        if percentage >= 100:
                            color = "red"
                            status_text = "⚠️ EXCEEDED"
                        elif percentage >= 80:
                            color = "orange"
                            status_text = "⚠️ WARNING"
                        else:
                            color = "green"
                            status_text = "✅ OK"
                        
                        st.markdown(f"**Status:** {status_text}")
                        
                        # Progress bar
                        st.progress(percentage / 100)
                        st.markdown(f"**Usage:** {percentage:.2f}%")
                        
                        # Metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Budget Amount",
                                f"${budget_amount:,.2f}"
                            )
                        
                        with col2:
                            st.metric(
                                "Current Spending",
                                f"${current_spending:,.2f}",
                                delta=f"{percentage:.2f}%"
                            )
                        
                        with col3:
                            st.metric(
                                "Remaining",
                                f"${remaining:,.2f}"
                            )
                        
                        with col4:
                            # Billing cycle info
                            try:
                                start_dt = datetime.fromisoformat(cycle_start.replace('Z', '+00:00'))
                                end_dt = datetime.fromisoformat(cycle_end.replace('Z', '+00:00'))
                                st.markdown(f"**Cycle:** {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
                            except:
                                st.markdown(f"**Cycle:** {cycle_start} to {cycle_end}")
                        
                        # Threshold indicators
                        if thresholds:
                            st.markdown("**Alert Thresholds:**")
                            threshold_cols = st.columns(len(thresholds))
                            for idx, threshold in enumerate(thresholds):
                                with threshold_cols[idx]:
                                    if percentage >= threshold:
                                        st.markdown(f"🔴 {threshold}%")
                                    else:
                                        st.markdown(f"⚪ {threshold}%")
                        
                        st.markdown("---")
        else:
            st.error(f"Failed to load budget status: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading budget status: {e}")

# ===== BUDGET CONFIGURATION =====
elif st.session_state.view_mode == "config":
    st.subheader("⚙️ Budget Configuration")
    
    # Initialize edit state
    if 'edit_config' not in st.session_state:
        st.session_state.edit_config = None
    
    # Action buttons
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("➕ Create Budget", type="primary", use_container_width=True):
            st.session_state.edit_config = None
            st.rerun()
    
    # Fetch existing configs
    try:
        response = requests.get(f"{API_URL}/api/budget/configs")
        
        if response.status_code == 200:
            configs = response.json()
            
            if not configs:
                st.info("No budget configurations found. Create your first budget config.")
            else:
                st.markdown(f"**Total: {len(configs)} budget configs**")
                st.markdown("---")
                
                for config in configs:
                    config_id = config.get('id')
                    provider = config.get('provider', '').upper()
                    budget_amount = config.get('budget_amount_usd', 0)
                    invoice_day = config.get('invoice_day', 1)
                    thresholds = config.get('alert_thresholds', [])
                    is_active = config.get('is_active', True)
                    
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
                        
                        with col1:
                            status_icon = "✅" if is_active else "⏸️"
                            st.markdown(f"{status_icon} **{provider}**")
                        
                        with col2:
                            st.markdown(f"**Budget:** ${budget_amount:,.2f}")
                        
                        with col3:
                            st.markdown(f"**Invoice Day:** {invoice_day}")
                        
                        with col4:
                            if st.button("✏️ Edit", key=f"edit_{config_id}", use_container_width=True):
                                st.session_state.edit_config = config
                                st.rerun()
                        
                        with col5:
                            if st.button("🗑️ Delete", key=f"delete_{config_id}", use_container_width=True):
                                try:
                                    delete_response = requests.delete(f"{API_URL}/api/budget/configs/{config_id}")
                                    if delete_response.status_code == 200:
                                        st.success("Budget config deleted")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to delete: {delete_response.text}")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        
                        st.markdown(f"**Thresholds:** {', '.join([f'{t}%' for t in thresholds])}")
                        st.markdown("---")
        
        # Create/Edit form
        if st.session_state.edit_config is not None:
            st.markdown("### Edit Budget Config")
            config = st.session_state.edit_config
        else:
            st.markdown("### Create New Budget Config")
            config = None
        
        with st.form("budget_config_form"):
            provider = st.selectbox(
                "Provider",
                ["openai", "google", "anthropic", "groq"],
                index=0 if not config else ["openai", "google", "anthropic", "groq"].index(config.get('provider', 'openai'))
            )
            
            budget_amount = st.number_input(
                "Budget Amount (USD)",
                min_value=0.01,
                value=config.get('budget_amount_usd', 100.0) if config else 100.0,
                step=1.0
            )
            
            invoice_day = st.number_input(
                "Invoice Day (1-31)",
                min_value=1,
                max_value=31,
                value=config.get('invoice_day', 1) if config else 1
            )
            
            thresholds_str = st.text_input(
                "Alert Thresholds (comma-separated percentages, e.g., 50,80,95)",
                value=','.join([str(t) for t in config.get('alert_thresholds', [50, 80, 95])]) if config else "50,80,95"
            )
            
            is_active = st.checkbox(
                "Active",
                value=config.get('is_active', True) if config else True
            )
            
            submitted = st.form_submit_button("Save", type="primary")
            
            if submitted:
                try:
                    # Parse thresholds
                    thresholds = [int(t.strip()) for t in thresholds_str.split(',') if t.strip()]
                    
                    if config:
                        # Update
                        update_data = {
                            "budget_amount_usd": budget_amount,
                            "invoice_day": invoice_day,
                            "alert_thresholds": thresholds,
                            "is_active": is_active
                        }
                        update_response = requests.put(
                            f"{API_URL}/api/budget/configs/{config.get('id')}",
                            json=update_data
                        )
                        if update_response.status_code == 200:
                            st.success("Budget config updated successfully!")
                            st.session_state.edit_config = None
                            st.rerun()
                        else:
                            st.error(f"Failed to update: {update_response.text}")
                    else:
                        # Create
                        create_data = {
                            "provider": provider,
                            "budget_amount_usd": budget_amount,
                            "invoice_day": invoice_day,
                            "alert_thresholds": thresholds,
                            "is_active": is_active
                        }
                        create_response = requests.post(
                            f"{API_URL}/api/budget/configs",
                            json=create_data
                        )
                        if create_response.status_code == 200:
                            st.success("Budget config created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to create: {create_response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    except Exception as e:
        st.error(f"Error loading budget configs: {e}")

# ===== ALERTS =====
else:  # alerts
    st.subheader("🚨 Budget Alerts")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        provider_filter = st.selectbox(
            "Provider",
            ["All", "openai", "google", "anthropic", "groq"],
            index=0
        )
    
    with col2:
        unacknowledged_only = st.checkbox("Unacknowledged only", value=True)
    
    try:
        params = {}
        if provider_filter != "All":
            params["provider"] = provider_filter
        if unacknowledged_only:
            params["unacknowledged_only"] = True
        
        response = requests.get(f"{API_URL}/api/budget/alerts", params=params)
        
        if response.status_code == 200:
            alerts = response.json()
            
            if not alerts:
                st.info("No alerts found.")
            else:
                st.markdown(f"**Total: {len(alerts)} alerts**")
                st.markdown("---")
                
                for alert in alerts:
                    alert_id = alert.get('id')
                    provider = alert.get('provider', '').upper()
                    threshold = alert.get('threshold_percentage', 0)
                    current_spending = alert.get('current_spending_usd', 0)
                    budget_amount = alert.get('budget_amount_usd', 0)
                    alert_type = alert.get('alert_type', '')
                    sent_at = alert.get('sent_at', '')
                    acknowledged_at = alert.get('acknowledged_at')
                    channels = alert.get('alert_channels', [])
                    
                    with st.container():
                        # Alert header
                        if acknowledged_at:
                            status_icon = "✅"
                            status_text = "Acknowledged"
                        else:
                            status_icon = "🔴"
                            status_text = "Unacknowledged"
                        
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"{status_icon} **{provider}** - {threshold}% Threshold Reached")
                            st.markdown(f"**Type:** {alert_type}")
                            st.markdown(f"**Channels:** {', '.join(channels)}")
                        
                        with col2:
                            st.markdown(f"**Spending:** ${current_spending:,.2f} / ${budget_amount:,.2f}")
                            try:
                                sent_dt = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                                st.markdown(f"**Sent:** {sent_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                            except:
                                st.markdown(f"**Sent:** {sent_at}")
                        
                        with col3:
                            if not acknowledged_at:
                                if st.button("Acknowledge", key=f"ack_{alert_id}", use_container_width=True):
                                    try:
                                        ack_response = requests.post(
                                            f"{API_URL}/api/budget/alerts/{alert_id}/acknowledge"
                                        )
                                        if ack_response.status_code == 200:
                                            st.success("Alert acknowledged")
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to acknowledge: {ack_response.text}")
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            else:
                                st.markdown("✅ Acknowledged")
                        
                        st.markdown("---")
        else:
            st.error(f"Failed to load alerts: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error loading alerts: {e}")
