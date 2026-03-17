import streamlit as st
import requests
import time
from datetime import datetime
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="Upload & Ingest", page_icon="📤", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

st.title("📤 Upload & Ingest Data")
st.markdown("Upload documents or connect to external sources (Redmine, Git)")

# Tabs for different upload methods
tab1, tab2, tab3 = st.tabs(["📄 File Upload", "🔗 Redmine", "📁 Git Repository"])

# ===== FILE UPLOAD =====
with tab1:
    st.subheader("Upload Documents")
    st.markdown("Supported formats: PDF, DOCX, TXT, MD, JSON, HTML")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Choose files",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'md', 'json', 'html']
        )
    
    with col2:
        source_type = st.selectbox(
            "Source Type",
            ["document"]
        )
        
        project_key = st.text_input("Project Key (optional)")
        
        language = st.selectbox(
            "Language",
            ["en", "vi", "ja", "auto"]
        )
    
    if st.button("🚀 Process Files", type="primary", disabled=not uploaded_files):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for i, file in enumerate(uploaded_files):
            status_text.text(f"Processing {file.name}...")
            
            try:
                # Upload file
                files = {"file": (file.name, file, file.type)}
                data = {
                    "source_type": source_type,
                    "project_key": project_key,
                    "language": language
                }
                
                response = requests.post(
                    f"{API_URL}/api/ingest/manual",
                    files=files,
                    data=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        'file': file.name,
                        'status': result['status'],
                        'chunks': result.get('chunks_created', 0),
                        'success': True
                    })
                else:
                    results.append({
                        'file': file.name,
                        'status': 'failed',
                        'error': response.text,
                        'success': False
                    })
                
            except Exception as e:
                results.append({
                    'file': file.name,
                    'status': 'error',
                    'error': str(e),
                    'success': False
                })
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.empty()
        progress_bar.empty()
        
        # Show results
        st.success(f"✅ Processed {len(uploaded_files)} files")
        
        for result in results:
            if result['success']:
                st.success(f"✅ {result['file']}: {result.get('chunks', 0)} chunks created")
            else:
                st.error(f"❌ {result['file']}: {result.get('error', 'Unknown error')}")

# ===== REDMINE =====
with tab2:
    st.subheader("Import from Redmine")
    
    col1, col2 = st.columns(2)
    
    with col1:
        redmine_option = st.radio(
            "Import Type",
            ["Single Issue", "Single Wiki Page", "Project Wiki"]
        )
    
    with col2:
        if redmine_option == "Single Issue":
            issue_id = st.number_input("Issue ID", min_value=1, step=1)
            
            if st.button("Import Issue"):
                with st.spinner("Importing issue..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/ingest/redmine",
                            json={"issue_id": issue_id}
                        )
                        
                        if response.status_code == 200:
                            st.success(f"✅ Issue #{issue_id} imported successfully")
                        else:
                            st.error(f"Failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        elif redmine_option == "Single Wiki Page":
            project_id = st.text_input("Project Identifier", key="wiki_project")
            wiki_page_title = st.text_input("Wiki Page Title", placeholder="Home")
            wiki_version = st.number_input("Version (optional, leave empty for latest)", min_value=1, step=1, value=None)
            
            if st.button("Import Wiki Page"):
                with st.spinner("Importing wiki page..."):
                    try:
                        payload = {
                            "project_id": project_id,
                            "wiki_page_title": wiki_page_title
                        }
                        if wiki_version:
                            payload["version"] = int(wiki_version)
                        
                        response = requests.post(
                            f"{API_URL}/api/ingest/redmine/wiki",
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Wiki page '{wiki_page_title}' imported successfully")
                            if result.get('result'):
                                st.json(result['result'])
                        else:
                            st.error(f"Failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        else:  # Project Wiki
            project_id = st.text_input("Project Identifier", key="wiki_project_sync")
            incremental = st.checkbox("Incremental Sync (only updated pages)", value=True)
            
            if st.button("Start Wiki Sync"):
                with st.spinner("Syncing wiki pages..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/ingest/redmine/wiki/project",
                            json={
                                "project_id": project_id,
                                "incremental": incremental
                            }
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Wiki sync completed for project {project_id}")
                            if result.get('result'):
                                res = result['result']
                                st.json({
                                    "processed": res.get('processed', 0),
                                    "failed": res.get('failed', 0),
                                    "errors": res.get('errors', [])[:5]  # Show first 5 errors
                                })
                        else:
                            st.error(f"Failed: {response.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

# ===== GIT =====
with tab3:
    st.subheader("Import from Git Repository")
    
    repo_url = st.text_input("Repository URL", placeholder="https://github.com/user/repo.git")
    
    col1, col2 = st.columns(2)
    
    with col1:
        branch = st.text_input("Branch", value="main")
        file_patterns = st.text_input("File Patterns", placeholder="*.md, *.py, *.txt")
    
    with col2:
        use_auth = st.checkbox("Use Authentication")
        if use_auth:
            git_username = st.text_input("Username")
            git_token = st.text_input("Access Token", type="password")
    
    if st.button("Import Repository"):
        st.warning("Git repository import not yet implemented")
        st.info("Coming soon! This will clone the repository and index all matching files.")

st.markdown("---")

# Recent uploads
st.subheader("📋 Recent Uploads")

try:
    response = requests.get(f"{API_URL}/api/ingest/stats")
    if response.status_code == 200:
        stats = response.json()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sources", stats.get('total_sources', 0))
        col2.metric("Source Docs", stats.get('total_source_documents', 0))
        col3.metric("Chunks", stats.get('total_chunks', 0))
        col4.metric("Embeddings", stats.get('total_embeddings', 0))
        
except Exception as e:
    st.error(f"Failed to load statistics: {e}")

# Tips
with st.expander("💡 Tips"):
    st.markdown("""
    - **File Upload**: Supports PDF, DOCX, TXT, MD, JSON, HTML
    - **Large Files**: Files > 10MB are processed in background
    - **Redmine**: Use Jobs page for scheduled project syncs
    - **Best Practice**: Tag documents with project_key for easy filtering
    - **Language**: Use 'auto' for automatic language detection
    """)
