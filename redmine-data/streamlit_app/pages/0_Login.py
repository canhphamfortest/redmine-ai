"""
Login page for Streamlit app
"""
import streamlit as st
import streamlit.components.v1 as components
from streamlit_app.utils.auth import login, check_authentication, hide_pages_based_on_auth
from pathlib import Path


# Page config
st.set_page_config(
    page_title="Đăng nhập - Redmine AI Assistant",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide pages based on authentication status
hide_pages_based_on_auth()

# Custom CSS for login page
st.markdown("""
<style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF3333;
    }
    .error-message {
        padding: 1rem;
        border-radius: 5px;
        background-color: #ffebee;
        color: #c62828;
        margin-bottom: 1rem;
    }
    .success-message {
        padding: 1rem;
        border-radius: 5px;
        background-color: #e8f5e9;
        color: #2e7d32;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Redirect if already authenticated
if check_authentication():
    username = st.session_state.get('username', '')
    st.success("✅ Bạn đã đăng nhập!")
    # Auto redirect using meta refresh
    st.markdown(f"""
    <meta http-equiv="refresh" content="1;url=/?session_user={username}">
    <p>Đang chuyển hướng...</p>
    <p>Nếu không tự động chuyển hướng, <a href="/?session_user={username}">click vào đây</a></p>
    """, unsafe_allow_html=True)
    st.stop()


# Login form
st.markdown('<div class="login-header"><h1>🔐 Đăng nhập</h1></div>', unsafe_allow_html=True)
st.markdown("### Redmine AI Assistant")

st.markdown("---")

with st.form("login_form"):
    username = st.text_input("👤 Tên đăng nhập", placeholder="Nhập tên đăng nhập của bạn")
    password = st.text_input("🔒 Mật khẩu", type="password", placeholder="Nhập mật khẩu của bạn")
    

    submit_button = st.form_submit_button("🚀 Đăng nhập", use_container_width=True)

    if submit_button:
        if not username or not password:
            st.error("⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
        else:
            success, message = login(username, password)
            if success:
                st.success(message)
                # Redirect using meta refresh with session_user in URL
                st.markdown(f"""
                <meta http-equiv="refresh" content="0;url=/?session_user={username}">
                <p>Đang chuyển hướng...</p>
                """, unsafe_allow_html=True)
                st.stop()
            else:
                st.error(message)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>Redmine AI Assistant v1.0.0</p>
    <p>Nếu bạn chưa có tài khoản, vui lòng liên hệ quản trị viên.</p>
</div>
""", unsafe_allow_html=True)
