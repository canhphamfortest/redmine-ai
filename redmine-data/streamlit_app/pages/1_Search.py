import streamlit as st
import requests
import json
from streamlit_app.utils.auth import require_login, show_user_header, hide_pages_based_on_auth

st.set_page_config(page_title="Search", page_icon="🔍", layout="wide")

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Show user header FIRST (at top of sidebar)
show_user_header()

# Check authentication
require_login()

API_URL = "http://backend:8000"

st.title("🔍 Intelligent Search")
st.markdown("Semantic search with optional AI-powered answers")

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'rag_answer' not in st.session_state:
    st.session_state.rag_answer = None

# Search input
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_input(
        "🔎 Search Query",
        placeholder="Enter your question or search terms...",
        key="search_input"
    )

with col2:
    search_mode = st.radio(
        "Mode",
        ["Vector Search", "AI Answer (RAG)"],
        horizontal=True
    )

# Sidebar
with st.sidebar:
    top_k = st.slider("Number of Results", 1, 20, 5)
    
    st.markdown("---")
    
    # Search history
    st.subheader("📜 Recent Searches")
    try:
        history_response = requests.get(f"{API_URL}/api/search/history?limit=10")
        if history_response.status_code == 200:
            history = history_response.json().get('history', [])
            for item in history[:5]:
                if st.button(f"🔍 {item['query'][:30]}...", key=f"hist_{item['id']}"):
                    st.session_state.search_input = item['query']
                    st.rerun()
    except:
        pass

# Search button
if st.button("🚀 Search", type="primary", disabled=not query):
    with st.spinner("Searching..."):
        try:
            if search_mode == "Vector Search":
                # Vector search only
                response = requests.post(
                    f"{API_URL}/api/search/vector",
                    json={
                        "query": query,
                        "top_k": top_k
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    st.session_state.search_results = response.json()
                    st.session_state.rag_answer = None
                else:
                    st.error(f"Search failed: {response.text}")
            
            else:  # RAG mode
                response = requests.post(
                    f"{API_URL}/api/search/rag",
                    json={
                        "query": query
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.rag_answer = result.get('answer')
                    st.session_state.search_results = {
                        'results': result.get('retrieved_chunks', []),
                        'sources': result.get('sources', [])
                    }
                else:
                    st.error(f"RAG search failed: {response.text}")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display results
if st.session_state.rag_answer:
    st.markdown("---")
    st.subheader("🤖 AI Answer")
    st.markdown(
        f"<div style='padding: 1.5rem; background-color: #f0f2f6; border-radius: 10px; border-left: 4px solid #0066cc;'>{st.session_state.rag_answer}</div>",
        unsafe_allow_html=True
    )
    
    # Show sources
    if st.session_state.search_results.get('sources'):
        st.markdown("**📚 Sources:**")
        for source in st.session_state.search_results['sources']:
            with st.expander(f"📄 {source.get('title', 'Unknown')}"):
                st.markdown(f"- **Type:** {source.get('type', 'N/A')}")
                st.markdown(f"- **Project:** {source.get('project', 'N/A')}")
                if source.get('url'):
                    st.markdown(f"- **URL:** [{source['url']}]({source['url']})")

if st.session_state.search_results and st.session_state.search_results.get('results'):
    st.markdown("---")
    st.subheader("📄 Retrieved Chunks")
    
    results = st.session_state.search_results['results']
    st.markdown(f"Found **{len(results)}** relevant chunks")
    
    for i, result in enumerate(results, 1):
        similarity = result.get('similarity_score', 0)
        metadata = result.get('metadata', {})
        
        # Color code by similarity
        if similarity >= 0.8:
            border_color = "#28a745"  # Green
        elif similarity >= 0.7:
            border_color = "#ffc107"  # Yellow
        else:
            border_color = "#6c757d"  # Gray
        
        with st.container():
            st.markdown(
                f"""
                <div style='padding: 1rem; margin: 0.5rem 0; border-left: 4px solid {border_color}; background-color: #f8f9fa; border-radius: 5px;'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 0.5rem;'>
                        <strong>#{i} - {metadata.get('source_reference') or metadata.get('heading') or 'Unknown'}</strong>
                        <span style='color: {border_color}; font-weight: bold;'>{similarity:.2%}</span>
                    </div>
                    <div style='color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;'>
                        {metadata.get('source_type', 'N/A')} | {metadata.get('project_key', 'N/A')}
                    </div>
                    <div style='color: #333;'>{result.get('text', '')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Expandable details
            with st.expander("Show details"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Metadata:**")
                    st.json({
                        "chunk_type": result.get('chunk_type'),
                        "source_reference": metadata.get('source_reference'),
                        "heading": metadata.get('heading'),
                        "author": metadata.get('author'),
                        "page": metadata.get('page'),
                    })
                
                with col2:
                    st.markdown("**Source Info:**")
                    st.json({
                        "source_type": metadata.get('source_type'),
                        "language": metadata.get('language'),
                        "project": metadata.get('project_key'),
                    })
                
                if metadata.get('external_url'):
                    st.markdown(f"🔗 [View Original]({metadata['external_url']})")

# Analytics
st.markdown("---")
st.subheader("📊 Search Analytics")

try:
    analytics_response = requests.get(f"{API_URL}/api/search/analytics")
    if analytics_response.status_code == 200:
        analytics = analytics_response.json()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Searches", analytics.get('total_searches', 0))
        
        with col2:
            st.metric("Searches Today", analytics.get('searches_today', 0))
        
        with col3:
            avg_time = analytics.get('avg_response_time_ms', 0)
            st.metric("Avg Response Time", f"{avg_time:.0f} ms")
        
        # Popular queries
        popular = analytics.get('popular_queries', [])
        if popular:
            st.markdown("**🔥 Popular Queries:**")
            for item in popular[:5]:
                st.markdown(f"- {item['query']} ({item['count']} searches)")

except Exception as e:
    st.error(f"Failed to load analytics: {e}")

# Tips
with st.expander("💡 Search Tips"):
    st.markdown("""
    - **Natural Language**: Ask questions in natural language
    - **AI Mode**: Enable AI Answer for intelligent responses with citations
    - **Similarity**: Green = highly relevant, Yellow = moderately relevant
    - **Context**: Click "Show details" to see full metadata
    """)