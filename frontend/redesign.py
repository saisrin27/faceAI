import os

app_path = r"D:\New folder\frontend\app.py"

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# Helper function to replace content between start_marker and end_marker
def replace_block(text, start_marker, end_marker, new_content):
    start_idx = text.find(start_marker)
    if start_idx == -1:
        print(f"Warning: Start marker '{start_marker}' not found!")
        return text
    end_idx = text.find(end_marker, start_idx + len(start_marker))
    if end_idx == -1:
        print(f"Warning: End marker '{end_marker}' not found after start marker!")
        return text
    return text[:start_idx] + new_content + text[end_idx:]

# 1. Replace style block
new_style = """# Custom Premium White & Black High-Contrast Styling
st.markdown(\"\"\"
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: #F8FAFC !important;
        color: #1F2937 !important;
    }
    
    /* Hide standard Streamlit header and decorations */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    div[data-testid="stDecoration"] {
        display: none !important;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    .main,
    .stMain,
    .stAppViewContainer,
    div[data-testid="stAppViewBlockContainer"] {
        background-color: #F8FAFC !important;
        background-image: none !important;
        color: #1F2937 !important;
        padding-top: 0 !important;
    }
    
    /* Global Card Base Class (Stripe, Linear, Clerk quality) */
    .saas-card {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 24px !important;
        padding: 2.5rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.01), 0 2px 4px -1px rgba(0, 0, 0, 0.01), 0 10px 15px -3px rgba(0, 0, 0, 0.02), 0 4px 6px -2px rgba(0, 0, 0, 0.01) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        height: 100%;
        box-sizing: border-box;
    }
    .saas-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.03) !important;
        border-color: #D1D5DB !important;
    }
    
    /* Sticky Navbar glassmorphism */
    .custom-navbar {
        border-radius: 50px !important;
        padding: 0.6rem 2rem !important;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        width: 100%;
        margin-top: 1rem;
        margin-bottom: 2.5rem;
        position: sticky;
        top: 10px;
        z-index: 1000;
        height: 80px;
        box-sizing: border-box;
        transition: all 0.3s ease;
    }
    
    /* Navbar Light style */
    .custom-navbar.navbar-light {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(229, 231, 235, 0.7) !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.03) !important;
    }
    .custom-navbar.navbar-light .logo-title {
        color: #1F2937 !important;
    }
    .custom-navbar.navbar-light .logo-subtitle {
        color: #64748B !important;
    }
    .custom-navbar.navbar-light .logo-svg path {
        stroke: #2563EB !important;
    }
    .custom-navbar.navbar-light .logo-svg path[fill] {
        fill: #2563EB !important;
    }
    .custom-navbar.navbar-light button {
        color: #4B5563 !important;
        background-color: transparent;
        border: none;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .custom-navbar.navbar-light button:hover {
        color: #2563EB !important;
        background-color: rgba(37, 99, 235, 0.05) !important;
    }
    .custom-navbar.navbar-light button.active {
        background-color: rgba(37, 99, 235, 0.1) !important;
        color: #2563EB !important;
        box-shadow: none !important;
    }
    .custom-navbar.navbar-light .nav-login-btn {
        color: #4B5563 !important;
        font-weight: 600;
        text-decoration: none;
        font-size: 0.9rem;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .custom-navbar.navbar-light .nav-login-btn:hover {
        color: #2563EB !important;
    }
    .custom-navbar.navbar-light .nav-register-btn {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #2563EB !important;
        padding: 0.5rem 1.5rem;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.2s ease;
        text-decoration: none;
    }
    .custom-navbar.navbar-light .nav-register-btn:hover {
        background-color: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
        transform: translateY(-1px);
    }

    /* Navbar Dark style */
    .custom-navbar.navbar-dark {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1) !important;
    }
    .custom-navbar.navbar-dark .logo-title {
        color: #FFFFFF !important;
    }
    .custom-navbar.navbar-dark .logo-subtitle {
        color: #93C5FD !important;
    }
    .custom-navbar.navbar-dark .logo-svg path {
        stroke: #FFFFFF !important;
    }
    .custom-navbar.navbar-dark .logo-svg path[fill] {
        fill: #FFFFFF !important;
    }
    .custom-navbar.navbar-dark button {
        color: rgba(255, 255, 255, 0.8) !important;
        background-color: transparent;
        border: none;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.5rem 1.2rem;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .custom-navbar.navbar-dark button:hover {
        color: #FFFFFF !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    .custom-navbar.navbar-dark button.active {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
    }
    .custom-navbar.navbar-dark .nav-login-btn {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 600;
        text-decoration: none;
        font-size: 0.9rem;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .custom-navbar.navbar-dark .nav-login-btn:hover {
        color: #FFFFFF !important;
    }
    .custom-navbar.navbar-dark .nav-register-btn {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #2563EB !important;
        padding: 0.5rem 1.5rem;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.2s ease;
        text-decoration: none;
    }
    .custom-navbar.navbar-dark .nav-register-btn:hover {
        background-color: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
        transform: translateY(-1px);
    }
    
    /* Hero Banner Section */
    .hero-section {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border-radius: 24px !important;
        padding: 7rem 4rem 4.5rem 4rem !important;
        color: #FFFFFF !important;
        margin-top: -112px !important;
        margin-bottom: 2.5rem !important;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 40px rgba(37, 99, 235, 0.12) !important;
        z-index: 1;
    }
    .hero-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 2rem;
        position: relative;
        z-index: 2;
    }
    .hero-left {
        flex: 1.3;
    }
    .hero-title {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        font-size: 3.5rem !important;
        line-height: 1.15 !important;
        color: #FFFFFF !important;
        margin-top: 0 !important;
        margin-bottom: 1.2rem !important;
        text-align: left !important;
    }
    .hero-subtitle {
        font-size: 1.25rem !important;
        opacity: 0.9;
        margin-bottom: 2rem !important;
        line-height: 1.6 !important;
        max-width: 550px;
        text-align: left !important;
    }
    .hero-badges {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
    }
    .hero-badge {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem !important;
        border-radius: 50px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        background: #FFFFFF !important;
        color: #1F2937 !important;
        border: none !important;
    }
    .hero-badge-check {
        color: #10B981 !important;
        font-weight: bold;
    }
    .hero-right {
        flex: 0.7;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* Face Recognition HUD Illustration */
    .face-scan-container {
        width: 280px;
        height: 280px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .scanning-ring {
        position: absolute;
        width: 280px;
        height: 280px;
        border: 3px solid rgba(96, 165, 250, 0.4);
        border-radius: 50%;
        border-top-color: transparent;
        border-bottom-color: transparent;
        animation: spin 8s linear infinite;
        opacity: 0.7;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .face-mesh {
        width: 170px;
        height: 170px;
        position: relative;
        opacity: 0.95;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .verification-checkmark {
        position: absolute;
        bottom: 10px;
        right: 10px;
        background: #10B981;
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        font-size: 1.25rem;
    }
    
    /* Circular scan animations */
    .scan-circle-wrapper {
        position: relative;
        width: 200px;
        height: 200px;
        margin: 0 auto 2.5rem auto;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .scan-circle-ring-1 {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: rgba(37, 99, 235, 0.04);
        animation: pulse-ring 3s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
    }
    .scan-circle-ring-2 {
        position: absolute;
        width: 80%;
        height: 80%;
        border-radius: 50%;
        background: rgba(37, 99, 235, 0.07);
        animation: pulse-ring-delayed 3s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
    }
    .scan-circle-center {
        position: relative;
        z-index: 2;
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: #2563EB;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 30px rgba(37, 99, 235, 0.35);
    }
    @keyframes pulse-ring {
        0% { transform: scale(0.6); opacity: 0; }
        50% { opacity: 0.5; }
        100% { transform: scale(1.1); opacity: 0; }
    }
    @keyframes pulse-ring-delayed {
        0% { transform: scale(0.4); opacity: 0; }
        50% { opacity: 0.8; }
        100% { transform: scale(1.0); opacity: 0; }
    }
    
    /* Rules Card Styles */
    .rules-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 1.2rem;
        margin-bottom: 2rem;
    }
    .rules-header h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        color: #1F2937 !important;
        font-size: 1.4rem !important;
        margin: 0 !important;
        text-align: left !important;
    }
    .rule-item {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        margin-bottom: 1.8rem;
    }
    .rule-badge {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .badge-green { background-color: rgba(16, 185, 129, 0.1); color: #10B981; }
    .badge-blue { background-color: rgba(37, 99, 235, 0.1); color: #2563EB; }
    .badge-orange { background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; }
    
    .rule-text h4 {
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        color: #1F2937 !important;
        margin: 0 0 0.25rem 0 !important;
        text-align: left !important;
    }
    .rule-text p {
        font-size: 0.9rem !important;
        color: #64748B !important;
        margin: 0 !important;
        line-height: 1.4 !important;
    }

    /* Core Admin KPI and Profile Metrics styles */
    .metric-card {
        background-color: #FFFFFF !important;
        padding: 1.8rem !important;
        border-radius: 24px !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.01), 0 2px 4px -1px rgba(0, 0, 0, 0.01), 0 10px 15px -3px rgba(0, 0, 0, 0.02), 0 4px 6px -2px rgba(0, 0, 0, 0.01) !important;
        margin-bottom: 1rem !important;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 15px 25px rgba(0, 0, 0, 0.05) !important;
        border-color: #D1D5DB !important;
    }
    .stat-number {
        font-family: 'Inter', sans-serif !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #2563EB !important;
        margin: 0 0 6px 0 !important;
    }
    .stat-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        color: #1F2937 !important;
        font-weight: 600 !important;
        margin: 0 0 4px 0 !important;
    }
    .stat-sublabel {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        color: #64748B !important;
        margin: 0 !important;
    }
    
    /* Content Box generic */
    .content-box {
        background-color: #FFFFFF !important;
        padding: 2.2rem !important;
        border-radius: 24px !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 1.5rem !important;
        color: #1F2937 !important;
        transition: all 0.3s ease;
    }
    .content-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.04) !important;
    }

    /* Input elements style override */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 0.2rem 0.5rem !important;
    }
    div[data-baseweb="input"] input {
        color: #1F2937 !important;
        -webkit-text-fill-color: #1F2937 !important;
        font-size: 0.95rem !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 1px #2563EB !important;
    }
    
    /* Custom style targeting start/stop button specifically */
    .custom-action-btn div.stButton > button {
        background: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 30px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.65rem 2rem !important;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.2s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.5rem !important;
        width: 100% !important;
        margin: 0 auto !important;
    }
    .custom-action-btn div.stButton > button:hover {
        background: #1D4ED8 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3) !important;
    }
    .custom-action-btn div.stButton {
        text-align: center !important;
        width: 100% !important;
    }
    
    /* Feedback list and comments styles */
    .comment-card {
        background-color: #FFFFFF;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1.25rem;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
    }
    .comment-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }
    .comment-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #EFF6FF;
        color: #2563EB;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        border: 2px solid #DBEAFE;
    }
    .comment-meta {
        display: flex;
        flex-direction: column;
    }
    .comment-user {
        font-weight: 700;
        color: #1F2937;
        font-size: 0.95rem;
    }
    .comment-date {
        font-size: 0.8rem;
        color: #64748B;
    }
    .comment-body {
        color: #334155;
        font-size: 0.95rem;
        line-height: 1.5;
        margin: 0 0 1rem 0;
    }
    .comment-actions {
        display: flex;
        gap: 1.25rem;
        border-top: 1px solid #F1F5F9;
        padding-top: 0.75rem;
        margin-top: 0.75rem;
    }
    .action-link {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.82rem;
        color: #64748B;
        text-decoration: none;
        cursor: pointer;
        font-weight: 500;
    }
    .action-link:hover {
        color: #2563EB;
    }
</style>
\"\"\")"""

content = replace_block(content, '# Custom Premium White & Black High-Contrast Styling', '# Session State Initialization', new_style + "\n\n")

# 2. Replace navbar block
new_navbar = """# Header banner with Navigation Buttons
active_home = "active" if st.session_state.current_page == "Home / Scanner" else ""
active_feature = "active" if st.session_state.current_page == "Feature" else ""
active_tech = "active" if st.session_state.current_page == "Techstack" else ""
active_comment = "active" if st.session_state.current_page == "Comment" else ""
active_team = "active" if st.session_state.current_page == "Team" else ""

# Use different style classes for Navbar based on page
navbar_theme = "navbar-dark" if st.session_state.current_page == "Home / Scanner" else "navbar-light"

auth_buttons = ""
if not st.session_state.authenticated:
    auth_buttons = \"\"\"
    <a href="?nav=Login" class="nav-login-btn" target="_self">Login</a>
    <a href="?nav=Register" class="nav-register-btn" target="_self">Register</a>
    \"\"\"
else:
    auth_buttons = f\"\"\"
    <a href="?nav=Profile" class="nav-login-btn" target="_self">Profile</a>
    <a href="?nav=Logout" class="nav-register-btn" target="_self">Logout</a>
    \"\"\"

st.markdown(f\"\"\"
<div class="custom-navbar {navbar_theme}">
    <div class="navbar-logo" style="display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0;">
        <svg class="logo-svg" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 12V6h6M26 12V6h-6M6 20v6h6M26 20v6h-6" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 10a4 4 0 0 0-4 4v2c0 2.5 1.5 4.5 4 4.8V22h-2v2h4v-2h-2v-1.2c2.5-.3 4-2.3 4-4.8v-2a4 4 0 0 0-4-4z" fill="#FFFFFF"/>
        </svg>
        <div class="logo-text" style="display: flex; flex-direction: column;">
            <span class="logo-title" style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.25rem; color: #FFFFFF; line-height: 1.1;">Face AI</span>
            <span class="logo-subtitle" style="font-size: 0.75rem; color: #93C5FD; font-weight: 500;">Attendance System</span>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; gap: 0.5rem; justify-content: center; flex-grow: 1;">
        <a href="?nav=Home%20%2F%20Scanner" target="_self" style="text-decoration: none;"><button class="{active_home}">Home / Scanner</button></a>
        <a href="?nav=Feature" target="_self" style="text-decoration: none;"><button class="{active_feature}">Feature</button></a>
        <a href="?nav=Techstack" target="_self" style="text-decoration: none;"><button class="{active_tech}">Techstack</button></a>
        <a href="?nav=Comment" target="_self" style="text-decoration: none;"><button class="{active_comment}">Comment</button></a>
        <a href="?nav=Team" target="_self" style="text-decoration: none;"><button class="{active_team}">Team</button></a>
    </div>

    <div style="display: flex; align-items: center; gap: 1rem; flex-shrink: 0;">
        {auth_buttons}
    </div>
</div>
\"\"\", unsafe_allow_html=True)"""

content = replace_block(content, '# Header banner with Navigation Buttons', '# --- PAGES ---', new_navbar + "\n\n# --- PAGES ---\n")

# 3. Replace Feature & Techstack pages
new_feature_techstack = """# A. FEATURE PAGE
if st.session_state.current_page == "Feature":
    st.markdown(\"\"\"
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💡</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Core AI Features</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Explore the advanced technologies driving the Face AI Attendance System.</p>
    </div>
    \"\"\", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(\"\"\"
        <div class='saas-card' style='text-align: center;'>
            <div style='display: flex; justify-content: center; margin-bottom: 1.5rem;'>
                <div style='width: 60px; height: 60px; border-radius: 50%; background-color: #EFF6FF; display: flex; align-items: center; justify-content: center; border: 2px solid #DBEAFE;'>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                        <circle cx="12" cy="13" r="4"></circle>
                    </svg>
                </div>
            </div>
            <h4 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.25rem; margin-top: 0; margin-bottom: 1rem;'>YOLOv8 Face Detection</h4>
            <p style='color: #64748B; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500;'>
                High-speed bounding box localization optimized for low-latency scanning.
            </p>
            <p style='color: #4B5563; font-size: 0.9rem; line-height: 1.6;'>
                Performs deep learning-based single and multi-face localization across video stream frames, providing pre-processed segments for subsequent recognition steps.
            </p>
        </div>
        \"\"\", unsafe_allow_html=True)
    with col2:
        st.markdown(\"\"\"
        <div class='saas-card' style='text-align: center;'>
            <div style='display: flex; justify-content: center; margin-bottom: 1.5rem;'>
                <div style='width: 60px; height: 60px; border-radius: 50%; background-color: #FEF3C7; display: flex; align-items: center; justify-content: center; border: 2px solid #FDE68A;'>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                </div>
            </div>
            <h4 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.25rem; margin-top: 0; margin-bottom: 1rem;'>InsightFace ArcFace</h4>
            <p style='color: #64748B; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500;'>
                Industrial-grade 512D facial vector embedding recognition.
            </p>
            <p style='color: #4B5563; font-size: 0.9rem; line-height: 1.6;'>
                Uses the state-of-the-art <code>buffalo_sc</code> deep model to extract distinct facial feature mappings, verifying identities against database records with cosine similarity comparison.
            </p>
        </div>
        \"\"\", unsafe_allow_html=True)
    with col3:
        st.markdown(\"\"\"
        <div class='saas-card' style='text-align: center;'>
            <div style='display: flex; justify-content: center; margin-bottom: 1.5rem;'>
                <div style='width: 60px; height: 60px; border-radius: 50%; background-color: #ECFDF5; display: flex; align-items: center; justify-content: center; border: 2px solid #A7F3D0;'>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                </div>
            </div>
            <h4 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.25rem; margin-top: 0; margin-bottom: 1rem;'>Liveness & Anti-Spoofing</h4>
            <p style='color: #64748B; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500;'>
                Pose-symmetry estimation and validation filters.
            </p>
            <p style='color: #4B5563; font-size: 0.9rem; line-height: 1.6;'>
                Integrated MediaPipe FaceMesh landmark analysis calculating symmetry ratios to check head orientation, ensuring only live individuals are recorded.
            </p>
        </div>
        \"\"\", unsafe_allow_html=True)

# A2. TECHSTACK PAGE
elif st.session_state.current_page == "Techstack":
    st.markdown(\"\"\"
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚙️</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Technical Stack</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Detailed breakdown of the architecture, models, and dependencies powering this platform.</p>
    </div>
    \"\"\", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(\"\"\"
        <div class='saas-card'>
            <h4 style='color: #2563EB; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.2rem; margin-top: 0; margin-bottom: 1.25rem; border-bottom: 2px solid #F1F5F9; padding-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;'>🧠 Core AI & Computer Vision</h4>
            <ul style='color: #4B5563; margin-left: 0; padding-left: 0; line-height: 1.8; font-size: 0.92rem; list-style-type: none;'>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #EC4899; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>InsightFace ArcFace</b>: Deep model mapping faces to 512D spatial coordinates.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #EC4899; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>MediaPipe Tasks</b>: Live landmark tracking assessing head rotation.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #EC4899; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>YOLOv8-Face</b>: Backup model to perform fast face bounding-box localization.</span></li>
                <li style='margin-bottom: 0; display: flex; align-items: flex-start;'><span style='color: #EC4899; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>OpenCV</b>: Native system camera IO, frame rotation, and image preprocessing.</span></li>
            </ul>
        </div>
        \"\"\", unsafe_allow_html=True)
    with col2:
        st.markdown(\"\"\"
        <div class='saas-card'>
            <h4 style='color: #2563EB; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.2rem; margin-top: 0; margin-bottom: 1.25rem; border-bottom: 2px solid #F1F5F9; padding-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;'>🌐 Web Architecture & API</h4>
            <ul style='color: #4B5563; margin-left: 0; padding-left: 0; line-height: 1.8; font-size: 0.92rem; list-style-type: none;'>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #3B82F6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>FastAPI backend</b>: Asynchronous routes with validation using Pydantic schemas.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #3B82F6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>Streamlit frontend</b>: Visual dashboards mapping user data tables.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #3B82F6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>Uvicorn</b>: Lightning-fast ASGI runner hosting the endpoint interface.</span></li>
                <li style='margin-bottom: 0; display: flex; align-items: flex-start;'><span style='color: #3B82F6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>HTTP Requests</b>: Communication protocol between frontend and local APIs.</span></li>
            </ul>
        </div>
        \"\"\", unsafe_allow_html=True)
    with col3:
        st.markdown(\"\"\"
        <div class='saas-card'>
            <h4 style='color: #2563EB; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.2rem; margin-top: 0; margin-bottom: 1.25rem; border-bottom: 2px solid #F1F5F9; padding-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem;'>💾 Database & Security</h4>
            <ul style='color: #4B5563; margin-left: 0; padding-left: 0; line-height: 1.8; font-size: 0.92rem; list-style-type: none;'>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #8B5CF6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>MySQL / PyMySQL</b>: Relational database storing user tables and logs.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #8B5CF6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>Bcrypt</b>: Strong security password encryption for dashboards.</span></li>
                <li style='margin-bottom: 0.75rem; display: flex; align-items: flex-start;'><span style='color: #8B5CF6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>JWT (JSON Web Tokens)</b>: Stateful user role authorizations.</span></li>
                <li style='margin-bottom: 0; display: flex; align-items: flex-start;'><span style='color: #8B5CF6; font-size: 1.25rem; line-height: 1; margin-right: 0.5rem;'>•</span><span><b>python-dotenv</b>: Environment separation configuration files.</span></li>
            </ul>
        </div>
        \"\"\", unsafe_allow_html=True)"""

content = replace_block(content, '# A. FEATURE PAGE', '# B. COMMENT PAGE', new_feature_techstack + "\n\n")

# 4. Replace Comment page
new_comment = """elif st.session_state.current_page == "Comment":
    st.markdown(\"\"\"
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💬</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>User Comments & Feedback</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Submit comments, suggestions, or reports directly to the administration team.</p>
    </div>
    \"\"\", unsafe_allow_html=True)

    # Load comments from DB
    try:
        db_comments = api.get_comments()
    except Exception as e:
        db_comments = []
        st.error(f"Could not load comments: {e}")

    with st.container():
        st.markdown(\"\"\"
            <div style='background-color: #EFF6FF; border-left: 4px solid #2563EB; padding: 1rem; border-radius: 12px; margin-bottom: 2rem;'>
                <p style='color: #1E3A8A; margin: 0; font-size: 0.95rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;'>
                    ℹ️ Feedback board is online. Your comments help us improve the platform.
                </p>
            </div>
        \"\"\", unsafe_allow_html=True)

        # Display comments (latest first)
        if db_comments:
            for comm in db_comments:
                c_col1, c_col2 = st.columns([12, 1])
                with c_col1:
                    initial = comm['user_name'][0].upper() if comm['user_name'] else 'U'
                    st.markdown(
                        f\"\"\"
                        <div class="comment-card">
                            <div class="comment-header">
                                <div class="comment-avatar">{initial}</div>
                                <div class="comment-meta">
                                    <span class="comment-user">🧑‍💻 {comm['user_name']}</span>
                                    <span class="comment-date">{comm['created_at']}</span>
                                </div>
                            </div>
                            <p class="comment-body">{comm['comment_text']}</p>
                            <div class="comment-actions">
                                <a class="action-link">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
                                    Like
                                </a>
                                <a class="action-link">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                                    Reply
                                </a>
                            </div>
                        </div>
                        \"\"\",
                        unsafe_allow_html=True
                    )
                with c_col2:
                    # Only Admin sees delete button
                    if st.session_state.get("user_role") == "Admin":
                        st.write("") # Spacer to match avatar height
                        if st.button("🗑️", key=f"del_comment_{comm['id']}", help="Delete this comment"):
                            try:
                                api.delete_comment(comm["id"])
                                st.success("Comment deleted.")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Delete failed: {ex}")
        else:
            st.markdown(
                "<p style='color: #94a3b8; text-align: center; padding: 3rem; font-style: italic; background: #FFFFFF; border-radius: 16px; border: 1px dashed #E2E8F0;'>No comments yet. Be the first to share your thoughts!</p>",
                unsafe_allow_html=True
            )

        st.markdown("<hr style='border-top: 1px solid #e2e8f0; margin: 2rem 0;'>", unsafe_allow_html=True)
        
        # Post new comment
        with st.form("new_comment_form", clear_on_submit=True):
            comm_col1, comm_col2 = st.columns([5, 1])
            with comm_col1:
                new_comment = st.text_input(
                    "Write a comment...",
                    placeholder="Type your comment here and click Post...",
                    label_visibility="collapsed"
                )
            with comm_col2:
                submit_comment = st.form_submit_button("Post", type="primary", use_container_width=True)
                
            if submit_comment:
                if new_comment.strip():
                    try:
                        user_id = st.session_state.get("user_id")
                        user_name = st.session_state.get("username", "Anonymous") \\
                                    if st.session_state.get("authenticated") else "Anonymous"
                        api.post_comment(user_id, user_name, new_comment.strip())
                        st.success("Comment posted successfully!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to post: {ex}")
                else:
                    st.warning("Comment cannot be empty.")"""

content = replace_block(content, 'elif st.session_state.current_page == "Comment":', '# C. TEAM PAGE', new_comment + "\n\n")

# 5. Replace Team page
new_team = """elif st.session_state.current_page == "Team":
    st.markdown(\"\"\"
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">👥</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Meet The Development Team</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>The engineers behind the Face AI contactless attendance system.</p>
    </div>
    \"\"\", unsafe_allow_html=True)
    
    # Initialize session states for toggling contact details
    if "show_danvanthiri" not in st.session_state:
        st.session_state.show_danvanthiri = False
    if "show_bavanshree" not in st.session_state:
        st.session_state.show_bavanshree = False
        
    dan_img_base64 = ""
    bavan_img_base64 = ""
    
    dan_path = r"D:\\New folder\\uploads\\users\\Dan.jpg"
    bavan_path = r"D:\\New folder\\uploads\\users\\Bavan.jpg"
    
    import base64
    if os.path.exists(dan_path):
        try:
            with open(dan_path, "rb") as f:
                dan_img_base64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass
            
    if os.path.exists(bavan_path):
        try:
            with open(bavan_path, "rb") as f:
                bavan_img_base64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass

    dan_avatar_html = f'<img src="data:image/jpeg;base64,{dan_img_base64}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #EFF6FF;">' if dan_img_base64 else '<div style="width: 80px; height: 80px; border-radius: 50%; background-color: #DBEAFE; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: bold; color: #2563EB; border: 3px solid #EFF6FF;">DV</div>'
    bavan_avatar_html = f'<img src="data:image/jpeg;base64,{bavan_img_base64}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #ECFDF5;">' if bavan_img_base64 else '<div style="width: 80px; height: 80px; border-radius: 50%; background-color: #D1FAE5; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: bold; color: #10B981; border: 3px solid #ECFDF5;">BN</div>'

    team_col1, team_col2 = st.columns(2)
    with team_col1:
        st.markdown(f\"\"\"
        <div class='saas-card'>
            <div style='display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem;'>
                {dan_avatar_html}
                <div>
                    <h3 style='margin: 0; font-family: "Inter", sans-serif; font-weight: 700; color: #1F2937; font-size: 1.3rem;'>Danvanthiri V</h3>
                    <p style='margin: 0; color: #2563EB; font-weight: 600; font-size: 0.95rem;'>Machine Learning Specialist & Core Architect</p>
                    <span style='background-color: #EFF6FF; color: #2563EB; font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.6rem; border-radius: 20px; display: inline-block; margin-top: 0.25rem;'>Student Developer</span>
                </div>
            </div>
            <p style='color: #4B5563; font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.5rem;'>Specializes in deep learning architectures and real-time computer vision pipelines. Responsible for optimizing the YOLOv8 face detection framework, managing embedded datasets, and minimizing inference response latency to ensure seamless contactless scanning.</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        
        if st.button("📞 Contact Danvanthiri V", key="btn_dan", use_container_width=True):
            st.session_state.show_danvanthiri = not st.session_state.show_danvanthiri
            st.rerun()
            
        if st.session_state.show_danvanthiri:
            st.markdown(\"\"\"
            <div style='background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 12px; padding: 15px; margin-top: 10px; color: #1E3A8A; font-size: 0.9rem;'>
                <b>📞 Phone:</b> +916374098843<br>
                <b>✉️ Email:</b> danvanthirivenugopal@gmail.com
            </div>
            \"\"\", unsafe_allow_html=True)

    with team_col2:
        st.markdown(f\"\"\"
        <div class='saas-card'>
            <div style='display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem;'>
                {bavan_avatar_html}
                <div>
                    <h3 style='margin: 0; font-family: "Inter", sans-serif; font-weight: 700; color: #1F2937; font-size: 1.3rem;'>Bavan shree N</h3>
                    <p style='margin: 0; color: #10B981; font-weight: 600; font-size: 0.95rem;'>Machine Learning Specialist & Pipeline Engineer</p>
                    <span style='background-color: #ECFDF5; color: #10B981; font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.6rem; border-radius: 20px; display: inline-block; margin-top: 0.25rem;'>Student Developer</span>
                </div>
            </div>
            <p style='color: #4B5563; font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.5rem;'>Expert in ML workflow engineering and data preprocessing pipelines. Focuses on feature extraction, threshold tuning for high-accuracy facial recognition, and structuring backend state management to reliably route system logs.</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        
        if st.button("📞 Contact Bavan shree N", key="btn_bavan", use_container_width=True):
            st.session_state.show_bavanshree = not st.session_state.show_bavanshree
            st.rerun()
            
        if st.session_state.show_bavanshree:
            st.markdown(\"\"\"
            <div style='background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 12px; padding: 15px; margin-top: 10px; color: #065F46; font-size: 0.9rem;'>
                <b>📞 Phone:</b> +919843215073<br>
                <b>✉️ Email:</b> mallikabavan@gmail.com
            </div>
            \"\"\", unsafe_allow_html=True)"""

content = replace_block(content, 'elif st.session_state.current_page == "Team":', 'elif st.session_state.current_page == "Home / Scanner":', new_team + "\n\n")

# 6. Replace Home / Scanner page
new_home_scanner = """elif st.session_state.current_page == "Home / Scanner":
    # 1. Hero Section
    st.markdown(\"\"\"
    <div class=\"hero-section\">
        <div class=\"hero-content\">
            <div class=\"hero-left\">
                <h1 class=\"hero-title\">Smart Attendance,<br>Powered by <span style=\"color: #10B981;\">AI</span></h1>
                <p class=\"hero-subtitle\" style=\"font-weight: 500;\">Real-time face recognition for accurate,<br>secure and contactless attendance tracking.</p>
                <div class=\"hero-badges\" style=\"margin-bottom: 2.5rem;\">
                    <span class=\"hero-badge\">
                        <span class=\"hero-badge-check\">✓</span> AI Powered
                    </span>
                    <span class=\"hero-badge\">
                        <span class=\"hero-badge-check\">✓</span> Real-Time
                    </span>
                    <span class=\"hero-badge\">
                        <span class=\"hero-badge-check\">✓</span> Secure
                    </span>
                    <span class=\"hero-badge\">
                        <span class=\"hero-badge-check\">✓</span> Cloud Ready
                    </span>
                </div>
                <div style=\"display: flex; gap: 1rem; align-items: center;\">
                    <a href=\"?action=start_attendance\" target=\"_self\" style=\"text-decoration: none;\">
                        <button style=\"background: #FFFFFF; color: #2563EB; border: none; padding: 0.75rem 2rem; border-radius: 12px; font-weight: 700; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; box-shadow: 0 4px 15px rgba(255, 255, 255, 0.25);\">
                            <svg width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><polygon points=\"5 3 19 12 5 21 5 3\"></polygon></svg>
                            Start Attendance
                        </button>
                    </a>
                    <a href=\"?action=learn_more\" target=\"_self\" style=\"text-decoration: none;\">
                        <button style=\"background: transparent; color: #FFFFFF; border: 1.5px solid rgba(255, 255, 255, 0.4); padding: 0.75rem 2rem; border-radius: 12px; font-weight: 700; font-size: 0.95rem; cursor: pointer;\">
                            Learn More
                        </button>
                    </a>
                </div>
            </div>
            <div class=\"hero-right\">
                <div class=\"face-scan-container\">
                    <div class=\"scanning-ring\"></div>
                    <div class=\"face-mesh\">
                        <img src=\"https://raw.githubusercontent.com/danvanthiri/FaceAI-Assets/main/face_hologram.png\" style=\"width: 200px; height: 200px; filter: drop-shadow(0 0 20px #60A5FA);\" onerror=\"this.onerror=null; this.src='https://img.icons8.com/color/512/artificial-intelligence.png';\">
                    </div>
                    <div class=\"verification-checkmark\">✓</div>
                </div>
            </div>
        </div>
    </div>
    \"\"\", unsafe_allow_html=True)

    # Check query parameters to perform button actions if clicked
    q_params = st.query_params
    if q_params.get("action") == "start_attendance":
        st.query_params.clear()
        st.session_state.scanning = True
        st.session_state.current_page = "Home / Scanner"
        st.rerun()
    elif q_params.get("action") == "learn_more":
        st.query_params.clear()
        st.session_state.current_page = "Feature"
        st.rerun()

    # 2. Main content area: Scanner Card + Rules Card side-by-side
    col_scanner, col_rules = st.columns([1.8, 1])

    with col_scanner:
        # Auto-start scanner initialization
        if st.session_state.get("last_page_tracker") != "Home / Scanner":
            st.session_state.last_page_tracker = "Home / Scanner"
            if "cooldowns" not in st.session_state:
                st.session_state.cooldowns = {}
            if "pending_checkout_user" not in st.session_state:
                st.session_state.pending_checkout_user = None

        # Checkout prompt modal dialog
        if st.session_state.get("pending_checkout_user"):
            user_info = st.session_state.pending_checkout_user
            with st.container(border=True):
                st.markdown(f\"<h3 style='text-align: center; color: #1F2937;'>👋 Welcome back, {user_info['name']}!</h3>\", unsafe_allow_html=True)
                st.markdown(f\"<p style='text-align: center; color: #1F2937;'><b>{user_info['name']} has already checked-in today.</b> Are you leaving now?</p>\", unsafe_allow_html=True)
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("Yes, Leave Now", key="btn_checkout_yes", type="primary", use_container_width=True):
                        try:
                            api.check_out(user_info["user_id"])
                            st.success(f"✅ Leaving time recorded successfully for {user_info['name']}. Have a nice evening!")
                            time.sleep(1.5)
                        except Exception as e:
                            st.error(f"Error checking out: {e}")
                            time.sleep(1.5)
                        finally:
                            st.session_state.cooldowns[user_info["user_id"]] = time.time()
                            st.session_state.pending_checkout_user = None
                            st.rerun()
                with btn_col2:
                    if st.button("No, Stay", key="btn_checkout_no", use_container_width=True):
                        st.info(f"ℹ️ {user_info['name']}'s attendance is already marked.")
                        time.sleep(1.5)
                        st.session_state.cooldowns[user_info["user_id"]] = time.time()
                        st.session_state.pending_checkout_user = None
                        st.rerun()

        # Placeholders for scan states
        status_placeholder = st.empty()
        
        # Scanner card container
        with st.container(border=True):
            st.markdown('<div class="scanner-card-marker"></div>', unsafe_allow_html=True)
            
            is_scanning = st.session_state.get("scanning", False)
            if not is_scanning:
                st.markdown(\"\"\"
                <div style="text-align: center;">
                    <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
                    <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 2rem;">Start camera scanning to mark attendance instantly.</p>
                </div>
                <div class="scan-circle-wrapper">
                    <div class="scan-circle-ring-1"></div>
                    <div class="scan-circle-ring-2"></div>
                    <div class="scan-circle-center">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                            <circle cx="12" cy="13" r="4"></circle>
                        </svg>
                    </div>
                </div>
                \"\"\", unsafe_allow_html=True)
                
                st.markdown("<div class='custom-action-btn'>", unsafe_allow_html=True)
                if st.button("Start Camera Scanner", type="primary", key="btn_start_scanner_custom"):
                    st.session_state.scanning = True
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
                cap = None
            else:
                st.markdown(\"\"\"
                <div style="text-align: center;">
                    <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
                    <p style="color: #2563EB; font-size: 0.95rem; margin-bottom: 1.5rem; font-weight: 600;">Webcam Active - Face recognition in progress</p>
                </div>
                \"\"\", unsafe_allow_html=True)
                
                frame_placeholder = st.empty()
                
                st.markdown("<div class='custom-action-btn'>", unsafe_allow_html=True)
                if st.button("Stop Camera Scanner", key="btn_stop_scanner_custom"):
                    st.session_state.scanning = False
                    if "camera" in st.session_state and st.session_state.camera is not None:
                        st.session_state.camera.release()
                        st.session_state.camera = None
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

                if "camera" not in st.session_state or st.session_state.camera is None or not st.session_state.camera.isOpened():
                    st.session_state.camera = cv2.VideoCapture(0)
                    
                cap = st.session_state.camera

            if cap is not None:
                if not cap.isOpened():
                    status_placeholder.error("Cannot open system web-camera. Make sure it is connected.")
                else:
                    last_call_time = 0.0
                    scan_line_y = 0
                    scan_dir = 1
                
                    if "active_scanner_detections" not in st.session_state:
                        st.session_state.active_scanner_detections = []
                    
                    # Continuous scanner loop
                    try:
                        while True:
                            ret, frame = cap.read()
                            if not ret:
                                time.sleep(0.05)
                                continue
                            
                            frame = cv2.flip(frame, 1)
                            clean_frame = frame.copy()
                            h, w, _ = frame.shape
                        
                            # Draw real-time bounding boxes
                            if st.session_state.get("active_scanner_detections"):
                                for det in st.session_state.active_scanner_detections:
                                    bbox = det.get("bbox")
                                    if bbox and len(bbox) == 4:
                                        x1, y1, x2, y2 = bbox
                                        name = det.get("name", "Unknown")
                                        status_det = det.get("status", "unknown")
                                        user_id = det.get("user_id")
                                        draw_face_overlay(frame, x1, y1, x2, y2, name, user_id, status_det)
                            else:
                                # Draw default guides
                                box_w, box_h = int(w * 0.45), int(h * 0.55)
                                bx1, by1 = int((w - box_w)/2), int((h - box_h)/2)
                                bx2, by2 = bx1 + box_w, bx1 + box_h
                                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 255, 255), 2)
                                cv2.putText(frame, "ALIGN FACE HERE", (bx1 + 10, by1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            
                            # Scanning line animation
                            scan_line_y += 8 * scan_dir
                            box_h_guide = int(h * 0.55)
                            if scan_line_y >= box_h_guide or scan_line_y <= 0:
                                scan_dir *= -1
                            by1_guide = int((h - box_h_guide)/2)
                            bx1_guide = int((w - int(w * 0.45))/2)
                            bx2_guide = bx1_guide + int(w * 0.45)
                            line_pos = by1_guide + scan_line_y
                            cv2.line(frame, (bx1_guide + 5, line_pos), (bx2_guide - 5, line_pos), (255, 255, 255), 2)
                        
                            frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
                        
                            # Trigger API scan validation every 800ms
                            current_time = time.time()
                            if current_time - last_call_time >= 0.8:
                                last_call_time = current_time
                            
                                _, img_encoded = cv2.imencode('.jpg', clean_frame)
                                image_bytes = img_encoded.tobytes()
                            
                                try:
                                    res = api.scan_attendance_face(image_bytes)
                                    status = res.get("status")
                                
                                    if status in ["recognized", "already_marked", "ask_leave", "not_approved"]:
                                        res["results"] = [{"status": status, "name": res.get("name"), "user_id": res.get("user_id"), "bbox": res.get("bbox", [])}]
                                        status = "recognized_multiple"
                                    
                                    if status == "recognized_multiple":
                                        items = res.get("results", [])
                                        st.session_state.active_scanner_detections = items
                                    
                                        need_rerun = False
                                        messages = []
                                        has_unknown = False
                                        
                                        for item in items:
                                            item_status = item.get("status")
                                            user_id = item.get("user_id")
                                            
                                            if item_status == "unknown":
                                                has_unknown = True
                                                continue
                                                
                                            if not user_id:
                                                continue
                                            
                                            # Check cooldown (30 seconds)
                                            last_action_time = st.session_state.cooldowns.get(user_id, 0)
                                            if current_time - last_action_time < 30.0:
                                                continue
                                            
                                            if item_status == "recognized":
                                                st.session_state.cooldowns[user_id] = current_time
                                                messages.append(("success", f"🎉 Attendance Marked Successfully. Welcome {item['name']}!"))
                                            
                                            elif item_status == "already_marked":
                                                st.session_state.cooldowns[user_id] = current_time
                                                messages.append(("info", f"ℹ️ {item['name']}, your attendance is already completely marked for today."))
                                            
                                            elif item_status == "ask_leave":
                                                if not st.session_state.get("pending_checkout_user"):
                                                    st.session_state.pending_checkout_user = {"user_id": user_id, "name": item["name"]}
                                                    need_rerun = True
                                            
                                            elif item_status == "not_approved":
                                                st.session_state.cooldowns[user_id] = current_time
                                                messages.append(("warning", f"⏳ {item['name']}, your account is pending admin approval."))
                                        
                                        if has_unknown:
                                            last_unknown_time = st.session_state.cooldowns.get("unknown_face", 0)
                                            if current_time - last_unknown_time >= 3.0:
                                                st.session_state.cooldowns["unknown_face"] = current_time
                                                messages.append(("warning", "⚠️ Unknown User Detected"))
                                                
                                        if messages:
                                            with status_placeholder.container():
                                                for msg_type, msg_text in messages:
                                                    if msg_type == "success":
                                                        st.success(msg_text)
                                                    elif msg_type == "info":
                                                        st.info(msg_text)
                                                    elif msg_type == "warning":
                                                        st.warning(msg_text)
                                                        
                                        if need_rerun:
                                            st.rerun()
                                        
                                    elif status == "unknown":
                                        st.session_state.active_scanner_detections = res.get("results", [])
                                        status_placeholder.warning("⚠️ Unknown Face Detected")
                                        
                                    elif status in ["not_aligned", "no_face"]:
                                        st.session_state.active_scanner_detections = []
                                    
                                except Exception as e:
                                    pass
                                
                            time.sleep(0.03)
                        
                    except Exception as e:
                        pass

    with col_rules:
        # Styled Rules Sidebar
        st.markdown(\"\"\"
        <div class="saas-card">
            <div class="rules-header">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                <h3>Attendance Rules</h3>
            </div>
            <div class="rules-list">
                <div class="rule-item">
                    <div class="rule-badge badge-green">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Daily Record</h4>
                        <p>Only one attendance record allowed per day.</p>
                    </div>
                </div>
                <div class="rule-item">
                    <div class="rule-badge badge-blue">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Check-In</h4>
                        <p>Attendance automatically marked on first recognition.</p>
                    </div>
                </div>
                <div class="rule-item">
                    <div class="rule-badge badge-orange">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    </div>
                    <div class="rule-text">
                        <h4>Check-Out</h4>
                        <p>Attendance automatically marked on second recognition.</p>
                    </div>
                </div>
            </div>
        </div>
        \"\"\", unsafe_allow_html=True)

    # 2.5 Statistics Row Section
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    with stats_col1:
        st.markdown(\"\"\"
        <div class=\"metric-card\">
            <h3 class=\"stat-number\" style=\"color: #2563EB;\">150+</h3>
            <p class=\"stat-label\">Employees</p>
            <p class=\"stat-sublabel\">Registered</p>
        </div>
        \"\"\", unsafe_allow_html=True)
    with stats_col2:
        st.markdown(\"\"\"
        <div class=\"metric-card\">
            <h3 class=\"stat-number\" style=\"color: #10B981;\">120</h3>
            <p class=\"stat-label\">Attendance Today</p>
            <p class=\"stat-sublabel\">Total Check-Ins</p>
        </div>
        \"\"\", unsafe_allow_html=True)
    with stats_col3:
        st.markdown(\"\"\"
        <div class=\"metric-card\">
            <h3 class=\"stat-number\" style=\"color: #10B981;\">98%</h3>
            <p class=\"stat-label\">Recognition Accuracy</p>
            <p class=\"stat-sublabel\">This Month</p>
        </div>
        \"\"\", unsafe_allow_html=True)
    with stats_col4:
        st.markdown(\"\"\"
        <div class=\"metric-card\">
            <h3 class=\"stat-number\" style=\"color: #10B981;\">95%</h3>
            <p class=\"stat-label\">Monthly Attendance</p>
            <p class=\"stat-sublabel\">Average</p>
        </div>
        \"\"\", unsafe_allow_html=True)"""

content = replace_block(content, 'elif st.session_state.current_page == "Home / Scanner":', 'elif st.session_state.current_page == "Login":', new_home_scanner + "\n\n")

# 7. Replace Login / Register split block (WITHOUT the User Dashboard title at the very end to prevent duplication)
new_auth = """elif st.session_state.current_page in ["Login", "Register"]:
    col_login, col_register = st.columns([1, 1.2])
    
    with col_login:
        st.markdown(\"\"\"
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🔑</div>
            <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0 0 0.25rem 0;'>Sign In to Dashboard</h2>
            <p style='color: #64748B; font-size: 0.95rem; margin: 0;'>Welcome back! Please enter your details.</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="saas-card-inside" style="padding: 1rem 0.5rem;">', unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("Email ID")
                password = st.text_input("Password", type="password")
                
                col_remember, col_forgot = st.columns([1.2, 1])
                with col_remember:
                    remember_me = st.checkbox("Remember me", key="login_remember_me")
                with col_forgot:
                    st.markdown("<div style='text-align: right; padding-top: 5px;'><a href='#' style='color: #2563EB; font-size: 0.85rem; text-decoration: none; font-weight: 600;'>Forgot password?</a></div>", unsafe_allow_html=True)
                
                submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                
                if submit:
                    if not email or not password:
                        st.error("Please enter email and password.")
                    else:
                        try:
                            res = api.login(email, password)
                            st.session_state.authenticated = True
                            st.session_state.user_role = res.get("role")
                            st.session_state.username = res.get("name")
                            st.session_state.user_id = res.get("user_id")
                            st.session_state.approval_status = res.get("approval_status")
                            
                            st.success(f"Welcome back, {res.get('name')}!")
                            time.sleep(1.0)
                            
                            if res.get("role") == "Admin":
                                st.session_state.current_page = "Admin Dashboard"
                            elif res.get("role") == "User":
                                st.session_state.current_page = "User Dashboard"
                            else:
                                st.session_state.current_page = "Pending Dashboard"
                            st.rerun()
                        except Exception as e:
                            import requests
                            if isinstance(e, requests.exceptions.ConnectionError) or "Failed to establish a new connection" in str(e) or "Max retries exceeded" in str(e):
                                st.error("❌ Connection to the backend server failed. Please make sure the FastAPI backend server is running (port 8000).")
                            else:
                                st.error(f"Authentication failed: {e}")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 0.85rem; color: #64748B; margin-top: 1rem;'>Don't have an account? <a href='?nav=Register' style='color: #2563EB; text-decoration: none; font-weight: 600;'>Create one</a></p>", unsafe_allow_html=True)

    with col_register:
        st.markdown(\"\"\"
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📝</div>
            <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0 0 0.25rem 0;'>Create New Account</h2>
            <p style='color: #64748B; font-size: 0.95rem; margin: 0;'>Fill in the details to create your account.</p>
        </div>
        \"\"\", unsafe_allow_html=True)
        
        if st.session_state.registration_step == "form":
            with st.container(border=True):
                st.markdown('<div class="saas-card-inside" style="padding: 1rem 0.5rem;">', unsafe_allow_html=True)
                fe = st.session_state.get("reg_field_errors", {})

                with st.form("registration_form"):
                    full_name = st.text_input("Full Name")
                    if fe.get("full_name"):
                        st.error(fe["full_name"])

                    email = st.text_input("Email ID")
                    if fe.get("email"):
                        st.error(fe["email"])

                    c_code_col, phone_col = st.columns([1.2, 2])
                    with c_code_col:
                        country_code = st.selectbox("Country", ["+91 India", "+1 USA", "+44 UK", "+971 UAE"])
                    with phone_col:
                        phone_num = st.text_input("Phone Number")
                    if fe.get("phone_num"):
                        st.error(fe["phone_num"])

                    department = st.text_input("Department", placeholder="e.g. ENGINEERING, HR, SALES")
                    department = department.upper() if department else ""

                    if st.session_state.captcha_data is None:
                        try:
                            st.session_state.captcha_data = api.get_captcha()
                        except Exception as e:
                            st.error(f"Could not load CAPTCHA: {e}")

                    if st.session_state.captcha_data:
                        st.write("---")
                        st.write("🤖 **CAPTCHA Verification**")

                        captcha_key = st.session_state.captcha_data["captcha_key"]
                        captcha_base64 = st.session_state.captcha_data["captcha_image"].split(",")[1]
                        st.image(Image.open(BytesIO(base64.b64decode(captcha_base64))), caption="Math CAPTCHA")

                        captcha_input = st.text_input("Enter CAPTCHA value")
                        if fe.get("captcha"):
                            st.error(fe["captcha"])

                        if st.form_submit_button("Register", type="primary", use_container_width=True):
                            errors = {}

                            if not full_name.strip():
                                errors["full_name"] = "⚠️ Full Name is required."
                            if not email.strip():
                                errors["email"] = "⚠️ Email ID is required."
                            if not phone_num.strip():
                                errors["phone_num"] = "⚠️ Phone Number is required."
                            if not captcha_input.strip():
                                errors["captcha"] = "⚠️ Please enter the CAPTCHA value."

                            if errors:
                                st.session_state.reg_field_errors = errors
                                st.rerun()
                            else:
                                temp_password = "TempPass_123456!"
                                payload = {
                                    "name": full_name,
                                    "email": email,
                                    "phone_number": f"{country_code.split()[0]} {phone_num}",
                                    "department": department.strip() if department else "",
                                    "password": temp_password,
                                    "captcha_key": captcha_key,
                                    "captcha_value": captcha_input
                                }

                                try:
                                    res = api.register(payload)
                                    st.session_state.reg_user_id = res.get("user_id")
                                    st.session_state.registration_step = "enroll"
                                    st.session_state.captcha_data = None
                                    st.session_state.reg_field_errors = {}
                                    st.success("Personal details verified. Proceeding to Face Enrollment.")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    import requests
                                    if isinstance(e, requests.exceptions.ConnectionError) or "Failed to establish a new connection" in str(e) or "Max retries exceeded" in str(e):
                                        st.session_state.reg_field_errors = {"full_name": "❌ Connection to the backend server failed. Make sure the FastAPI server is running."}
                                    else:
                                        err_msg = str(e)
                                        if "email" in err_msg.lower() or "Email" in err_msg:
                                            st.session_state.reg_field_errors = {"email": f"❌ {err_msg}"}
                                        elif "captcha" in err_msg.lower() or "CAPTCHA" in err_msg:
                                            st.session_state.reg_field_errors = {"captcha": f"❌ {err_msg}"}
                                        else:
                                            st.session_state.reg_field_errors = {"full_name": f"❌ {err_msg}"}
                                    st.session_state.captcha_data = None
                                    st.rerun()
                    else:
                        st.form_submit_button("Submit")

                if st.button("Refresh CAPTCHA"):
                    st.session_state.captcha_data = None
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 0.85rem; color: #64748B; margin-top: 1rem;'>Already have an account? <a href='?nav=Login' style='color: #2563EB; text-decoration: none; font-weight: 600;'>Sign In</a></p>", unsafe_allow_html=True)
        
        elif st.session_state.registration_step == "enroll":
            with st.container(border=True):
                st.markdown("### 👤 Face Enrollment Process")
                st.markdown("Please align your face in front of the camera and perform the rotations as indicated below.")
            
                poses_cycle = ["front", "left", "right", "up", "down"]
            
                if "enroll_pose_idx" not in st.session_state:
                    st.session_state.enroll_pose_idx = 0
                    st.session_state.enroll_captures = {}
                
                current_pose = poses_cycle[st.session_state.enroll_pose_idx]
            
                pose_instructions = {
                    "front": "Look directly straight at the camera.",
                    "left": "Rotate your face towards the LEFT side (profile).",
                    "right": "Rotate your face towards the RIGHT side (profile).",
                    "up": "Tilt your face slightly UPWARDS.",
                    "down": "Tilt your face slightly DOWNWARDS."
                }
            
                instruction_placeholder = st.empty()
                progress_placeholder = st.empty()
            
                instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
                progress_placeholder.write(f"Progress: **{st.session_state.enroll_pose_idx} / 5** poses captured.")
            
                frame_placeholder = st.empty()
                status_placeholder = st.empty()
            
                start_capture = st.button("Start Enrollment Camera")
            
                if start_capture:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        st.error("Cannot access camera.")
                    else:
                        last_call = 0.0
                        try:
                            while st.session_state.enroll_pose_idx < len(poses_cycle):
                                ret, frame = cap.read()
                                if not ret:
                                    time.sleep(0.05)
                                    continue
                                
                                frame = cv2.flip(frame, 1)
                                clean_frame = frame.copy()
                            
                                h, w, _ = frame.shape
                                cv2.rectangle(frame, (int(w*0.3), int(h*0.2)), (int(w*0.7), int(h*0.8)), (255, 255, 255), 2)
                                cv2.putText(frame, f"POSE: {current_pose.upper()}", (int(w*0.3), int(h*0.2)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            
                                frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
                            
                                now_time = time.time()
                                if now_time - last_call >= 0.8:
                                    last_call = now_time
                                
                                    _, img_encoded = cv2.imencode('.jpg', clean_frame)
                                    image_bytes = img_encoded.tobytes()
                                
                                    try:
                                        status_placeholder.info(f"Scanning for {current_pose.upper()} pose...")
                                        api.upload_enrollment_pose(st.session_state.reg_user_id, current_pose, image_bytes)
                                    
                                        st.session_state.enroll_captures[current_pose] = True
                                        st.session_state.enroll_pose_idx += 1
                                    
                                        progress_placeholder.write(f"Progress: **{st.session_state.enroll_pose_idx} / 5** poses captured.")
                                    
                                        status_placeholder.success(f"✓ Captured {current_pose.upper()}!")
                                        time.sleep(1.0)
                                    
                                        if st.session_state.enroll_pose_idx < len(poses_cycle):
                                            current_pose = poses_cycle[st.session_state.enroll_pose_idx]
                                            instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
                                        else:
                                            break
                                    except Exception as e:
                                        status_placeholder.warning(str(e))
                                    
                                time.sleep(0.03)
                        finally:
                            cap.release()
                            frame_placeholder.empty()
                    
                        if st.session_state.enroll_pose_idx >= 5:
                            status_placeholder.info("Finalizing face profiles...")
                            try:
                                api.complete_enrollment(st.session_state.reg_user_id)
                                st.session_state.registration_step = "password"
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                            
                if st.button("Cancel & Restart"):
                    if "enroll_pose_idx" in st.session_state:
                        del st.session_state.enroll_pose_idx
                    if "enroll_captures" in st.session_state:
                        del st.session_state.enroll_captures
                    if "reg_user_id" in st.session_state:
                        del st.session_state.reg_user_id
                    st.session_state.registration_step = "form"
                    st.session_state.captcha_data = None
                    st.rerun()
                
        elif st.session_state.registration_step == "password":
            with st.container(border=True):
                st.markdown("### 🔒 Setup Account Password")
                st.markdown("Please choose a strong password to protect your user account dashboard.")
            
                with st.form("password_setup_form"):
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    submit = st.form_submit_button("Save Password & Complete Registration")
                
                    if submit:
                        import re
                        if len(password) < 12:
                            st.error("Password must be at least 12 characters.")
                        elif not re.search(r"[A-Z]", password):
                            st.error("Password must contain at least one uppercase letter.")
                        elif not re.search(r"[a-z]", password):
                            st.error("Password must contain at least one lowercase letter.")
                        elif not re.search(r"\\\\d", password):
                            st.error("Password must contain at least one number.")
                        elif not re.search(r"[!@#$%^&*(),.?\\":{}|<>]", password):
                            st.error("Password must contain at least one special character.")
                        elif password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            try:
                                api.update_password(st.session_state.reg_user_id, password)
                                st.success("🎉 Registration successfully completed! Waiting for Admin Approval.")
                            
                                if "enroll_pose_idx" in st.session_state:
                                    del st.session_state.enroll_pose_idx
                                if "enroll_captures" in st.session_state:
                                    del st.session_state.enroll_captures
                                if "reg_user_id" in st.session_state:
                                    del st.session_state.reg_user_id
                                
                                st.session_state.registration_step = "form"
                                st.session_state.captcha_data = None
                                time.sleep(3.0)
                                st.session_state.current_page = "Home / Scanner"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to set password: {e}")"""

content = replace_block(content, 'elif st.session_state.current_page == "Login":', 'elif st.session_state.current_page == "User Dashboard":', new_auth + "\n\n")

# Remove any double "elif st.session_state.current_page == "User Dashboard":" line that may occur from overlapping markers
content = content.replace(
    'elif st.session_state.current_page == "User Dashboard":\n\nelif st.session_state.current_page == "User Dashboard":',
    'elif st.session_state.current_page == "User Dashboard":'
)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Redesign run successfully with pure string slice method!")
