import logging
import streamlit as st
import requests
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Job Scheduler", page_icon="⚙️", layout="wide")

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

# Fetch job types từ API (render form động — không hardcode)
@st.cache_data(ttl=60)
def fetch_job_types():
    try:
        resp = requests.get(f"{API_URL}/api/jobs/types", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("job_types", [])
        logger.warning(f"GET /api/jobs/types returned HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Failed to fetch job types from API: {e}", exc_info=True)
    return []

def utc_to_local(utc_dt_str: str) -> datetime:
    """Convert UTC datetime string sang local timezone datetime."""
    if not utc_dt_str:
        return None
    dt = datetime.fromisoformat(utc_dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)

st.title("⚙️ Job Scheduler")
st.markdown("Configure and manage scheduled sync jobs")

# Tabs
tab1, tab2 = st.tabs(["📋 Job List", "➕ Create Job"])

# ===== JOB LIST =====
with tab1:
    st.subheader("Active Jobs")
    
    # Filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        show_inactive = st.checkbox("Show inactive jobs")
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Fetch jobs
    try:
        params = {} if show_inactive else {"is_active": True}
        response = requests.get(f"{API_URL}/api/jobs", params=params)
        
        if response.status_code == 200:
            jobs_data = response.json().get('jobs', [])
            
            if not jobs_data:
                st.info("No jobs configured. Create your first job in the 'Create Job' tab.")
            else:
                for job in jobs_data:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            status_icon = "✅" if job['is_active'] else "⏸️"
                            st.markdown(f"### {status_icon} {job['job_name']}")
                            st.caption(f"Type: {job['job_type']}")
                        
                        with col2:
                            st.markdown("**Schedule:**")
                            st.code(job['cron_expression'])
                        
                        with col3:
                            if job['last_run_at']:
                                last_run = utc_to_local(job['last_run_at'])
                                st.markdown(f"**Last Run:**  \n{last_run.strftime('%Y-%m-%d %H:%M')}")
                            else:
                                st.markdown("**Last Run:**  \nNever")
                            
                            if job['next_run_at']:
                                next_run = utc_to_local(job['next_run_at'])
                                st.markdown(f"**Next Run:**  \n{next_run.strftime('%Y-%m-%d %H:%M')}")
                        
                        with col4:
                            if st.button("▶️ Run", key=f"run_{job['id']}"):
                                with st.spinner("Triggering job..."):
                                    run_response = requests.post(
                                        f"{API_URL}/api/jobs/{job['id']}/run"
                                    )
                                    if run_response.status_code == 200:
                                        st.success("Job triggered!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to trigger job")
                            
                            if job['is_active']:
                                if st.button("⏸️ Pause", key=f"pause_{job['id']}"):
                                    update_response = requests.put(
                                        f"{API_URL}/api/jobs/{job['id']}",
                                        json={"is_active": False}
                                    )
                                    if update_response.status_code == 200:
                                        st.success("Job paused")
                                        st.rerun()
                            else:
                                if st.button("▶️ Resume", key=f"resume_{job['id']}"):
                                    update_response = requests.put(
                                        f"{API_URL}/api/jobs/{job['id']}",
                                        json={"is_active": True}
                                    )
                                    if update_response.status_code == 200:
                                        st.success("Job resumed")
                                        st.rerun()
                            
                            # Delete button with confirmation
                            delete_confirm_key = f"delete_confirm_{job['id']}"
                            delete_confirm_id_key = f"delete_confirm_id"
                            
                            # Initialize delete confirmation state
                            if delete_confirm_id_key not in st.session_state:
                                st.session_state[delete_confirm_id_key] = None
                            
                            # Check if this job is in delete confirmation mode
                            is_confirming_delete = st.session_state.get(delete_confirm_id_key) == job['id']
                            
                            if is_confirming_delete:
                                # Show confirmation UI
                                st.warning(f"⚠️ Are you sure you want to delete '{job['job_name']}'?")
                                col_confirm1, col_confirm2 = st.columns(2)
                                with col_confirm1:
                                    if st.button("✅ Yes, Delete", key=f"confirm_{job['id']}", type="primary"):
                                        delete_response = requests.delete(
                                            f"{API_URL}/api/jobs/{job['id']}"
                                        )
                                        if delete_response.status_code == 200:
                                            st.success("✅ Job deleted successfully!")
                                            st.session_state[delete_confirm_id_key] = None
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to delete job: {delete_response.text}")
                                            st.session_state[delete_confirm_id_key] = None
                                with col_confirm2:
                                    if st.button("❌ Cancel", key=f"cancel_{job['id']}"):
                                        st.session_state[delete_confirm_id_key] = None
                                        st.rerun()
                            else:
                                # Show delete button
                                if st.button("🗑️ Delete", key=f"delete_{job['id']}"):
                                    # Set the job ID that is being confirmed for deletion
                                    st.session_state[delete_confirm_id_key] = job['id']
                                    st.rerun()
                        
                        # Expandable details
                        with st.expander("📊 Execution History"):
                            history_response = requests.get(
                                f"{API_URL}/api/jobs/{job['id']}/history"
                            )
                            
                            if history_response.status_code == 200:
                                history = history_response.json().get('history', [])
                                
                                if not history:
                                    st.info("No execution history yet")
                                else:
                                    for exec_item in history:
                                        status = exec_item['status']
                                        execution_id = exec_item['id']
                                        status_icon = {
                                            'completed': '✅',
                                            'failed': '❌',
                                            'running': '🔄',
                                            'cancelled': '⏹️'
                                        }.get(status, '❓')
                                        
                                        started = datetime.fromisoformat(exec_item['started_at'])
                                        
                                        col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
                                        
                                        with col_a:
                                            st.markdown(f"{status_icon} {started.strftime('%Y-%m-%d %H:%M:%S')}")
                                        
                                        with col_b:
                                            st.markdown(f"Processed: {exec_item['items_processed']}")
                                        
                                        with col_c:
                                            if exec_item['items_failed'] > 0:
                                                st.markdown(f"Failed: {exec_item['items_failed']}", unsafe_allow_html=True)
                                        
                                        with col_d:
                                            # Show Cancel button for running executions
                                            if status == 'running':
                                                cancel_key = f"cancel_exec_{execution_id}_{job['id']}"
                                                if st.button("⏹️ Cancel", key=cancel_key, type="secondary"):
                                                    with st.spinner("Cancelling execution..."):
                                                        try:
                                                            cancel_response = requests.post(
                                                                f"{API_URL}/api/jobs/executions/{execution_id}/cancel"
                                                            )
                                                            if cancel_response.status_code == 200:
                                                                st.success("Execution cancellation requested!")
                                                                st.rerun()
                                                            else:
                                                                error_detail = cancel_response.json().get('detail', cancel_response.text)
                                                                st.error(f"Failed to cancel: {error_detail}")
                                                        except Exception as e:
                                                            st.error(f"Error cancelling execution: {str(e)}")
                                        
                                        if exec_item.get('error_message'):
                                            st.error(exec_item['error_message'])
                        
                        # Config details
                        with st.expander("⚙️ Job Configuration"):
                            st.json(job.get('config', {}))
                        
                        st.markdown("---")
        
        else:
            st.error(f"Failed to load jobs: {response.text}")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# ===== CREATE JOB =====
with tab2:
    st.subheader("Create New Job")

    job_types_data = fetch_job_types()

    if not job_types_data:
        st.warning("Cannot load job types from API. Please check backend connection.")
    else:
        # Map label → metadata
        type_map = {jt["name"]: jt for jt in job_types_data}
        type_labels = {jt["name"]: jt["label"] for jt in job_types_data}

        # Chọn job type ngoài form để UI cập nhật ngay
        selected_name = st.selectbox(
            "Job Type",
            options=list(type_map.keys()),
            format_func=lambda n: type_labels.get(n, n),
            key="create_job_type",
        )
        selected_type = type_map[selected_name]

        if selected_type.get("description"):
            st.caption(selected_type["description"])

        with st.form("create_job_form"):
            job_name = st.text_input("Job Name", placeholder=f"My {selected_type['label']} Job")

            st.markdown("**Schedule (Cron Expression)**")
            col1, col2 = st.columns([2, 1])

            # Resolve preset → cron value BEFORE rendering st.text_input so the
            # input always reflects the current selection on the same render pass.
            _CRON_PRESETS = {
                "Every day at 2 AM": "0 2 * * *",
                "Every 6 hours":     "0 */6 * * *",
                "Every Monday":      "0 0 * * 1",
            }
            if "cron_expression" not in st.session_state:
                st.session_state["cron_expression"] = "0 2 * * *"

            with col2:
                st.markdown("**Common Schedules:**")
                cron_preset = st.radio(
                    "Select preset",
                    options=list(_CRON_PRESETS.keys()),
                    index=None,
                    key="cron_preset",
                    label_visibility="collapsed"
                )
                if cron_preset and cron_preset in _CRON_PRESETS:
                    st.session_state["cron_expression"] = _CRON_PRESETS[cron_preset]

            with col1:
                # NOTE: Do NOT pass both `value=` and `key=` pointing to the
                # same session_state key — Streamlit raises StreamlitAPIException.
                # Instead read the current value from session_state and pass it
                # only via `value=`; the widget result is captured in a local var.
                cron_expression = st.text_input(
                    "Cron Expression",
                    value=st.session_state["cron_expression"],
                    help="Format: minute hour day month weekday"
                )
                # Keep session_state in sync when the user edits the field manually
                st.session_state["cron_expression"] = cron_expression

            # ── Render form config động từ options() của job ──────────────
            st.markdown("**Job Configuration**")
            config = {}

            for opt in selected_type.get("options", []):
                key = opt["key"]
                label = opt["label"] + (" *" if opt.get("required") else "")
                help_text = opt.get("help")
                default = opt.get("default")
                placeholder = opt.get("placeholder", "")

                if opt["type"] == "text":
                    val = st.text_input(label, value=default or "", help=help_text, placeholder=placeholder)
                    config[key] = val if val else None

                elif opt["type"] == "number":
                    try:
                        safe_default = int(default) if default is not None else 0
                    except (TypeError, ValueError):
                        safe_default = 0
                    val = st.number_input(label, value=safe_default, min_value=0, help=help_text)
                    config[key] = int(val)

                elif opt["type"] == "checkbox":
                    val = st.checkbox(label, value=bool(default), help=help_text)
                    config[key] = val

                elif opt["type"] == "select":
                    val = st.selectbox(label, options=opt.get("options", []), help=help_text)
                    config[key] = val

                elif opt["type"] == "multiselect":
                    val = st.multiselect(label, options=opt.get("options", []), default=default or [], help=help_text)
                    config[key] = val if val else []
            # ─────────────────────────────────────────────────────────────

            is_active = st.checkbox("Active", value=True)

            submitted = st.form_submit_button("✅ Create Job", type="primary")

            if submitted:
                if not job_name:
                    st.error("Job name is required")
                elif not cron_expression:
                    st.error("Cron expression is required")
                else:
                    # Validate required fields
                    missing = [
                        opt["label"]
                        for opt in selected_type.get("options", [])
                        if opt.get("required") and config.get(opt["key"], None) is None
                    ]
                    if missing:
                        st.error(f"Required fields missing: {', '.join(missing)}")
                    else:
                        try:
                            response = requests.post(
                                f"{API_URL}/api/jobs",
                                json={
                                    "job_name": job_name,
                                    "job_type": selected_name,
                                    "cron_expression": cron_expression,
                                    "config": config,
                                    "is_active": is_active,
                                },
                                timeout=10
                            )
                            if response.status_code == 200:
                                st.success("✅ Job created successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"Failed to create job: {response.text}")
                        except requests.exceptions.Timeout:
                            logger.error("Job creation request timed out after 10 seconds", exc_info=True)
                            st.error("Request timed out. Please try again.")
                        except Exception as e:
                            import uuid as _uuid
                            error_ref = str(_uuid.uuid4())[:8].upper()
                            logger.error(
                                f"[{error_ref}] Unexpected error creating job: {str(e)}", exc_info=True
                            )
                            st.error(
                                f"An unexpected error occurred while creating the job. "
                                f"Please try again or contact support (ref: {error_ref})."
                            )

# Cron helper
with st.expander("📖 Cron Expression Guide"):
    st.markdown("""
    Cron format: `minute hour day month weekday`
    
    | Field | Range | Special |
    |-------|-------|---------|
    | Minute | 0-59 | `*` = every minute |
    | Hour | 0-23 | `*/6` = every 6 hours |
    | Day | 1-31 | `*` = every day |
    | Month | 1-12 | `*` = every month |
    | Weekday | 0-6 (0=Sunday) | `1-5` = Mon-Fri |
    
    **Examples:**
    - `0 2 * * *` - Every day at 2:00 AM
    - `0 */6 * * *` - Every 6 hours
    - `0 9 * * 1-5` - 9 AM on weekdays
    - `30 8 1 * *` - 8:30 AM on 1st of month
    - `0 0 * * 0` - Midnight every Sunday
    """)