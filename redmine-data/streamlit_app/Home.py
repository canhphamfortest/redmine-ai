import streamlit as st
import requests
from pathlib import Path
from streamlit_app.utils.auth import check_authentication, require_login, show_user_header, hide_pages_based_on_auth

# Page config
st.set_page_config(
    page_title="Redmine AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide pages based on authentication status (also checks and restores auth)
hide_pages_based_on_auth()

# Redirect to login if not authenticated
if not st.session_state.get('authenticated', False):
    st.switch_page("pages/0_Login.py")

# Show user header
show_user_header()

# Backend API URL
API_URL = "http://backend:8000"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🤖 Redmine AI Assistant</div>', unsafe_allow_html=True)
st.markdown("### RAG-powered Knowledge Search for Redmine & Enterprise Data")

# Check backend health
try:
    health = requests.get(f"{API_URL}/health", timeout=2).json()
    st.success(f"✅ System Status: {health['status'].upper()}")
except Exception as e:
    st.error(f"❌ Backend not available: {str(e)}")

st.markdown("---")

# Overview
col1, col2, col3, col4 = st.columns(4)

try:
    stats = requests.get(f"{API_URL}/api/ingest/stats").json()
    
    with col1:
        st.metric("📁 Total Sources", stats.get('total_sources', 0))
    
    with col2:
        st.metric("📄 Source Docs", stats.get('total_source_documents', 0))
    
    with col3:
        st.metric("🧩 Chunks", stats.get('total_chunks', 0))
    
    with col4:
        st.metric("🔢 Embeddings", stats.get('total_embeddings', 0))

except Exception as e:
    st.error(f"Failed to load statistics: {e}")

st.markdown("---")

# Features
st.markdown("### 🚀 Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-box">
        <h4>📤 Data Ingestion</h4>
        <ul>
            <li>Upload documents (PDF, DOCX, TXT, MD)</li>
            <li>Sync Redmine Issues & Wiki pages</li>
            <li>Sync Git repositories (code files)</li>
            <li>Automatic chunking & embedding</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
        <h4>⚙️ Job Scheduler</h4>
        <ul>
            <li>Scheduled automatic syncs (Cron)</li>
            <li>Redmine & Git periodic sync</li>
            <li>Job execution history</li>
            <li>Retry on failure</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-box">
        <h4>🔍 Intelligent Search</h4>
        <ul>
            <li>Semantic vector search (pgvector)</li>
            <li>AI-powered answers (OpenAI GPT)</li>
            <li>Find related Redmine issues</li>
            <li>Response caching (Redis)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
        <h4>📊 Monitoring & Analytics</h4>
        <ul>
            <li>OpenAI API usage & cost tracking</li>
            <li>Response time percentiles (P50-P99)</li>
            <li>Search analytics & popular queries</li>
            <li>Cache hit rate monitoring</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Quick Start
st.markdown("### 🎯 Quick Start")

st.info("""
**Step 1:** Go to 📤 **Upload** page to add documents or sync Redmine/Git data  
**Step 2:** Use 🔍 **Search** to find information with semantic search  
**Step 3:** Enable **AI Answer** for GPT-powered intelligent responses  
**Step 4:** Configure ⚙️ **Jobs** for scheduled automatic synchronization  
**Step 5:** Monitor usage, costs & performance in 📊 **Monitor** dashboard  
**Step 6:** Manage LLM models & pricing in 🔧 **LLM Config**
""")

# Tech Stack
with st.expander("🛠️ Tech Stack"):
    st.markdown("""
    | Component | Technology |
    |-----------|------------|
    | **Vector Database** | PostgreSQL + pgvector |
    | **LLM** | OpenAI GPT (gpt-4o-mini, gpt-5-nano, etc.) |
    | **Embeddings** | mxbai-embed-large-v1 (1024 dims) |
    | **Backend** | FastAPI + SQLAlchemy |
    | **Frontend** | Streamlit |
    | **Cache** | Redis |
    | **Scheduler** | APScheduler |
    | **Container** | Docker Compose |
    """)


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Redmine AI Assistant v1.0.0 | RAG-powered Enterprise Knowledge Search</p>
</div>
""", unsafe_allow_html=True)