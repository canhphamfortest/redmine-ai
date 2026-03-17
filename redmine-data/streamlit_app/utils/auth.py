"""
Streamlit authentication utilities with URL-based session persistence
Uses Backend API for authentication instead of direct database access
"""
import streamlit as st
import requests
import hashlib


# Backend API URL
API_URL = "http://backend:8000"

# Session param name
SESSION_PARAM = "session_user"


def _get_session_from_query():
    """Try to restore session from URL query params via API"""
    query_params = st.query_params
    
    if SESSION_PARAM in query_params:
        username = query_params.get(SESSION_PARAM)
        if username:
            try:
                # Call API to verify user
                response = requests.get(
                    f"{API_URL}/api/auth/verify/{username}",
                    timeout=5
                )
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        'id': user_data['id'],
                        'username': user_data['username'],
                        'email': user_data.get('email'),
                        'full_name': user_data.get('full_name'),
                        'is_admin': user_data.get('is_admin', False)
                    }
            except Exception:
                pass
    
    return None


def _set_session_in_url(username: str):
    """Set session_user in URL using Streamlit native query_params"""
    # Use Streamlit's native query_params - no iframe needed
    if st.query_params.get(SESSION_PARAM) != username:
        st.query_params[SESSION_PARAM] = username


def check_authentication() -> bool:
    """Check if user is authenticated, with session persistence"""
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'session_restored' not in st.session_state:
        st.session_state.session_restored = False
    
    # If already authenticated in session
    if st.session_state.authenticated:
        # Keep session in URL using native Streamlit
        _set_session_in_url(st.session_state.username)
        return True
    
    # Try to restore from query params (only once per session)
    if not st.session_state.session_restored:
        st.session_state.session_restored = True
        user_data = _get_session_from_query()
        if user_data:
            st.session_state.authenticated = True
            st.session_state.username = user_data['username']
            st.session_state.user = user_data
            # Keep session in URL
            _set_session_in_url(user_data['username'])
            return True
    
    return st.session_state.authenticated


def login(username: str, password: str) -> tuple[bool, str]:
    """Attempt to login a user via API"""
    try:
        response = requests.post(
            f"{API_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('user'):
                user = result['user']
                st.session_state.authenticated = True
                st.session_state.username = user['username']
                st.session_state.user = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user.get('email'),
                    'full_name': user.get('full_name'),
                    'is_admin': user.get('is_admin', False)
                }
                # Set session in URL
                _set_session_in_url(user['username'])
                return True, result.get('message', 'Đăng nhập thành công!')
            else:
                return False, result.get('message', 'Tên đăng nhập hoặc mật khẩu không đúng!')
        else:
            return False, f"Lỗi đăng nhập: HTTP {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, "Không thể kết nối đến server. Vui lòng thử lại sau."
    except requests.exceptions.Timeout:
        return False, "Server không phản hồi. Vui lòng thử lại sau."
    except Exception as e:
        return False, f"Lỗi đăng nhập: {str(e)}"


def logout():
    """Logout the current user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user = None
    st.session_state.session_restored = False
    # Clear query params
    st.query_params.clear()


def get_current_user() -> dict | None:
    """Get current logged in user info"""
    if check_authentication():
        return st.session_state.user
    return None


def require_login():
    """Decorator-like function to require login"""
    if not check_authentication():
        st.error("⚠️ Vui lòng đăng nhập để truy cập trang này!")
        if st.button("🔐 Đăng nhập"):
            st.switch_page("pages/0_Login.py")
        st.stop()


def hide_pages_based_on_auth():
    """
    Hide pages based on authentication status:
    - If authenticated: Hide Login page
    - If not authenticated: Hide all other pages
    """
    # First, check and restore authentication if needed
    is_authenticated = check_authentication()
    
    if is_authenticated:
        # Hide Login page when user is authenticated
        st.markdown("""
        <style>
        /* Hide Login page from navigation when authenticated - multiple selectors for compatibility */
        [data-testid="stSidebarNav"] a[href*="Login"],
        [data-testid="stSidebarNav"] li:has(a[href*="Login"]),
        [data-testid="stSidebarNav"] ul li:has(a[href*="Login"]),
        /* Support for newer Streamlit versions */
        section[data-testid="stSidebar"] a[href*="Login"],
        section[data-testid="stSidebar"] li:has(a[href*="Login"]),
        nav[data-testid="stSidebarNavItems"] a[href*="Login"],
        nav[data-testid="stSidebarNavItems"] li:has(a[href*="Login"]),
        /* Target by text content */
        [data-testid="stSidebar"] ul li a[href*="Login"],
        [data-testid="stSidebar"] ul li:has(a[href*="Login"]),
        /* Direct targeting of sidebar list items with Login link */
        div[data-testid="stSidebar"] li:has(a[href*="Login"]),
        /* Generic sidebar link hiding */
        .stSidebar li:has(a[href*="Login"]),
        .stSidebar a[href*="Login"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # Hide all pages except Login when not authenticated
        st.markdown("""
        <style>
        /* Hide all pages except Login when not authenticated */
        [data-testid="stSidebarNav"] ul li,
        nav[data-testid="stSidebarNavItems"] li,
        section[data-testid="stSidebar"] nav ul li,
        div[data-testid="stSidebar"] ul li,
        .stSidebar ul li {
            display: none !important;
            visibility: hidden !important;
        }
        /* Show only Login page */
        [data-testid="stSidebarNav"] ul li:has(a[href*="Login"]),
        nav[data-testid="stSidebarNavItems"] li:has(a[href*="Login"]),
        section[data-testid="stSidebar"] nav ul li:has(a[href*="Login"]),
        div[data-testid="stSidebar"] ul li:has(a[href*="Login"]),
        .stSidebar ul li:has(a[href*="Login"]) {
            display: flex !important;
            visibility: visible !important;
        }
        /* Also hide the Home page link and app title */
        [data-testid="stSidebarNav"] a[href="/"]:not([href*="Login"]),
        section[data-testid="stSidebar"] a[href^="/"]:not([href*="Login"]),
        /* Hide app title in sidebar */
        .stSidebar header,
        section[data-testid="stSidebar"] > div > div > div > div:first-child a:not([href*="Login"]) {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)


def show_user_header():
    """Show username and logout button at top right corner of main page"""
    user = get_current_user()
    if user:
        username = user.get('username', 'N/A')
        full_name = user.get('full_name') or username
        display_name = full_name if full_name else username
        
        # CSS for fixed user header at top right
        st.markdown("""
        <style>
        /* Fixed user header at top right */
        .user-header-fixed {
            position: fixed;
            top: 14px;
            right: 80px;
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 8px 16px;
            border-radius: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        }
        .user-header-fixed .user-info {
            color: white;
            font-size: 14px;
            font-weight: 500;
        }
        .user-header-fixed .user-info .name {
            margin: 0;
        }
        .user-header-fixed .user-info .username {
            font-size: 11px;
            opacity: 0.8;
            margin: 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # User info HTML (display only)
        username_html = f'<p class="username">@{username}</p>' if display_name != username else ''
        st.markdown(f"""
        <div class="user-header-fixed">
            <div class="user-info">
                <p class="name">👤 {display_name}</p>
                {username_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button in sidebar (functional) - use unique key per page
        with st.sidebar:
            # Generate unique key based on current script path
            page_id = hashlib.md5(str(id(st.session_state)).encode()).hexdigest()[:8]
            if st.button("🚪 Đăng xuất", use_container_width=True, key=f"logout_{username}_{page_id}"):
                logout()
                st.switch_page("pages/0_Login.py")
