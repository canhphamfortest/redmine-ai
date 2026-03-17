import streamlit as st
import requests
from datetime import datetime
import time
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="Source Management", page_icon="📁", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

st.title("📁 Source Management")
st.markdown("View and manage data sources")

# Initialize session state for pagination
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'items_per_page' not in st.session_state:
    st.session_state.items_per_page = 20
if 'projects_list' not in st.session_state:
    st.session_state.projects_list = []
if 'projects_dict' not in st.session_state:
    st.session_state.projects_dict = {}  # {display_name: project_id}

# Filters and pagination settings
col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1, 1])

with col1:
    source_type_filter = st.selectbox(
        "Source Type",
        ["All", "redmine_issue", "redmine_wiki", "git_file", "document"],
        index=0
    )

with col2:
    sync_status_filter = st.selectbox(
        "Sync Status",
        ["All", "success", "pending", "failed", "outdated"],
        index=0
    )

with col3:
    # Fetch unique projects using dedicated API endpoint (cached in session state)
    # Store as dict: {display_name: project_id} to filter by project_id
    if not st.session_state.projects_dict:
        try:
            # Use dedicated endpoint for better performance
            projects_response = requests.get(f"{API_URL}/api/ingest/sources/projects")
            if projects_response.status_code == 200:
                projects_data = projects_response.json()
                projects_list = projects_data.get("projects", [])
                
                # Convert to dict: {display_name: project_id}
                projects_dict = {}
                for project in projects_list:
                    display_name = project.get("display_name")
                    project_id = project.get("project_id")
                    if display_name and project_id is not None:
                        projects_dict[display_name] = project_id
                
                st.session_state.projects_dict = projects_dict
            else:
                st.session_state.projects_dict = {}
        except Exception as e:
            st.session_state.projects_dict = {}
    
    # Create selectbox with "All" option
    if st.session_state.projects_dict:
        project_options = ["All"] + list(st.session_state.projects_dict.keys())
        selected_project_display = st.selectbox(
            "Project ID or Key",
            project_options,
            index=0
        )
        
        # Convert display name to project_id for filtering
        if selected_project_display == "All":
            project_filter = ""
        else:
            # Get project_id from the selected display name
            project_filter = str(st.session_state.projects_dict[selected_project_display])
    else:
        # Fallback to text input if projects dict is empty
        project_filter = st.text_input("Project ID or Key", placeholder="Filter by project...")

with col4:
    items_per_page = st.selectbox(
        "Items per page",
        [10, 20, 50, 100],
        index=1,  # Default to 20
        key="items_per_page_select"
    )
    # Update session state if changed
    if items_per_page != st.session_state.items_per_page:
        st.session_state.items_per_page = items_per_page
        st.session_state.current_page = 1  # Reset to first page
        st.rerun()

with col5:
    if st.button("🔄 Refresh"):
        st.session_state.current_page = 1  # Reset to first page
        st.session_state.projects_list = []  # Clear cached projects list to refresh
        st.session_state.projects_dict = {}  # Clear cached projects dict to refresh
        st.rerun()

# Reset to page 1 if filters change
filter_key = f"{source_type_filter}_{sync_status_filter}_{project_filter}"
if 'last_filter_key' not in st.session_state:
    st.session_state.last_filter_key = filter_key
elif st.session_state.last_filter_key != filter_key:
    st.session_state.current_page = 1
    st.session_state.last_filter_key = filter_key

# Build query parameters
items_per_page_val = st.session_state.items_per_page
current_page = st.session_state.current_page
offset = (current_page - 1) * items_per_page_val

params = {
    "limit": items_per_page_val,
    "offset": offset
}

if source_type_filter != "All":
    params["source_type"] = source_type_filter

if sync_status_filter != "All":
    params["sync_status"] = sync_status_filter

if project_filter:
    params["project_id"] = project_filter

# Fetch sources
try:
    response = requests.get(f"{API_URL}/api/ingest/sources", params=params)
    
    if response.status_code == 200:
        data = response.json()
        total_sources = data.get("total", 0)
        sources = data.get("sources", [])
        
        # Summary statistics
        if total_sources > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Sources", total_sources)
            
            outdated_count = sum(1 for s in sources if s.get("sync_status") == "outdated")
            failed_count = sum(1 for s in sources if s.get("sync_status") == "failed")
            pending_count = sum(1 for s in sources if s.get("sync_status") == "pending")
            
            with col2:
                st.metric("Outdated", outdated_count, delta=None, delta_color="inverse")
            
            with col3:
                st.metric("Failed", failed_count, delta=None, delta_color="inverse")
            
            with col4:
                st.metric("Pending", pending_count, delta=None, delta_color="normal")
            
            st.markdown("---")
        
        # Pagination info and controls
        if total_sources > 0:
            total_pages = (total_sources + items_per_page_val - 1) // items_per_page_val  # Ceiling division
            start_item = offset + 1
            end_item = min(offset + items_per_page_val, total_sources)
            
            # Display pagination info
            pagination_col1, pagination_col2, pagination_col3 = st.columns([2, 3, 2])
            
            with pagination_col1:
                st.caption(f"Showing {start_item}-{end_item} of {total_sources} sources")
            
            with pagination_col2:
                # Pagination controls
                if total_pages > 1:
                    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])
                    
                    with nav_col1:
                        if st.button("⏮️ First", disabled=(current_page == 1), key="first_page"):
                            st.session_state.current_page = 1
                            st.rerun()
                    
                    with nav_col2:
                        if st.button("⬅️ Previous", disabled=(current_page == 1), key="prev_page"):
                            st.session_state.current_page -= 1
                            st.rerun()
                    
                    with nav_col3:
                        # Page number input
                        page_input = st.number_input(
                            "Page",
                            min_value=1,
                            max_value=total_pages,
                            value=current_page,
                            key="page_input",
                            label_visibility="collapsed"
                        )
                        if page_input != current_page:
                            st.session_state.current_page = page_input
                            st.rerun()
                        
                        st.caption(f"of {total_pages}")
                    
                    with nav_col4:
                        if st.button("Next ➡️", disabled=(current_page == total_pages), key="next_page"):
                            st.session_state.current_page += 1
                            st.rerun()
                    
                    with nav_col5:
                        if st.button("Last ⏭️", disabled=(current_page == total_pages), key="last_page"):
                            st.session_state.current_page = total_pages
                            st.rerun()
            
            with pagination_col3:
                st.caption(f"Page {current_page} of {total_pages}")
            
            st.markdown("---")
        
        # Display sources
        if not sources:
            st.info("No sources found matching the filters.")
        else:
            for source in sources:
                source_id = source.get("id")
                source_type = source.get("source_type", "unknown")
                external_id = source.get("external_id", "")
                external_url = source.get("external_url", "")
                project_key = source.get("project_key", "")
                project_id = source.get("project_id")
                sync_status = source.get("sync_status", "unknown")
                last_sync_at = source.get("last_sync_at")
                updated_at = source.get("updated_at")
                
                # Status badge
                status_config = {
                    "success": ("✅", "green"),
                    "pending": ("🔄", "blue"),
                    "failed": ("❌", "red"),
                    "outdated": ("⚠️", "orange")
                }
                
                status_icon, status_color = status_config.get(sync_status, ("❓", "gray"))
                
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 1.5, 1.5])
                    
                    with col1:
                        # Source title and type
                        st.markdown(f"### {status_icon} {external_id or source_id[:8]}")
                        
                        # Source type badge
                        type_badges = {
                            "redmine_issue": "🐛 Issue",
                            "redmine_wiki": "📝 Wiki",
                            "git_file": "💻 Git",
                            "document": "📄 Document"
                        }
                        type_badge = type_badges.get(source_type, source_type)
                        st.caption(f"Type: {type_badge}")
                        
                        # Project info
                        if project_key or project_id:
                            project_display = project_key or f"Project {project_id}"
                            st.caption(f"Project: {project_display}")
                    
                    with col2:
                        st.markdown("**Sync Status:**")
                        st.markdown(f'<span style="color: {status_color};">{status_icon} {sync_status.upper()}</span>', 
                                   unsafe_allow_html=True)
                        
                        # Last sync time
                        if last_sync_at:
                            try:
                                last_sync = datetime.fromisoformat(last_sync_at.replace('Z', '+00:00'))
                                st.caption(f"Last sync: {last_sync.strftime('%Y-%m-%d %H:%M')}")
                            except:
                                st.caption(f"Last sync: {last_sync_at}")
                        else:
                            st.caption("Last sync: Never")
                    
                    with col3:
                        st.markdown("**Updated:**")
                        if updated_at:
                            try:
                                updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                                st.caption(updated.strftime('%Y-%m-%d %H:%M'))
                            except:
                                st.caption(updated_at)
                        else:
                            st.caption("N/A")
                    
                    with col4:
                        # Action buttons based on status
                        if sync_status == "outdated":
                            if st.button("🔄 Re-sync", key=f"resync_{source_id}", type="primary"):
                                with st.spinner("Re-syncing source..."):
                                    try:
                                        resync_response = requests.post(
                                            f"{API_URL}/api/ingest/sources/{source_id}/resync",
                                            timeout=60
                                        )
                                        if resync_response.status_code == 200:
                                            st.success("✅ Source re-synced successfully!")
                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            error_msg = resync_response.json().get("detail", "Unknown error")
                                            st.error(f"Failed to re-sync: {error_msg}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                        
                        elif sync_status == "failed":
                            # Show retry button for failed sources
                            if st.button("🔄 Retry", key=f"retry_{source_id}"):
                                with st.spinner("Re-syncing source..."):
                                    try:
                                        resync_response = requests.post(
                                            f"{API_URL}/api/ingest/sources/{source_id}/resync",
                                            timeout=60
                                        )
                                        if resync_response.status_code == 200:
                                            st.success("✅ Source re-synced successfully!")
                                            time.sleep(2)
                                            st.rerun()
                                        else:
                                            error_msg = resync_response.json().get("detail", "Unknown error")
                                            st.error(f"Failed to re-sync: {error_msg}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                        
                        # Check button for all sources
                        if st.button("🔍 Check", key=f"check_{source_id}"):
                            with st.spinner("Checking source..."):
                                try:
                                    check_response = requests.post(
                                        f"{API_URL}/api/ingest/sources/{source_id}/check",
                                        timeout=30
                                    )
                                    if check_response.status_code == 200:
                                        result = check_response.json()
                                        if result.get("success"):
                                            if result.get("outdated"):
                                                st.warning("⚠️ Source is outdated!")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.info("✅ Source is up to date")
                                                time.sleep(1)
                                        else:
                                            st.error(f"Check failed: {result.get('error', 'Unknown error')}")
                                    else:
                                        error_msg = check_response.json().get("detail", "Unknown error")
                                        st.error(f"Failed to check: {error_msg}")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                    
                    with col5:
                        # External link
                        if external_url:
                            st.markdown(f"[🔗 Open]({external_url})")
                    
                    # Expandable details
                    with st.expander("📋 Details"):
                        st.json(source)
                    
                    st.markdown("---")
    else:
        st.error(f"Failed to load sources: {response.text}")

except Exception as e:
    st.error(f"Error: {str(e)}")

# Footer info
st.markdown("---")
st.info("💡 **Tip:** Use the filters above to narrow down sources. Outdated sources will show a re-sync button to update them from Redmine.")

