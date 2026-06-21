import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from PIL import Image
from utils.api_client import FaceAiApiClient
import base64
from io import BytesIO
from pathlib import Path
import logging

logger = logging.getLogger("faceai.app")

def generate_audit_pdf(audit_logs):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    
    # Title
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(200, 10, text="System Audit Logs Report", ln=1, align="C")
    pdf.ln(10)
    
    # Table headers
    pdf.set_font("helvetica", "B", 10)
    col_width = [15, 20, 95, 25, 35]
    headers = ["ID", "Admin ID", "Action", "Target ID", "Timestamp"]
    for i in range(len(headers)):
        pdf.cell(col_width[i], 10, headers[i], border=1)
    pdf.ln()
    
    # Table rows
    pdf.set_font("helvetica", size=9)
    for log in audit_logs:
        log_id = str(log.get("id", ""))
        admin_id = str(log.get("admin_id", ""))
        action = str(log.get("action", ""))
        target_id = str(log.get("target_user_id", ""))
        if target_id == "None" or not target_id:
            target_id = "N/A"
        timestamp = str(log.get("timestamp", ""))
        
        if len(action) > 50:
            action = action[:47] + "..."
            
        pdf.cell(col_width[0], 8, log_id, border=1)
        pdf.cell(col_width[1], 8, admin_id, border=1)
        pdf.cell(col_width[2], 8, action, border=1)
        pdf.cell(col_width[3], 8, target_id, border=1)
        pdf.cell(col_width[4], 8, timestamp, border=1)
        pdf.ln()
        
    return bytes(pdf.output())

# Initialize API client inside session state to persist credentials across page reruns
if "api" not in st.session_state:
    st.session_state.api = FaceAiApiClient("http://127.0.0.1:8000")
api = st.session_state.api

# Session Inactivity Timeout (15 minutes = 900 seconds)
if st.session_state.get("authenticated") and st.session_state.get("user_id"):
    import time
    current_time = time.time()
    last_activity = st.session_state.get("last_activity")
    if last_activity is not None and (current_time - last_activity) > 900:
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.session_state.user_id = None
        st.session_state.approval_status = None
        st.session_state.current_page = "Home / Scanner"
        api.clear_token()
        st.sidebar.error("⚠️ Session expired due to inactivity. Please log in again.")
    st.session_state.last_activity = current_time



# Camera memory management: Release camera if we navigated away from the scanner page
if "camera" in st.session_state and st.session_state.camera is not None:
    # If the user changed the sidebar navigation, the page tracker changes
    if st.session_state.get("current_page") not in ["Home / Scanner", "Scanner", "Live Attendance Scanner"]:
        st.session_state.camera.release()
        st.session_state.camera = None
        st.session_state.scanning = False


def draw_face_overlay(frame, x1, y1, x2, y2, name, user_id, status_det):
    # Select color based on status (BGR format)
    if status_det == "recognized":
        box_color = (0, 255, 0)      # Green for checked-in
        status_text = ""
    elif status_det in ["already_marked", "ask_leave"]:
        box_color = (255, 255, 0)    # Cyan for already marked/leaving
        status_text = " (MARKED)"
    elif status_det == "not_approved":
        box_color = (0, 165, 255)    # Orange for pending approval
        status_text = " (PENDING)"
    else:
        box_color = (0, 0, 255)      # Red for unknown
        status_text = ""

    # Draw bounding box around face
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
    
    # Format labels
    label_name = name.upper()
    if status_text:
        label_name += status_text
        
    student_id = f"STU{100 + user_id}" if (user_id and user_id > 0) else None
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale_name = 0.55
    scale_id = 0.45
    thick_name = 2
    thick_id = 1
    
    (w_name, h_name), _ = cv2.getTextSize(label_name, font, scale_name, thick_name)
    if student_id:
        (w_id, h_id), _ = cv2.getTextSize(f"ID: {student_id}", font, scale_id, thick_id)
        label_w = max(w_name, w_id) + 16
        label_h = h_name + h_id + 18
    else:
        label_w = w_name + 16
        label_h = h_name + 12
        
    # Place label ABOVE the bounding box
    lx1 = x1 + (x2 - x1 - label_w) // 2
    ly1 = y1 - label_h - 6
    
    # Fallback to drawing BELOW if it goes above the frame boundary
    if ly1 < 5:
        ly1 = y2 + 6
        
    lx2 = lx1 + label_w
    ly2 = ly1 + label_h
    
    # Clip coordinates to frame size
    fh, fw, _ = frame.shape
    lx1 = max(0, min(lx1, fw - 1))
    lx2 = max(0, min(lx2, fw - 1))
    ly1 = max(0, min(ly1, fh - 1))
    ly2 = max(0, min(ly2, fh - 1))
    
    # Translucent background capsule drawing
    if lx2 > lx1 and ly2 > ly1:
        overlay = frame.copy()
        # Draw background
        if status_det == "recognized":
            bg_color = (0, 45, 0)
        elif status_det in ["already_marked", "ask_leave"]:
            bg_color = (45, 45, 0)
        elif status_det == "not_approved":
            bg_color = (0, 30, 45)
        else:
            bg_color = (0, 0, 45)
            
        cv2.rectangle(overlay, (lx1, ly1), (lx2, ly2), bg_color, -1)
        cv2.rectangle(overlay, (lx1, ly1), (lx2, ly2), box_color, 1)
        
        # Apply overlay with alpha blend
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Draw text on blended frame
        ty1 = ly1 + h_name + 6
        cv2.putText(frame, label_name, (lx1 + 8, ty1), font, scale_name, (255, 255, 255), thick_name, cv2.LINE_AA)
        
        if student_id:
            ty2 = ty1 + h_id + 8
            cv2.putText(frame, f"ID: {student_id}", (lx1 + 8, ty2), font, scale_id, (200, 200, 200), thick_id, cv2.LINE_AA)

# Page Configuration
st.set_page_config(
    page_title="Face AI Attendance System",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Process HTML navigation query parameters
if "nav" in st.query_params:
    nav_val = st.query_params["nav"]
    if nav_val in ["Home / Scanner", "Home %2F Scanner", "Feature", "Techstack", "Comment", "Team", "Login", "Register", "Profile", "Logout"]:
        if nav_val == "Logout":
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.username = ""
            st.session_state.user_id = None
            st.session_state.approval_status = None
            st.session_state.current_page = "Home / Scanner"
            api.clear_token()
        elif nav_val in ["Home / Scanner", "Home %2F Scanner"]:
            st.session_state.current_page = "Home / Scanner"
        else:
            st.session_state.current_page = nav_val
    st.query_params.clear()





def inject_css():
    st.markdown("""<style>
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
        box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08) !important;
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
    .badge-green {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10B981;
    }
    .badge-blue {
        background-color: rgba(37, 99, 235, 0.1);
        color: #2563EB;
    }
    .badge-orange {
        background-color: rgba(245, 158, 11, 0.1);
        color: #F59E0B;
    }
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
        box-shadow: 0 12px 35px rgba(15, 23, 42, 0.08) !important;
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
</style>""", unsafe_allow_html=True)

def render_navbar():
    active_home = "active" if st.session_state.current_page == "Home / Scanner" else ""
    active_feature = "active" if st.session_state.current_page == "Feature" else ""
    active_tech = "active" if st.session_state.current_page == "Techstack" else ""
    active_comment = "active" if st.session_state.current_page == "Comment" else ""
    active_team = "active" if st.session_state.current_page == "Team" else ""
    
    navbar_theme = "navbar-dark" if st.session_state.current_page == "Home / Scanner" else "navbar-light"
    
    auth_buttons = ""
    if not st.session_state.authenticated:
        auth_buttons = """<a href="?nav=Login" class="nav-login-btn" target="_self">Login</a>
<a href="?nav=Register" class="nav-register-btn" target="_self">Register</a>"""
    else:
        auth_buttons = f"""<a href="?nav=Profile" class="nav-login-btn" target="_self">Profile</a>
<a href="?nav=Logout" class="nav-register-btn" target="_self">Logout</a>"""
    
    st.markdown(f"""<div class="custom-navbar {navbar_theme}">
<div class="navbar-logo" style="display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0;">
<svg class="logo-svg" width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M6 12V6h6M26 12V6h-6M6 20v6h6M26 20v6h-6" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M16 10a4 4 0 0 0-4 4v2c0 2.5 1.5 4.5 4 4.8V22h-2v2h4v-2h-2v-1.2c2.5-.3 4-2.3 4-4.8v-2a4 4 0 0 0-4-4z" fill="#FFFFFF"/>
</svg>
<div class="logo-text" style="display: flex; flex-direction: column; text-align: left;">
<span class="logo-title" style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 1.25rem; line-height: 1.1;">Face AI</span>
<span class="logo-subtitle" style="font-size: 0.75rem; font-weight: 500;">Attendance System</span>
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
</div>""", unsafe_allow_html=True)

def render_hero():
    st.markdown("""
    <div class="hero-section">
        <div class="hero-content">
            <div class="hero-left">
                <h1 class="hero-title">Smart Attendance,<br>Powered by AI</h1>
                <p class="hero-subtitle">
                    Real-time face recognition for accurate, secure and contactless attendance tracking.
                </p>
                <div class="hero-badges">
                    <span class="hero-badge"><span class="hero-badge-check">✓</span> AI Powered</span>
                    <span class="hero-badge"><span class="hero-badge-check">✓</span> Real-time</span>
                    <span class="hero-badge"><span class="hero-badge-check">✓</span> Secure</span>
                    <span class="hero-badge"><span class="hero-badge-check">✓</span> Cloud Ready</span>
                </div>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                    <a href="?nav=Home%20%2F%20Scanner&action=start" target="_self" style="text-decoration: none;">
                        <button style="background-color: #FFFFFF; color: #2563EB; border: none; font-weight: 700; font-size: 0.95rem; padding: 0.8rem 1.8rem; border-radius: 30px; cursor: pointer; box-shadow: 0 4px 15px rgba(255,255,255,0.15);">Start Attendance</button>
                    </a>
                    <a href="?nav=Feature" target="_self" style="text-decoration: none;">
                        <button style="background-color: rgba(255,255,255,0.1); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.25); font-weight: 600; font-size: 0.95rem; padding: 0.8rem 1.8rem; border-radius: 30px; cursor: pointer;">Learn More</button>
                    </a>
                </div>
            </div>
            <div class="hero-right">
                <div class="face-scan-container">
                    <div class="scanning-ring"></div>
                    <div class="face-mesh">
                        <svg width="170" height="170" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 15px rgba(96, 165, 250, 0.6));">
                            <path d="M18 10a6 6 0 0 0-12 0v2c0 3.75 3 6.75 6 7.2v2.8h-2v2h4v-2h-2v-2.8c3-.45 6-3.45 6-7.2v-2z"/>
                            <circle cx="12" cy="10" r="3" stroke="#60A5FA" stroke-width="1.5"/>
                            <line x1="6" y1="10" x2="18" y2="10" stroke-dasharray="2,2"/>
                            <line x1="12" y1="4" x2="12" y2="17" stroke-dasharray="2,2"/>
                        </svg>
                        <div class="verification-checkmark">✓</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_scanner_section():
    col_scanner, col_rules = st.columns([1.2, 1])
    
    with col_scanner:
        st.markdown('<div class="saas-card" style="text-align: center;">', unsafe_allow_html=True)
        st.markdown('<div class="scanner-card-marker"></div>', unsafe_allow_html=True)
        
        is_scanning = st.session_state.get("scanning", False)
        status_placeholder = st.empty()
        
        if not is_scanning:
            st.markdown("""
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
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='custom-action-btn'>", unsafe_allow_html=True)
            if st.button("Start Camera Scanner", type="primary", key="btn_start_scanner_custom"):
                st.session_state.scanning = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            cap = None
        else:
            st.markdown("""
            <div style="text-align: center;">
                <h2 style='font-family: "Inter", sans-serif; font-weight: 800; color: #1F2937; margin-bottom: 0.5rem;'>Live Attendance Scanner</h2>
                <p style="color: #2563EB; font-size: 0.95rem; margin-bottom: 1.5rem; font-weight: 600;">Webcam Active - Face recognition in progress</p>
            </div>
            """, unsafe_allow_html=True)
            
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
                    while st.session_state.get("scanning", False):
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
                finally:
                    pass
        st.markdown('</div>', unsafe_allow_html=True)

    with col_rules:
        st.markdown("""
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
        """, unsafe_allow_html=True)

def render_stats_section():
    try:
        stats = st.session_state.api.get_public_stats()
        users_val = str(stats.get("users", 0))
        att_val = str(stats.get("attendance_today", 0))
        acc_val = f"{stats.get('accuracy', 99.4)}%"
        monthly_val = f"{stats.get('monthly_attendance', 95.0)}%"
    except Exception as e:
        users_val = "0"
        att_val = "0"
        acc_val = "99.4%"
        monthly_val = "95.0%"

    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    with stats_col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 class="stat-number" style="color: #2563EB;">{users_val}</h3>
            <p class="stat-label">Users</p>
            <p class="stat-sublabel">Registered</p>
        </div>
        """, unsafe_allow_html=True)
    with stats_col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 class="stat-number" style="color: #10B981;">{att_val}</h3>
            <p class="stat-label">Attendance Today</p>
            <p class="stat-sublabel">Total Check-Ins</p>
        </div>
        """, unsafe_allow_html=True)
    with stats_col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 class="stat-number" style="color: #10B981;">{acc_val}</h3>
            <p class="stat-label">Recognition Accuracy</p>
            <p class="stat-sublabel">This Month</p>
        </div>
        """, unsafe_allow_html=True)
    with stats_col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 class="stat-number" style="color: #10B981;">{monthly_val}</h3>
            <p class="stat-label">Monthly Attendance</p>
            <p class="stat-sublabel">Average</p>
        </div>
        """, unsafe_allow_html=True)

def render_features_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💡</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Core AI Features</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Explore the advanced technologies driving the Face AI Attendance System.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
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
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class='saas-card' style='text-align: center;'>
            <div style='display: flex; justify-content: center; margin-bottom: 1.5rem;'>
                <div style='width: 60px; height: 60px; border-radius: 50%; background-color: #FEE2E2; display: flex; align-items: center; justify-content: center; border: 2px solid #FCA5A5;'>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                </div>
            </div>
            <h4 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 700; font-size: 1.25rem; margin-top: 0; margin-bottom: 1rem;'>InsightFace ArcFace</h4>
            <p style='color: #64748B; margin-bottom: 1rem; font-size: 0.95rem; font-weight: 500;'>
                Industrial-grade 512D facial vector embedding recognition.
            </p>
            <p style='color: #4B5563; font-size: 0.9rem; line-height: 1.6;'>
                Uses the state-of-the-art deep model to extract distinct facial feature mappings, verifying identities against database records with cosine similarity comparison.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class='saas-card' style='text-align: center;'>
            <div style='display: flex; justify-content: center; margin-bottom: 1.5rem;'>
                <div style='width: 60px; height: 60px; border-radius: 50%; background-color: #D1FAE5; display: flex; align-items: center; justify-content: center; border: 2px solid #6EE7B7;'>
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
        """, unsafe_allow_html=True)

def render_techstack_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🛠</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Technical Stack</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Detailed breakdown of the architecture, models, and dependencies powering this platform.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="saas-card" style="padding: 2.5rem 2rem;">
            <h3 style="display: flex; align-items: center; gap: 0.75rem; color: #1F2937; font-weight: 800; font-size: 1.35rem; margin-top: 0; margin-bottom: 1.5rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 1rem;">
                <span>🧠</span> Core AI & Computer Vision
            </h3>
            <ul style="list-style-type: none; padding-left: 0; margin: 0;">
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>InsightFace ArcFace:</strong> Deep model mapping faces to 512D spatial coordinates.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>MediaPipe Tasks:</strong> Live landmark tracking assessing head rotation.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>YOLOv8-Face:</strong> Backup model to perform fast face bounding-box localization.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>OpenCV:</strong> Native system camera IO management, frame rotation, and image preprocessing.</div>
                </li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="saas-card" style="padding: 2.5rem 2rem;">
            <h3 style="display: flex; align-items: center; gap: 0.75rem; color: #1F2937; font-weight: 800; font-size: 1.35rem; margin-top: 0; margin-bottom: 1.5rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 1rem;">
                <span>🌐</span> Web Architecture & API
            </h3>
            <ul style="list-style-type: none; padding-left: 0; margin: 0;">
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>FastAPI backend:</strong> Asynchronous routes with validation using Pydantic schemas.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>Streamlit frontend:</strong> Visual dashboards mapping user data tables.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>Uvicorn:</strong> Lightning-fast ASGI runner hosting the endpoint interface.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>HTTP Requests:</strong> Communication protocol between the frontend script and local server APIs.</div>
                </li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="saas-card" style="padding: 2.5rem 2rem;">
            <h3 style="display: flex; align-items: center; gap: 0.75rem; color: #1F2937; font-weight: 800; font-size: 1.35rem; margin-top: 0; margin-bottom: 1.5rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 1rem;">
                <span>💾</span> Database & Security
            </h3>
            <ul style="list-style-type: none; padding-left: 0; margin: 0;">
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>MySQL / PyMySQL:</strong> Relational database storing user tables and logs.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>Bcrypt:</strong> Strong security password encryption for dashboards.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>JWT:</strong> Stateful user role authorizations.</div>
                </li>
                <li style="display: flex; align-items: flex-start; gap: 0.75rem; color: #4B5563; font-size: 0.95rem; line-height: 1.5;">
                    <span style="color: #2563EB; font-weight: bold;">•</span>
                    <div><strong>python-dotenv:</strong> Environment separation configuration files.</div>
                </li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

def render_comments_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💬</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>User Comments & Feedback</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>Submit comments, suggestions, or reports directly to the administration team.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("ℹ️ Feedback board is online. Your comments help us improve the platform.")
    
    # Retrieve and render comments
    try:
        comments_list = api.get_comments()
        if not comments_list:
            st.markdown("<p style='text-align: center; color: #64748B; margin-top: 2rem;'>No comments posted yet. Be the first!</p>", unsafe_allow_html=True)
        else:
            for c in comments_list:
                username = c.get("username", "Anonymous")
                user_letter = username[0].upper() if username else "A"
                date_str = c.get("timestamp", "")
                text_content = c.get("text", "")
                st.markdown(f"""
                <div class="comment-card">
                    <div class="comment-header">
                        <div class="comment-avatar">{user_letter}</div>
                        <div class="comment-meta">
                            <span class="comment-user">{username}</span>
                            <span class="comment-date">{date_str}</span>
                        </div>
                    </div>
                    <p class="comment-body">{text_content}</p>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not load comments from database: {e}")
        
    st.write("---")
    st.write("✍️ **Post your feedback**")
    
    with st.form("comment_post_form", clear_on_submit=True):
        comment_input = st.text_input("Type your comment here...", placeholder="Enter feedback, bugs, or feature suggestions...")
        post_btn = st.form_submit_button("Post Comment", type="primary")
        if post_btn:
            if not comment_input.strip():
                st.warning("Cannot post an empty comment!")
            else:
                try:
                    # Posting requires active session username
                    active_user = st.session_state.get("username", "Anonymous")
                    api.add_comment(active_user, comment_input.strip())
                    st.success("Comment posted successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to post comment: {e}")

def render_team_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">👥</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0 0 0.5rem 0;'>Meet the Development Team</h2>
        <p style='color: #64748B; font-size: 1.1rem; margin: 0;'>The engineers behind the Face AI contactless attendance system.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        dan_avatar_html = ""
        if "data:image/jpeg;base64,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" != "None":
            dan_avatar_html = '<img src="data:image/jpeg;base64,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" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 4px solid #DBEAFE; margin-bottom: 1.25rem;">'
        else:
            dan_avatar_html = '<div style="width: 100px; height: 100px; border-radius: 50%; background-color: #EFF6FF; color: #2563EB; font-weight: bold; font-size: 2rem; display: flex; align-items: center; justify-content: center; border: 4px solid #DBEAFE; margin: 0 auto 1.25rem auto;">DV</div>'
            
        st.markdown(f"""
        <div class="saas-card" style="text-align: center; padding: 3rem 2rem;">
            <div style="display: flex; justify-content: center;">
                {dan_avatar_html}
            </div>
            <h3 style="color: #1F2937; font-weight: 800; font-size: 1.4rem; margin: 0 0 0.25rem 0;">Danvanthiri V</h3>
            <p style="color: #2563EB; font-weight: 700; font-size: 0.95rem; margin: 0 0 0.5rem 0;">Machine Learning Specialist & Core Architect</p>
            <span style="display: inline-block; background-color: rgba(37, 99, 235, 0.1); color: #2563EB; font-size: 0.8rem; font-weight: 700; padding: 0.3rem 1rem; border-radius: 30px; margin-bottom: 1.5rem;">Student Developer</span>
            <p style="color: #4B5563; font-size: 0.92rem; line-height: 1.6; max-width: 480px; margin: 0 auto 2rem auto; text-align: center;">
                Specializes in deep learning architectures and real-time computer vision pipelines. Responsible for optimizing the YOLOv8 face detection framework, managing embedded datasets, and minimizing inference response latency.
            </p>
            <div style="display: flex; justify-content: center; gap: 1rem;">
                <a href="https://linkedin.com" target="_blank" style="text-decoration: none; color: #64748B; font-weight: 600; font-size: 0.85rem; border: 1px solid #E5E7EB; padding: 0.5rem 1.2rem; border-radius: 30px; transition: all 0.2s ease;">LinkedIn</a>
                <a href="https://github.com" target="_blank" style="text-decoration: none; color: #64748B; font-weight: 600; font-size: 0.85rem; border: 1px solid #E5E7EB; padding: 0.5rem 1.2rem; border-radius: 30px; transition: all 0.2s ease;">GitHub</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        bavan_avatar_html = ""
        if "data:image/jpeg;base64,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" != "None":
            bavan_avatar_html = '<img src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAHgAoADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9AZJm+9t56DnFNWbcuWx+fSo2kbZ82OvcYoVtrbl6fpXQA/cu4bWHGD15FI0jq33jj1x3prTKV9OaY0zL9M9AaBWsOZm+8zdDkH0NRXEzbT82ec9KWS4Xbt2kAfhUTMzZZenP4UrIYxmbhtpP04xTGbdjfxjv3zT/AJixKrkcnNRyKzMN2BimA15FX5lbgDqD0qN2ZvutxjrinyRqqjcxpu5R0bv60AMkbCjeuMD1qGRvmDKp+npViRlZd4xxzkVWlbGWY44yD70rAldkUkm35unYc9KjVlXq2PoaJJF3FvfApkkisw+bGM1BoK0m5envnOKYuzd8vHbOOKX5cbs8dc0jMvPzHg/TFABJIyx7V5GeKj3bl3KoJz09KJJGf5UPFN3MFOWOPrQAsjbV3Mpz0GDTG+6c9cUoZSw2sOvY4oZVEZbcffFAEZ7e3WmybSPmGKc+0jczEfjTZGUKCeewHegVkQMv8R69R701WYHcrYI6USfKx9abuXfu3c/XigY5pFZR8xzmom2L8249emMc0rSMv8Wee1RsrMxZcjjqRQA5ZO+39aPM6bV57fWmYY/dbt3FKo6BmxQBJGzL8rKfYDpTZJlVvugZ755p24Mpbdg44+tQuuZCrMDg9jzQANIv3t2f0phfc2fU5qQhVU46AetRtIqqdq4I96AGttUFtvJ6euahk3Mp3KfX0p8jbl+8Mg/w0xt247W7+nNAEe5V45/DrSSSKE+UEHNI0m1vvD+tRyNubd+OaBWEkkKtuVj14wcUx5GZD8pHvnvRJ90/Wk3Ns2++R7VmMZJIysPmPPQ00yLn73Pt0pGVmY7mxg/jUbRq38RzngkUBHuOZl3Hb9aT5tw+bAxSLGq/N3/KlVQvzLxz170DlqizpOh6j4m1WDQtMhZpbhsMyjIRe7HvX0j4b0O30nS7PRLSMrFZ26RKxABfAwWOBXlP7OFjDdeLLq7dQzwWoRSRnAJycV71p+k3ENqmpyRFVmJMbE4z6muyj8JlLcbbw7cK6HOKtxKy4Vc5JwB6mm7VX5mYfQHNZnjzxvpfw58I3fizVWJWGMiCMHBkf+FRW7dtwPNP2tviva+GvDj+AdKuFN5exFtQlHItbc4DMe9fHOnq3xW8XPeSW7jRNLwEQsVL9gua1fjl4u8QfETxoNCtb1ZtX1SXdqIDbVgicBkjx1rodA0Wy8OaVFommqTHF80szHLTSHG52NcFSbk7M2graFuzhXKxQxqigBURRhVA4AAryX9rb9oPw38JvA9011JE7opWNWYgs5wOg5ruvin8RtI+Gvhe41S9u1SRYstzyo7AV+cnjC++If7c3x6tPBOhX7W2lRztLeSrGWWG3Bw8jEGszW5H+xX+zJcfHX4mXXxi8eWkp8JaVch7aFnYC6u0YkIDk1+hWk6eGuFkWNERAEjijXACgYAGKyPAXgHw54B8Naf4L8H6clpp2mQiO3jjUDecYLMRXb6VpqwqsjL0PXrWbtYaV2WtNtWhjCsDnA6cEVd8xY1DNjAHWmKyqoXdgDp7VR1zV4NMtXuHkUlBkjGQoOeTWcn0R0LQq+OPFmkeHNGnuNQmyzRYEatgnPQCvKfhf4H8WfGXxzb6NpUMhaeUmac5Koo6k1HqEmv/ABn8epoGjwy3UAlCxQQR4Mp6bsjJr7U+AnwS0j4M+FksY4Yn1a7VTqF0gztHUItOKViKtT2cVbqdF8PfAGjeANBg0TS4xNKqA3N9ImZJWwM89a6SFVjx83PTgUyNo4owq/pzTkbd82wkCrjscT1dyRlDY6/yqS3haSQKvHOQRUSyBmCqv5HpVu1O1RGuMnuegrQC3H5kaBIYyWI/L615B+07+1D4U+Bfhi4lW9jlvmQgBSGJbn5VGak/aP8A2kvD3wi0Oezj1dUmCfvpomBcHONiDFfIXhLwS3xr1e7+PPx21N9O8IaYWkgguJmQ3oVsGJGWs20kdFKi5ask8D+DfEnx9v7n9oD9oXV30rwTpsrSwxzTNGt0VYBo4ytc/wDHP463fxfvotA8MWH9leErBFjs7CKMRG5CAKryBeKq/GX406z8ZtThsrW0OmeFtMIXSdIjAQEKNolkVflrkJGSOMLGoOB0A4rlk7yud8Eqe2xLbxxx46Z9qsqrK4EfQj1rn5NdZdbj0aO0nZ2Xc0yqCq84A65roIZDHGWbkgEn2qi4uy0HtIsK/d6dabdaxp2m2b3+p3sdtbxjLyy5AFYniTxno2ixyzTX0YW2QtczOT5UfHC5FeZaHoOs/GDXFkhM1noFgSs17I5ZmY5yqc4qHqQ9XY7e+8fN49vToHgHQ2u4lYG7vrxdsUQHRsZzWj4Z+HegaA326+t/7Rv2ffI93IZoI+PuojjFaWj6fpmhaamkaJZrBboS20cl27sx61ajbao+UDvWU3dlJaaitb2m0yR2cURQAqsUYQDH0r9Ev2QdL8MeK/hDo/jNtLgnvZrD7LdyMA2CjFea/OebUFhYr14xj2r63/4JbfFiPUNG1/4f/bEMtlercQxO+SQ67W4qqc7OzMqkbo+vG0W0hKtDpsAIOVKwrlf0pfstvEB+4QDqQFxirP8AaC+cLdiu4gnapyQP50jQtMxYqcZzycV2K3KeZJOMioscbSbY0I54OelaFvCzRjK44HNFjp8fnGSTJGMCryrGq7VXj6UWT1Yis1mpXK8Eenak8tVX5mOQf1q0zRqpZeD9cGoGbdJub1qhxSRF5KlvvY9MU+ONVUtzgdCOKeqqzFdvPTg8U5Y2VgdpHPrQkPRM8naZwpRlz3+9TVmVVDMvGOxzitrxB8PfF3h23+1XmkSSQgZM0B3BR7gc1gLIzMV79cHgj8OtdhiPkkbHy5H40LIzL868dQc5qNpPlKswB+tRNK6qPmwB3JoAmZo1ba2Qfc0eYqn5WGOhNVvtH8LZ+uaVZG454IzxQBM0m3ksTnpjpUckjBfl9e1IsisfTn170SMu0LuPrwOlADGkbbuK4OccGoZJmVvmbvnGKJpNrbtx49OKglm3tvX86ACW4ZW3KTz271FJNIyn5ufpSSMobcGx+lMdm+8uMeoNTzWRUV1EbzPvNz70m1N27P60MWZfvZIHFN8xlb5kHvg1JQjqytlj0OAc0MdvzZP4UM27tgY/CmMw/hbGPx5oASSSMj5lJPHemSMrL8qkEHuakqN1bcSp469eaAE8zcu1e2OhzSNJsUKOcHp6UM23J2nHuaY21WwcigBJpGfjaQMZqFpNvyq2CM89adJJtbczdvTmoGZd3zMPwoARpmVsMCfx5NJ5iryr89vWkkZWb7o9jmmMmFD9h26DNADmmKt8zYweg4pvmr/ePvg0xm3DaVxzng4oZlX+LHpQA5pFX8+KRG2tudjj645prbAud2O4NIsje3rQBI0m1flXtxUfmtndg9PXvSNMV+X0PYc1HJIqruWgB81xIuNjfmah852b74PPTHJpjMsjY5B9RxTGVVYr6Y5zildATNMqr8zD2GKjeaPnawB4GPSo2kRVPyng+tRSTMzbt2D6ZouAskzfeLdOnrUfmO33ufxpJJG7d/SkVvlzjHPUmpcuiAesjfdXAH9aSRtq+v04pvmL/fH5U1iwwu7t26UhK7dxGkZvlVfyOKayblHUH88Ukm5fmDZGfpzSK20H659MUGiVh6qqrtXI5zwaZJIsa+44yTSNNgfuwAeuQc1G2GzubkjigZ6v+yrG11quqyRyENFsBYDsUJFe+XF5LNaxQswCRIAiAdBgCvB/2RZFXVtbh/iIjIHcgI3Ne1apfNa2hXcDI4KxDrz6110NjCT2JVkhdmkkuNqRqWkbGcCvlf8Aal+Oseu6g1xbTZ03TpGi0u2Vsi5uAMFz2r0j9pP4syeEPDL+EtGvSl/eQiW/uVbb9ltyQCWPWvlixjk8d+Jf7ZuoGXS7AgWiuow7KR8pBzSrT6LccFd3JvAXhuTTIJ/EWp7pNR1Ncs8o+eOItuxnrW1q2tad4a0qXW9ScKkQzGhbBdvarG3dMGmfCnl2PAAr5b/a3/akt9PuL3wxoVrMZhCItNhchUuOcu5zXLq3c6VFI8a/bU/aO8WfFbxIvwk+FSzTahe3QtpJ0iy1s8mQgRDg19B/sq/s56R+zz8OLfw5HHFca7egTa5qITDSSEA7AfvVwX7H/wCzpNJqEPx2+I1vLLeyRkaBa3ZLGCNhgyc819O6Xp6ySmSTgk5ArNtJXGS6Pp7bg0qnjv3zWzGqxxhVYAD9KZBCscY2rg9vWiWZV/dqwyepJwBWUpXZrCD3YlxdLGpZmO1RlsHmvIPiB401XxvrP/CGeF5JP3koS6kRiQMtjHFavxb+Iy2+7wx4bvd9xIdtyYx9wHoM163+xz+ze3hi0h+JnjazJup8PptpKuSmf+WhBpRV2VJxpxO5/Zi/Z+074QeHItVvrJTrN5EGYyjLwqccE16/Zwqqlmck85OckmqturNJ5jDk+g4Aq0vyr6cc81oopI4ZSlOV2Sqy7tu7IznANPX5mCrwBxzUcLbl+VjnI5z2qaNWGFiUljwADmnFtMWzuKrKrCONSSSMAE5+tecftM/tG+GvgN4Nmuri/Q6lOhW3iVsseBnFUP2jv2nPDfwO8P3FwtxHLdqu0BSCXfGfLXtXyx4F8E3/AMYrm4/aX/ac1WW08MWzGSy0yRmj+3KjbSiMpNOUuVGtGnzsr/D/AMD6j8Yrq7/aF/aI1mbT/BmnSGWOKeZkbUGDYMcZGa534x/GTVPjBqcNra2Q0zwzpqiPSNHiRUAVRtWSQJ8tHxf+Mes/GHVYIUs103w5poCaNo0KBFVVG1ZHC4WuSlLKp+XgDHpiueUrs9CCtohrKqjbGMAYAA4xSxr5jbWJOO3pUe5tvyqfrjtUtq3zBdpJJwAOM0rFx1WpNHZ2jSeYsESuBkylACF6nJ61x/jDx0qWM9/HqZsNHtARPehsG5zwQuBmn/ELxnaGG605tTjtNI09d2sX7N98jGYlNcZ4S8J3nxv1eDxb4jtprPwjp0hGnWCnY1444OccUnJLcfQt+CfBuq/Fbytb8RrJaeHYJCbSCMlWusHGB1r1CC3tdPtItM0uyjt7WBQsNvEu1UFEk0O1YYbdIYYkCQwxKFWNQAAoAprXAjUfNx1rCpNvRDUbO4/dHD95QPoarXmpLGpVXwMeveq9/qi7TuYgDNYGseIILeF2klRVUAs+77v4Vle+guUtahrkit+5YhgcjjnNek/8E+fiBa+Dv2n9LsJLgxpraNZStnoWGVr58vvEN/r1zLFawvFb7grSElWfHYV0nwg1u98HfEvQfFFko8/T9ShmQtz91wa2pwluZzdj9udJ0G002QzMhMjLks7EgfSrczRhhCGAJ6LnGap2fiC31KC0mjyTPbI+VPHIzV+OON2EzKC4GASBkCu1JxR59RPm1GYaNQrMQODgdqVplZdq9TyKWRvmIVST0OKb5e35lU56n0ovYxejHR/NGWZsHoMUz5gwVVJyeMHmnxxs38RAx2HWpI41jzJtJx39KHsK7Y+2jVVDNkHGcZps00fO1sEds5wahmumbKqxGBxz0qo3nM25mO3PGDWi0RaTW53VxbyQsWhYjjn3FYOueFfD+vMW1nRIJiBjzVTY/wD30Oa6m++6V249MVl3Fu27co9fwrqkrO5keb698GLdVaXw9rez5si3vFPA/wB4Vx+ueD/E2hM32/SJjGhH7+Fd6EH3Fe2zW69WbntgVUkjkjysbEAnkDoaYHg7ssi/K3Q8jHSo23Ljacc969f13wb4c1kFr7SIxJjAmg+RwPqK5PVvhBJteTRNZDEHKW91Hgn23g0AcW0jod3Xnimtcs2NzAHqATVvWvDfiTQlMmo6TOiA8zIN6D6layXulk+ZWB9SDnFAE00kjLu3AjqAahZm2Bt2c56Go2uI2XarUzzduNrA4GBz3qHKwluiWSRVXbuOaYJF+npimfaOu7GOnBprSKy/ICPTvU6t3ZolZD2m/hVsYNNaTd905Pr0xTG3Ffnb6H0pqybWCtge4PSmMfubkl/rimtIvKr17UNNt+VFAPck9aYrfxKPy5FACqzr/Eev40LtblVJ/GkWRVUrx14xTGk2/Luxn86AHyqrN94jBpkiqqjn1PHamNKy/KrZOOucVG0khUq0mCOBxQA2Zl3FV6561EzBRubqOlOkbaxJb8cVGzbmI9/pQAkvzfMGIP1qKRmX5d3PrmnSK3BZievPpTZFbb/gaAEEjFdoaim7W/h6epHemszq33jnIoAc3b5scZ4NNVlVT83POKGb6kg9+9MaTavzLjnjntQA5mGC341EzKuWZuc9utDMzNtVhj1ApjMWXDNwD9KABpG5ZSfp0qOSRmXauM5zycml8xVYsOmM9eajZlb5ueuOlZt3egCNu3fM3T+VNZVbq3Q8HOMU5dv94+vApaAImXbjP60xY23DdwM8nPSnyMy9jjrmmNIzLtXp78UAo9xWkVV3KR7UzzActx68dqFKr93r1psknlr8uDnrigtKw2Qq7bVkIxx0PFNZm+4DnPNDSKq7tp6/kaY8yqNwXHpgcVLkkxgxUDG3kZxzUEkjeb8vHbrzilmm3Y28EenarGi6bJqd6lrtLKWBkIOMJkZOadwPTP2VWn07xdeMtuZWuLZwsPmBSxVRznpXsfirUo9HjudekUyLbW7vBCTgyFFJCivHfA18/h7xBY3WnzRwpG4iyyA4QkA5zXpmtatHqf2jV2wLVbd/KEjgKFHDEknFbUZuOhlJdD43+O/iHxZ4u+KE3hq3Y3KXtys+r3isD9mj2grGRkVp6TYw2VtFp9kpMcS7VLAZPTLHApmpeHrew8Za7qVjcyXKX+rTTxyyhTgM2SqsvFc18afihZfB7wBe+I7mNZJ0gYpAHAY8cHHWnPV3KpvlZg/tF/tFaF8J/CN5cRzrG8MQDXTuMBycBQAc18tfs5fDDVf2kPGsnxG8aWpbw/p8+6QOCFuZV5CLXn/gS3+Jf7eHx1aC+vZ4tA0+4E99eQOTFa27FkZAQSK+9PB/hPQvBnh6z8IeFtPS10+xhWO3hjXGAO5xWFtbm3MrGnYWisojWMJGoAjQDGAK29PsVjjG5efpzVfTbFY8NJ26Y4rQZlhX7wHHGKxnLWxcF1YkzLGNq8HjOOtcB8T/AIk/8ItpCw6RfIt/cMAuFDMg7nB4rU+I3j6x8L6VI32pXuGYKkK5y5PUZrmv2fvgp4h+P/jddd8QNJ/ZFg6m5uGG0FQchF7VNza6jG7Om/ZF/Z0m8b6rH8QfF9mw0mzfdbROP9fIDnAr7AghjZUWOEIiLhFUYwKpaHo+m6Jp1vo2jWyW9naxhIIoxtAAGOlacK/L8vHOPWqikkcdWfO+Ymjj2fMy5x0xQzMzbOxPY0ir/CvHfrShWZgqqSTgAA96szHb9jBY1yx6KOoryf8AaY/ao8O/BTQJdPtb5JdTliIIjYfu/UE1B+0r+0ronwn0abTNIu4pdRaNvOkDgCIYPGc5r5j8G+B7PxL9o/aP/aR1GaPw9FKX03T52ZH1d1YjCgEiocuU2pUuZ3E8D+B9R+KlxJ+0r+0xfPY+ErRi2k6TIzA35VipVSprmfi/8X/EHxk1lLi9iFhodkQmlaNCqpHEijarsF+Wofil8VPEvxh1xNT1mIWWl2gCaTo8ACR26KNoJC4Wucl2L8xbA+uCDWTk5SO6EVFCqzKu3vUVxcfNtLD8OlJJMqptVsdxiqlxcLu3buR6HFBcbNalhWZmG1iSenOKy/GniGTRtPTSbC48u/v1KpIG5toujS1NJrFrpVtLql2pMUAyUU4LseFQV5hJJr/xe8WSeGrC5aOOTEviTUouBbQnpAh6VLkluXay0JPDHg2H4v6ykMbTQeDtEmzK6uVbUbjBBBINevbooYY7Ozt44LeGMJBBCm1YlAwFAHFVrGy0zRNMt9E0S1W2sbOPZbQRjAA7k96Sa6WOMspOeNpz0Nc0ql2KKaRPLdeWp3N7jnGao3moNtKrwcZznpVLUNWbkbiCBkEnANcL4n+IEd3dHRvD14ZGZSs8ijJzxgDNYttsrmVrmt4k+IOlWe+E3hbC5aGJCW49T0rmzeXmuyG9vWZVZ8xx4xtHaqun6HDDMb65kLuCSATkD3Ndd4Z8F3Grqby/kkt4SMRsV5fnnFdFKhJvUwqVEir4Z8N3+u3a22mxlU6y3LLlIx7npXoek+F9K0eELBYrJMgyJnJJJ74qXTl8iJbO1jCIMYCjBJAxk1ft4ZpZEs9PhM9xIdqRRgE5PtXoRjGOxyyqO5+k37GvxDg+I/wM0e/kkDXunQCyu1LbirRgAEk817NasfLHyk8YBA618t/sT/Bn4rfBvw8mu+LvE5sbLUyZx4aNmrOSU2q7uTmvqLR5nuoEufJZVlG5A4wQKejRjKTerJ1UBgpjOT6ip1hh3bpBkgZxnFPjt/4mXBI60LHCWxIQOeueSaEmtyJbkLNHHJujUA9QRxVa4n3LtVfTJxUt9eQQqVhUZzx71mXGoLG23bjnOR2pqy1ETSwySRhlYDByeM5GKj2xxxvLNIqxxrud3OAKpa14r0jSLWRZ5mebbiKKMYLNx6iuL1vxJrPiO7S1VpI4JJAtvY24LGQngZxzSe+oK6Wh9F3Vqrfe69ODms+4t1/hPf1rTulk3ZXv3qrNCqqdzc9+MV2ppmZkXEaLltuTn0qlcR/3VrUuvLVjt6k1TmhX7xP5GjkVwMyaELncc/piqdxDuzuXHpWpcQqq4P51UmjVfr7cVOqYGRNHJGrKrna2QVIyCPpXP654S8OavGy32kRqxHyywDYyn2xxXUXSqufmxVG4jVlLK3bp0pgedal8KVRg2la2x4JMdymCT2+YVgat4R17RVElxYvIh6SQjeB9cV6lcR7WO7J54x2qrKix5dcqfUHFZO92VFdTyFnkVjGykEHBBGMUxp1X73H0HSvS9T0zTNUJW+sIZSTksUwfzFc5qXw5sJlLWGoTQsBwso3gn69aZRy32r/az+lKs3zbhnPtVzUvBmu6arNHCtwgPD27ZyPp1rHma5tX8u4hdG/uSKVI/A0AXfMXhmYj1JFOaRQu4SADHr2rO+2Dd8ykH8sUNc/MNrE+wNAFxrgbuM/lTWmZvm9upqq825vvd/oaGuNv3c4HvkUr2AmeQbvmz1zxSMzN6cHt2qv9oDNu4H0PejzG5bcMZ6k80uZASyzFVG1znPTpUTTclm9eCBimSSLu+9z0BFRtJuY/NyPajmQEjTKq7SoGT1z1qJrna23rzjg4pJG+Y/Nzj8ajYPnfuAx6mmpJgSNLtY7WP4ZpvnbV+VsfXgZqNW/vOPzprNz97I4ouA95mLfLk49Kjkm3LtXHPv3oZlXhW59M9KjaRmyV5IPQUnJJhra4vmt/e/z+VDMzr82TznikXdtwy0jb9vy4zScuwk7jZPn+6xH401WG0bW6fhSsvzDcCMZ6U3btbdu4HPvSGk7jlZeze9NaReN2Rg0Fo1+bd079cUySZV+ZV9epxzSvZFpWVhZJFZvl/DFRsyr95uTzwOaa9wrHdtPGCMU1pFZvlU59c9qXMhjWkZm3Lkj0x3oZuu1vwxR5m1vnbA5IBGTUbSM33W5B6VDetkANK3KqtRPIu07uD1xStMFUNu571BJMkjbW6Zx1waYD7eGS6mWOONmdmwqrySa7Dw7pK6bZhWUCWXDTEHOPRc1keFLGNZBfrMSVyqqF6H1zXRNcQwwtNNIERFJdz2FKLs9QI9Y1qTSbRpoeZWUiBAeWauw0fXr+bwja6RqTMkjWRS5QKFILZJHeuA8Ow3PiLWU12RjHbWjkQxFclmHIPpXWxyMq53EnOTmtU9TNtNnNa34H0i3li8vUZQArFYpNpz+Vfmz/AMFK/Gn7RHiX4023wJ0T4dXa2WpTLHo93br5i6gCBls4xX6TeLr62tZGmuL5YnIJUvngD9K8u8U61ZaleLNHHHO8Lfubh4uV5/hJ5pu9hLc8n/Zj+AWkfs7fC608GW6xTaxdAT65eqvMkzclQSM16jptirMsijjrn0NVLWNriQszZJOSx71sWqrDHuVsDtgdaylc3p2ejLAWOGMNtOcZFYnirxVZ+HNKl1O/mSNFTMZY8sc9hVjxF4gsdB0yXU9SnWNEQlSxznFeXaVpPir4/eKbbRNPQswYqCM7YgSSxJHFZXOhWRL8MPh94o/aS+IJhjV4bCGTddzgZWKPPbtX214I8G6B4E8PW3hTwtZJDaWyYJUcyHuxPWsr4TfC7QPhR4Rt/C2gQKJAuby5IG6V+5NddEqxKFK5I7+lVFW1OerU53psSRqqrtXp06VNCu1h8v1xTIY8tu2k8561Ztbdpm8uPk9ec4FWYys9AjibiONfmPpwB715N+0r+0jo3wi8M3FppN5HLqM0bRhvMACNg5UNkVP+0D+0HoXw30C4tdP1JUlKES3ecBVx82w5zXzJZ6bZa3G3x++PXnQ6HBJnRdGlkYSajIrHBxytYuajodFGinZyK3hvQINatZPjv8f7maPQ0naTS9KlZlm1SUE4wMla4X4lfE3xP8WvEC674hUW1nbL5el6XEAsdsgG0EhflpvxB+IfiL4oeIDruvbYYYVEenadCAsdpGBhQFGBWKzFVG1c4689DWMqqctNjtjFR2FaRlww56+2Kikm2ruc5AGRxjFLLJu+ZV6cH2NV7iRQu7dxVcyRZHcXi87WA75zjBrOaZprgRxtlmbAGaXUrlVUqrc54xXIfEXx8vgjwncavbzKL65JttOQ8sXYEbwOtZuorprYDnvi/wCN9R8Y+MLT4NeA1+1XEs4S5YZ2xNjc0jmvT/BfhTSvh54Zh8MaRcGTaTJeXRGGuJjjc5rjvgV8Lo/hroT6zrMIPiHVE3XkrtloIzyIwx5rs7i+2qWLHgZ9cVlOV2LVbFq4vFVSW+vWsrWvEVlp9u1xdXqxqOAcE4P0rN8V+MrHw1p0t9qF0isADFETln57CvK9Z8Za34z1lf3sltasQIYRg8j3AzU3LckmdL428X6jqFwlno19sR1zPIFKnnjHPNQ+HfDVvYxquwM6jAZlyTnkgGl8P6DLIojm3tPkFgOwyccGuz0TTYbGQqrBpHIC4HIFdNGjzatHLUrNOxL4d8JWcJW71WASOR8sLMcL7nFdZZ2rMqr5YAAAUAYxVXTLHaoaRsDGSSMACu9+Gnwi8SfEq+hW3lGmaSWAuNXuFyiICVJUDmutR10M7qS3Mrwh4V8QeM9dg8LeDtIlv9SuXCRwwrnb7k9K+5f2bv2VPB/wQ0yHX/EsEOp+KpFDvcyANHaE4OxAa3vgd8Ifht8F/CsNl8P9MR7m6jLXesSkPNckcferq7i6bcS0hLHkknOT61WrepzyupF9tUZpDJNIWbOSSea9C8HW82oeGrfU7CQzRpHibY2TEcklTXkcl0ytu3Z5B64rtPg/4i1GSHUNAtbh0hkIdyHOCdpyMCquhXu9ztG1pYsrDgsBgMex+lUJtQYqWkkJJ7k9TUU0Mm4q2cjqcc5qjNGq5bzMnnNTZJkvVehNJcSXEgjViWJwPU1ga14qiW7k0/RlNxcRDDycFFPsKzvE+vavHrCaJp8gSAxq00inBbOSRnrVW616DSNKn03TLdBc3KlZrvZ8yKVxhTTSTZK3Rm3lxf6hfTrHK91cW8ReWQAkIvXkjivT/gPoOjW9qmv30edTEQH2icBxESP4EFc78B9Q8PWq3Wja/awCF7jfveMsZfkChWAFd38QviF4B+Ht/LPq+rxrczKZFsbVAZXPAHAFDlyyKs2tD0CSHZjcx+gqjeQhWLK3XnrWzJDHgFV57VRvrfcpZVx9OK642S0MjBuI8HeFyP5VXlj3feUgZ9a0LiFlY9j9OtUpo5C25ePqOnvVgU7qHdyrcD07VSmgblkY9605EbcVZc1VuI1VvlXH41nLYDIuLfruXn1rPuI2VtqrxzW3NGvO5fzrNu4/mO3IxQCV2ZNxblfm6A1Surfcvy+uDnmtWeNmPzfXpVG6haPlc1k9zQxbqzZWLK5H0PSq0isvIU988VrzRsfmC/XtVK4jzltv5UwMy4G1vmUZByD0IqrfWdtqEfl3ltHMuMAOmcfj1q/cw7WLMcfj0qvJE24svPNAHOal4G0a4UfZfNtiBgbW3j8jWDqHgbW7V3ezkiuEXldjbWI+hrvZIy31/Kq1xHtzz835mk3YDzWe3vbZgt1byRk8gSIV5/Go2uJI22vkH6V6LcQxzQmGZVdDwVdcg/nWNfeDdIuiZI/MgJBH7s7h+RqHdgcqtyrIN3UdzxSGbd8qyAY9DV3UPBOq27EWzRzKOnlvgn8DWPdWd/YsVuraSP8A66IVoAs7lZv9ZznHFJuZW+8fzzWf9okjPzKR9TUkd4gXazf4UAWZGVuHY5Bzimecv3dvJ6VD5zM2d3bgU4SLw27BHPTpQA6ZmZvlboeh7ULIVX5hnA+lRyTKWHzYyevSk3Y+bd0GM0DiluOZ2ZumB6U1mZfu9frTWkZWPYAdaTzemWHPIoLJFZlX5gfU0bm3blY01ZkZdm4ccgCopJG2lh6daAJtyr97GT/OkkkZl2rxgcVVaRlX730pFuHVsM3B61LkkBJNMyrtGc/TFQGZt27np1xT2mzlccZ44xUbN8pbvUNNu4AtwpcbufxxSNI7N8q9TxTGZV+YZ/8Ar02SZlQeXkHHXqaYBM7K3zL06HsBTPMXbu3fhUck0ithckgdc1E1w+4tz14z1oFckmmXd90j9TUun2Ml9cLDGCMnLEDkDuaqwyNNIArYBIHTNdZoumrp8LquSWYF2J69OKCXLU0LO3jhjVI49qqAEUDGAOBWTql4viDWbbw5YszRBi108ZyAAcMMipde1qbTYo7axBa8umEdqijJByBmtTwnoMOhWrwxsTLcssly+7ILY5UHrQLU1tNt1t4UjhQIiKFRAMYA6VbWJmU7geRxUcMTRqG3DGO1TR5Zdqscj07VSb3AxfE3hzS/EWnyWOoK0bMDsuIx8yV5J4m+GninQrh5mtzd2akeXdW/zED/AGl617lcQs0Z3J261ntayLJ+7YjkHgcGi91YDxSzsWt4w23GAMnHQ1JHJskELOACckk5wK9U1TwfoGqOzX2nKjsMGWA7GH5cV5N8b/AvijTFsdE8EXUk8msO8SEKAycAYzUy3Li7tHlviy41n4rePYvB/hrdctFJsDRrwAcA4HSvrP4HfB7Rvg/4Vi0qxtUGoTRg3dxj5ieuCay/2fv2fvD/AMFtCjaSNbvW7lQ95eMvQ/3V716dbwlm3MuSTkk8Gs0kXUqJuyJ7VfLXczEkkknqSamjXzGG0YA7VHDGy4+XGCCOc1Yjt5NpmEZIABJAzitDFbk0O3btVgCBkk9q8u/aH/aH0D4Y+G7qFdViVihSUhuScdARzUv7Rfx78O/BvwrM95qCLd3ETCCAPtdyBng18w/Z/t0J+PPx/kkg06GYvoXh+Uskt9KMfNg7lrKU1FHRRpc75mS7o9Zhb43fHiSa10NJM6NoUjHztRcemOK81+IPxG1/4peIv+Ej8Q7YYoFEWmabFgR2kQAAAA4qLx54+8QfEzxG3iXxLIEVF8vT7CPiO0iHAUAcVisylslsjqcCuNtydzuUUloStIysflyB3BxTGm3NuVccdzmmSSK33c8479KiaTa5+Xpx6YovoXFX1JZG3Y3cdOlU76RljbaOg6jjFTtMzKV6AD8RVS6WSRdq4yxwATjJpRk9ugrtaGHqV4u1vMmCKoJdifuqOSTXG+E9DuPH3jb/AIWVrbSro+lN5Og2LjImcHPnHNV/iJ4t829bwjaiSOS5uYY5mCkZhYncQa6fQZLPR/Dlvp9nCxjtYiuC20sdx5z0pOUbg9HY27jUpJJGeSTJJ+ZmPU+lcn49+JsXhqEQx2yyu6lgpk2lyOuODXL+NPjSvljS/C6yS3YlaMNGu4BjjGARWX4T8F3VxeprPiG7knmlYSCKSMqwOcjeGqYwcpWE3CCuyOws9X8Y3Z8Q+JshJsmKFQUJUcDFdr4f0Vpo1W0tI0WMgGUJhUH161c0fw7GsnnSttU4ACryB6V0VvaqyiGGMKg4VVGAK7adGMdWcdSs3sVre3MMaWNixdiOXYbQT6mtvS9Lg0+PzJJWllc8tggn2A61N4T8Laz4p1uDw34R0abUNRuH2xwW6biPc19h/s4fsfaV8MZrXxt8SY4dU13AeG1Vg0Vi3biulamDbbPJPgp+zXrfieSHxR8QbWbTtJjbfb2EiFZroj+8DzXq154fm8LauLjS7x3t7ncZoGboc/lXs/iLTbfWlEvmJBIvIZU+U/UDmuD1S3kjmls7qEqwG2SM+lKV90KLtKxu+CfiLZRxpfNebY4yAAW5UHg8V3Vj4ktb+Bbi3mJDdATjJ9q+ddWW40LUY9UtrUTpAxKxb9u4NxjNdX4J8dq2n/aLLTRDNC376AzbsZzgg4FZ83K9zRw5lc9em1JWfO4nPHWuq+DniCPTvEUlq0Jd542KkAfLheteVab4iW8hWY/IW4wTW14X8SLo+u22oNMyspKgqepIxWkZamck07WPfW1SK38yOa1MjOpCsWxtNU302a8s5buBizRjIjQZJHGaux+H9R1C10+ay057hdTjLxYAC4HJ5OBW7Y+HdZ0aN5msSNqkbYiCoPuRxVx1dyZOx5h4t0ia1ih1COPIclHIGCD2rk9QjkhkzMpBPIBGM17ovgLV/FcSeHlWGBr1G4JDmIgcHjivEPFmnapp2uz6XrMDW89k5hkhdcFWBOa0skhbO5iXHjC68JTT31xNBbwrFlri5m8tIxkENnIrx7xx8X/iD8Y/FV14Z/Z30xmkKoNS8U3xPkwLkDahcGu3+NPw18L+KZdN8S+PvGcljomn5efR4wUN4+MZ3Bs1wvij4x2GjeF5NI8H28Ph3QNPTECQoEkmz7g5rixFT2aO3D0uaKaWp+nTQsvrnqKp3SqqnA78VoyK23ayY4wD3qpdQ9d3b04r1FZHnGNfQqzfuxg44qhNC33mbnrwK17qHa24Ak9setUbi1YMTnGffmqAzLqPapCr756VSljZWLc9PzrUmj3DaoJx1JHSqt1DtHofXFZy2Ay7iPbyT/Ss3UI2CllIyOwrXulVu59azrqFtxUnAz6UBHqzFmkk2ncuMHg5qrNNtX5ufqMVrSWasxX36EVUutPCtuCnHYY4rLW5oZsm1l4/A1SuIVY9/r6VrSWqqN20HA6iqckPlsWYe44pgZNxbksd3OOlVJ4WX5VXpzgVsTW+5idvHtVO4tdrHaT2pN2AzWVuVVc8dKguI/8APTFaMluq5Yfn0NVJo9zde2ah6vUChJG3XOenPrVeSMcbR+XcVoSRM2fYfnVaSE98jnPHGaAM+aNvw6+9VJoWkQxtkrjBUng8elac0P5j0qrNGyMflxnB9KAMG+8L6VcKQbXy2PR4Tgj8OlYWoeC76BS1pcRzEchSNpP07V2kiM38PPXHSq00Z/x5NAHn15Z6hY4+1W7xg9Cy8fn0qOO6kVv3inr6V3U1uzKUA4IwR2NZt54d064JaS1Ct/eiOw/pxUuSS1A5rzkY/K2M/gafGyr/ABcYyOcird54SnjbdZXKtgfdf5SPx6VnT6fqdixa4gkUKcFtuR+Y4pXY1siZ5FVfmyB0qNrhV+7xg9emKhW87MCPTnNDNHIuFbHP60tb7lkjXDMMq2c85prTNghmPoPSq7Ltbdu4z2p6zKqj5s9unQ0rO9wJW2soZm/I0jNGvyqRnP0qNpN2GVsA++KRptq4znJx1zTAezKqhsHoOh61C0ysx2sRznrTJpuvzdOMZqs14qttZuvQClcC07KzbmYn056U2RsZ68Dg4qONpGXzfuqBwzDFZuqeM/DWixyXWqazFDDAhaWST5FA+p4qlFbCvbc0WZucNyenrUUivxtUZzXkXib9uD4C6EzIvjXS7gg4AtNRjkY8+lbnws/aa+EPxIvBa6V8Q9MWUrn7NLdxK68+xquVpbGbbbPUvDtj50xmkjJKMAhzjJ9a6S5vLfTLCS+uGASFctzyfQVk6PcQtCt1pmq2skRHEscisoH61XvLibxXr1voFvqsD28KmScxSKGduQVAFS4qwy/4O0+41K7l8UanbjzHYLZqwxtX+8BXY2NuyqGbI4wf8KzrFbuOGOO4iZjGoQER44HTpxWlbzSKvzQvkdAVxihQTFdMneT5jtUjnPXFSQ7tu7d0xj2pkMyyNtaFlI5OQRxU+3aPulfQHina2gxkkjKuG+tQLubIVTwcVZaFpF3Mp4yKrNDJHJtCnk/nVPRARTQszEtn27VJpuh281/b39xbrI9qxNuWXOwkYJq3b2MkzDdHxkdq19NsVQDcuBxgEVnLoCuhlvaybt0jEnOSTyatrEyqFRe/B6Gp1tlUVJDG24KqgnPGPSgIptjbW3kkkCqCSTgV59+0V+0t4P8AgxokvmXCSXSxM8EHm9Wx0Y074+/tH+FfhJ4dudPt7iO51GWElAJAoTuck818u2sa24uv2gPjxcyQ2gnMumaXKxSS/lU/KccpWM5pHRSo8z1IvM1Ca4n/AGi/2jJpmRZifDnh6R2je7mU5XCneleYeMfGvib4ja6fEfim6G6NdllZRDbDaRjhVVRxR448ea98TPEJ8T+IWWNVUJYWMZxHaxjhQAOKzJJNny5x6VzSbkzsjFLQJJFX/Go3lZm+ViO9DSBs49euai8w/wBwdfWkXFdhzSbW+bOfU+lN8xlbduz+Ypskjbu4+lRtN5a/exj9KycuxTa2JpJmU7uBVW6vFjUMvJByMHFRzXytII9+Cckn0rzn4lfFe10KOa6hVxBasAxDqGLcdM8UxO7dzj/jD4sh034nqtqojkXRjKwAzhxK3fpXO3nxG8ZeMbebwxpdpMq3LANNHhhEueSSMVy2sWvjD4x/FB7vwxbzR2wt1immnG1bZASSCVNepeHvh3Z+HI1tdMhe5umUJNdOPmc9PpVU6XNIynUa1M3wf4bfSGSy09Tc3crKJJNhIQ5z8uea9N0vQ4rFR5kjSSE5dieCfanaDoseiWpt1ZZJHOZJFHB9h3rSj8u3xJNkkkKqgck+wruhCMHocdSo5Ins7eNV3OwAA5PSvRfgV+z58Qvj7ra6d4PsWttNhkAvtZuEKxQjjIBru/2ZP2IfEHxOWDxx8VfN0jw4SHtrH7txer1HvX2Voel+HvBmgW3hbwlpEOnaZapst7W3XaB7k9a06GadzB+C/wACvh98AtC/sjwbZLLeyri/1mdAZpzxnBrorxo1Zn3DJySfWmzX21fvZPX6VTurpmyytk9MdKpOKQypdX81rM1vNMG5ypA6qenWsLxJIt1GFjXc5ztwegFauoL9qjZVZgyqWTHqBmvBbf4q/Fzxn8R7/wCHekeFbgrbTxrI08KqIgUUgk4WsZzaQRWp1GpX0Muo3NhMqu1uwDxkAbcjNcxcXTWuomSzm3COTKMAVyPT1r1Xwf8As6eGNRZr/wAbXUN3q0rF1MFzLF5JOS2NpxTfiD8D/BHgy0N2sl0VMbvIounZiBg5Fcc6kmzqpq6MPwh4is7y2VbciORAP3bPkg9a6201yJSk0xOEkViB1GCK8E8K+Mmk/wCJzpTfuxIyBXIJAB4ziu603xza3Gnef5hLqmJAeMGqp19kxTp31R9zfAjWNZ8U/D631GbV3b7JGlvaq2cxqScDOc16ldW8el+HYtO1HUkurlkUyGKTBLE7snPNeHfsWeK76P4eC7hhSRrmSKG0jnX5S2cbgBivePEngvxOus2vkXlixmUSXMwJVYWXHy4PNelTaa1OCbdzR0fw7pd5pP8AaugSPYXVigZ7m6fIGB827ORXyH+2h8VrLwJ46n8S26xXcGp2ivBcRkPGZVCjqOK+rvFa3fjPwvqvgfUnNnG6BZ7y365B3A4NfMv7Uv7LmneIfh5FpGm69HKRG720sQzIz5bJwRtrR7aBFx5j4w+JPxts5ml1XxXqZ1C+lUG1tElyoB5ACjivG/FHifWfF96k+sXAEEIxb2kQwiD3rutQ/Y1+JMN3NceHNUs9UmDHzbcvsdD/AHTnivNfHfh/xN8Nbt9N8caJdadNHkHz4yFbHcHpXkVaNeUrt3PWp1KSiuU/oCuLM7trL746VQvLXaxG08f410t1Zrt4GD2PTFZ19ZfKW2nIr2k9dTxznJYVXKsOTVO4tFZTt59hzWzcae0jlgpx7VVmsDGp2qcj8K1Aw5LdlU7uw6jgVnXkLcrycdM9q6Ca3KKdwOcde9ZmoW7eYfl6HqBzWcrtgYNxC3Pymqlxbtt3bemfwNbc1q2doUk9qo3VrIWK7e/figI3uYzQ7WLMpPOc5xUM0as3zevOK05LORc7uOevWq9xZkKdynj2xWctjQyLqNVYsuO5HOKz7iFmXOc+hxk1r3VnI33VP1BqjNYv059etAGXJHtXa+B9KqzKvOxhnHHHStS40+RcszcdvWqcli247c/QVk9wMyeFmU/nxVOe3YNub8MGtiSzk+6qkH061BNp7bd3Ix146UwMaSNmG1V9iRxUM0PXcvTHtWtLZlWJ7/lmq01q3oB6Y55oAypIcffXt1qvJCfvdx3xWpJa/wB5s/h2qCS1VgW3dO/YUAZM0f8AFt465zg1Xkt1xu/kcVqzWa8sq9/xqtJbtu+XGQOvp7Vm5dgM2S2jb5duMe/NQzWXy7lX8a0prdlJZowSO4NQvA33gMAfpSs73YGJcW7RsV28HpUEkbK3ysQfUcGtua1Vssy4B7g1WuLVcfKoHFMqOqOcvtFtLpzJJbAMxyWj+Uk+vpWbceGXVWa1uRkZwrjGRn1rp7i1Zc/0qs1uzsVGetBRx1zY39v80lu/BwSBnB+o4qFZGbO5cdPauyk09uWVsHHbis+80WJmLfZ1BJJyq4yazcuiA5uRmL7lYjucmommaPLSE4DDBzitS80dvM3RtgA5I96ydet302za+mmVIokLl36cHvRF6gVNY8RWGkafNqF028xr8sSkgux6DNeJ+Pv21PAXgayC6vNNLdrgSpYbJPLJB+UnIrxf9qP9ti38W/EFvhN8P9TK28eUu7u2AZpHGQQDmvmH4t+OpbHVp/Ou4Hs7AIHijByCwAO6umEU9RN6H034z/4KSNrt3JZ6dCNP09AAJ5HzMw4Gcoa8K+NP7Rdv4l0NtG8L+Jr25S7cLNC9yzuSCSMgivCfFXihmm8qRltbRVLtKTjevUgkVzOj/FLT9MvWkhsp7hopA0UhYKpx75rRLqRq3c9d1rRbDRtGtr2adJLu5cCSJ1IODk8A81znizxF/wAIhpy30MqLJKQIYgxBY55xiuRsfijd6hqcd3rMwkVYygEkhHGeACSad8S/GkN9YQWtpDDLCvzJI55RjwOlO6JV7m1oX7SfxG0PFjpvjLV7G1lYCWK0vnVQO5IBrb0P9pb4l/C3xNa+NPh58SNRhvI2EguEmZgx/wBpSSK8IXUpI23NjPc5xk1f0bX7CTU7Wx1EuttLMqO0cgTGeByeKOVMHoj7Hk/4K2/tm6MsC3XxPguGljDADT4jgdsnbW7oX/BZj9sXTYzNNq+mXa44FzpiH6nKla+V77xN4e0uT+1tOsroyI5jijklQhyDzhjWW3j121FZpLLykJJLKqkp7cUmrERbTPvPRf8AguF+0/8AYIrGXwr4cF0BhrmSzfDc/wB0Pivaf2VP+CtXxF+IXiZdC+MOiaQFuXAt5rCJofLU92BZq/JyPx5cXF0BDAYl8wFScEqPwNbGheO/EWh6zFrvhy/kiuYXBDZ4cd+BSlZGlz+iv4UfFHw/8UdGhvdItpElLBZrcupMBIJ+bHFdd/Z8bMG24wRkEdDX5l/8E4/25F1eWLw/J4ntIdQYKLnS9QBDPgYyjV+kHgHxJceIrB9UvII4nlcFIY23YUDrmgZuQ2ZjxtAA6gjirtvH5ahuQcdcU1WWTCqvOe1WVhkjjC7STjgA8k1hPYFdsgmkZZArYJPA7V5f+0z+0v4X+BnheW1juo59ZvIcW0IYDYO7HNSftH/tEaN8IPDEkOmyRTalcRkQI4+50yx4r5R0+10+4vJv2gvjhdSXUYmL6Ppk7FZr+Xgr8hBWsZy5Ym1Kk5Gppqq1u/xu+OV3NHaLMZdN012Ky6hMDlTsOUrzP4hfEDXfidrY1rX1WGGJQmn6bFxHbRgYHA4qPxr418SfEXXW8Q+JbgKEytlYRHbFaxjgKqjish5lVd3Tjr71yyfMzujGwpZV+XaRgflUc0m5gqt2546GmSTMzbVPB4yDyaTdlSx7ZqU0aC/dbc2cZ5psjfKdrD8Dk0LJlstnHbHaobi4VfmLEEHHWs5SuwV1sK0yquNwHocYxWfdakvI8wAA8sTgAVHqWrRW9u0kk2xSQPMJ4FeXeOviqt0zaRoUxZJjsZ1iyCTjAGeaer2RLmomj8TvivFo9q+n6ZMWmYkEREEgdyxNeY6X4A8RfE7XGuL+1ktNMhfDOzYAxztAJzXW+E/hXeTXCan4lmWOIkuttG3zMc5G7NdyscMaiGOMIoOQqjoa1p0G3dmE6z2RU8M+HNG8NaamlaJYiKNTksBy31rWtbVYm+WML67e9Rww7F8xmwBySTgAV3PwU+CXjr4764ukeDbExWUTD7fq86EQ269+a64prQ5m21dmB4Z0HW/FOsweG/CukTahqNy+yG2tkLEn1NfZP7NX7D/h74ayQeOPiysWq+IAoe207hreyPUZ7V3fwS+BXw6+AGhCw8JWa3OpTIBf6zcIDLMepCmuwk1AsxbzMknJJ5zVtpEvU0brUJpMCSTG0YVRwFHoBVWa4ZvnaTJ7HHaqcl8u7czY4JGDUUmobW3K3I460XQrluS4bbu561DJPt+Vm/CqU2oN/e/Xmq8mobj978uorNtsFdlm6uNq/K2MjnvWV4Yt9P0bxNf6vcbEN+wLSbMkEYAyQM1JcXysvytyO/pWddXCsxZX5ByfrWVRNq5pGNnZHr+h2ekado0l9CwlmuCVTjjbjt3ryb9ovxXa2Xg+TTbWYSXd3bvFakE5OeGIqx4b8W3MMb6bcNkRRFreU5yDwCprzvx9Df6lr9xcaxcCaWKZkQr91F4ICiuOb10OiHu2R474LhuPC0MumXluQJZFLFmIKMOM4rdutQmsVaKGQqHOXCnGfat7UPCcOpR7dgSQD93IDyPY1y95p91Z3j2d6h3xnAznBHqM1UU0bOyWp9DfsI/E2O18bR6ZqGtpDDp15HeJHJKdoMZyWxX6YeCtU8N/ELQDrGmXk13cSSkFlkwUY/NyBxX4t/BfWJvAXxm0jxfaqXhW42yw7+TvOwgV+v8A8EkS0tV19b2RFcLDCpOVCnG446V34ebascGJgk7nWafpeppqr2J0a3t4ipE8ty2S45GRXkvxM8KXfiXTtU8KaQoFxb3Dm1LAc7T90c4r2TWvDcfie4WPWnlit4wxt1iIDkkj5mzXHeL/AIOeKrS4e88F+Ioowyl0NwCGQk4C5wRXdG7ZxXcZHxEvhjXfD3iqfdayQSC5IktzAwcn/aU81c8e/CDwp8b/AAnN4W8aadFJG6bVmdAXiz3U9a73xt4T8QeBPGF/eeMJCl3czsGEiAFjwS4AGK3vhT8JfGvxGvP7V0S1htdNhXzJJ79SEn5+6oHNHKpI19pJPRn2VNaxt8uOcZznmqV1p67TtXJrV8tf7g/OoLiH5iV/QdDSTszHU564tQrFmXB59sVn3UaeYeD16iug1C3ZlLKpJ/Ssa6jEbFtpznqetbKSYKWuplXMKrlljHfBx0FZd1CrOWVRk9TjGa2rr5gWwRzjNULiFmztXHcEelQ027mhi3UKqpZlGcHvWXdQs0m7bwDxwSK2r63bcX2njv6Vm3EJXLDqMHOM0wWhmzKq8MuM9BmqtxH3Vcg+1aFxHu+51zwR6VSuImXKsSACOorNu7RotTOuI9ueeTkjFUZFZmPQY/GtK4j25ZW6n0qjMrM21l4PYCgClcR/L8zcY7VRnhEefmJz+daM0e7Py9ecAVSuLfc33enfpis3e7ApMq7jvYnnqfSmTKrL8vTIqw0Cq27nIHc9DVW6Vg25Wxz+NAFS4j2scOBk9j2qnMvylm5AHWrcyqrbifpVWZS3HIH6UAVJfLbKtwB0+tQTKq42sCMZ6YxViaFsHbk454qtNC235VIxzWbdtgK0y7furgdetQtGd3ysMehqxNCxbbu9zUEisrBXX/GgCGaHapPP4VVkj3L8xPH+c1ckyF5b29MVVmWRmO1uOo7YFAFaRdq/ezx9KryIG6e2DVmRSrFlU9M596hkZl+XrzQEdipNCrZ3KOtQyWqqpZVHXr15q6yq3TP4VG0bZLbTjODjjms3LojQpNGq/wDLMfgear3EMbZ3KAe31q/IjLlVU9eKrXLQ28Ml9cSKiQJvdnOAAO9AHK+NvEGjeFGtrW7mZ7u9bFvbIpBPTJJxivk//gqz+0HcfCf4aWnhLw5fvFfayJDI8Um0pbqo3HI5ro/B/wAVrv4ofF1tfuNTa4tLCVRLcg4EzISoIA+WvjL/AILH/E9tU+L1hotjc71h0IKqowIG53BoirL1A+V/C3xCu/DF/qHjBZi921rKYnk5+bgqea4dfEeq65qL6hrOpXEpkuPOkUv3PWpbyS6uoFtYYycEZCDIJA4qhNtsYy8jBTyAScEn0rohLQhtWJtYa/1jUZLiFZTCihUQkjCgAcgHFUpLe4tZCsilWA5FS2d5dtEzRo3zAgOBnB9qasd4zD7Qzv2LyEk1spaEpBppka4Amk+UkcHoav69fTPAtnJbp5bHcJC2WyPaobHVIbBWjWwhkdhw8sYOP61FeNJdsbiRAuTnaq4Apt2QzOuG+T5fXgA1TmSSRtrKQD09qt3R2yBS2BSQw+cw2845yKht3A29B1pZmit7+3Vo44gA0R24YdyCauN9ikun3Xa4OSqmQLn2rKTSb6C2S4jjJDjPUDA/E1WnkZWCysQTxnPWruxW1udBb2casZVzgcnjtV7T7xbSZLhYwxU52E43D0rndNvr7zAqzyOGO1gWzntWxb280pH7s5PTjBpWTjcNTq9J8WPoWp2vifQr6W1u7WdJIZUYowIYHHBr9f8A/gmf/wAFN/hh8a9Etvhl8R9Zg0fxXDEsUJncLHejGMoTX4rak11YxhJI2QsDgMMZFV9N1zU9HvYtU0m+lhuYHDxSo+GUg5yCKi9heh/UxYLIypcQssqOMxyRkEH8q84/ah/aN8P/AAY8OnTlZLnV7qImCzMmMqMEsxr8xP2E/wDgtP8AE3wdoEfwq+IWnLrMiIBY3lxciNxgc7mY4r6I+G2pT+Nb67/aa+Ol1cpYwTCXSrC6G2S8nBO0BDWM209C4JOWpoal4b1ea+l+Mn7R88kNlCVfStGlZTLfSFVZfk6V51428b658QtfOv63iGOMbLGwiOY7SIdFA6UvxB8e+Ivid4kbxJ4jkCRx5TTtPRv3dpFnhVA4rFaZVb73THGOhrzpyfN7x6UI2SsPZmZdq8nPGeKgk3KxbqQcH2oklZl3LnPr0qFpm3bmbOB1rNtmpIzAru6HqOajaSP724ZPIOar3F4y/wAQAHUgYqheas0alt3btQK5dvNS8tiqtz04rI1DXpI97K20IMk9SfpWP4q8UtoVg2pzW5cJgsDKFwMgd68rvvEfij4lXj6Po8b+Sz5uSBlSob5SxoinJ2JlJJWNXxz451fX7p9I0S6aSN3WOERryx7gCtjwP8P08PQrqWq7JNQIzGqtvWEHnjIqx4U8I6R4OgEluRPdkDzLtyDjIGQtasN19qmKRsc+oPJrqp07as5py6JlhpmZvlbJ7kGjakI86Z8Y4AHc+1S6bpepatqMGi6Fp017f3LhLe1gQszsfYc19Vfs+fsfaJ4NaDxl8XI4tR1gAPbaSAGhtT1BftW14rQyurnAfs5/sceIvif5HjL4meZpHhskPBag7bi9HbAr7E0DS9A8HaHb+GPCOkQ6dp1sgSK2t1wCPVjVSTULi4YMzYCgBVUYCj0ApGupGUfN78UubUiTbZqLdNJ96Qj8elNkmaNv9Zjng1nLdMq/exznmo5L7d96QY6DA6Um1sJXexoSXhVSysevXpUMl838LZIPriqDXjbvlbPfjio2vGVi24/n0pO25aiktC/JcM2WVsHsM9KrTXTbvmOTVWS8P976VBJqC/xNyOhxUuVild7FiSdtm1mAP5VWmmbdlW/H0qvNfbfmZgfQ+lVZtUjVP9YAcdQaxlUujWEbI0dOuJItTg8uT786Ix9iwql46sbeLVppo5A7SXMpY46AEYFV7HVt2pW3kzBG+1RkORnaQ4OcVL8QryzstXVZpCJJot7kdiWOBXNKa5tTeMbNGDJJHG21lGcY645rO1iOG6he3uIxIjEEqTyCO4NMvNRaOMzM2FBznGAKyLzxNHDMEWPflfmO/GD+VWpR2TK5ZbmXfabNpOp2+q28xkSCcStEVwQAQcZFfpR+zl+0hZ634T0zWYbwz2E6xrFE0JCxsM5ya/OeGaHUlZl2liPmQnGK+vv+Cft5YSeB4dGbbKBqhiZSu4DgGuihJKehz11emfcPhDx0uuz3Ws3txK9hbQgRTHAWRwMnauK6Cx1C7123lvJrKS2tiw+yiZQpZSoO6vOPDN7DY2CaNMzLCtztQSPhYkbGetavin9ojwN4Jmg06OcXsggCrBp2GWMDplicV6qbSueU7XLHjnS/Cuoa5Jq+vaVHqi6fp0hgZYlfy2GG2jedteEL+0z4yvNZk0bTtKtdOsmcRo7pvlUkAHDA4r2LRPHtx448P3dzfww2z6gf9FJw0jxspGNvFN8P/A2wubuC+vNGmtra0sHK5Cq0s56MRjNUnYd0tWevUxl3fXHWlbfsO3rjimRrl927ntx0qbEle6t2ZTuAPt7VmXFmwUsVxz1Pet2UbV4BqncQ+ZGSWA4/WqjqSrXOduNP3MW2gY5zmqN1Z7WPy/iK3rqHbn25yeMGsm6RlkP6e9UbGLeWLYJb+VZ01nGzbWBIz24xW9dR/KU46HA9KpTWv8XHrx2oAxJtNhGf3eT1zis680+NgflA7cc10FxHtzzjr71nXkOWLbueuaye5S1Rz02n7cqvH09Kpyaaqsdwx3z1NblxCysdynHPNVpYVLbVWmUYdxaoq/c5AxnrVV7RWYt5fb6Gtu4tVbO1f6VVkt9qn5Tj2rOW4k7mJNZxqxZV5z196p3FmrMW24zz1wRW7NCrZO3H86p3FuFUsq9OlAzDlsYdx3IQT2681UurONWyqHGOADwK17iFlbcq4OetU7qMMpbaenYd6VwMia1RVI2nOfXvVWS3VcrtI7jmtSZF3DcvT17VVmjDZ2/l7VAGZJas3zI3v9KrTWrKw2tzWjcR7csq8+tVZg31wc5FAGfJauG+Zj7EVDJbsrf6zPpxV6bYvO7vnIFQsse0/nnOKnmSQGfNayK24NnI64qtNCy53KM9Pqa0pkjXrnk+tVpI1bkLgCoeoRtYoeSyN8/b0Pej/lmVfse4qzJCq/d5457VFLGyqcd+RimaFOdmX5dvuD0zXnX7UniZvBn7Pfi3xHHuLJpEkQKnG0yDy91ekyQs33m75HbiuB/aV8Nt4z+AfjPwjbw+ZPd+HrlYFGMmTymK+1AH5t2fxrsvhjImhSEI13Zx6hZToSMgpnLcivin9pP4m6l8SviLPrN/c+f5ESxrIWJ4GTjmug+LPxI8Q+I9MttGjuBBdaLbG03GT95KnJ214lqGsXF0o+1Tlm2gHJwQOuKcbNAXYdUkhzJHsJySpYZx+tYGo6o10qRpdPKFYtuJOCfXmrd1qka6MdOjUBnkLNLnJA7isb5WYbc5z0ArWnLoSbWn61cLYx2q2sW6NzghSNw9+a6bSfsWqWLrAwRtuJUcAFeODXKaNcTWk3mmNGyACsi5Fat9eW8NqLnTJnQsAJlcDgnqBit4vQi4TQ28MpaVsAHHHOah1SSFbfy45sZIPytg4qjcak9xhefXB9aqXdxJJ/F07Z6Um+gXFmmhRt3mZP1zmnWOoRwyr0YFwCCegJAqluZmOeTzj2ojkaNgxxwRgeho1QWPRbiOz2rCsy7TgBt2ciuT1lg2ozRqoVUlKLjgEDjNMh1aRoRGrkADABbpUM0jNncuMk5OetDlfQeppWOtQR2YhubdFljIEckK4LqAPvVv2+oK0atFcLIqgAOj5wfwriNzKQzMQAeg44qazvJLeaSSCaRUYAEBsAgdM9qd7In0Oq1TUo5oz5k5ZlHQtnHtWSt2Vbc3TqMVjTarLJKzSMzZPJJ61JDdnaGXjj64qX3BO9jotF1660zV7fUbVSXikVkwMjcCCMiv0Y+Dn7YX/DRWkWOjePL+Kz1zTLZYobFV8uFwFA3qucV+amj6lNb3MVxbxqzRyhlWQfKcEHnFex/CjxXPrWo21yY0t7uN1Ects2wghuoySa5qztB2N6Kjzan6CzStGxWRencd/pUDXC7i3qfxrgPDPxFt5LaDTZL6WSQIFleVydrY6jNdRa6k0ke6Rs5HPfFeZJ3lqeik7GhNebW+924A7VWmvlVfmbH41BNeKq7mbGPesrUtSVlLLNtAB56g4plPQs3moNJJ5cbZJ9D0rkvHHxB0nwtaC4kZZrhmxHBvKl/pxXO/E/4z6d4SjaysJhNesgKojDKHnrXC+FfDeq+M7p/EvjO8uFMpAjVRtZ165xjFKMXKSRjOfQ0obXxH8UNVOq6ncvHaq+x5SfljGfuoM16Bptvpnh/ThpejweVEDkgnLO3qx61nrdrHGkNvGqIihYo0GFQDoABUkcyqwluOvQY5zXZCKpo53OTZoQyNcMGdiAOSCcAV2fwm+EvjD4ta2uj+DLA+WjA3mpSjbFbr6lq6T4Dfsq6/8RvI8VePGl0rw+cPFDjbPejqNoIr6t8N6f4e8GaJF4a8I6RFYWEK4SGFcF/9pj1olWUdETyu1+pQ+D3wV8C/BbTRDoEIvNWlQC81i4QF39QgruIZN2ZGc5JySRkmufkv2ViysR9TUlvq00alkkyDjgjOKwVV9RSi7HR/alVflUg+uKbJeKq/NJnuMHpWAurzO25XIwR0FJJqTHA3HJ+tHtluVGnK+ptSakqru3e/JxVabU45AF8znOcYxWW18zN8rHOOlRtcSfebPHvQ62th8krmnJqbK25ZOgxwOlQyawysQGHr1xWfNeMq7VXn3qu8zMxbaQT3xSVVXCNNvc1W1ZmO1sgnkHNV7jUG3HdIQO2DWdJeNGvzE4B+lUrrUlZvlbAHcGs3M0jDlsi/catJyqyH8TVG4vpFUt5mTnIGc1n3mpLbqZJJlVRwXZsAGuX1zx3fXWoweGPBNu9/q11L5UaJEHG49AM8VzzrRjqdEINs9a+FGhWXiO9utW1lpBDZMgtowCFkkPzEkitH4m3HhVrORNTuI90Y5MSncpz2OKh8AfAO/g0KK4+KfjK7W5kAZ9N8P3rQCJsceYSGWu2Xwp4Ts40gsdKM+xQok1BhOzDpySMVh7SU9S1B82p8qap4iia/e303zZF3YQhcFh/Kr1n4N8VajG17Zac80CNiSdZVAByOxOa+jvElzpWk6U7SaRarEqsWEVuihQPwr58+KvxCur3TLjS/D95awacs4MskabZJQwAK1pH1LlG2pU0mRoWLNJkHB4PFfUX/AAS08RWkfx9m8J38gaC8snlihJwBIoyCK+PtH16T7KkcjA4UYJ4I7V6P+zD8Wbr4W/H7w14wiZDGt8sM4Y8eW/yN3rsoStJM568eaJ+m3xD8QNNrOoeHNNujbK1wQkSglpVHJG4Vy8PhmPyWa5iV5JF228QTcxY8A5616h8SPA9ppqW3iq1gRzdACeUtjGQNuBXmsPhnW9K8WQXk2ppdW89wJ/LMjbQQ2QrA17cPeR5ErJnsfwD+GFlpWkQ+INVm1D7dFI6GC5LKiNjadoNenTvDHC0k0gSNV+dmbAA9ya8y0v486b4di0/TPG9k9sLqUp/aMAxAjFjgHPNegawIptIuQ0jtC9u2XiG4lSO3am1bczu1G5o0wKyyblXHpzSqqqvy/WnUCFZUZdoqvdQqqHnn1FWVbcgKmmyRrIh/lSi7MDGvI933eD71mXkO1SxHPPTiuguLNSpbnj1rIvoWVj6fStOZFKWhiTwszFmxgYziqlyrKhXaccjAHNalxD8m7cc/yqhcRspO1cc/h1qXJdCjKuo1ZR6jpVC5jWPKvwc/nWvcRqv3lOScAelULq33KXK/4GkGqZkXEbMxVeeaqyRbcrt7fkavXkMkeWX+WMVQmkbd6c9cUA9SvNGytubIwcCqsi/N8y49u9W5JGb73Y1XmZfu8ZxkZ9Kyl8QFG4/urwfWqdwvX5e/5Vemj+b8ep61WmXa25l5pjuzOmh3ZbH/ANaqV1DjI256fhWo67W2twe9VLiLr/hUO1gUtdTGuLfcx+Tj17VVms2ViydPrWtcQ/NtXrnHAqrNGy/KynikWY93C65LL/SqUytyu08d62biNTn16/SqU1sv8QPSgDJkVmyWXA7VXmhUL1wOvWtSe3Xdjb9OMVUurRl5Tis27tAZskYZuv09DUUkbbvvYParU8LK24L0qKSNhh24Pr1oCLsyrJEysODnoSBQ0Xy7+pA9Kmkjy3vjgio3+5/wKgtO5Vmh/iKgjrycc1yvjiFre3vftEANteWLoWD5GdgU5FddIy7du7oa5D4w6xZ6F8PNV1e7bAt7KaVTnBIVCTigZ/PP8e7O+0D4ka/tZCbfVZoghXg4YivJNQlaa4Z2IBZskL0zXvv7U/h+/tfiFqN3rKm1h1G5e6V2GdwckgivAdUh3ak9vDKshMhCMBjd74PNXCN0KT2IM+YpXdjBxnNaFj4X1NdMXX7mzaOzY7YpHYDec7eB1rofgx8Or7x14/tdIgtFmhjO6cM5CnPy8kc1678Q/hdL4W8PReFJdJmMMLYhlkCsCOSDxWsY6jja54LHaSPlIYycDJI7Uya3kjUiRSB1ANelL4DtYPD4gjj23TcEK2QMNXP+LPDNvYzPHp8MkjMikru+4e/WtNUy4xT0ZxTKqn72SM9B0qGRX/hY56+lX5bVtxMfUE5GelVprO6Viyx/So9pFMmVJopszKxUr/ShNzMGwODwR61I0EqyFGhwwIyCcc1Na2puHMca5YdQOaTmugoU5N7EMbTL8y5/E1LC7MwVlz9eKJ7doWK8nBI4/lRGucfKQTSU1sU6UuwTfKx3KR71FJMsalY24IxgnOKszRny+FyTzn0qnMu35VkIOARxVqSM5LUiZmVtzeuRz1qRJGVgwY4x0zUTbtw+bPT2py7lzu4weOc4o3IldK5p2dwqqGjbB9uK9j+A2vaVa6VH9vhRnSdAhjVVYNz+NeJWsjbgqtyRn0r0D4NXjL4ihsbjBiZg4J5III6CsZW5Xc2oayTZ9p/COxure3l1nVbcqZziBZCGIHGGxXbf21Dbr8rcYwcGvHv+Fl3djCtvbMY0XCk56DtVOH4s3treGa+YiJyfMIkLbB64ryHNyk7HfF2Wp6/NrzXcjKrFVHU54FeU/Fn44w6fIdC8KMZbsgqXVuFPIzXH+NPjzqOt2w0Lw0skBfi4uSMEqf4VB5qX4W/C6TxPcx3E2nPcSTEFZWk3CIAjLHBqox55JDlJJDfBfgPUda1r+0/EMzuxO9kYhixHI3DNeo29i+0MsZCgYVQMBR6Cuo8M/BnSPD1i1xb6YRck5aYyk4HsCcV0vgP4FeJPiRqq2llD9l09WzeahMPlRM4OMHNdUUqK1OOUnN6M4Pw94X1/xfrMXh7wppk17ezMAkUS7guT1Y19D+CP2ULP4dLZeMNfls9d1C0ZXvtOkjZ1QcklF6V6J8PvAPhH4V6UdG8I6cqvIoF1fzAGacjnJOM1trdMrBlweehGQfauapX53psaRp9S9oviRdas01GO6EkbKAqrgeUcA7CBV5rzc27cMDpk9K868Uapq/gbWF8S6Rp/n6VdOF1K1gTLW8jPl5goIWum0TxJYa3pUGs6VdJPaXUYeCWN8jB7VmpK1maKKuby33RXYdOvapbe8jb5dwH4dKxJNQyx2yZpkeqMrDcwGcdOc0m76IbSOje6t1XG4ZxnI45pPtce0HjpjJ71gNqjLja35mk/tZmPDD6g0uZIaSSOhjvo9vysB9CabJqCL8u4Zzx71zzattXiT8Ae9Ryaxu+bzOh7npSuyVG7Oha+hZsswz9cUyS+hRS3H1J5rnG1rb91uR2zUU2ss3zBsfj0p8yKUbG1qF4si7lI6nB6Gud1LWltZNrRlmJOTu6UrawzfKpJH1xisrVJlm+YtznruqW+xSTTK/inX5dUUW1vCscKYOP4mIBySam+BHjDQvh74m1LV/ELCMzApaztHghOCVDdax7xlZSq5OetUZlXdyoyPU96ynC+5rGXQ+h7f9ojQLy3Vo5IWjBO0+fk4znGaz9a/ac8LaeojluDuJIKxncAPXgV8/TRRrlioB6k45NVWWNchVCj2GKSg0hq90d/4u/aH1HX45Ley054kO4Ru0mSQcjJzXnLTTSQiFnJUMGPHU+tE00Ma7lx+VVpLpWct5mBnitIx5Rp20Reh1Bo1Cq2AOmeMVYj1ySzlg1GFiGt51cEHnANYM+orH/ER75qvca0qwvGrZJXAB5zWkZWZLSaP2u8C/E24+MXwg8I+OLeZBbXGjRlY42JAfaobNa/h+GFr15LqGN1RMx+YMgNkV8u/wDBKz4tya7+zm+gzamjz6ReywLFI2fKQneuK9w17WGvLR4re+lQBsgRSFd5HT3r26FTmppni14SVR2NH4v6rp/iGwm0S7voBHbTbre2tTl9wHG6qmn/ABd+JcPgtfDVvqbpY2UARZog291ySMsa5WbXLWznK3yyTO7ZcA7jz3Oea6Gx8QQzWySW9yskTAA7TjHsRWspMyUb7s+vF3bR6+3rSNGoO7nrnrQqDdsZieOntSr8uPaqIHKFC8U5Ov4VGp5257ZqXsD9KlkpakVxnafm7frWTqCqclV98mtO43O21Vz369Kp3kYaM/LyfxprY2MKZVVirDvVS4jVs7+mfxrSuLdlLM6nHaqN0m1Tt49+lMDJvIlVjtYk5PHSqMqsqne2TWlcKzMflOR36VSuIcL8vX8jSuBnXkKtGW6/hWPNEqyHdkY54PStu6V4yU3E/jWbdW+5Sy4PPap5tLgZs8at8w49PWqs1v8AxbTntWhJGVY/LwP0qvNtbhV5xx2qetwM2aORW29QOarzL83ytk9eTzV6Zfmyx7n8qrTRtyVH5UwM+4/UHNU5m5OOwq/dR/MQF5zVSaNV+Vsj+dZyeqQFGZWZju/Sq00as3zHvgmrkyMv3fcVXmjwvz9z096CotMo3EKr8ydfX0qrNEP4mPXP1q9IvVfxFVZovm3K3H9am5RRmj2thVJOcetVpo1YbGX/ABq7cKytu57kA1WkVm+ZuoPpUW1uBn3Fuv3tvrjHODVW4hbHy9M1pTJuztPvx2qvJHuY7vxBpgZUg+baVwe57mo5V/izx/Wr81uqtu7evWq00aqu7ryKAV0VZFVl3DHA446VxHxr8C3/AI7+Hmp6FpDAXU9hNEiM2A25SK7qRFb5dvvms3VpGtofOTAIBPI4IxzQUpXPxJ/bR8DyR6JLoHivSlg1nTLhordghV1RcFg1eEaf8ENA03wVF4v8S2lwzyyOIVSZQMgnGe9fqd/wVA+B3g3xBpFn8UX06OHUFuEjlCAr54Od2ccV+e37UniRdP07T9Is1RAI/NaJIgoKsNvAFdFNLlM5P3tCL9knwZcW99qF1oUBnaV1BkyoIwrEKTkGvQ/iH4Z1TVo20SbTJWukYDhMkAjOK6D/AIJxeAZ9S8BXvja9s2ZNRu/Lt0ZMjbHldwr658J/CO3hI8Q3Gjxq7gneZckD/dIxXRBLluW3rqfCmo/CJm8PwWNzpU8E0bAx3IiwVJ6qcViw/AzU5pJLK40Qx2cu5TPNCDnjINff3jCx0iy06S1sL+3il3EMViUn3Br52+MOrS6FcPHZ+TMJBi3WVMqMYJJ2msa10tDqoPnR8Uax8JtRZZ7O18PTSXtvOUlkjUbSQ3PPSuOh8KX66utnPp7QksRtc5IIr6X1C4uLG5lurpYxLPM0rhF+Uljk8GuU8SrHqt+L9o1V0UqpRQMDOa4pTktEelCjGx5dpvwriuLi4ur6SB3kCiMqpJGOPpXQ6D8JLCOF4dPjjWY8iSSPqO9bFvtt5wy4IAIweorpvCtrDfXEclwrrGGy7Lxgemaz9pUehoqC3SPL/E/7P2pXEjXuiLG7JGDJDF94nn1OK8z8ReEvFXhaeOPWdEnhEoJiLKMtjrxmvrm+a1hkKWqgAjH09qx9Y0+11OFo7q1hd0UmKR4QSpP1puUr6GM6MPmfKbLNtPmQupHG0jkVBdWNxCoeZMDPc4I/CvZ/HWl2uhLCtxdLtndiCsG3OCPQV51rlrbsrKpDYOQxHI5rZSaSOadOPQ5R1ZWC+vQ9KVY2ZflYA5wM1ZmtSsm2PAOfTnNNlt2iUNMoGQcZOM1pzNHDKm1LUS1XbIFZST3INdp8LLtbXxrp8kzEReZhyBzg4FcXasvmd+uK7H4aR/bPGOn2ix5aS4REwOjM6gUpNOOgQXLLQ981Ca9vJ49P0+2knuLu6WC3hhXczu7bVCgV7P8AFL9mq48LeHNC0zXrmS1ubq2ldmRPLERG0fMOTXD/AA/0Nrf43+GNOeI7h4msnUEYB/0iPBr7t+KHgPwtqHiawk1fRo2eTTmDtKSwP758fKTisKeHiosdSu3JHwbb/sz3Vtf22owMNQslcmcwbt7AdsdK9J8FtZaHcQQrpwtVUiNS8e0gDg8da9I1LwpY6DpCw29sFMEjKbl5T8+WzyM4rsvgZ8Lrf4mfEvwx4BvoYGbUtetYluGtgSqmQA5qYxipaFzqScCbwT4P0rWZob+986CIKDsZANwI9+K9OtZLOztktrC3it4UAEcUMYVR+Vfrxrn7Cv7Lnibwza+HNf8AhFpLi2t1iS7srb7NKcLjJaMg14B8Vf8AgkF8HtrTfDn4l6no9wpJaC9QXKEHlRxsNXUoTrLQ5qeIVJ2e58DtdMG3buD2FOjuPOkEaNljwADya9a+K37AP7Tfw+knk8M6JpniK0iUlbi2uQjFQeMo7Ka+dfEHh/4mXbTeHr6Kw0y4jciYSW0omiI4IzyK5JYWUdzrhiIM6PVry3W3ntb23E0M0Zhnia2Zw6MCrAjGK8f17xlq/wAHPF02jaPqMqaXrDiW1B2uYi8myNP3mBXVQ+AdX09G/tnxzqQBH3bDUWQA++SaW38GeFGkjvNQtZtUmiKmCbVpludmCSAAy4rm5XF3OhTV9Tso9UZo1K6gLkMoYTqoG8EZzxgVDJqEm7cshyeQetZa3ywqF3DAGMegok1BWUsr9+1S2NN3uaDaxdLld5AzjpSf2xMGz5hODyBWY10rKXVvxziq0lxKrEx8dDwaXUZu/wBsMV3eZ/jTW1hmbcGz+nNc9JfSRsc8nr1xzUMmrSK33iMdecgVQ1ax0jav/D049aik1TcvEmB164rm21iRT97360yTVZGUnnpnOaCzfm1ZY/m3n65qpca4rKdsmSO2cVgXGpyMpxIRj0NU5tW2/KGyT3JpXA25tYXcWEnOe5qpNqmzLeZz1znisabVFP3Gx261Vm1JlzubIz60RaYRT3Na61Ztp2sQPY9Ko3GsYX5pMH3PNZNxqzBT8/A9TnFZt1rCNnEmOexqZS1sUl1Zt3Grq33pDn2NVZtY2qdrY9Oc1gzaptYNuyfr0NVrjWGZtysSPrUc4e89DWutYk3HY5Hb1BNQNqzGQbmzkj2zWLJqUjMep984NIt1JIwYZAA9c0+fqh2SR9qf8EjvH1ha+PvEPgG+1FYpNQhintYXfAfYzBgK+7fEkcMV5ItipWMHgE8fma/Ib9knx5N8Pf2kPCfiVrhYoTq0cFw7NgbJD5bE1+v2rxxzad9suGKrLGAmO5PFengavPBo8/FKzucY1zJdX8s0zbmdyc+3QU9tWuLbEcMzhd2SEbAqzcaWIW84cZPHY1B9j2yBplIB5BAzkV6TbaPPUUz725UhNvHftinU1tzYKsenH+NLubaFx079Krd2IDam7d3p38DfSmjrSSzbUK802JbkFxJIrfLyO9VZmaRSrZ5qW6uGV9qqSfbtUUKs2ew96ZqZ900gJXGec+lZ8zdd2Rk9q175Y1Utxn+VZN5947enrUN6AULlV+4uOKo3DMo+ZRmrtxuVj6k5NUrpl5ZifXPep1vcChdFWYtg/hVC4Vdx7A9z0q9cOqt8v69apzLuY7unemBSuFUKcfn/AEqhOrLyvqD71fuGXlVHvVKZtzH5ugoApzLub5sj3qCb5V2tz1FWbj5VO3sciqszM2V5/OpckgKlxGrMXXqPeqdxH/D/APXxV2Zdq9zVSXcw3bTn16VDTbuBTmXo239arzKuz7vQZq3MrOfmYA+3eqsyyK3qKYK6KVxGqt8rYOfxqnMu1tx45zWhMq5+dSD0qrNGG+XvnHSok7aFppozriRFUsOg5z6VSuJv4lXJyT6YrRntQzblUememKqzWnXd654FIZSaRmXg4qGZpFXKnPOcnircltt/hx6VXuIW2/e9D9KAKsjNu+ZePXOKqzbpG2qucds1amLL+WBVdlbcWZiPfrQBUkj253LyDgjsKo6xZrdW/l7ipByGA6VpyRtu3K2Rj6ZqCaPcpVlxjuKAPjX/AIKn3lxo/gjQfDNgC8l/cO5YcYCKo71+T/7YN9Na6np2l3KlJ7eERsc4J6Yr9mf2+Pg1qvxC0O18TW8DyRaTEwjVesZZhljX5Cfts+Bb7VvjnYaBY2kivdNAkUTDB3NJtxV05WVgVnK3Y+wf2YpPD3wW/Zz8PWet6rHavHYJNP5gALySZcrg1xPxk/4KP6h4a1N9D8G3sYt1GHMj5VPTmvL/ANra81mxvLXw1Z6hM0dtbBkgJAXJyMivmnWtLm1C5aS6keWVjkiQEk1r7WUVZHZDDqXvHuPjL/goZ4jmllkks4ZJC27fFKfnPXtXIXn7bGq6w3+naBIpxhTv3gD6EZryjUPBN4IWvFtyoTAJBGMH6VnLpf2dvmbIHU1lJtq5vCCiz1eP4/zeLdbhtb20dEkG0eWSoB7HBrW1O/ljyqyEA8Bs43CvGreOOErImQVwQQcEGt3w/wCIL2GQ2rPJJHKwwN2dpHpmsH7zuelSs0juYbrD+Y7E9zzXQ6Hr01jYhvMVIixJLY5I9M1yUkd1HCq7MOQCAT1rmPFDsytuUh1BDMCQRSSu9TScnyux1WsftDKl1Jbw6YCEchZlAOQO+BWBeftE61Mzpb25jG0hdoAzxweRXB3SrHJ5cbYA4GKiW0ZmDbck98Yq4pX0PMqyu7G3rHxJ8Xa/bi0vrtXjVsglcn6dKxmju3ba3ToADW7oOj27W6tIoDDJOR1NakOjWk0wjkt1bJ4OOlNrTUai2jkrPR5ri5jhaMjfIASF6DvXokPwysf+EPnmtoxJcpbNPHscncQpIHSr2heEdMuI1kuLXcQQUYPjH5V3vh3SY4VMcygqE2xgDIAIxQncznST0Z8pR2skN2bdpN/lkAsBjsD0r1v9kPT7PVPjxpNveoHhhhkkkU5Bb5SoHFcn8T/DNv4a8f6lplnkRG5LRqVwAMA4FXfgpdavpnxU0W60OCea6N7EPJtwS0i7xuXirUvdOKpHlkfbOuaDpHhz4teHPEOmXBMo1m2laHeG8srOpHQZr7n+OehyW/iTStVuI/8AR7jSv3LhhltsrbhjOa+QPiV8L7Pwda6X4ommke5l1GEuSxAQFyw4r7T+NLSNa+GtLuEYm10MMJHPL7264rRL92ckpWkfGH7XHjXxF4H8RW1rp1nZT2culrNIl1as7CR5WUsu1lrN+Fn7eXh/wRLbt8QvC+tWV/bSA2ur6REilGByWClhXW/tdeEbPW/EmiLqVw8cMtgqSvGvzACUkmubuPgp8L7y3kt9M0Vo4pUIjlmmM20kEBvmNc0LOWppOWiR9zfs/f8ABc74hyJb2OjftJeHtejRAg0/xRAttMTxhRuAevprwv8A8Fa4/EiwSePvhPceZKgWS90S8W4DEDrsFfgr4t/Zw0jRryaG+sbm1kWUmO4E25HBOVKgCm+GdP8Aif8AD6QTfDn4talYFTloYruRFyPUZ21u6ttEc/sot3bP6Bl/a1+BPxCLR6f4/FrOwJNrfSPblT6EsQtee/E/wjoniXXY/FlrHZ3BMbLMgAcyqQMHg1+PXh39t79qfwQqx+MLLTvEtojg4vrVQ4A9GiwK9P8Ah7/wVR8F6bcfZ/GPgbXfD8zMBJLpl550Y9ypKGspy5lqbQgovRn6ESfC74eaupa78JwRsDgyWq+UR+Vc34m/ZX8F6tYyTeHNXn0+5Jyi3MzOgGeQcc1478Lv+CgHwx8YzRL4W+NulNITgWWs4hkkJ6LiTY1e16H8e4b2FTqfh+OVSo/0jTboOD9FNc8qcHsdCl3PMPEn7MHxL0aETaRJa6oofBitchgOfmy2BXF614L8YaAJG1fw5eW6RDMkkkfABIGc5xX03a/EDwvqEivb6mYJCMql3EYyD1xzVea6t1haGzaGdGBBX5ZMgjvnJqPq7m9C1XUEfJ82oLDII2lG4jIBOCajk1Jm+VmI5zivfPFfw98F66Ej1HQEgeMkhrMCEgE55AGK4nxB8CNMlVW8MXyxspO9L64c544xtGKxnQnHc1hWjNHmzagNp+bvnrmqsl2rZbdg8g/WtbWvhp4z0WSSNdInvFQ4WW2t2wR+PNcxdXUkTmGdWidchklXaw+uaxcZLc2U0lZFia82/dY+uQagbUmXKq2OOcGqdxeKrfM2PTms+41JFywYAg9zSuaJ3NKbVGXLbsc8f41Tm1IsxbdjnAOeazpNWhYfNKMjkAcZqncaiqt8rfjmspN3GtTSm1BY3LNIc57HvVK81ZuVWTJz69ayrrU2VdqsfTk9KpyXkjNu3EEenNS5dCkuhoXWpSMx3Sc/liqc18z53Nn0wcVXMzM3zLk+ucVFIWDBmfHsD1rJ1YspRsyWS4kYfNnr2pqszyBmY49uOahkulj+VZCcUz7U7MNvpnjrUOrG25vCDaLjeWrALwM8knrS+csb/Kuf8aqRrPcMNqsQTwAOMVftdHkZwzcDAzxj8awqYuMdjVUNBbfVJ7GaC/tlIkt51kUjjBB4r9p/gV41j+JXwb8O+N5ZEl/tHR4HkROQGKfOtfjbZ6HasoEi7iTkFjnmv0W/4JNfFSbXPhpqfwu1ZWD+HpvNtJS3WOUsdtd2VY3nr8r6nFj8Pai2j6Iuo1mYRsuMEkACmtY+XGZtyjYNxycZAqzr01vHqbzWshJkAZlzkKxHOKl0+3WaEyXUm7eOFxgAV9O27aHgKWh9nhdv3eO9HyZ3Z5oKsxChuc5/Cl2Nu7Y9c1sYtPoLUVwy7cseeuaWZ2Vfk6g+tUdQ1JYIyWYg9AM4zQOLvoiC5uv3m1l78c0+O5WOEtu9+KybjUlkkO1hnPYc/WnyagqxhWPJ6AUGpJeXnmSH5uM8etZ15N83ytikuL5XY7X568cGqF3eOyncx68YrKV7gOmmDOWLY561SumX7yt9D3pkl4u77/TA4PTmopLiFl+VhnOc0wK1wjMx+fpnjpiqt02fl3VYuLhVB+YcdTVC4uF5/wAaAK1wgbLKSD1NU5mZfcg/e6VNcXDbtq/oe1UppmZs7j9cVm3YBsjls7vcVWklVWP9KfJNtbDN+mKrXE0W4ttPHTjGKVne4DJpFkz0/wDrVVmZUXb3qSa6j27duDnrnpVOSZlbduyPWmAkjKee3QfWqs0jbiytkdqdNMyr9489KrTT/Lt2njuDUN6ANm2t827pz6c1Uk3K43ducippHZVO5sCqszszFSv/AOupauwV07kc0jc8njmq8jKuV9+/rUk0bcMw4A7Gq8zKGPy4wT060yk1cayjafYZHtVS728r+VTyTFht6ewqndN12v7jmgoqyKFYrjr+FMaH+9wD+tPkZVbc2TgdaRpI3UfMQRxzQBXmjZeF/DFV2jYt1HXv1q3JIrMfm6dB3qCTa2WVsdDkDpQBXuIbS6t5bC/gSSCdCkqsgOQfWvz/AP8AgoN+wrdw/GTwV8UfB2jJJpn9tW8E7KOInMysm49a/QNgGX73PHsRXlv7Vev2+h+FdP0Zm3S3N402zzMHEaFgcE0la6GmnY/Jb9rPwrdax8cW8NWCliojgeQISMkD5sDmsK68I6BoEkmlaFa3Mil98yae4njhIyCGLDNeh/GPUJLf4var4m+xzSrGB80CBmHGOASBXzv8c/HHjnTbiSS71hNCeeOWSG3tZ/s8xUfdLhDmtFHS51RqPSKNb466lZ6VpNpYWGkK8k4aV4hOsbRgD7xXbmvB7qS3kXzWUIjcqA2ce2etZmqaxreuWLTazreoahcAgxedds+Bxn7xNdXaJomn+HrS3WzuJLloEaYpKGwxGW6mm2kjppqpszn7iPyV2q2CT26mtj4b2smqeJEs2szcRxpvliEuwnsBnIrNuNH1mS4eb7M5SRiYIyRu9hgcV7D8APhI17qemafdWu281LUVMrK5DJFkADmsW76o7U+WN2es+Nfg9DoHwU03UlWNbtbdJUUozEiRwSN2QK+YviM0OmyLbwQ7zcSOJGHCqR0r7k/ahkh0PwnDo1vEIxHGqqoGdqrXxd4o8PrfXVy0jBmBJjAbIBHQVi5xg9S9ZxuedtbrGDNK2BxgnIAqDzJFYys2FU5JB4Fbt94fkvlW3ZShSTJBBGCOOcVTvtNms4TZqVVnRguRgHIx3raE01ozgqKSeha0XXtKjtmW41UIwKgea2AvHPXmtrSZodQuEjstQt5XY4QLMCSfzriZtPuo7VbVlRVDhmdUyScY5NbsDWd1bJY6JY3e9EQFhECQ3qCtOTSQRckj1zSdLvrO1i+0fK4XO4LjNdZpLtLbqzKAwUDIGAa81+Hd14m0u0ex1u/muFYDyopiS0RHuea7/QLppFMbRkMpyfTBNZKor2RUU2tTyj9ou1VfHrHaRmHfkDqTitf9hzVtO0X9pnw5e6rgwPMbclhkAyAquRUP7S9nO2t2l9HbExtYIZZBgYO4gVl/s8eHtQ1Lxnarp0Un2u51S2h09/u5beBwauMro46610P0e/atRo/BdtOq426lEVGMYOW5r65+MElvrvgvwHrUany7rw+soUk8b442FfKP7Taw33gC1Zs/LdRlyDnkZr6t8VLHJ8IfhxcRqWjXw3bDaTjI+zxkCuqN3TPMm2pnzX+0D4Vm13WdJjjtWlWOzy5XgqPMNcdqFqNPVLVlCtGMFQOg9PSvZfHdq39q2EzKBi1Khj0P7w14lr1wz63eCPAzeSZVR0JNc0fiFUZNDceZC0bKroww0bqGB/A1i614L8H6pI9xfaAhnLAh45CgHrwDir9vcNH6jHY84p01xGy/eGcZ96vS5lGXc5DVvhFoF9LE2na7BZqkZJt5G3EsTXN+JPhd9oY6YupQTxIclXtgVc5967+4VpJC24jHQZ5FZ95b7XMinPPJJzms4xdzaE7nj2tfs3SXNxJNcW/lAsBHcwx7VPyg8KDiqej+H/jB8NbmG4+GfxP1awDOTKkM7RJGy4CgqW217C2vXumzIY44pFRs+XMhIPt1qO+8eaFfWclrqPgWIu/LNCsaq3OR15rKTknpqzdSuVdL/bE/bT8AxwXWsX1h4itmXbJFcWEe8EdM+XsavoX9lH9rTxZ+0T9r0iH4Q66mrafA8t42iw+bEiohZjncDXhlw3ww8Ux/b2vBZ30sIE8d9qCqA23HIFfQH/BITSV8F/tP3vh631O2kOteF7lbVrWUukrq8bDGQDW9CM5SsyKkrLQ7XR/jf4e1ObyZLu5tJAQP+JmNoJ9CQTXR2viWDUozJZahaXIB5a1uEcD8iTX2R43+B/wK8Z3V7Z+NPAGjXEiEoHuYFSUD2cYavHPiF/wTh+BHiGwk8Q+C9T1fw1JFEWVrW6NxCcd9shLV21ML1JjOOx4tNq3mMWaR1PGctWXq1npWsqY9TsLa5UjBEsQYj8a73xJ+wX+0f4ejOoeBfifp2v6aYxIi6gzRyscZ2gHeK881zwL8e/BDNH4z+Dd8EAz9o0wGVVHckoZBXLPDpnTCs0zk9a+DXgvUpjJZrdWDlSMW8+5SfXDAmuY1j4BaiyhtI122I3MG88vk9McYruY/GGmzN5cyz2+OHN3GE2/qanjvbO+jDWN/b3AODiCdWP6HNcs8KnolqbKvNdT5+8TfDT4i6JdyLN4fuLpAcrJZRsy4wOneuW+3SrcNDIrI6nDpIpBB+hr6omWSNh8zqwH3WGcfgawfFHgvw74pjRdb0aCZ4ifLlEQDDPXmuWWFmnqbQxEb6nzpJcMzD5cc+uaRrhsfMwA9uK9d1j4AeFbyNpNJvrmzfGFBYMoP0NcPrfwc8VafMFs5Le9jJYq0JZWIGOoNc86EorY3VRPVM5Rr7y32x5JJzx2FK0k1x90Ec4I6VbuvD93p99Jpt/bPBcQNiSKTqp/DirNnpbK24KT+HWvExlX2E2kejQipxuzOh0uWVgxyM+1W4NFt1VvOy+4AEbsYFa0WlsWG7gegOKvR6bCWDLGBx0A4Fee69SpojqUUmZsNmsjblUKOp4xV+1tGXGV6VctdLZm3LGMAemM1ftdLVVDbSOw46Vi3FvV6jStqV7GzIYNjp1wK+mf+Ca3jmHwn8Zr/AMOTyBF1rSysAbgNIjBsCvnu2s2jbDLgHpxjmuw+DGuf8Ij8VvDniE3XkJbavCZps4CxlwGya9DASdLERkYYiPNSZ+m81xHIWZgQATgZ5FbOkt9stU+zxuWVckEZxiuOurq4jkMkcxaJ8OhByDnuK6Hw94m8y3MMmUdVGHU4BB6jrX39OcZJM+RqRak0fZnhrXYvEOiwa1BDsS4Usihs8AkZzgVeZ1IOc5rJ0WaCy0e1tbSGRYIYFjiLHJ2qMAkirZvAy7lbOTnBGMfnXS4nCqyb0JprlVUlscDPWuf1e58xmVW5B47VqXE0ojZdpIAySOcVz99JuuGy2DnoetRLRWNoSuQwxtIxkY8DpzTLhlQhlYYHQZ4FWLd1VSrL7n6VTuplVjIykAdT1BNJ8yLhZor3UjKCy549PSqV1MzL8zHjH51NcXke4srDj9KoXF4vO1+5J55pGhHdXCjO1sf1qjNdNkruwPbrUtxcK2d3U8gGqU0jbvmYAdu1ACTXW1f3bZHXmqs0wZeoySDTpplXO05qCSZdp2r7Dnms5O2gEcsj8s3A9+9QSTKzZXAOO/pT7iZeNucfWqkk247VUAfXNKzvcAmX5iytn0+tVpmZlPUHrmpXbblVbkH8qhmk3N+87A8CmBTmZs/M3f0qvMy7tvtjip7hl3ZXp7Gq0jBVG5u/40AVpJGViQTnr1qvNJtXc3HIOc81YmZVbrxnv0qjdTLu2rnINZt6gNmmZl+X8x2qs0y7v6nmiaZY2+9yeeBVaaTq3ryDQBJNKzNjd+PTFVppNuRjH45pkkzfwtzn6kCoZZGZj8xx60AEjKy7t3fOKqzSbmKq2CDT2bDfMxzjPpUczbl3ZxQOLsrMikDbtzY+oqKXarbV4Pep22bTu/yahk2/e5z2x3oLIXVV+8xHPrUe1c/LxznI61LI+5vlbFQ/dyAxPegzu3oR3issZMa5bIwM8mvkf9snWNQi/adtvD1xeIbeTwW15FE6sxWTzHj2jBxX11t86RFxjLAE57V8N/H3xJ/wn/7ZXiia4d2tNH0JtMtiAF2CNkDkGhaGtJLmszk7H4c+HtaWRbzR4pCZPNLugIL84LA818pftqfsjeILGZ/EOieE4ri1itwEvLKLbK2MnLAkmvp2b4o6Z4Q8Q3OlTXQezgwiO77dx2jgmuY+LvxBk8S3sM2mamq2rx4SBEwSQMHOTiqdaCVj0IYdqaaPzRm8K67DcvZpoF2Z42wUMBGDjPNesfCT4WNosw1XxHJHJIIw0cdu5OM/3gwr6I1TwXpniOYtqNqigcoYhtGSSSTgVymtaPpejLKtmwEMIJLFywOPeuN1Yt6HpU6XY8/8YaHozXMQs9IRGjUmGRo13Eng4wK+s/8Agnj+yFP4jM/xW8T2+zTrAFLXz1x58pHJHWvmfwPpbePPG1rZRx+bFHMryRLxlS2AK/WjR9IsfhN8FLXQIdMLJa2StIloVTBIBZueK3p2erMcRzppI+A/2zLNZvFTadbDbHErIoPOQDgZFfKuraVGszfaINrq53LnHPXtX17+0LY2Him9l1bUWCXEgZ4lWX7o3HqBXzZ448O3kGozTKqspYEsrD2FedWm3Vdj0aEF7FHAL4dsZrgyGMB2IJIHWnat4FguLVlkYFQMkGLkenzdatTXX9n3QZUDdwM4yK6PS3W4ULMoBIwQDmqi2tUR7GMnZnml58NLK4bdCsyZOWVpicH24zUmh/DiTT9RjuopiQrAuFmYE/TNeo3WkwS/vFjwfrVG4htrf+EAjpzSlOb0KlhoJGZpukxwMrMpLdOTnNdNottGse5VAJHJA61ixyLJINrA89q3dHZfs/ysOGI4PTpVQXVnLWhGCsY/xV0Kx8S6Fa291C7SQXQERQgZBySDmuY+G/ij/hE/2gPAuiqsNrp8Wu2q3CKoADGdVznNdd8Sr6XSfCyahb4Eq30ZVm57MTXjPizTl13Sk8U6NdiO6sLhJN4Ykli4bIreM+VJHHyc6bP1J/aD0No/AEj3EhEUc6spxk9+a+kdJvJtX/Z18BaivzKdD09IB0JzbYNfJGl/Ei++Lf7GmieNtU3NeXejxfa3KBcyxuUc4HFfVvwkZtQ/Y8+H3idWKxxwQwsCudvl+bHkV309aZ4WIShWseefFppLbTrfVYLeNjE4UtKxAXknORXz9eah9qvJbttuZpmdirZBJYk819IfGPQZLv4YXvkQyO8l3DEiRqWJyTwAOa+aNUt7HTrxrWwmeSKMhQ8kTIxIHIIPNQopO5E37pahm3LuXr39TVa8mYt8rY9wcCnQTI0IZGwQM5zVS+k3Sbd2fpSStqZN6ixyKzFWYk9+aiuo2YlemefrSQ7lwxY57GnMkrDAbAzwcYptrYcXzLRGLqELKxWRc9hntWNfRBWOO/IFdNqluzAttzgcZ71gahHuYs3QEnHfNYS5ea/U2g7RMhrVWYttGCOcjrXv3/BK7Xh4a/bv8DxzTHyr57i1wzngtCwAGa8HuO7N65z713v7HWuNoP7Xnw11NZthHi60QNux96RVxW9B2noyZSbVj9tvijNJb6uG1C1g3XErfZmiTDBVxksa5ZbVWjuJUkKxGPbMWfAAPHSrfxLW0bxPd3s+oyrMkAQbw20cEjYadI15N8O9PufD01pdOsI84TxElxkggEkV6kqmlnqSoOKu0U7fxHqlpDaWFlNKLcyJA0kUIfYD3Ymrup6pG0ZaSGJwRglk5J+ormlvtV07wvd39rDEZYr9AqvGdpVgoJABpNK1abV7WeaVo98AJkSHOAMdQCay5o3BKS1ZmfEDRfCut6U02s+C7HUZo5FVWnsklKKeWI3A14P8Qv8Agn38PPG+pya/4D8Wan4SvbhRKsNtKJIIyck4Q4avZNX1aVrhkkYHBB9c/rWb4h1LxZHp1vdeD7V5pmfbOY4tzRKCTkLWbs37xrTnJny94g/Y3/a4+HFxJJoXjPTfE1orYjSaYiRx7iUVwuteLvih4EvzZ/FL4T31pGrFWubO0dVB9QzEpX2nH8S9b3JF4h8I6raSJ8rTSw+VHIc9ctitD/hPfCmqQmyvp7Aux2xwzTIxPbkYqeRN6HS7rc+GW+LPgm6jDSX8tkx+YC9CJj6kMRXpX7KHwu8SfH/XbzWPC9gZdB06ymbUNUhiaRFKruCoQK9w+IXwG+F/xO0q9s9Y8EaZFd3Fs2y/trONJQwXg7gua9N/4Ix+B9K0v4feOPhYrCW5sfEbPcQkAMivAsZ4FZVqUXG9hqo42R+cvxg0uOTU4ZZlxOyCO5wgG5lJIPFcdHY+W3y4wPSvZP2wvA8Pwz+JPizw9qTSCPw/r88DuRghUdlBNfNWofHXwNpN2t1Nb3dwFBAjjUDaSMdc18lmGWVsRV5oHq4XGQhCzO8gt1GG29cHnoatw26L8u3HOcdCa5fw/wDGPwPqumR315cHT3bJMVxIGwMkDkVtWPjjwveM8ceqr5ke0uiwyMAHGVO4LivElhK2Hl72iPShiITXu7mtDGqt8qgZ4JznJq3DDJt27RjOeBwBTIV/eeTuy2eg7mpOY2CtgEk7QTjNcspRg2mzpjGc3sPRdrAbuOuPSrCzbYzNHwYyGBzwMVzWsfEHw/pULNDcC9kwPLjt5AASTzk15x8R/jf8StN1G2j8G2trGsqg24jsvOlRs4xycVrQxEefQqrh5qOqP14+D3xB07x98H9A8Q2c3mSixjgu2D8iRFCtmur069WP5pGOM5HNfHn/AATC8dfEPVvB2ueHvihZNZ31vcRTmJrYReYrIcyBQcV9Y2OpRyQqy5BA5yOlfcZfiVWoJs+UxlGVOpqj621PwXrmhf6TpniPVpbcJ87yXm0hueNoxWU0euTMzNeRzFyObuRyR+RrA0+2+KGk3Ucd5rKTKFYyvcys49AuK0PGvjPWNC0bR7K2jtbu4ETvfMLVmBGBgAjBr7n6lT5bM+PVWUXuaFhfeJ9IufOt762TJJIghLY9vnq9p/iTxFeTPFb29/MzHLMlmhGPqRXFeCvH2o+NvE1n4fbTruHz5mE0UFkNsSAAbtxy1esW2mWWlSubZpgGG1leTIwDnjiuergqeyNYYmaZk33ja88MaNJcazpkqLM4WK4mZQM9OQvNMvNWm3NHI3IJDAdMisH4+a+19qPhb4cWxjLX16bq8VBh0iXhaTVtWaOaRtxYMxKkcfjXk148krXPTw8uaN2WbzXC0xWNTgAZJPU96rTawzY2rgAnJz1rJmvt0m7B5Oc+tN+2LtKr171l03NW2maMupBvr1HPSopL5WzukB5+lZskrfxNjnPWq8l0rMV3YNZyl0Roacl5Hu3Fue3PANQTXiqvytznsazJLlo8nJz2wcVUuL6Zm4kIHPGc0wNKe+X+9nnNQNdRtwzY5zg1n/aJPvLzz6UyS4kVg24j2oA0VvI1yu4ge9RTXSsOegrOm1Btg2tj3xiq818rfebntgd6ALtxex7iqt0zk1UmuoxnnkHrVWS8VmKhh6YJ5qJpI+WaTt1z3rOTtoBYa4VlJXPQkdqo3DN5hO7PfHpSteMo2q3AHJzzVWa4ZsleMk496AGSM27czdD64qKSTcxXnPQe1LJNu+ZnGfao5Jo1X3zkc0AMmVuPm5qGRtvr09eKfJOrKd3HpUDy7mwv0z2oAST7g+uajk4XdzntzUrMu37x/A4qJmVmO3r69jQIZIrHAU9OTzUbKrfezj605pG53NwD2FMkdfubuO56UFyXREcirj5cA9KiaNl+b0GcjtUknzMGTH1BpG3bTtbnHGKDOTuzF8feJofBXg298WTOQtsg2KoGXYsBtGeK+GvijpjaF40ufG10qLdeKtKuJ5hGzECaSfecgk19TftV6lI/huz0RckLqMLOPdlbPFfKf7SOtPaanockjbYYrYQADgEljmjVlQlytI8E+Ks0lx4knVZgVMmXVVIwfxrCtWWHbIZCQB0JPArd+LzTNqL6naxKYSwDEevA3V5jqXje6tVlht1zyAkqjBUd8ZrirK07n1GBca0DtdS8YWVpZS6e1uDMEwwDYJDV5R8TvE0y2KadDGApQtIx5wMc1HqPi6GGT7Rb3DOZATlsk5465rnpFn1q6Ed1L5jTSBSxGePSso3lI7nywVkfSf7JfgTRvhr8MW+JXjC3ie/1oie2ilYnZAvzxrgc13viD9vjx/q9uPOurWSAgKtulvjC9Mda+T/j38WfFGjaJpWgQyPaWdjZRiFS42yFPl6ZrjPCXxPtLvy9QZRb3CbhNFJKW2n1HatZ+0WiMKUacpNyPfvin8bdC8QX8El1H9juZFYTqIshh2xivN5tS0/V5njs7tZCScAZBIx71wvjDx9p0dxJq97eLM8cWVhU7SwHUDtXDaD8a4YdZJ1LSp7e3uJiHkD7hEOccAZrnVKTV2dEq1OPupnefEbSVsL63+w5VpIcsrEgA8/hV/w/IqwxyLIShAAYgjOOKw7rxRB4z1O0a0uVlhicDAQgDJGTzzXTbUt4hGrEhRhcjFOLb0YbO5euL1VjDK2O3pWFql8qsdrc54Ge9TXGoKqlQ3Yke1ZF06zSEdcnrWhUpJontbrLDcx5PXPAro9CWWSSPywcM6knrxxk1ztjbq7D5cnIxxjBrqNFj+y4VW4AyCDTieZXkmzK+N9xHY+FbRtocC/DuhOcqFIryHw3fLbzSaVJzFdQsgUdAwUkGvRfj7qSzWFlp0eDk5ck9eScVxeh+D7tVg1eaGRVcZQSIVAGcAirjuYQl7rZ+g3wQ8Oyab+wjodhdQlD/ZNxIAxPAMkrivrb9ny4+0fsF+C7VWwftbqhPIGLqevnTwzHHJ+yfpGm267WTwrC2MYx+6ya+gf2WJlvv2IfCMDqcRalcAc4x/pM9elT+A+bxcm61yfxzYxx/DTc0Slm163BZxwDyRmvkn4s6VN4e8bX2kTFHkW6klZ0JOVkIZeTX2j4+sI4/hLeSsoKxX9s7An0r5T/AGqdPisfGVvfrGI2utEt5WxySWkZc1D3M2+Z6HntpeMq+Xux6D0qLUm2r5kbHONx5ziq1rcbcsrY/GkvLjzFG1gcVneQN32Es9QaOQxvyAe3GK1beaOZQytj8a5ySZlfcq8Z4xU9jrHlSLHJIAoPJJx24od2CSbNq/jj8ljuBGOoHSuV1ZUSRkZuB6HJzWjqXiKLy1WGZSzZyAelYOoXSzMeeuST7VDXM9TTRpJGbeXS+YY1bkE4wcVs/Aia5tf2jvh/qbSAeR4z087t3AAuY6wb1lXLL1z1HWmr4otPDv8AZ/iPTp5I9SsbtJ4ijf6t42DBzW0HaVyo3i7n65fGH7PqXx+1u8udXvAJBG1okV2yoAsSgfLVO68SeItJQSadqIZFUALdM74A4wOa+RPCX/BZbwNq1pZWXxm+E73d9bQCKTWtMkRZZCP4tjYr03w3+31+xp49hhVfiPqPh65nO1YdXtmCqT6sN61o6rvofT4WtlsqKjU3Pdof2ifHWmMbO9tY7qOTO4Wtsquc57tmn6B+1X4R1LVbnSFsxYTx5W4N2owT/dBTNeeaHqnhrxnbpffDj4j+HteQNy9teqzD04Uk1g23gfxFoXiTUPEeqaRIWunIRIWEihS2ScDmsnVOt5flmJh7rse3TeP/AAnrF2i6dfLMZAxYxSqxGPbrV3S/EGnTxxSaffFh9oCMoDIQRjscGvCryaFWVlhaI4yONrD8RzXX/s/T3F1/bjSSPOLbUoXi8yTcSCDgZNXCo5PU8rG5ZSw1Pmgz2WG4a4iKzKJEPJSRQwJ+h4rK1jwz4P1QrNdeHreKeM5iuLKFYWDep2jFX2vreKP5VVcnIA4qmZI5G3bs89M4ro1TueHzuOgK0itDHbsQEVUBJ5AAAGTVb/gmxrkfgP8A4KMa14OaQA63Yak0ytJgkF0mjwKLq6+zsFRiBnOQcYryqPx1efCD/goh8PviLo0fljVDZQ6k2dwmWW4aA9eKTcmg5k9jU/4K7/BZV/ak17S5lMFj4qs0vVdGyG3JsZ8Ag18xaP8Asafs/wBrGzarol7qsznIe6vWGOOgCbK/Qn/gtV4cit/iH4I8dwsWN1o09q+3odkgcc18X3V9dW1jPeWgTzYoHeIyg7cgEjOOa5KjdOLOrD8tTRnyr46+BHhnT9VvtO8Panc2kCSFIlL52YPIxya4hvC3ijwpfifw94ihZHkAkDXMjAgHncpG2u/+Iy69qnjK6uI9ryTztIwt1YKp47ZNa/irwL4R8GaJba/ql0k81wyqY4XlIVyM9CMV8Vj8wdXmg+h9VhMDycsjHs/id4ht7KC3EsAlSILLIYAQzdyBmsfVr6/1iUTXV7LJyTt3kAE+grmtQ1a4k1Fo1nhEaMQVRSpHoMmn6brklteBpN0kZBBRpMY9MV8vNu7ufTQpwitDpLKw2ru8sAnB4GM1fsbxNEu49VhskeaBgVYrkgZ59qztJ1aG+hM0ccigNtKyAAj34NX4/LuFMKsAzKQCBxWVKT5ty5KPLdn21+yNo9x4Zm0rxdG1xP8A25pTSXTsvyRrJtdBmvpTR7xbuHzIeAWII6gEHGK+cf2MPE1rrPwI0qS+Z3k0u5FpOwOMBHLDFfUuk6HG2gRa7a6YYrS4USQys2AwPQgZzX6Lk8H9Xi73R8Fm0/8AaGz6E0fQbHT2aRvjOsqsMKs1yHCn6b6t6FFrtvq9utz490y6sVkzMfs2GZPwFeW/Ebwf4gWWCbwToCSRiLNw63ADF89MMwNU9L0/xDavBa3l5qGnyyuEd0ZwAT6cgV95HNIOgqkkfIywMb2i9T6b0zWtBDG5stajOSVAFsy98ddtXVvrK5mSNZEZWIwQSCR+PNfOMml63DG7SeLruZ1T5TPcOoJ/76NX/h3N4itbq+1m6uoZobCFpWEkrhiQCwAPNTSx9Gurx/ExeAlB6s2L7V28VfHrWNeaRmtNGs/sVox4COvyHAFad9eJI33uB79DXL/DmxvNP8PSahqC7bi/u3nkcn5mXgDOea0proSSHcxPNedVlzTbZ3RXLCyJZrwKSysc9cd6qzXzM25Mj3BqK4mjbP0GOaqSXCbjtx19eax6aFq90WJNSZf+Wh6Z9KrtqL7t2459RVa4mbaW3D/CqzSbs7c9eoNZuSRqX21BpG4bPfrSNdL/ABE/nms9rpY87mxgdR1pn27cp+Yn37UKSegGhJeLu2q+MevrVea63ZUN9e9UJLxmb73vUM15tX72efriqAtyXGxTlueM44qrNcNu+9+XrVeS++Xarfjmqk1xMuWWQ4z+dZylYC+1yjLtdunvyKgnutr4Vj/WqK6gv3W7d802S8WT+L86ALLXxHys2fxqNrtlbcrcfXNVJZduW3Z5455NQTXjRnhvb6UAXZL5N3zMfXGcVFJfRsx2tj29KoyX0bfxAEe/Sonuo/4ZMfSgDQa6jb+L8qa0kbZ65zwaoNcLx82eeKFvArbe/rQBdaTau7cPy70zz29/++qhW4LcMeOOc0ecu4bW7j2zQJNdSRmZmx+mailkZWI3d8AU4TLu+Zue/NRSSLuxnnr+NTrzDbvsL5kh+62PpTXkZejEn07UjSKpHzdT64qOSSNs/NjJzn0qiFy7M8W/aZvJJr9LeXOV1EOMnBIAOK+XP2rI1k0DSr1ZCRb3iGTByQCWxX0z8d4zeeJJYWkKmOZ3OBxXzH+1uzWfw/naBiw81NpJyRjNJXTuK95JHi3jO6+3aYN1skjYLozHnDA8CvnnxtqU1rqb2NwpQxDDANwT3r21NSk1Dw7aSSS/vNoRsnPAJFeJ/FTS5Z/Ed55TFW80uCxwCpJ4rKpFSR9BgZqEVY5xbxppAqSZye1dd4D09Y830yqZC4EZI5A71xOk2czXQDMQFOcevNdroWqW9vNFDdTGNM4Y4II49OtKnStqzprYjXQ7nWvh5Z/EbSo49bW2htrdHxcSjDKSp6HBr4++IWl3Hhjx9qOjWk7Rw2t7LEhiJRXVWKqQCSa+pPEXxdhs9AuLXTrdo4IgfMuDIcAgAZA614P4+tLLxbcRazp9wpuioW4ZmyrjJbOcV0WTV+pxRqTlO9zgLzUJlUzSM8jkYLsck/U1BpKtdXA+0NgkgZAxz/Kt240FthWRlVhyPmz/ACrPfTWikEgYjHYCs3DTQ0T1PS/Aen21nAlmspMjKXw4wSQPUV2MU0dxZi4jmDAHBweQRXi+k+JtV0ZY4obktFGCFjcYwPrXSeAviE0N7/wjl2yiG4BaAk9GGTjNcqg3qkdaxDirM6y8uNjNJIwz2ycZqvBumYsT1OB61WvLxZrg7m5B7HAFWrGSP5fLHOeMcms2mmbQqXja5taPb+ZGrMv3e44ratd0bKqqASQBzjmsvS7hVjKx9evTvVqOaZlaZmKrHyeccDmqgk9Dkry944D4vaha6h4ya13CVUVdoRsckgYrrPDvhe78QtpGlxwgPcskUUUbZLHdhVrzPxZeTXXi9p5I9jPOgVQckYavpX9l7w7NfeNdP8S6vGzx6cTLFAY8EOp44wK3jCKdzkdVQi7s+wdQ0+DR/BE/hq0jAhttGMEYUcECPAwBXqf7Duq/2z+y1b+G7iNSuleIZ4gQeoIE2a8evNWl1LRr28hheOPynG1+rcH0r1L/AIJ0LHf/ALOutLMpaWHxPKeDggeTCa9CkrUj57ESlzHrHxAhjk+EPiC3kXiKwklQjqCsbEGvhD4yx6vY3umtqesy3YvdJhaMSSlxHGpJRFya+9vHMKt8LvEMIYF20S5JXGCD5T4r83/iX8QX8T63beZGYotJ0+KzjTIJcgctxWUtAhfkVyG2kZmCeZgH0pby6jjBVm5Hf0rJXXLeG3a4YEgDBweT2xVO6177Y/lxKVGeu7JNZJN6spq2pPqWrNGx8tsnPB7CsuTVbh8qzYJ74xzS3jSMu7ac9cepqjJIrN8qgEHoDmm7LSwlfdllbqZW3eYSc5znFJNdTMu/ceOvJqGPc2G24APryabM7Lj5jzk8HoKZUdBZZmaMmX8Kzb1I5sq3OQQQeamurpo1O5sgZ781WWZn+YZ5HXNKMrMtaMybzw3YSZ22u3J5Kscn8+K53VPB6yRm3a4bcMYkEeCfwzXbSKrKVZscZGTnNVZreN2O5gSPeld3N1JrVM89tdB8UeG74X3h7W7lJo2BilglMZX8yK9J8Fftd/tg/Du4WbTfivq88QADQ390t1Hj/dcuKzptNjkk+VAM9gOlIukxqu1lGSP7tF7GkKkk9Gew6R/wVV/aGkvrXTPEfh7wxcAyok15dWLLgEgFn2uBX0N+yl/wVf8AAni/x9YfCPXPAg0i71q9WGG7tWWSKWdmCDoM18K3GkrJCYHjDIRyGHAq/wDDyzt/C3xF8OeMLK2SOfTNctpkZRtJ2zK3JppWNJ4ipKNpM/cfW9PWG6dIZtwVsMAeAazmt3RT5Z+bHAJ71Z0XV9K8T3U1ra3+bq3G6SMNjcp5JFLdWd7asVj8uRWHDKSCAPY10wkpR0OKUbGfJGrKPtCnPcA5Ir58/b6vL7w5qHw68b6Ndta/YdTcT3Cj7pSSORQTXv2oXF1br+8gdcnGWUjmvCf29oV1r4GW8lxE3lWWuxSSsBgIvlyjJNU1fRkNNI+y/wDgoJcad8YP2LfBvxosw0ssUen3NurLhreGeE78nNfBOnTLfWTQyYIeBgeOoKmvsT4WeJr34+/8E0tA8KabG0s0fhWKMIrZZprOP5Rk18ZaLdQrbwsrZxjHviuTFQvB2OjCS/eJnz/4i1iTwh4suJ5Ldp/KkmiMajG8BgTXK/ET4ha94ptRpkmnWa2y3PnwJ5bb4yMgBiGxXS/GxZLHxlqNqqllN47xEDONxBPNefXEdxMx3LjnqRnFfl2Om6eJlE/SsJThUoxl1M3TdFlnuh5igsSSQDgA8k1qnSYbdtvlrkcggZxT9Nhkt5RIzbjgjIGBVqSOSSTbJhSehcY4rzrznLRHa3GK1diG38yNRHC2Mdge9a2i6fcPfRyfaGGM5ABO7P41Ws7N/MCrbyO3VfLQtk/Qc13Hg74W/EfV7uC707w1LDFvAM96wiCgjGcHmuuhgcTV1jBnPiMbhqMG5S1PX/2Pfjr4F+GOlaz4L+IGrixs57r7XaXLRuwDBVV1IQE19Y/s1fFjwf8AF601G38F+Nl1i30kRIFQS4tkYOQp8wAV8caD8FNXt7U2viHxhIIi5LWWlFVznBOWYV9F/sn/APCMfB/xDq/9nac9rp95pnm3Ubzb2eRCApLV93l9OrQoxgz4jF1I4io5H6IeMIfD/hrw9NrOq3SwJGyoskjk72J6AVStfDtvqFnFeNfERToJI2jGQVPIPNY3xc8R2Gq+IdN+Hep3kKCW8ineON/nJIKhSCCK63VL630nTnmZY4ILVFRVztWNRhQor9MrYLDzhZrQ+Mp1qy2epy954Pub2R7VdRSBGYhZNhbIzxxmopre78OfDx7Oa4EtxqV8YU2ZGVDe9bTXn2iBbqIBkdcoyHO76VS8SKt1490nw5AqyR6XZtdXJU5Ku3I3V5NTD0MLF8iO+E3Ne8W5o47W3S2jb5YkEanOcBQAKzZpFVvlY59qvXytHnc3bPJrIuJWViuOB1/wrznZstJ21EmmLMfm4x+QqpNMo6t19O9E1xuYr096pzSHdu689T2qJbDjJ3sF1dMq7d2DVb7Q3Tcev40XPmMp+bkc8VUkkkVTuY5rGzTNSW4uG/iYg9uarm8ZZMbuMiopJGbLNnioVZ2k3DJweKE7sC5JIzruVuo7GoZJG2/Ln05prTMvyt0z0zUU0o2/e+nbFOTtoBDNJNuJViR14qNppuV5/OpGmVvm3dKiklVWLds9aAIJpJFYsq++QcVC1w275mIxViSRdpbHv6VXkVdwb8aAFWZmwzMc465qO4k+XC/nmkaRVX5Wx2z0xUE8jc/MfXrQBHMzMdzN36VCGbd94/nT2dm+Yt9OaiZdvzbsfjQBNuO0N5hJx0/GnLN/tHr65qrJI33VbgdzkYp1vIzEMWz70r3YFyOYqo+XPcHNHnMrbtvv16U1W2j5Ryec01t277/0zTEh7XDbePwxUMlwxkO7j0wKVlZWO5h1z6Go2ZmY8Dj35FAueyHrcfN94/iKZNN8u7d0HY4psirt3dD9OTUEjNyytxnI/wAaTdkHup3R5d8WV8jxo7NHnzoFkAAycGvlz49+Er7xXaavpFreRQW6YKtIpbBGTgcivr74saXHcNp+rsq/LI0ErgYYgjcor5z+IVhb6Ff6va6rJvjhLGZgucoQCDxUN6Epanw7c3V3o002kXUgLWk7Rkx5CnH8QzzXJeKNNh1RZLxrjy5UiI5GdwGSM816J8a9E0zSPFkl3pc00n25TKyOVZU542kc15p4okeTSri3hbEjxgKScYGQTUfFqephZqOh5v4u8RQ+HNHmu7fa9w4CQR7uST3NeWTeLPErXiTLq8kZjHyiN2GTnOTzXb+PLf7ZIysCrISEcjI6VxEeiyNMFfcSTj5eM1rF2VzskrvQ6G48f63rumC11LUztIBmjUBQ+PUinR6lcWNkj3kKRochGEqtuH0U1t/D7wpp2hZ1HU7K2vWkKlYbuFZQgHPcV6Npfjnw7axyLN8OtFaNfuodLhIIx1OarmsFOKueIalqnlyFpGVRgYw4YH8Qazl1KG6bdbsrAgkEYya968VeJ/h5q3h51k8F6FaOZQAINOhjYgcjBHNeY6ze6ZdXDx2+nQqhJKqYFGPfpSTZ0csbHI3LReSWY4YDjA71i3V1NG+6GRhgggq2CDXXahosN0oaGNUIODsXGR/KsbUPD8MMo8tmIIJwxyaZzzjaWhq+CPFt7cSNZ6vqAwigxO/BI6c132m3DRSBtwwTg5OeK8w0ixaG4VmXgNnOOCa7zRLiQlWZiSCDya56kL6mtOVlqztdPmWRlWNsDHX0NalwytDtj44yQGxniud0u8WNl28DqcGp9e8RQadpU93cXQjjSIjcVJJJBwMCs0pKSMa89LtnBR+HdX8R+Il1DTJoJZY75RBA0mGfad3HGK+rvAGl6Vb6IkmlTyW2qRjGo2bXJEiPkb2ABxXjH7KPhzTNb8Rp4v1XUjG8DCO1gUBVf1Yk17R8U77TvBes6Z420uZfInkS1vHicbHjZ8tkDAroTtqzy6ri3c7fwB4uk0vxJP4H1XUZZzewma1YSswQKhJBzzX07/wTYmv18CeM/C0akNZ68skuDkYaMLgV8SeAdbuPH/x9sF0eNxBZ6bIXTePu5PzcV9vf8E87gWtx8RI1j4OpoJB0xxKBXXSb5LHmYl2aPc9ajjbw5qcEy7lfTZlKnndlCK/IXUtW1OHVb+3kuGwbghwR1Ir9er9mmsLqJVyGtXBGfavyI8cxra+N9ZtYshI9UmVQewDkUT1ZUL8l+pFHqssz7mmPPHXAFa+lHzsSOx68knODXNQttb5W75+la+i3jQttVvyOcVhLQtPW50TWyPHtfrjBNZl1GsMhbaRgkcDmtKzuo5odzdQCDg4qpfNDIxb+Xc+tO2g0o7sgjZdu4KMjueKS4kjVdzKD15z0qKa4jjXsOOMGoGuGk4Vsg9hxUPcItrUp3jNJNtUEgHANLFbsyjfnjj0q3HCrH5lAPuKe0bRgfKT19+aoptrYoTW7LllY8YwB1xTI49yleSc5yR3rQe3Ein5SOPSoltdvzKpA6kdM0DjfdlHyZPMC7icdQOgqZYVbG5QD75qXy1jkDKcEEVOyx7Q20EgUFp66FGSPapXaBn3qreSTW8Imt2w8bq6keoINXrtlK7V446Vn3WVUj0GRg1LbTLV7q5+kv7Ln7eH7PviO7t9Y8U+N7fQtReyWCe21GbYgJ+982AK9+t/jn4A17WbTT/DGr2up2V4QiajY3ayKjYYnIBNfhrrVu8kjSLM4B5AU4xVTTPFHjfwxdC88L+LdS0+RTkPbXLIR+KkUUJOOrY5Wkj96r5obiQrHMkgIxlTjNeZftX+F7XX/ANnXxfpl1CQItJluoSpwVkiHmKcivyg8M/toftN+FlRofifqdz5RzGtzeO4GPUMcV2rf8FS/j7eeH7zwp44W1vrHULOS0upBFskWORSpKkHFdSmpIwm0mfrZ/wAG8niiH4ifs2eLPhvrt2Z7jR9XZYVl58qCe3G0CvlXxVoN/wCDvFmqeF7qFoJ9O1GaB4yeUZHKkVuf8G73xzvbP4meJvB+jTxm01GyNy0iE5dogEGDXRftr+F7jwt+0z4rtWUK11qct6oIxxMRJxWVe6psdCXv3Z8x/GPw7Jc67fKpRpJLeO4R2GSuOWHrXCQ+BPEGq3P2XStAu7j5gPNEBRAcZ5J4r2zUrd5L8XkluhnEewyvEGO09Ac1YuNQh09BHJcCKJ84BRgoA9cDFfEYjJ6WJxLnJn1dDNqlCjyI8y0P9n7xCWSbWHswpAL2kM5Rx7Fuld14R+DWgafJDql5p12rxqS9tJdRzRgkEc8Go9W+JXhPR2aObxLagKAS0DCQg+mK57xB+0PpFvm30KS5lKKCpuLNBGxIB6hg1ejQy7D0I6I8+vmNatK7ketaTptvpio1rYwWyngSQ2qjI9eBmust9L0+SyjvrW5eRo5UadDlQV6lcHFfLGp/ET4seMdXk0DSNTis4ZowUbTbdlJ2oGzu3Zr3D9lOS/k8B6p4c1i6kl1KS4kDPMzFiTCMsc5NehTppK6RxSrSk9Westp9g9nBfaRaqIoygjOzGA4LHtXL/E/UNR0a+0LS7B3T+172ODzY4dyqPNXcG5Fdv4N3ah4XjscsiWMSxuCd2WVCSaq6xpthfadp82tTKsVvqMMwkchRGcMc5NW49R05Rbsfb9noeneJfG+n+NbrxLHeXF432mBIrhQW8sgrgYrp/FV1deJbW90ZVaGMTo8rZ6YGcGuf+Hmkx33i4eI1WKaHS9KSysEtrnCxsSeoFNt9D8S29lqjyXBe51q6LSLBM5EYJJ4zX6HXqKNjxKFFrU7vwlYw3EdjpMEJCQxKMgcDaOWrkfA2sN4l8Sa942WTfHNdfZrZgMAovA4rp/EOs2/gH4ear4otZpd2maeLW0lbDOZGCxoxzxXL/CvS/wCxvANjbyKVluFa4kB77zla8TF1LvQ1s7mxfTNJIWbuexxWVdNtY7umfTFaF1hWLbsj+tZt0ytld3IP6V5zu2VJJogmaHaMc8VSuH2ncrYFOuI2aTdz9RUckbL8249uvNROzVh01y6EMjR7QzNjt061UuFVvmX65FWpGVs7ug461Wk27Tt9eKx+FmxWkdt3yYz6mhVVRubr160N8sn3j259qST5W3Fj06mnrbQCvdMS2N3fPWqzyE4C4HeprpmLfK3HfmqzNuYjt/SmA2SRm/iz79qazMw+cfrT/KX+4PzpVj2r29fc0AQtG20tu/XNV5gy/Mzd889KtySbfl7DHSql1Jx8v169KAK00m37xP8AhUTN/Ez4GfyoZssP8nNIv3v8OuaABSv8fTPWiRVZflx0zz60M235lU8ds015Ny7dtZyk9kBDIvVd349OadArK42888HrTW6bVXPanKzRqG2475zSSaYFhWZV27SfTFDN8u1lxUSzbl3KuOAetJJJn73boBWpLjcf5i+55psjKzblU9OxpqsrN39eeKSRlZvlb9eKV0DsMkb5vlbn6dKhaRixX3xUkv8ArPwprxrtPY+uelZSeoaNmL4y02XVvD93a28ZaVIzNCoGSWTnAFfOvxj0WPXrOPVbW3B+2Qm2uc4ALAZXNfTzM0cgkVckHJB5BrwP9ovR5PCV5c28dr/oV4jX1jKPlCFckxZxipabQnZM+DP2tfDmpaJqNn4n0zRvKtBGIbgwxhVRgT1AOa8b17bNal45gGyAcDOK+zPGDeHPit4K1HTLi5jSWSHypkVMvC5HfivjzxV4N1XwxdXNjdXKTwxTNHHNECAQuBnnmqw8r6G1Obi79jyLxhayNds20EtkgAYAFYmn2e26HnRggHkEda7rWNPWacq2AQTxjqKxbjR5oZCyxkgnhh/+utZpq9j06FVVEMbVJrMiWBsFRkAjg1zOteMvEUcnkxrHCpOSPJDbj6810kmk3Uke7aR9KxtU8O3lzIrRwlsg5BGMdPWlBnYlyoxLzxjqd5Iq3TREKm1SIQDnueKRdQuGYMyjPpjp71q/8IXcQzCSbYFKg5VsnPpRJoccfKryB1I7USstSop7sqw3Ukije2BngYxTL5VmA2rkg9hg1O2n+W33gPYHFRzLGvyswGO1Rza6C0SuyvZwsrFmUDHIre0i5XaI1YjbjA6CsKWZYVMisCBzwMYqG18S/YZw0igpnDL0JHtTUZN3ZzTq2eh3n9rR2sJZpMFVyTVAza743vY9C0C1e8kKM4hhA4UAkk1yl94whuoRbwQsJXbCIJMlj2A6V9ifsZ/AzTfCHgm18b+IYUl1TUZFlURncYlY5Az0rOcVBnLWcnqeN+Bta8SfCa1t5PGvwtuGtoWYJqcdsysmV2j5vu1Z8X/Few+IKw+HvD1rqd3dy3aGx0/yMgyHC7QFJr7t8SfA618V6dHDpur/ANmF483CpbpIHU84wcVD8KP2X/hP8IdT/wCEh0Tw7HdayVIOp3SbnQnqVB4p3Xc4JNqRw/7K/wCzR4k+EXhOfxh4ujA1rVbdVe1Tn7JCDuCDBNe/f8E/bp4dT+I0bcF723cgDocy0XEdzdRysrEyPEwVgcHODiqf7D95DpPjTxxp1x8sl4qyRr6CN2BrsotWOOtZ6I+h2uGYyRsxG6JgPyr8nvjjaw2Hxh8S2duoCLrdyVUdAPMNfqq903mllbgqQe2OK/Mn47/Drxhe/HHxTNpWg3E9uNXmbzlG1QpkYbstim31YU/M82ZyPmb1zkdqvafcbY/MVu3GaoXSqrFYZA2CRuB61Ppaq2VkYjBHGOKynZvQ0TVjThvppGKsxwe3rVqOaSRfmY5x3NR2dizMG/HPSra2jRrtCn1yB2qbPoNJXKc0LNjcxOec0+zt1GNp4xipWt23b9x+mOaWONlx1APcd6mN9irPfqP+WNQqtgn260LJGo2s2QeabI21tq547g4xUMzNx1J+vNWXYnaaHbtU9R0zUEjKrHbxk9c1E2efmI/HNQTSO2FVic8jBPSgnlbHSPJ5g25wCMnHNPmkWKMsrAkjPAxVaaSSMBnbPueoqpcak27a2eOpzQVa8tCaaZpm+73qK4VUhLN1IJGDUS3SsvysAeMUy4mbyzuYYweelK2ty1exj3nzSFdo4OKoTQqWO5cehq3dbmYszHr1z0qGRGZcbvpgUWG09GUpreNsrtOeuQKyNWtVVirKCCDgDnitqbcpBVuR796ralatcQr5aZIOQeKqGkjKpF20Prz/AIIS/E+DwD+2H4YhvboxWN5PNZXBZiAxljKqpAr9IP8Agqz4RgsvjjofjGOyVI9U0IRzSAYDyxyMvNfjN+xn48n+Gfxv0PxKuQ+na7a3KLvwGAkBPIr9xP8AgpBpNn4l+EfhHxxZ3XmnT7tUcjnMdwocE5rSS5omNL3Zan5f654s+Iur+MJ7PT9Ojza3ssU0tlaODhTtGW3GrEvhvx5rsAa8125tdxBIuruRQT/uitXxhfQ+EdV1aeNYxdT3LzqHk25RnJBqg3xF0iGwinuNRilnwS6wThi3JxxXnxwz52+htiMX7N2J9L+FFvcSrJqfiBHaPJaO2QEtkHuRWrY/CzwbaMWvNPNwoyWEqKQfqAM1L4O1S416wbWLGwkWIEqrzD5WIwOCDV+8svEkWlTX93DaiIRMZEWR1OMdR1FEaDdSyJdb3eYqtH4dspJLfSLKxtp0IDC3gEZGQcAHGK6r9m7xp4cPja98LW9wst3dwl45VmyEYA5AGM187andXsl28zXEyLKdxiSZgBnn1rZ+EniS88KfFDQ9ZhkAX7YtvKDk/JIQrV7DyyUKN2eXRzJVK3K3Y+7Ph5ayaZc39hNGVaSV5UjzkBcBeual12G3bT9Vt5Y1CLZzogOGAKxkA4qXw/Jb2fi6GaaQeXeW5hAZ9uHLAgnNWPGmj/2Z4kmt5rdVivIxLGFOQc/K4NeVOKS2PfhJq1j7F8F6bq/hX4cXsckMZ1DUZXWIwMzYU/JnIqS1sZl8UWltDb6qlnZ2EZa4MrsDKDk/MeKh8bWPjCS40+z0S11GK1s7RAXhLLvc8HJXitL4d6fq+oLLHrE1+JZ7oRRw3hYbV2gllDV9jWbk2mzz6bcadzP/AGlbi5k8MeHfhvattuNd1bzZgr4O1cKoYCujmt0tUW1hYBIUVFUHGAoAwK5LX9Qj8Z/tTSLCsbW/hnShGGRtwZwCTXVXsckjfNzk5z714uI1ncIyuipcbm+VWz7A1QuI5FyzNg+gHStGSGVTt2545zVa4jVs7lx6YNc12aKNkZckbN8rckdKhlXbgMvPua0ZrVRllx0z9KpTQsrFlwTnj2rNp3uwSadypcLkfd6enFU5l2ktz149qvyQyMpbaPb2qtJG33doz6deKoad9ShI25t2McZqORwuV9gOtWprcP8AKuQc+uKryWrKpbcT61KWthOWuhVnVZPm/WoJFVV+Xn3AxVuSPaPun6VDNbn727GenNKSVrl3KzKyMWVupyfXNIzMrfeqVoZFzt6dqimjbaN3H45xSKIZpOqlifTA4qrN8yj5upzwDViZfm27uenFRtDux3x07UAVHjCtuXt6cU1WVW+526irEluzHH4DmomhCsO/1NAEbSKzbd3PTjrTGjX7ynNStGvP7sE+xpjRqqhmUjHcGpcUwIZF3N8rEHrmkZnVQvX0p0jMv3evt1qNnjZvm4NJR7gKzbV+ZcHPrTJJCz7t2BnvzQ21eA3HY01pFbO3njrT5kkTdJj1nXd2xjryDmlaRj04/DNQq3zfL2P0waerKQG3DPpnFS9WJ2sKfm/iPXqKazKqn5icH86Gkb7yqB9TSNIzLt6H160AnpoRyMrNuWuT+Nvw/j+JXw6vfD9vII76BDPp8oXJDrzsPFdUzbfm/DJPemMz28iyxsAynjvms5SitGJXvqz8rda1TWfDXi6WG1vLmIO5F9ACU5yQRiuZ8eabZXFpPHNZxCOaFjDKzY3P6k19hft2fsqyTXc3xn8C2n7i4wdWtolAMMnA8wCvlJbNb63ufCXiOEtFLlHHl4YDPBHenRcIy0GvU+WNcvrzTtTlt70MjCQhUcYwBwOnFWdNvLO+mFusyhyhYBjwcDJHSpPjz4K1nwD4sl03VYwYQgNneKuBLGTgHNcB/wAJJNpEwmZWcKrBkDYJyPWutOMkb05yptM9Gmt4TbCdYxsY4Vx0NY+pLbwsWZgCASTnAFcpH8TrpbJNsaxiMsyKXzluR0qLX/G6w6BFC37y5ugC5UhQFBB5NJxT2OqOKlozcm1CGa3MiyKVHQlsYrCvtcjhmMcMikqRkEZ561ial4ma3Eax3GVYEuA2cDjHtWPLrs1xM0zc5OTk8UnTTXkbSxumh0F5qzK21WAJOBjmqc19lS0jZ788ViyamzSeZuxk5AJzUd1qzSfw4PoDxR7NR2M54puOhfvtSVR+7bOR0B6Vk3F5JIxkZScHgA8k0yS4aRSzMQBzyeldf8P/AIfzatNHqWq2pSESK0WX6gH0FDkkhU+aa2Om+Bnw6klWfxdrdmSTEyWMMiYBPOWINfdnwQ3Q/D7TbWNgEEMJjOCSCcg18r6G3lqq264WNAsaA4AGMV9XfBS5sZPBOi6fCsjXBVC6JE2Bk7uTjFc83zGtWCUD6D0m1SPTrdVkL4gUFiME0twqqdo+uRVuSFYUVdpJWMDeT97HGap3DMT83rwc9ealRfLY8qUXd3LFizbtyrkhSM+vFc/+yzvl/aV8T6NIxKtpdy6DPJzJC1dBZttUKEySRx61z37NLQ2/7WerC3uC0j6BNJLGUK7cmEYya6qLvHQ46ztoe7X8jQzmFZMMHCkHqOcV8KftOfE+78JfGjxD8LVt9MSwvrm5uL68u7f5ysqoyorZFfcWvXLNrszqxLGcBsDoeBX52/t7Qrb/ALR+u3DKCXgtyFIySSiDNXJaGkUmjyNYmaaRlkyDK5U+oycVfsVVVDHkjgYPIqvb27fZ45GUgSIHU9Mg85q7arGu3afQGs3ojU2tNmZowzLg447Zq5uV1LFgD2B5qlp7RqAqtg8Zx1q4m7+Hn69aQo92RTRszfKw/AURw7vlZs/hipvLLN93nOepp0cKphu/oKzctTUha1DqVVsEc8jFQzW+3O7nGec4rQaFdvfOOM1GbbcxdlyPamm0BlS27bhtXP06YpDDHxu6gVdmj2sdq54znFUryTy8suc9etTre9xWKOrMqrmMjjAGP5Vi3Tb34XBB7Vq3jtI3qfY1nXUZjfc2eD0FNDT13GQszR7lXt69KjupHZNoyMDGQaljVmXzEYYHr2qKRWkYqy4z0PtV3Lk7aGXcKfM+6Tz1NIsbMoVW7dqsSfZ1uDCbqJSME5kAOaVVRmC+cmOASGHFPoZqSuZ01vtG5mJAOelRrIrAq3AHrW3Jp8bNsYA4xkg84rGvreS3kKls4PUDrSu0XdPUd4Rmk0vxpa3sMhALEr7EfMMV+7kPiK4+LX/BPmx1C4k+0X0nhfTrkuz5JMKK8jZr8Fo75bG5gvuQY5ACwHTIxX7Tf8ErPGWnfFT9jL/hDppgw0+S706Ybskq8QfnNaQempi4xjNM+Nf2k7FmvNO1WHhbuyWAgjGWRiWrzeztSsJaZSUxkgHHFe2ftH6HNN4AS8jjAbSNUXzWAxtUkg14jNqkaxyWbR4Ixhsc4x2r0sElKMo2PHzWMlKM0z3zwbNa3HhWwm0+0jtreS2DR28YA2nv0ArSuIZLzTbu0hXc0trIir0ydprB+E102qfDbTby3QlYoTGWAyRgkV0VrdR290nmMQTx0xjIxXlVU6eJO6m3UoI+b9W+0w30sVwxVkcKUJ+7gDio1uprdor2FiJLeZJUYdRtYHNX/GUKw+LNRhkYBxeOVBODjORVBVj2srMNxX7o619Oq1J4dNvofLwpV1inbufePw+8XSeK/Bnh7xbFGjSTxQTzkfMEJOSB3r0L4iXC6pBpHieyjE9sJHikcHbncwI4PNfPH7IutTXXwtbwxcSkHTCqJNggkEFz3r3rTbr+0/hcitGHNoqkEHcQyMSTXydflU32PtsO26abWp9+zW90pKq2QTyATzT9K26fcXHiLU5lS2063aZpSxJQKCWJrYXSnj5dDgHryK4L9pfxHD4H+CV7YabDIlxrF0tkkokzw4LPnPNfa4mmqcHI8qHM3ZHJfs8Wt1q+na58QdRYfatZ1ViSFwCNxdiDXfzQs2d/YelZnw20dfDXw+0jQFhZXisxJMG7SP8AM1a95MtrYT3kNmZ3hhaRYlYAvjnGTXgU6M67ZtUqRpbmbMrKxVVwOnAqncK24/Lzms2x8XXl5JJJeaNNb7QTgOrZA6nqKv6LrVpql4lqu7LqxJJGVwCfWh4SomZrEpshmZY1OFwO2PWqdxNuY4z3xXRXFjavGW2k9xk45rNvLG32luBjOCWwBUSwtVLVGirrqjFkbdlu47mq0isrFmbA65xmr8jWzZ2yDjsOaq3UKsu5VH17GsXSqReqNo1FJlSSRWX5eec8cZqNkWTJ6Y4HNJMyRzGNmwwwSPSomuCrHcvGOR0rO3KVe+o24jXlvTpkVWmVeGbGO2DUk0ytzwOvbNV5m3Z+Y+1RK3LoOm9AaTdnb0B7DmopFSRio45pqt83zNx1pXZdu4/jSNiCaHc2707iomh2rubPUcg1YaRd3GAD05xVeaVVbb1wc+lAEci/MW3EAD0qF41X5tw6+nNStJuGWXkdDmoJmZWBXjj1zQANtVsN+lQzKOfl7delEkjMvJxxxx0qIzScbl4GAMjmgBsnOG6j0qJmb723GDxx0qSWRlbsBkHGMVGzbm3KoA69MnFAEcytuDK2OOuOtRyblGOT39BU7MrJuzjjqBiomKtn5uh71nLRE8yRHuk3fd49M1JG25dvQjjrzTfutuXt3xQzMzFt3/1qCX3HFWXPzE/Qc01pGC/e/GhZFX5c85x1prsrZzgE9s5pWGhjMSxbd34oZsNsbOfamtIyt8vGKa0jfeKnOetcrtJlaMS48maGS2urdZYJoyk8Migq6nggg8V8jftSfsbzaTdXHjD4f2UtxpUjmRkgTfLZOeinJFfWzMzNt25HbnFZPxE8aeFPhb4D1Dx5421WCx020hLSTTtgH/ZxXTRp21e5VOCex+Sf7Ufgu61bwMNA1tbYX0dyRZyPxsZORJn71fHPijSdX063Ml9DkrKUlkQYAI4Br74/ad+OnhX9qTxhdar4VkVtA0yPyrRIwqL5jgtK+ExXyf42tfs9+9vCFIQFWbb1zXRHRnZTpKSszwm8mkhmKbj9QaqTX024bmJC8AA9BXR+I9FhjmaSBiyuckFcbT+Fc/caawb5VPXPpV86MqlKcGQSX0jfcYjnp0ojumVRuYfyxSTWrRsCy4x0560xY1VwVbOOBiquZ6vYlkun27dpJJ4xxSwq0zDHHfrniiO3kkYbYzkc8c4Nami6PNdTFZlKxgDJ9fpWUp2N6VGc3dmj4U8LS6pcJcfZ1CRSKGaQ4B9cV6hptvDZwpDDgrGMKQMcVzGgQx2MKRwqQq8gE5zx1rdtb5WQK3TI6HpXJUqTvY9KlTjGJ13hm6VmO6M8jCkHOOawdS/aJ+JPwQ+MD6h4c1m5msoZhJ9jeUsgU4yoXOKs6frENpD5zNhYxuY57V5v8TtQk1fxG+rtja6AAgdeacXdpMKkeZn6hfs0ftY+Bv2g9AhntrgWmrCEGe1kPDHnJWvUbhWZjHIpDDqM1+QXwA8f674B8ZQXeiXLo0cgkAjbBUDOcE1+mnwW+Oem/ETw3Bd3VwoukjAdgwUOcgdTWrhdHn4ihZXR6baxusgVmI7kkgVynwCuLO1/a7utQ07UknFz4YkDxqhTyyHiGMmuusdtwqNHhkYgqwGMj+dcL4Xjn0v9qS21X7Y1xHHobeTbRRhDGpk2FeK1ppRZ5FaL5We/+ILiOHWZmXJUTkkA++a/P3/gpSraZ+0BHeQwgtd6FBKM928x0r788UbYdZuVVQVExIycD1r4O/4KdWbL8Z9JmjUsjeGYQpzyT9olpyl0HTT5Tw2HWN1vGrMSBGABnOMCp4bhtwZWPXgVh2vmcK3Qdge1bMLJDGu9gT37A1Euxqom5pNxJ5isCT2zWvGxZg2/B4PJrK0eSF0WRWBB5B647VrwssmGjxwOo+tQ7paFpPoSq3yhdxJ+malt0Abd7+mKhZtrbVYZHpU8bfLw2DzSKauiSRWb5V5pqqwHzLnnkk4xSbmb7zZx0p0asynOcY7cYoEldFe6iUruX0z7isu8hZm3dvzxWvJG247cHiq11b7lLMoB9uKB8mhz9xGyhtq/Ukc1Sm+Zfu4OfrzWzeW6xqW4GRk4HJrJuWVmO1eAeM8Uriu1YascaxlsYwOw6iqjKdxVlODxxxkVYaTcu1eMcEg5pzWatHu5wBkkjFOFuYck7HL3EMkdwytwwbDYPeprW2laaPapIMgyM4zzV2+037PezxzRlXjlwwJwSfpWnY+D9Qjhi1WWZBCZCrKrBiGIJA4NdPLGxzq1rj7PS1mkLMSGK5XBwBWH4x09rOZYUXcWUFmBxjPIrqrGFY7jcq5IQgY6jkc1j+NJJryNre4UZifKgDBAApNaXRcZ6WODuJJNrbVJ2jK5GQCORX6a/wDBDf4q+XpHiv4cSahgTPHqFrbMvIGAjsDivzL1NfLYruyCMH1xX13/AMEb/Htv4a/aQ0/TLxsJq2kT2bO0mNj8EHFSlaWoptuSPqL9qbwVK1r4505oVRDcz3MMQGMKjmTOK+OrfSbi/wBXeFbgeSFBW6KgAfKO2a/Sz9o/wdYXHj6aSSFimsaZKkoJyCR8pOK+BdJk0TwDNqPh7V1tJNSsNZngZZlAzswp5NWsVLDXlHqZ4nCwxkEn0Lfg/R5tDmgbTvDs7OZGO9QzEZBBOc4rrIV1VdwtdKuYpAMhri2ZVGPXnFY9x460GSFWkOnxSAjcYrxSwPbGMVYh8dQyKFihuHQgEvGqsCfbJrzauJlVnzFUsPGjGyG6h4AbX71rzU7m3VpjmcIrAsAcjnFWoPBeieHo3W1lkZ5FxI3n53HnHBGaW11a8vG+0R2M6gcgSwFQR9c4rTsfBvj7xLZrf6d4ZkniZiqeVMhY4OPu53VrCpWmEKUE9jqf2drxdN8S3Wm28haKeNppAT0YLgZr3L4bXzXVjrOmSR4YspTBxlWRlzivNfgZ+z58XtI1keKtb8C6nbWDRtHLI1sAQpH3sFg1dpo8kfhrx+1o05kiaydVYfLuJAYCokpJ6ncoKMbo+65v2/PBto3/ABN/hVrNuAMhluUOPwbbXB+OPjHcftD/ABF8P6Fb+F7jTtKsblZRHcyo/n5YbiwU16ZN8P8Awo2Y10CJARgqirg/mDUWm/CjwlpmrxazYaQ0U8Dho2E5GPbAr254qtVVpM89QjF3R1ELNJII0yduFGO4HFaCwrDC83k7ykLMEIzuIUnGKh0HTZJLnzHX5UGSc85PAq3qmtaJol0tvfanbxSFQ5SSYKQDyOtejg4JU02eZiZJzaR5RDY/EiO2WZtOikd9xfydLBIGTgY4qPSdU8WadqTXGoeGp2iMJUmGxWNgewHevU9Q1TSWVVtNTswWBEeyYEHpg4BrltQ0fxLexyyQ2ti/lkkyRlsnntk12e6jBN8pzs3xPkt2S1uPCmrwyDG9/s6kNnv81GpfEjSobGRpLO+w4woKIpP/AI9Wjbabr7WBmtdMuJg5O0pa7iT7A1n6hY6qqiS/8M6i2OgNluz36VEtWXFvcwdQ8T6Ba6dFqc2p3Fok8hjRJpdpBA5xg0vhnxDpHifVI9M0/wARxXDoN5jWdicDk4zXSx+F9O1bTLdtV0gMoBeOG4hCtHnIPFJovh3w94euLjUdPso4ZDAwklwBhFyxAAArnq8qWptT92V0c0txHfeKNVmWVvLt5EgRQOCyjaxqeRVZs7u2RxWb4RZ5NIkvZFJN3cvMDnkg8VeaT5iG/P3rxJWlI9O9loRSR7m+7nB9ehpkkaqpDrj8c1O0kaD5hznHSo5mVvl24zzxzisZWuONkUmVo2O1uM9MUjqzKFZiAPbFSyxybi23vwfSo23bju/Oka3RBMqlflYnJ9Khkjk2bvQ8dsVakjU/N6DPWoZlVV+VT0z9KBcybsQNwu5uPxqCRldvl6VPIu4hmf6e1QNhWJVcd+ueKChjKqru24x0INRszPlmXj1Bp8jMo2s3BPHrUbM33dvB6dzQSmiN41b5uePSomVVUspPB/EVPt/Lp0qJgzNjdgCgogZtxLfnzUbNubc2fbirPkr03c/Sk8pVflRmpaTQFbzNuex7e9MZvn+Xkn0qaSPcxzkemD0qFoWjGHYZ61DTTJcUwaYLlehHAIOKYxZgWLEA+2aJGVfX1ppZmbPYH86E7sWqQ12YAbmIz0pG2t95TzzxTnVWbbtx9DSrGrP83TrzVU6N3dFO+5JpOnyX18lvyFY4ZgOgr8vP+C5X7Yl1rHi5P2cPB94V0/RzHLqU0UgAnlKEFflOa/VS8T/hFvBWo+JJGKTRWLyxZXlMKSpxX87/AO1xJ4g8dftUa3pGo3ge7a/lluJmYnJbLk8cV0+zdONzpwyTbPSv2ZbW4h+D66nOoC32oyyoN3RQAnNcb8ULNI9aupLdMRk5AyTjtXpHw6tVs/hvbaHp6qptsIUBwAQoNcN8R9J/tOee8ht2DlFJCnoQMdBWLbSO2nFxex45rlurMfl4JIxisCaNVYq0YHOMkV0+uQtHMyu3I4PGK5+6VWY7ex/KlfWx0cicbszLizjlYsVGcY6dKii0mONtzKTk/Sr7Qs8hKsQB1B61Nb2+5h8wxjPXpSTa6kxpRWqRWt7FY/8AlmQM8Vp6bGqsu1cHvUflr90MAc9c1PZ7Y2G5geegrOTvodMIJK9tTWtbiRFC9B647Zq1b3jRtuzyP51mxzKwGxh69OlTQs3LLkA9MjFc+2hSSky9dalJJHtLHHQ5PGa53xCzSQlt3AOR7YrVm3N8rNnjoKy9WhZoTtU4A7d6nm5XoJU76kPw+vmtfGlk3AWU+UWx0YlQK+1vg9qEfhqQLesRDcrkNG20I2QobNfFPgm1kl8SWDQxsdmq26swXIBLjAr7B0eRGsIbfcW+TLHOMAkmuujPniYcl3Zn0j4b8U6lo9otm8iyRxjMRlJbK9sHNVNA8byaF8TbX4havEZHt7MwTW6NtL5P3smuW8AatHqHhy0jaXEtrGsUils5A6Gt/ULOzkX7TMpBMfzFRgkDpmuhKyOSphoPdH0VD8Q/DPiaNdb0/VbZ4ZgWaM3IDrjqCOtfHv8AwUa0vU/EXibw/wCLdGszJBDoQW5KyAhQZmK8muisdfbRL0yaZfCCVlKsFYAEe4rWtdftbyNZrqS3uCqbALnEm0dcDdRzKxzvCNL3T4ytbqGNxvmTI5IJwR+dX5pgsYXJAwCCO9fU2p+AvhTq9qbG+8G2caZyBYqINp9igBrkta/Zc+Gmuq7aV4sutJmBBT7RKJVAzyMcGs29SHhpJniui6oq2rIqsSSAp6YxkH3rc0rVPlKMxAwOTwRXaSfsmeJNMZofD3ijStQjHKGSR0ds+2DVFvgN8StNWRrjwzNLg4UWy7g3PrmlK7QpUWlsZEN0s0o3Nnpj1Jq6si+WNqkEY5Bzg1Rl8J+MvDl0Jtd8N3dpFuwZJYjgjtVyOaGTaqzKSxAwGwc1GxnKMrk0ckbfKyjJOeueamVVZvlwMcdeaia2bjCke+cYNPWNlYK2cZ69OaiV7aCUW9R4t2b5lYYPtzmmSW6qpZs9OKsRt8o2kYxxg0bdylQwPuO1EXzIUmzB1S3BRtq5GMVzd4rRsVV/59a6/VI3WNlVc54H0rlriH987yKRkk46VoPlTRVhjbduZSeQR9a0NPZo7qBlUDbcISGGRgMM1Xt4WZiseB6cZqzHDIsbbWIIUkEHpSg03oN6o7Xxl4Z0pvEmnXklhGwljWWbqDMrPgA812Hj/wAnUvDcmlWelafaQWpEgaKzUSEIhVV3Vz/jLyW0/wAJ6vIpLyabEHPYsHBNdndaNJqCyxKpkEscgVCMCUEHvkV2xehyyVpHg0l4bDRDqZtmkCFQEU4JJrjLvxA14HZ1YuxJJOBnmu78RWvl+F760W0eN7dtzxOcFSrYauFtdHSa3MkZAUKdhJ5NS3oNW2MLUmVpNzKcnkV6X+xj4ibwt8d/DGrx3RiW28S2rSMx4CNIua4LWNPWO3a43AFCM8dean+GOqNpnjC0mUnclxHIpz02tmokrNMptcp+6nxlktdXtrDX4WPmW52FDxgSOOSa/NL9rPw1N4B/aC1i6uoJ5re/uWvYBDxnzSSfav0VuNWXxX8GNL8W23zi7060uzjndlA1eJ+M/C/hXxXq0ev67p32qYxKio8gCDDFtwUjFZVVeNma07NWPj/wrr1xq8LtZeCbiYLjM0tgDg/8BrvND8K+Ko/DsHiHVbKw0+1lJCK0boxwcZI5r3nT9L8I6aqSaX4etIyvCyGIE/yArkP2g457fRLG60izllS4QBo4Iiyod4O4gVjSiojk7Fb4Z6RoEyxtrviEJFJMFm+zXYQAcjB3ivs74I/F34UfDPwvD4T22Ec0Uhij8mKGWefk8tt5r8+7GTW5IRHbqtqwByJkI5/DNdT4C1DX9EuBqv8AbKfa43BUxKWUDOejV2U5RgjJyuz7o8c/Erw/f6ZerZQ6vI01nJFiSzUDLLgdCBXzhNqUtvrNrfzMwkivEDkjJVN2CK4nVviz46mb954kuGJzuKyFP0FXvC+rXWq6Uby4kZ5A+HLckEe9c9eSlY7ITUoWP1zVVbDFenQjtSKys3zL+IqGOZmX7wHPBqVZo1UsGAA5JB6Cuunds86UlGLbNbRI41jDEkhnwRnGa8p8UXmq674ovL+4gJLTbEVAMKq8DmvZdO0+S2jjj24YAEg9j1xXll1q3j+TU78nwWslv9rYRs2luhZVOOBnNfSUY8tNHiVLuo7GFcabNbMnmQqrhQ64OSB+FMhj1WRWsdNW4ZpyAYoHYb/TODVzVPiPb2NiF1rwmRdISCrad8uOw+Y5rT17xbpXg+aytJPDNzDcXenLcyx28Kr5QY/cbODT1TCN+pteGdH1DQtIi0+/u0mdQCFVy2zI5XJrm/iL4g1W31mLTbaYQR2sYclCcuz9c84qC6+NegWe2K+0q/iBUEPtQ5HPbdWdr3jDwXfs2oPLqPnTtgxjy1AHrkmplZFpOLGf8Jx4iWNVW6hYqcl3gHI/OqmreJ9TtPAGuazqYRykJggdBty0mEPHNV5PEHgmS/gsIb8q9xIFO+4XKE8AcCqvx3jt9D8PaJ4Ds3kaXV9ZL5ByCqYBz3rixMkoPzOugpOSLnh2zjh8OWUO0BhaqWA7E5Y1YlgVV+7yOOadI/k5jVQApCqFGMY4FQyTyM23GOOOMc15R3XVyOT5W3bec0ySQbflxn86czYU4Htx61G0bMxZc9c1jO2yLEVWY7t3fFRSRqrbuck+tPdWVgdxA+lNkRg272x+NSBE0bbfvc1XmRlz9c1ZkkWNThjn26is+6mZpCvvQSrp3GzSMuF24P16VBIzbu2RSuz/AHcYI7g00vn2oKV2lcNny/Ng+wB60x4mb7q5HY8VIqszbV45zTo4ZJpBDHySck4JApJ6mhBtaNfmwMDPFMa1m2mZ8RxjlnlO0AetfLP7b3/BVn4X/sr6rN8PPAelJ4o8XRKRcosuLezbHAdhzX54fHn/AIKe/tDfHCOeDx98UZtF0m6LFdM0SExxKo/hJT5q1jByRPMj9Rvjb/wUJ/ZU+A2oz6J4t+IgvtSt1JmsNIj89lYHBUlTtrzrw3/wWV/Y68R6qml3txr2lJI2Bd3tgPLH12sxr8gL7xroGpfv7HUvtckjEyPKSCx/GtXwr4G+I/xMvF8OeA/AGpardTkCKGwtjIxyCeAOa19jexN2fv34R8beDfH2mW+teB/F2n6pa3UYe3ktLpX3A+mDWpMjQsVkjKsOoNfmD+xn/wAEgP26rfX7Lx9qfiiX4fQWypPBJqnmqyA5PCRlq/TT4Z/DP4i+GNCSH4r/ABSsPEl3Giqr6fY+TkjjJYhaj6u29yr6iyLIzb1U46ADnmrUekzRkrcfIQAcNxWw0NjasfssIUtwSTk4+pqP7GtwwkuGHlqMsxbaoA9TW9PCrdidtEjLtdPuL2f7Lp1s0rDBZwCAgPcmpb7SUXUovD1rL51zIw8+YKdsSkZ6da2l1nTrSxuYfD6wbbaHzZp2XegPJ+8Dmsvwst1cX0moSSbpnjJlkJyTkiuuNOMVoNXSIvjLN5fw+v7WGHJuIzGAxByuME9a/Bv4k+A5P+G3PGUepsPlW4ubcOMhkITbjFfud+0RrDaR8LdUvk/1qWziNsdCRgV+Pnx78JzW/wC2TompSwlItb8KM5YD75Cyg1y4tctK6R3YP41bYwPB00dnZ3Gn7SHMolzjAK4ArE8SaGVkaGGZld1JUsc469K1NLkkhmS5j53DDgDIIPUVY1qFbiFdwAIB2tjoPSvJjUb0Z6EYWVz558WaW1vNNDJIS6PgkjrXIXULeYWZe/NepfErS1t7uKRoyA6MAMZ5zXnt5bMshVo8EdcjkVTkm9zojG5leT83XI646Y5p8UaN6jv1x3q4tqrDvk9O9NaxZW3RsRwTiodSy0NYxK7RsrfLmnxxMrZVjmp1tWZTuJGfbvT4bNVxuYk4FZSm31L5JJahaxSbhuz659auqrKu1lI4zkGmQxmNR19QcVJhmxsyPQ4rFzu9TWNJW1GNgKFDdfWobi1kmjZvLI4xnvV6G1k3bmYc8k4qW6t1ht3kbqqk5PpWMpPdGiioo1fhV4b0xfA934vvNoki8SQRwZJBbYF6V794JaSTTLdpJAzSKSxHpvbFeXap4fj8MfB3wf4eXaJtTvU1CV0XGVYlhmvWfA1usd0sLRlRDDjg5yeld+DcpROKoopneeEbn+zbmOTnaAQQGwCDXeQXi3Fqkir8rLlTurzuFWZA0a8evXmuu8DRvfadcR2yljbyEsoPbA6V3csrHHNrZEmrafbyy/aI4VVyMMyrjI96m0u1jkhKtGoxxlVxUTXkF1N5cc25gcEYxjH4Vcs2WP0JIHAHUVOtrC3W5TuoVhmK7iBn9KLPa0gYynCnIBqzqkO5fM24J9sZqlHDJbwmRmwckj3pKEriSRs2/wBmnw0kjjBHKPgitOGNWYeXqVxjurS1y2iPPJcMrTFiTkDgkYrbtZJo5ArMRz29K1UHczdpM6HT9Ja6XydysrdRKgcfrUl58GvCfiG3C3unW8MhHzS28flkn6gVq+DbF540kmjG9jwSeAPpXc6dosbRqzR56Z7GtfZJrY550466HgPjP9kzWrDTm1XwXqaXUSqTJbzKxYYP8JrxvUre60i9bTtWtXt50YhopBgnHcV95tZtDbmOFipIGCO9ee/GD4DeEfirpjfbLdLPUlGIb2BcN6gECsJ0VfQxcVY+RpNShjXcGHA5zzVixmhul3RsCAcZBzirnxC+DnjT4ba62ma/ZM0JOYLlDlHXOAQSar6PoN1FOVjUlNmWOOCawaaZk46lbUrfcxVVz+HSse40/wDeM0lvvVshs5GR+HNdk2gzTfIFA78jpTJvDMzKFZQBnkgUC0ucF9lW3Yqq8ZJGeDilhjXduYYUgiun1Dwssc7LMyqWBKyZyfristvDt2sYZcFQMtIDxn6dalaMNb6m1/blv4p0LTdGWS3tZdLlCRy3Nz99QOoGK9HsdeiSGOO6urWF0jCEeYSCQMeua8NurW6jjZWYg9trkfrXM6413CPOhnnHJDkSscZ78mtoyto2TKPVnp3jjw7b6Y1xu1nT2OoLIIoRNtLsRzgV5rNaNHuRnTIzny2yorm7xpJJlaaaVmBO1nlbIz171es5Lh7fy2mboBgseRWikJRtoQ+IP3dm6qoIYgEk5OKw9D1CPS/ENtd3TFYlLBiB3KnFbOqP+7KyNnPYjNcrr0iwK0rKCoYEAjPIIpS+HQzaVz9qf2SPGi+O/wBkfQYFkVp7bRzaMqtkgxrhc1x2pX1pbwvNeTKghO0FnADEcYGa86/4JCeOP7Q+DmveFGmMj2OrK6QN1RJIwK9F8aaHHD4m1CxuI1MS3jhA3QDjjFTNXdzWm1bQqR6lpsLJ9okiCsu4YK8qRkEZrI+M8NpceAbXVHty0VrfxyyFBgpGUIHStq3t7CHEckNtMUXahaJW2qOgGRSeJoW1DwRrem26FjJotykSxjOG8ttuAKLJbCad3ofOOn+J76+jjt9PUvJGrGaaQZVueM960rTVNZZWWZrZQeyxsSPfk1zvhiOOGEtEoI2qGbHJIznNb1qzSNuXjH4CsW3ILLe51Gg6sl5D5NxEEkQDkNkOPUZ5rsfA+qPCs+nMq+UVEi4xkNwDXnuk7lmWRWPBzxXUaHcNHOkjMF3HGScYrnd7WLg4o/YiS6bO2Pp14qzoEMmp6rb2Sru8yUFwWxhRy3NUJJVXK7ucdhW14BVpNQnuFh3GOAKGx03GvawkL1FocFeahT9Tq5riN2Zdu055rA8ceIfG+iQ2sPgXRlvnn3NeTyoWEAXgADIFbstrI3z8dPXJqvNazSMVUMM9SDjNfRL4UePrJ3PPLj4k/GVZBDeeD7QueCrrsx7531lat8QvHtwDHf8AgK2Mb5R2Nu0pIGe4JrW+Mul3Om31tfWuoXMbvAFcqzBTyehBxXELrGuKzRyancMDkEPITWbvcpKyvY2vC+tf23qL2+reA4YoorZneV9PAJ29FG6sy88aeDZreVtS+GbpMGItyLONSAMYbHBqO1udb1K8g0TT751lupAgYuRgdySOa7g6THbW6W3lpMqIE3SRhsnGCeayldMtN2MLwjonh3UNKtfEcfhZLS4LB4DNbRggg5DDAzXnnxXmg1n9oDRdFjlL/wBlacGmQDOyQlmzXsEEjW8kUHlqEBACgYUAegrwHwvrn/Ca/HbxL4nhZXjgnlgt5U6FVOxTXnYuVrI7sMm3c76RvMUszAEk5OKrt8rDc2QB24AqZz8oy+CP51C20NuVq86TaR1+6kSLtVtxHbtwaRljb5lyD/WmLMv3W6gYzmka42r8pH+FZlhJGy/XtjiqtxuVt2/HJqSS8j3bd3PsarXFwxPy5P49KAK91NtTarDPoaqSMu0MzDOeuelTTKzNu54PHOOKryM4+Xjr1zSu2xKPcY2dxbcPwNMaZVbaMZz60rbc/M2DjpmmbW3fKD9M96ajc1HLcGNdrHng/Svn7/go/wDtkTfsmfBprfweyS+MvEKSW2jxMoIgO3LSndxX0Pa6bdXEyNDCx+YHIXOB61wWtfsxfs++JfiXN8V/ibpFx4w8Qow+w2S6wJLezjj3bEFsy7a3p0JTd2ibXPxS+E/7E/7Z/wC1v4km1v4efDzVtSk1K4eS+1m4jVoWkY5YtIzYr7O+AH/BuBGs0Ov/ALU3xWhgMoDz6N4eklDoMDgyFStfpFpfibxHdWb6d4Z8K2ugafGMQ293pghyAMBh5RAqldeG5L6RZNb1u7llXI/0W8YIRnP8QNd0aUY7j2PEPhl/wTv/AOCePwGkjm0b4fDW9QtFAiOs6h9pEpHG7Y6+XXruk+JPCvgi0W38C/CyysYUUiJNNsYI9i+xVc1fk0XS7e3Fu1jFOB1a5iWRj9SRTYriGxUQ28aRoOiRoFH6VSgluFynefEHV7xYrx9C1tDgl41jBRs9Oc0tn4i1e8jM1vozRSlskXsZAP5FafdSR3DFlbJPJBOTSWM0LMY1YBgfu+gquSI9SzHD4ivF825k09BgYS3VwQPxBqOPw7Hc3LTajqF4wdsvHHcbVPsQQa1dPbbH8wBIxyemKZeXSwqW545wO/NWGmpneLbyOOO18OaVaxxoziW5SFcAL0UHFafhfT3tbN7iVVVpSFUA5wozWba28LTy3MilnlILE84x6VsR3Cx2YVcglcA4oJTaOC/aHhh1jwzF4YZTi8nAmIPbJr8zP+Clksngn4+fC660pUtQJ5LVmVByjyRIV5r9M/iRcQ3mtxWM0gKW6qSCOjHk81+c/wDwVv8AAt947/sjU9AjAvPD8q3zFQQRCGw5FceMXNSaO3CJxmeLapoMlrqtzH5ZJW4c7geuWJqSHw7NqUDLGAJFIKq38Q789K6SzVtW0DTvEtxbBf7SskuHQA4QtjjNWNIs4V1GLy2VFdtuTzjPFfOKVp2e57CtZnmPjj4c3U8Cr5W2Yq5LbM4GPavnrW9FvrW5eHUbdoptxBDDhselffniL4X3GsWO1VaOVeA0Z646HFeJfFP4GXkmpyanb6Qs0UKAyu0m3JIyTjFbO71NKcmpI+YY7Xf8vUZ9KdJY7U+UkH8sV1PiLwvc2GpyxyWpDAksgXlRVSPR227ZEAOehGDWM21qzspuNtDm1tXV8NwAP0qxb2LMwZVPrk1tSaKqsNrDg59afBp8artbqO2KydRo0krGUtiWUBV5Ht2qa301nYblJH64rSktY4udv0we1QyXUcfyqoJHvipk76hayFW3jhXbxwO45NQyWq6neW+kQsFa7uY4AxHALMBUnmNN8irzjgZ5rqfgh8Pr3x/8SLO3VSlrpkqXV3JnGSG+VahJydkZVJ8qPRdU8Im+8RWKtZumm6Ro0dpabs4Lo5xjPNdV4bs2hkDKo3scAgYwDXU+MNLtWsIvs6hfKm24z1Ug1X8NaG0kkKxoZZJJBwFztGa9zDU+SCXU8upNpl/S9Puby4jtrO3eV2IwqA8c+tfQHgL4XWOhWp1KOxCOUARVk3Ak9azPhd8LLKxuBqkkjbkUFyE4JPOK9NWRY4SpXAHIAHSu5JdTFy1PAfiB4ZvNA8f3VpeRlTdv9otiEwGUkjiptL0W4vpPJt4yzhckAdq6745ta2+uaTfSws0wgaIsikkAnK1B4fWO1jeSaEKGUEO5xjnpipcNRN2Ofk8O3WpKtnbxsZJBlQBggetQ6p4fuLd2tWtyCvRc5Ar2Twt4fkk09r7ULOSF5GAjV0GdvXOKow+BY9U1S6k+1AQhgQGiyTk9OtChZ6kqUtjgdF8C3cMcrPb4ESglgMAk1Yj8MyG4G2M5JAGOc16lZ6Db6VaTQ7TL5owWcYwPTFQW2hwMpbyRkHjIrRLoguY/h/TvsMiblACgDiux0mSNYxuXIIGM1lSWK253KCMd/SrFncNCo3NkA4watRsiW+rNqRY2UyBvrgVRmaNmKsuRkcjiiO7Yr8rH39qhmkaWQNyOaUldGD5W7JEXibwl4e8Z6QdI8Q2CzRuu0SA4Ke4OK+bPiL8NLv4X+KJPDFxKJoGTzbG5C482MnjrX1HbvuhHfjj61zPxX8CWvj7Qls2gAvrYF7OUnqOpUnNc1SF0Q1Z2PmlLdgp/d8D26GpYbdT/AAj8qtXum3GmXZsr2MpKhwVcYJIAzx1p8Maj7q5565rklBJmUkis1useGK4x0OOlYXiSz8xpZCgO5cHAwa6eaFtpZV5xxgdKxNYhO0q2eQT6YqbijZ6I861q18uRkVQCDzXI6rDuVty4yORXd+JrYNIVVfmJxnoK4zVraSTLKvIOSMY/Grv0G1pqcfqEO2Ytuxzkn1qSzkVowvB47Hoan1izZZA20gNkk9eaoxyfZ127M46djTV11LhH3dRmrNukDK3AAxz0rlPGTMtqi+XgMW2OPUDpXU3CtcxllBDDkZPNYnia0+06YbeSRlCyh8jsACDWkNYnNWVmfZ3/AARr8YXGl/ErU/DF5PhNX0USxqRjfJER0r7A+MOnrY+LJ5pJMfaFDgY5B4zX51/8EyvH8fhr9onw1FMwUTyGyUk/f8zK1+jP7RsGo293a67bxh4zbOX77drDmk3oTTejOZt7G2mt0mM0gDDhkfGfpkVoaZNBZyKu47QMbmOScjHPFZniTVLqw0TSNRjjEkd1Yo5ycEMyg44xWPH4kvJFDSRwhFOSQhGf1qXdRsjTseB6ro82geNNV8LrbSxx2WpSpEz5BaPcdrVrWtvuYN0z15xXUfGDR5JvH9retCzPe6aJVwCSDuYGq+k6OsMYmkQgOMLuHAGeorNaaMpqyI9HsZmVZNvykcE9hWvEzR4UduBg4OaSNY4FG1gBnHPrTbq6jVeZBgDOAeTUyjGSEvd2P15+3NJJtVu/Umu4+G9m0OiSaiykG6n+XIwCq8AivOl89pFjt1y8jBUA6kmvYdN02DQ9Mt9KhmLi3j2lj3PU17mBiubmPMxbfKWY/OmzHHGc4JJzjAqGG6t2X/j9gIAyCJ1PH51jeIdO1nU2kt7XXWs4HhCuEJyeSe2K8svrWWCZ4ZFJWKQplJOGI4yADmvXb6nnWaR6P8Tr920iG1tdCh1aNpS8uLgDySBxjg15s0cccguh4dKscjbHbg7fwxVa61GZVe1066njidQHCyFS2Oexqst1qLbvLv5/kOMiZs1F7FK9tUd/4C8M2FvpkmqSaM63M8pAecbmVQBjb3rRvLNh80asoBwcjg15hFrGuraSaZZ6hdFnm81iJmPygdOTWz4S0nxzbzw+IYrlXSZCojnnL4X3A4qG+oWb0NjxVqkPh7w3qfiW6hZo9OsJZ2VerBVLYFfOX7Mdqv8AYGoa3NkPc3eFPqBXs/7TmvT+D/2e/EGqzMgmuLeO0UA/eaV1RgBXlH7Plr9n+H0DLwXZXIHHJBrxcdP39D1MImoM7yabao+YE/XFVpZHdtysRjPQ9qkYsy7WJyDxzUEm77yrj3zyK5E3PU35OqGtJJzhuB3zTGlkzt8w/wA6dtkZe+PWmSNtw3eoe7sPW41sbdysSc80yT7o+v509WZmHzEDPr0pJO+Wz9T0NCdylCxXk3bSenB5Paq0iybtrc9+KtTMyqRuAGOO1U5Gdm+VvpmqS6IsZ5bM33j1yRjFWLW3hjmjS8jkIcZWKMfO/wDujrTre1+z2x1K8jfyUOWYDrjsCeKm0PT7671mPxnqimEJbfZtPtVGN0RYkSOM13UqK0bArxxeKNd1l5ry9h0uwgGBbWReO4f0DHOK07W30zRNMnazsIDNHE7LO8StKTju2M1h+HdQuLrU9TmnkLuLrJ44GWbgVp3UytYz7sgiBzgHr8prrirKxUVZEWn30k0LI0hJQcZ54NRSXDRyFd3fHXFZ2h6stxamZMLlyMds4FNur7dcFVbvxz3qiizfXTKNysay7q6+bcre/B5p2o3jLCPm5ByT0FZbXbM23d7etArK5djumkYMrHuMZzUkYaO6W6jAznB78VQt5N0g3P3Ge1X4pFhUNuyO9AWRrw3m2MN5gHA4xiqV1fLNdi3yCAMnHGKQzK0YZOh6c0+HyRhpEw2AARzQRyq5YtWVWG1SemABya0Lr92F3L8oHOBg4qHSbeOaYMi856gZJFSapeW6q1ujBmBwSD0wcVnK90Pd6HBeLLCa41G6ubdSwaXOC3QGvlr9o2xsr7xNGL+0SQPbSW08UqZDxsckc19O/EK4u7XS5541iMbSMJAxIIGMjFfLnizQ21eVZ4Zj5ioxOWJDHJIxmpmk43sdNFPmOO+EX7Pn/CxPBes/C7w9GDd2SvdaUJXwWgjG4JkCvGNL0+SzvU0+ZSssM6oxbrnIr6c+CHiLUPh38R7XWVt18i6t2sbl3AJiSVlBcA8V5/8AtG+D9M0b4y6nfaXagWt7O13aBSBkEjJr5vEUZU6za2Z61Od4lqO3ZrWNWJUrGAcHB6CuW8ZaaslnPIytIwIIIGM84Ga6a3umkt0kZgWMakkHOeBWXqs3Vl4IPJPQ1rKS5U2ioq7Pnr4o+D2vJi7QmQlMEDAyQScdK8V1Lw20czNbx4Ic71znHpX1p4zsbGSJZpFJZCSuDnJNeK+JvCMcOoyyR7SCxLFRjPpXJNtnVQvGW54/dWrLIY2wGU8gHpVdoGjbcegzg16hdeDdO1ORftMRLDjf5hUAf8BGax9S+E2trIWtFEkcmPLMcbOBjGc81zyu9zsUuY89vJHZT5akg9xzVe1sZrqQLtOTz0xXT6h4K1u1uCtxpUkYB+Ysw498ZzVnT9FWxmG6MhlyCDjikr2KvdGNa6KUj3yKQACScdK+hP2VfBcPh7wa+rzQkXOps1wWZSDsztQc15Jp+gzeIdVtfD1kFE15KEG44woGWY19QeC9JjtNFX7PDstwqR2aheAiDHFdOCpe0q3ODF1OXcpeILVbhobFV3NLJhF/2jwK9I+F3w3hjv7ZbyF/NlXYVKY2lenSqHwm8Cr4z8do1wzLDYIJi4XOZNwCrXv2h+HbPR9PgWGFRNCjRl1J5Ge1fQRVkeROpfUl0Pwr5NlLHHMAIVBJYZLgDtVSSNIpVaTgBgSCevNbCtLDCzQyMuVw2GxkenWsTVr+x0+CbVdUukitbWMyTyO3AAya0HDa9j5z+Jdj4u0T40apdW2vS3ccd07W8V7dSOkSSYIUKTivcfgp4ItbPw2NZ1iY395eojss7eZFEDkgKrjNeLXWtN428VX/AIpmt2dbqci3VVwWX7qDAr6O+HGj3+keCNPtdTieK4MW6SNiCVHRelAne2ppXELLHtVVBVcKAMAD6dKy/Cka3kM18uAplCKM5yQMmrfibUF03TJ7ncdyrsTBwQW4Bqbw9YrYaJbW6x7S0QkcHjluaAE1GNVhKsoJJABximWNqqruK9wamvGZpBu5/HpS26rGo+XGOlOOwFO8t1kYqvB/kazriFoj8ucfpiti4bawXaBkfpVW7tWblepGc1Zmm5N3KVrI27b1xzin3kyrCJFJBDAk56VHJHJCxdWxgjPFQ3E26F45MkMpBIOCD2NBm2ue5rafNut0Y8FlBxmprza0AVeCDkHPSszRbqOS0i2zbgF2ghueOKvzMvljfxgZ4NZNWkJq7ucB8Y/h6viPRn1nSLF5dQSVRJ5bYyucsxFeP29upUSLkA8j2r6TWZfMZmbIwQykZBBHPBrx/wCIPg+28N35ksYSlrKxMZLlsDOAM1hON0ZbM4+aFmz1OcflWHrUSlmjXrwSRxiunmjVlKrycduDWHqkayFv7x6jpXK1qTbVHn3iqNdyrHHgnJYjv6CuM1Tc25lXsTnpXfeLLdFiKswQqCWBHOD0rgdQkj2ssbA5GcjilJO90U07nPaooaQbskgYA5rNkslkY7lwcg5zitW8HzMxzkHOOvNQwxtK2GXJA5I4pJ9GarluZi2zK205xnqKwfEELrNLCMFCAAR3BFddcWa7tzcc544rD17TWjnMkeWRlBJx0PcVpHcxrQ6lj4Fa2vhDx7o3iuBf+Qfr9tMyq3OFdWNfst8So9N1nwXBqc0KypJErxHaDhZVIPWvxE8M3i2mq3MKSKmyVXjJfk4JAxX7IfBLxEfG/wCyx4Y11ZDMx8NW/mOW5LooU1ocsGlLQ5zxxY6mvguG40K3smj0+aKF47i3aTbEcKNpBrkLWHxJdae0sM2kqWDGPPmZX+ld14ya6/4VprVxp1xIrWyC5kMTlTtXluQc1wPhXWrP/hBWvIm837RGfK8wZwScDrzUtXOhLqZPxr8SSeFvAWh+NtSuo2OmyLb3ctupZEDkAnnmuE/4aP8Ah5qcYWG4vrhlGC1vbhv54rtfi7pK65+zB4tsmUtLaRm8BYZyIdshr4r0v4trpmkw2uladE8gb980qDA/I5rOcU4jik2fS83xz8IspaPQtZc44AhjH/s1UpPjvpsbYt/B+pSEE4DgKSfwNeF6F8TfE+t6jDYRwaahcElfsxyQAT1zW3N4yWzmEMlpab1AE3mFhk9eBnNc8lO2hvGhza2P6JPAeiya54stbeS3LQ25M8zFtoUL0zXqGyRpCzcEnJxxXzx8P/2qvh54Wa5vPEelalatKQglcK4CYB7HNbl7+33+zVpyn7V4wuiwOCFsZTg+n3a9/B1qdJO71PExFKdW3Ke03EKqu7jPua53xB4XjuIfM0vRLCaZpMlZYF5zyTnrWXb/ABv8I6jZW99Gt7bpcQiRUuISjLnPBVgDUg+L/hVSsy3UjqDnIAXH512PGUU9zn+p1Ecf4ktb3RrgQyeHbGzYDLILYBiOxyDVTw7o93rdnJdW+lC4kim2yx20edo6jqc1bubrQtR1WfUtU1+aVZgREJrosQpJIXoTW34Q8ZeBvBNlPbjUZZBLJ5mTKDg4A9BS+uUG9x/Vq7WxY8HfD/zPtNxeeHriyeQFDNISCRznG45roI9B/s+FbWzjPlxqFjDN0ArH1T9o34T+FtCuPEfirXW0/TrZgst5KrPGhOcZKqa5mH9uT9le4YSW/wAadBfByFe7CfzxSli6NtzNUKnNex5Z/wAFJPFFxZ+C/DXw4jXEmpau11MwbGViG0Liq/w003+yvB9ja28hy1uhdSOhArxT9pn9pvw18Zv2hrDUdOtWu9K0y2SKL7LdowP7wktuPyV6h4W+J7SaNbrpWgPPEFCxma8hiJxjjk14debqVGerRhyU/M73yZGUyM5HfrUTxuxLKDjP0rlLz4pa1aqGuPC8ES54DatCwP5HNVYfinqMytLNpFmoB+UnVIiB7YBpaWQ07yO1WNvu8n3xTZIe/fGenSuRk+JsiqPLs7FSOSW1OM5P5ikj+JlwrBprXTnU9QNUiUg/nT5bmp1YhLfdYA9sGmMrKvzZyPwrl4figyqWkh0oSE4VDqqdPqKvL450S8UD+29NjlIy0R1FCFP1OBUpIDTmVmUhcj9Kbp+ny3lyIY1JIBLHHYd6x7zxxoFnH5lxr9gFHUreI3P0BJrpNMXVf7Pt54Zolt75QTIg3Hy2GQc100ad5agN0m3uvE8YvplSPS7WbbDHnBnkUYJIq5fXHk43AAKRwOwFWY1jsLZLOxiEcKAhUTgD1NZuqTboyG6jnJ4r0NIpWCzscf4fvLq18UarBMxJkkZiCepD5remula1lXaATC4/8dNcprk0dv4klnhypLB8hupKjNbFvffarV28wgNE2AOB0NUWlY53wrq0cli0KzDckmGUnBBwKutcM9wGZu471w/gbxBNca7e6UzDaZ5GUnqAM9K6yGZmmDbug7jpQMu6o7fZyVboOCOMVjR3DNKFVsn06c1q3Raa3KhTnH1rDaRYbkI7YIYDk9KANJWZsMrEEjIxUkl1MqiNm6AAHOKNPVZowVUkDnAPQ1LLHHIwVV/XpQBl6leeJrQG98PXgZkALWpUEsOpIB4p3gn4r+GfG96dEhvY7TU0JU2U74ZyBk7ccVcuNOlhY3VupITBMYHXpmvnj4rfCjxBrravarc3GnzFpJbS4hk8v951TPOaWiQ4P3j7A0HS543EaszuV5ZRjafTrTdW8LzWeZo2IjxnLn7tflLq37X37fvwS0KfRvDXxGE+n6fKUaSTTI7owE5OGeUeZXni/wDBRz9rj4gfErwzpnxZ+LE50GPXrZNVt7GM2fm28kirJuaAq1FzeNFN3Z+pXxj1aOw8P3EPmnKISu053MRXz5JZSLGkMmRlQCQOte4+N5rLV/Ds97Z7ruO4hEsbxnA2g/e5ry7Xli/4Si02ybTJGgWM9CdxHSiyaH7NQ1OTs7Vo5o3uYSS0gICjGQOTirn7QPwuute8Caf8QdIty81nCv2x1GcxlieScVvXlgsd2kZjUkkmMAdARzivXPhVothq/wAPha6tCk8EpNvLE67htKkdDxXJWoqUbWNY1JQSkfFmj3ytpqBVIYqcAH34qjq07Kp2/j7V1Pxf+Gt/8L/ibfaAFcWUkzSWkhUgPGfugE1z19ZtJCWVck9h2rxKylB2ex6FGSlFO5xWsRtcKy9SQR3rk9S8Mx3CsrQlifunJBH5V6Ffaeqsdy88/WqX9lxsxbaMj26Vyy1R2Qep5NceHXs5i2wgA4yetPt7cwsN3HTnpzXqV94bsNStTb3cJILA7lOCMGsHWPAsscw/s+MvHjIJfB+nNZtNo1UraHG6hbpJAY5oY3yuBvQEgfXrXH6/4XWZpLi1j27cHaBwRwDXpt14Zuo2MLQncBkqeorOuvCt9dXCabZ2TS3Fy4jhjVclmbgYFZyXK9yublMX9nz4YavrniGTxVa2nmGF/slhCQAZpmxu68V9GWPhK9aaHRbG3NxONscaIuOT7da9J/ZX+Bdjb6jPp9nDF5HhfTljZgmGnu7hTvJ717M3wW0DwPYTXOmKZr2RRvnY5KgckDPNe/l1DlpczWrPCxuIlOvbojyXwv8ADy38HWltDbxj7VEd80gY4Lk5xXQeIPG3hHwboia3401+306GWQoGnbaGfBOBmtbUtLk81YVXB3YYkfdB718Zftg+Lrj4ifFGTTreffpOh/6PaxKTtaXGJH9K7mrakQSlqe7+Jf2yP2e9CtZVXxkLtwhAitoZHLH0BC4rwn4qftL+Ifi7cf2F4esG07QjIPKhJ/ez46lyK8zs/BFhMo1CS3aMBsK6tgE9DxXp/wAHPg9q/jBng0y0P2eMDdLs3DIxnOMUk7mvurU634FeGZvEPiTStAs4WkjjkWW7lC8Ko+Y5zX1HcSKzMyjgk7fYVy3wy+HulfDnRhb2Mai6mTE0g/gB52gnmuiuJlWNtzY9Dimrsx5tTD1iOTVL9LJpuHcAKTwDmugdlVdqqAAAAAMYA6VgaXJHda8qyYVlVyoJ6YBGK22kVfl3Dp9aAK8y7pCDjjpk4qSFmUBdoIHORUbNvb5eueCDU0cLLH3zx0NEepPPG5U1Bl84MrY4B4FRecsg27icdDRqy+XGZFbBA5NU7e6ZYd7Nx2NXfUwcne6ZDqDbpCvUDniqrFt3y8YOQc1YnXzJDIshBPtyahkh2n5cnvg8c0wUVu2VtNuGtpDaqcYlyDjPHFdBIyeWAzZHBrk5riS18Q20asG80giLOCecda6ZpFZflY4J4PT8ah2sMoNMv9pzWysQQN4AH8JxWZ4q0WDXtGuNLWQpIR5kRUZJZQflqS+vPL8dNYhiQdJVwA3Q7lpb6Zo5EZmwW5Bz1OaydrEuKZ41e2rWcz28yFJIztcMec4BrB1SJQp2NgZz0ya9M+LPheazY+JraEfZblglwEA/dS9M8c15tqESqpZW46g561yVFaRD3OM8XK00JXcBtUnJ7CvNbxV+ZlYEdsDGa9F8aQwzRqk0BJkVgzByM4xxxXnmsWckTFYWJBOB6mkMwb5WVizEAE9z3qOxuI1mKScfLnNGpSTbd3TBOPesibUJo5htbo3Ax1FK2tyoT5VY3ZJYZJAitzjgZ7VR1q2ZoQ0a7XJ4PTiqjao0bCTacjpjtRJrn2ldrKQc5PApx3MZy7M4+5t5NE14M0gQyBz5ZXIG7PGa/Uf/AIJqeO08U/sqw6FcSF30i+ms3T0VgGAr8xfFDNHNFfKuSilQc4B5z9K+9f8AgkZrX2nw34z8HC4ObO6hudncb0ZCa0OVq0j6U0vRF1C01nwddSFUvNIuIXcDOMKVBrxL4UeIdM1TSNQ8MW8cRFmEV8jJBYHg17Lq2vTaJ44TTI9i/apRCHHGQ5ANfmX+25448UfC/wCNfi+08L+Ir3T2bxDdrmzu2i+QS/JnaRQdsFdnsf7VP7dfw3+Cmlaz8KLC3k1rU9W0yWC4gtJAywGRCvzkkGvgy3+M+vwQKlvolsoViSZ2LE5OeccVnahouq3jXniK+uXuZXk827uJpcszMepJOayo7eORW3Sc5GAD1FRZ3DlUXqeq/Cj9o/SLPxRap8QtFFpYtMokvtPbDQZIGTkmv1G/Y5/Y1+B/7WGmDxPe6jeXdrMwWN7K6DsinIRwwG2vxeZoo5DGy5OcZPY192f8ES/23tT+AXxbfwD4r8SGPQNWjMcMU7ny4Z9wUHOapxTeh2YaUVKx+7OuabodxpFzDf6ZbTxGBgUNqjZOCBxivM3+EHhPUJobi80RYxFMjkraoFbaQQCCuK8Zh/4KWeJmcrP8LbaVTxgXm3+amnX3/BRrxRfRiG1+HdpaoQAczeYx/HApSUkjyk0kmfTFxqk0ihUkwAAAM4VRXNr4v1W+8UGztY7hrEW28T7MozAYxnrXzpqH7bvjDU7OW1h0GK2aWNkEy4JQkYDAZqlD+1FrK6ZYaZ/YzBLCSJgQc+aQcHdgg1lJSNItPQ+m9R1aSK1lkt7WSWbblIoBl3PoBU+h6xc3FhDcbmUSpv2MMFc8kHvWVoet6DZ6EPF3inU4rVrexMt2hchYCVySOKwvg58R9G8X+FzeSaiRLb3JikEi5Kt1xkCom2o6mkWubU4z9vrxj5Pw20nwOs7JLqmoieVUPBijBzmvMvhB+zp4A1/w3HrniazmuGvIUeKJrto/LAyCQExU/wC114q0jxz8af7H02bzYNIsYbQhHwPNZizYr274HaNpFrpVn4U1TTvNaztAUcnGBgHBxUUW3L1Iq8qV0cz4R+Edv4ZkNzo3h6CGKZBEzT3CzhuflJDEmvc9L8P6FbaZBZjQtPAEKlytjGuWIBJwBUv9i6c0YXyVALKSoAGcdOgq2W3L8y5x6Gu5QhfVHOm3oU/+Ed8PL97QdPPHe0Qg/pUbeH/Dq8f8I/pxAPQ2UeMf985q6zL/AAt9RnHNRSMdw2tg85wabimy1GxnzeFfDDMSvhvTQSecWacfpTH8LeHeGXw5p/XnFmnP6Vo7tvzbvejdu+b15pOMWtCjKn8K+G2+X/hHdPB9BZpx+lV5PCPhtsLHoFihByCLSPJ/Na2W3LnJJxz1qKTc3sQfxFSlqBV0vwjoE0iRyaFYuquD81nHkDv0UV02vXUdvpkcNhHHCQyRQIiYEaKOigcVT0aGOGFpmGWbAHOQBUOqXizRrIzfcY49q7KTsgjq7s1hdG6t1ZQASgLAHocc1ja1cNDGy5JYcDHWpbXVI4YVkaQ7WHB9RWfr1wkjGSMfMOCMda6+a5ocn4iWSS887d1ABIHSrOj3DTWpjaUBipXgdMggVT8RTLHYyTK2HOFi+uab4Ruo5NyyKSVkBY54NULocD4ChWPxlqc1xcFPs0kiFducliRXeW+VkDbscjP0rg/D9xHp3xS1/RbpWDS3bGIg8D5siu7hVsjcxyMHigqKutS/GvmAbW4xzj1zWFrUElvqBZVwrHK/1retW+XavB65NZ3ia3kEazKw2qcHA70CaS1LXhlpJIXZl+XCgHOPWr0kIjk+VeeegrL8IzMbeVZF5VwEbOQRjmtnau5W25z3zip0AdDGWjBVcHqD0rO1ixt7qcSXFvG7Dgu0YJIrdjjjaHdwCRng9Ko3MK87WycZB/rTsGt7nz/8Xfgp8Pp9bubPV/CcbpeKHW7jfbI4PJG4HNfOPxY/4J56Jqtn9v8AhtrpgKuZUsLwF1d1yVAZRmvurxh4QtPFdjHb3GEuIGzbzFiCAeSpxWLpeiR6TB/Z13bbnQEHJ9ec5pmqqSS8jwz9mL40+Z4IsPg946R9O1jRbYWCPcEkTKi4Y8c16PqHge0XxJDqsF08yW6ARMsWQSM9K5b9oP4AW+s2N/4v8PxzRXEFgzxyWLBZCUUlUYYxXx34G/bw+NPwz1WTwV8R7Rdbs7dxGVYLFPEMD5ldaV0jai1LQ+2/EelzaffW3lxlmmjdgxGAMdRXpPweSYfDa3lVuPOYnnG85IyK+XvDH7Tvgz4neFZNS8OSSi6tITC9jPL88G7qSSa+r/hbptxYfB/RI7yFknNt5kqsMFCxyQQeaGkwqQ5Y6HKfHf4RQ/FDw+12shS8tsCBQvBYkkdBmvlDVtEvdAvpNH1WMpcQkqyuu0nGOcV98NYsunCZWIZsMyBcgivDP2pfAehawhXSLeNdZAQvGsm1nQDf04FebicOpK5eGquErM+Yr6zWRtzKBzng1U+xxxr80YGTkn/GtS6Vo5GjkHzocOB1BqjcR8btxGPwrxKi5XY9aMuZXKkkcW7HTHSkWzhk+UKCetDLuk2qp4ORzU0K7W6D0H1rKKvI3g3JEDaDDMwVlBUHIUjpXQ+APCel+HItR+Kus2yC10K1MtjFOu0XUudu1WIIqDQtGvfEOrQaBp6gT3JIjdiABgEk80ftE67Z28mmfB3wvGwtdPuFlvSX3hppAPlBIzXNKXNVUUXLSDPrL9kHwTP4b+Amm6jqrvJd+Ipm1aVpBkhZMeXz1rtPElk01u8ax5YLhfer3gnTovD3gnR/DEK4i07SYLePPXCIFFW5LGO+3eZgKoy7dMCvsaEVTgknofMyblWZ88/tH+MG+Gfw+vtdjZU1CYfZbGMt8zSvjaR1FfF8miqsK+c25icySNyWJ5JNe0/tcfFnSPix8YI/CvhS/S40zw4rCa4jbKS3DYD4Necw+HdQ13U7bQtMhLzXUojCoM4BOCamTfNodUElqbn7P3wmtPG+sy6jrtnIdLshvDKQRK+QNhBOa+irG3stPt0stLsYreJQARGgG7AAGSBVDwX4S07wT4btfDelRqBCgNxKBzLIcZJPWtRVHmctn1OeRVJaCm7vQsRyNtHbHc+tVr66McZZW6AnPpVgMqqMqO2ao6wy+WdoA454qmriIPDKSNJLcL1B2Ekdc81tSNuXLNjvmsnw2qpFIWwCZM5zyeBWjI27AVwRzjHapUb7mM5O9kMVW8zcrc+mKsLIyx/M3br6VWDNu9RnGankZVh+VjngfSqSsiTO1yZVgManLMwAwOgqlGoW1BZcZAP0NWNZb5VZWwc4BzSyRsIcbj04rNt3Bb6szVZt23dgZ6g06VWVdyc4pki7JCyk9ex6UrMxjLdAD65qoyvuKxia0yrqtheNH80d0gLA4ONwOK6GO68xdysDknFc/wCIoWmsG8tiCjq5wOoGQataXqDSQpJIcMY1JBPTiiSVkFjC1LUVk+Lz6e2SyaYEJVuB0rT1K6WPWYrOZgPLgDkYzyWJrm1Zrj4walextkRWbAEHoQyDmtyGZptXN5MuXkBzzjAwBUTaew07vQ1761g1bTpdMvIwYZ0IYMuSD2NeN/EPwtH4fvz9jUiIMyynBwMEAEZNeyxs20bc56gdOKyfGnh1NW0w3SLiaI5yFzuTkmsJxuhVI8up8yeMIP3pbyQV6RnPX1rhtUs1XKtyVPJ9K9I8bWK6fqL2DKW8tR5chGNwODXn2vLHAzKrYI5Az0Nc97GDSjK5yGtQxszKvGTXMXFrMsx+XIJ784rqtSZZJCdo68c1nTW6s24cnqeM0WYN7GPcWcywmQREgDJIB4qkq7c7eCBnmt9lbaVVSCQRjGOKqf2S0kcjKpJRSQoGc0K6ZMrs5vXFaS1CtIQA+Tk9Rg19Sf8ABKrxgPDH7SGoeFbi6Kxa/obqEDcNJEd4r5w1DTVuNOmj8sEqodV7nacnBr0H9jvxP/wh37TfgnV+nn6qtpKCcAiUGOrUroxlotD9GviJYsfHNneSeaqBop7d0GFLxvnbmvy+/wCCrdxHbftW39s12qJqcVvJOsh2iJzGobcelfrj4gWbzY2hmCKkuWBGTg88GvyQ/wCCyeg3WiftXNPNJtXUNJiubdxwCPuEUb6I6qcvdPIPFmj+Gm+Hl5q+lagLg2yokgtb1XCspDHIArzqO9jZt0LYzyARgiqlrcTQrJHFcSKsqhZUWQgOOOCM4pY/9YAqgDjocVUXbQU3dk8a7pjIzE5JPuTXoXwY0/TINbtLzWW2Ws88kcpd2QIcfKQVOa4nS4Y2O5gAOufQ16b8GNBuPEvii10DSra3mlKGeGOa7aNTwQclQTVNxUhptKx+kMEy7Q3mEkdz1q9bzNIo2t/WuEh8VSQxhlXnsCetb2j+LLWR5NkbEJjaC4Gc59q15HJHHdnTRxy7s8j05qS4muLWB5ocB1QlC3Y9jgc1Ui1yzuNPkuI7pVdMEoWyQM17b8AvhZZ+IfBLeI/EMMTx3zslqDHuZdjkE88VnOnbRjTaZ5H8Ib7WYfE1zd6hNLdSiwlaBDI/JPytkFsVy0MniPxB4mu9S+2xRLJJvZIUaBQAcDCqSK+ldQ8JeFfD12tvplgtvcXMboskcZYgAAnkDFYXw3+EeiaXd6hcanZyXJuI1CSywlMjIJ4yawnRbjZFqrG5xXwq8Kwal4qsrWS8IBuVeRdjSGTqTyTmvrv4QWd3qXia5vfszCOG2YSO3ADc4FeaeHfDuieFLt7zw5pA82ZNsjjIIxnGMivZfg9Fdx6ZdzQyFS8ymSNkwXGODk8UUMPKm9RuSqSOv+zyKoVlOexBpPLlZcNjAOQBTppLwLxGfbGDUDXF4v8AyxkPXkLXSotMXLyse8MjD0x09qjkhZflZu2elNa4um+ZrZyf900gmuWk+aFgPTB4pJO47itF8u5WyRjAHemMs27dtNWFumVfmhYnHYYxUcl15alnhb1JIIFPldgumQSMyjLdeKiZyzFmGDnPWppLhZF28Z6gA96rrIWk27cd+tTrewy7DM0duE3YBHr1rFvNQjjvZ9IncgSR7lLDqMZ4NaMl4sfysvbrXP8Aii8jkvYZhgPAuMg4Jz8wrrprRJBHcuw3S/2ArBgrwylGQ9SCSRioodQW6hZpGyyYDDOM+9c1daxNb38DTTMsPmKXXOAQTgk1rX0zWSGSFhwcNgdRXSlY0SbZl+IpXksJo1cHb8xIGM4Oc1S8K3EayCTcAWBB56gU/Wplu7KSNVyrrg84xzVHwvIsN28bSEE4Ix0Jpj5dTkvGF5JpHx8u7qNV8t0jkIboQUUV6LCzeYVZT1yB0wK8y+NCtH8XtJdm2rc6P85x1KlwK77w7qkOoadb3UK4zEFZSc4KjFBZu2sjtntj296r68skloWXHDDJ9BUtu7N7emDSXStNCY2Ukdic5oIexW0DdCoZum7Ppmt2JVkYNuxgdMVlWMPlr8q8An8K04W4Xao7d+9RbW4i5G7LHtX09ccVFcYZdzZOR2pGk+T5e2BxSfK0e7v19qd3cLO1yCaGOSMsvBHb0rI1jTReQs1vMI5YwSjMpII/u+tazsqsRuxn9aq3jMMsqjBGOO9UPd6I5azvoZJHt7xQ6gbJ42UYYHORXxj+2D+xXbaZ4ok8afDmyECXDNIlqBlXz1KmvtXxBprKn2+0UAqSZUUYyOTuqtZx6brdm0F4IpljYFkZQSh7HmlZXNIScHdH5kfDhvEfgHxCdUtFW2uI4nhkS4i3qGPGSvSvbfhP8Y/2uNGgW00rVXu9HDlrWK30CMxjk52jaDX0brX7K3wx8U63Lqn9nywTzNukRZMI5wB0waivvA83hTVZtGtPLMNrEpgZIthC4HHFM2lJzjuc1rn7bHxj+HOgNrfjT4W63fRIVV7pLKO1hjzwNzMuK5f4NfGXw78d/EWo/ELRPFRvJgiC705pS72vmAMqk4Ar6A8P6HonivwMfDWu2UU0VzA0FwZYg5BI75r8x/2ofhT4h/Zj/aQvrC0jMunXDm70+GckxSwSHDJt6VhJK7uEHFS0R9afGvwI8d/J4p0KyRbcoPtkMZ5ErMQWI6V5heRyLIYpAAwydpPIx+Ndb8Av2xPCviXwu+h+MNTi0nWIYEEP9pMiRXrEAnnk12Xx7+K/wr1v4a+H9Zms1j168b7Otnkwi2YORI4jXArwsyhyR5j0MPJKaXQ8VkmaNgFGTxnip7Vbq4kENrDvdgSqlgAcDJ5PFdHq3wvvV1vS/AfhiSDU9f1NMw2VkzmQA/MpKnivR/H3wy+HH7NPgu28YfEWaxtNUC70RbqWRnkLZMao+Vrw5YnpY9SMUloc9BJpnwS8FT+NdQnCavPalLNLlMiYMQyhU5FeZeA9BbxP480eTV7h7ifVddg+0SMeSryLnisXWPGWq/ErxHJ4l1uOWCBTssLJ3BWKNSdvA4rtPhIpb4l+GYY1yx123AA5z+8WunCU/wB6mzPEc3sz730nzpLWGN1BbaAAp7Z4rwL/AIKEftPx/BjwEnw18HagB4n8SQPEXil2tZwEYMh717prXiTR/hz4X1Hxl4hvEgs9HtJLm5mc8AJlj71+WvxK+IOv/HP4m6v8U/EMzFr65K2ULnIggXIjQdq+rhZKx8/SS52W/hBokdppVzJJMGuGUMxJJOD83JNfQHwS+HI0mzPjPV7cNczjFoG4AUHO7FcZ+z14DsJPCNpqF7I7HVLgEoIwNqxsw65r3PzGaNV2hURQqKoxtA6AYq7a3Nm+VCtIyqWkyCTnI6E1Jao0nzdfTnFVp5lb7rEgkgDNXbNWjjDM3JHrTEStGwXdyDisvWmZY++M4rRkuGVTtYntgdqx9euW8sKo6kEjuaDOTsiXRWVUZmYjJ6A4xVppNrfu2I9R6VX0mNVtVZW5IySelSTXC7tq8YPp3oMyRZj91Vzz1zUjXDbRuUjHHWq0TKzbixB9Mc0szMq7ecY78EUAVdUuVkuIbdVJ3El2z24xU0zMybuwHIqo8fnXgk3fdPI6nFOuJtrbVJwODxnFYv4gK86qZCx459eBQsayKdqjp/kVFeSbn2x555OTip9P3CPazZ96aTQ3K9kZWoQtMzW/3QwK7iM4yMVjaLdSR74biNlZJdjKDggjg11OoWqsxbGAetcpfKtpqslvCxDySGQAjB+bnNTzOMk0LlklqYOhyST+OdcZpAshYg7eoy61091th117NMHYoOBzjgGuP8D3Mlx8S9bZWyYmkAPXJziuq0+aaTxdezSMQphRVUjkEBAabjd3NLpQN+PbtDcDH4cU6ZmjXc2CCMFSOCKZbs0siqeRjPAwaddRsxCrkAD1yKlrRmcpJx8zwj9ovRG0PxBFexs5s7qLfAxhwFJbDJu6V4t4pjWRWZF7YBHNfZHinwjbeN9El8OXyxEuc20spwIn9fWvNb/9g251ZTJH8Rba2L9I1t2cAfUsK5KkeWVzB2tqfKU0asxZjg57HvVC4hk3ErnjocV9Vy/8E4bqTDL8V4R6gaex/wDalRt/wTTupmDf8LjSMkdP7LLD/wBGUibts+U1WR2+Zc45zTGaaOTcvBxjg19Yf8OzWjAWT4yqCTkldLySf+/lC/8ABMSxYiSb40yHPIC6Vn/2rQJ6HyLcW7LkNkAg84/WqGkatd+G/Emm67YzFLnT9SinhdW5DowIwa+ypf8AgmJpUkn7z40z8jgDSTx/5FqfQf8Agl94E0q6a+1D4k3uouWBEYtxCp+uCxqUZtOWp9VW+qL4h0DT9bhkDpd2McquP4iyg5r87P8Agul4Qa4bwN8RrezXcgm066uBySdwkRSa+/PBGm3fhjwVpXhS+kWR9MsI7UyoeJBGgUNXzB/wVz8Dr4n/AGS9S1e3iV5NG1+C+YEZKKzMjYrWm1c2g2o2PyjWPy87mPWmMzeZ8qng8AVbhtWkEUUalpJMDAPJOK+tf2Uv+CSXjz9pTw1H4x8RePYPDdjMm+0RrPzXkXsT8wrXlUdjJzsz5MsbiWORGWcxgNyWAOfz4rtfh74gvvDWrjxJpd+8UjWjwgRrgjJHIbrX1/4l/wCCG/jLwHrdvqI8SXXi7QwMzppKiC6QnPIVywrmfFH/AASy+N8OprcfCXwZrdxYFcNb62I4pY279xScLscazjJM9H0+4YSCMtgZznPStvT7/wAuRVXqpyMiuQs7wqw3SYPTr0NaVrqDKxVZDuB611q6dtzCyZ6Fot1e69qNl4e0WJ7i6vrhIEhjXLFmOABX6GePPg9pHhT9nm48L6UGjOlaT5zhHIJZUaRuQc18c/8ABNr4cN8SP2hLfX7uENZeGrZr+4LqSrODsjGelfolrFnb65YXumXi5ivLZ4mXHVWBFc8p+9Z9Aa93Q/MO+8TapDfSwrqt/GI2UDy751BOATwDSX3i3V2t1VfE2qrz1XUJDj3+9WP8R7W88I+ONW8PX2VltNQliYHjOxiprEbXvMXZu57kjODXfSceVMzhBrQZ4u+JPxLsZN2jfEnxBbYyQF1abjr/ALVcTqX7V/7UvhqYQ6R8dfEsEOSVK6m7Dj6k1s+JriNstt3ZX07V5h4yWOZTHGwBTJyeprOSvLR2OmmtDtbH9vz9sPTvli+P+usByDNOJCf++gau23/BS/8AbatpAsfxxu2UHpJawt/NK8KupjHIRyCM8Z6VWW6dpDuYcnIwKxXxG0o9j6Lj/wCCo/7bVu42/F4uOg3WEB/9krStv+CsX7bNqo2/EmzkI4/e6Rbsf/QK+YZrj5CqMcg5HGKbFcSsu1mJOfXnNaRiuYylFpH1rY/8Fhf2z7eMJNruiXJz9+TSYwR/3zitjR/+Cwv7WEMqzaxZ+HryMMC6HTNpK9/uuK+O7OSTcPmOSfWt6wt2mUK2QSuCR2FaunBkRumftT+y98f9O/aQ+DGnfFCysltZ5gY720VgxgkUkMpIrv4ZNzGTsAMmvh7/AII0+PmXRvFnwsurxf8AR54r2ygJ+YhlKORX27HKY42kLZBHQDoa5KlOz0NBl5dMrblGcY/Cuf1KOOaaVgxDMSV9M9q07iYrIducH3rN1Rlhha4ZgqohZmJ6Y71vSVldscdzn9eufL0h79ZADbSAtnsMVoR6s2taRDdxyKRLGCQD0IHNYV1Ilw9wrMBBeRsrlmyAzAjPpTvA0yw6a9lJMC0MhCoP7pA5roNlFIsySSRs8MjHJ5wewqvpLLDfj5gCTgA1PcSRzarIyscbQNpGMEYrN85rfWpIc/NFOcEHp3FAznf2h5GsvE3hrXYWKja0LNnphwTWz4C1GSG3ns5pATFMHQA8gN1rI/aXhabwJZarbqWe11NQTnorA1R8J699nvYbzcVgvI1yx5ADDINAHrFrdLtDbs8dqm3szbtxAPSsjT73yVCqwOBjOcVeW8ZsMq8E9qBWuXC21S3mcYzVizmZowqtyOntWfJNIy7j06gZ6UsN00bAHABORzU6XsRsakkzbQy4HPPPFOWZpIgztjjp6VQa6bYMt345xxUkdwzKV3f0xSjzdQi3ezJLiZV+bcCeepxVa6mVoy3QgetVr24ZXPzZwetV2vkkUxyMRxxT1LUUiCa9ZWKliMdPauX1i+m8Mamup28LCB3AUL0KkfMtbl4zKSyt0J5FUbq3ttWt30+8UGOTuT909mHNUK7bsb2ntb3kEep2MwkhmXdHIpyCPSs3x3Yz3VnFfRygLGfLkQrktkkg5rgfDPjy9+HXieTw9rasLWSTEiseAT0YV6XqEdjrlhHItwWgmAeKRD0PNBqm0c/4Jae3vpoVb92yb2BGfm4AINeZftwfCLTPH+iaX42m06G4udLcpIJEBLKQSR6V7FoGjSWMLSSkGVshiBwB6Cm+KNJh13QrrQriFX8+MhFY4w3b3pNJolNp3PzX+KXw8sbeaKbTvD09ncRHElskO0SKSTuHFTeFPFGv3GkWuj295azXGjzrJYw6pB5uEUABMnmvqbXbOONJNJ13Tonkt5NjpNGMqwrh/FHw68H6wsl1Y6ZFZ36gFLuInnHGGrkxFCNSDT2O2jUe6PHvFXxM8d6xcQ6jY6jDYavFCYk1SwV4WjBJOFKturH1SXWPFF7DqPjDxRqus3FvGEifUtQkuFTnJ2iQmug+KXh3/hFtXihkmDrcW4mMgHBYsQcVyv2pY1LR8ehBr5avh40qjsrHt0qnPDU6LRZFVdq4AUYAHQV6j+zLA2s/H3wppyqCI9TWdyehWP8AeNXjGmao0KlnUnPGQcAV7J+xjdRyfGdNfnyq6dYsI3J6O+FzW2Et7RGWJu6dj1f/AIKk/HO18K+FY/hRoEqo+uxNLfKDkpHwAD3r450jS/s/h23h27ZHiBODz8zcV0/7eHjq98dftQ6xpMly0llpTwwRP1CARoWAxUnw68Pr4j8SaZplrtcG4V5kcfdRTk19DF3s0eUoRhqfQXhXQ4fDnh/S9IjVAbKyRCUHAbHJrpUkjazX5cNjnnrWNIzSTgqxKhwAR6DpWm11G0XzMASMg471sZya5hIY2muUhXoWzyeoHJrSmkEahV+tVNLjTzPOVQcdD6GtCZYvs7ySsQQODnGKAbSKMkzMxXfgeuaydUk3SDcwBwM81pblkyN2OOAeay9YhbzEX+8SAR26UHO3d3NHT2/0NSvBI4HoadtZm3N0pqSRxxrCuQAABxjin7lC7lY/XrQMRfl+ZWJ9MGmzXCrH8zYIHr0pkkjL91sHt61TvLgshUscAHkcUCuRyXTRzGSJiOevrUUl4zNuMh45zVSSaRZDtyRn16VDNdMreWrAHvWLeoy59oZn3Fs5P0NX9PCsu7cck9+orBa4LSD5gcEHArS0663YUNgg59xVDSUtdkaVwnmR7VYH2rl/EVusd/b3DKOgRjj0bPWuhmu+flbAx6ZrnfGl9Nb6Hd3FqxWSKMyAjnGAT3paPcjmvNHn3wquI7jxV4kv5JAgN4yK2c8bs11/h1ppLye8uFKtIxCgnJOTk81wnwcZT4Zur9+JLnUWLFjkkBV713OhLJcTFmbEaNhmIxn2FMuT5nodTbyrbxm4bAAUkknpSW8zXkjSKMAHA561nahqjXEht7VSsYxklsknuK09BjVYRJIpYAE7R3IoepKYWbeXePDkZjIDDOMV0WiyPcZjVSxUZyOcCuD0nUGuLtp9oUPISFzkgE5710uka3/Z+oxXHnEJ92UDkMp61hNXFKP3HSzRzrhY7diTzwuMGmRx3rLua1ZSD/EeorPm8bQyTCOOGRUAySUQ4/Wh/iXpVnCtvN524nDv5KEL+RrnaSZjL3S5cx3jMNsbj1YL0qxCzbBuULj1Fc9D48sL5nVZLh3yCrmBFGPwNW/+EhVo/Jj3jcANwQHH60rXZDaetjXkbcvynB7YBH40kML7QzZJPAwKxZtcaGMsqsxOSVMeMj0zuqGz8TK9uLq1tZDIASylODjpyDVKKQXT3Oqa1njURzRspIOAV6ivLP2nfDFr8SPgh4u8G3FrkXnh+5CZGSJEjLI1Vr74m+JvDuu2vh7T5E+zTMzLFJCS0gBJGSSDXZ2Kf2ppUEN5aqrXFmy3Khcbtw6YzShf2iuF+VH4xeHfhRqcdwlxNdWzotwhkjDtujVTz2xX6Ifsw/twfDjwH4RtPCfizSr2yaG1jhSeGRXG1RjJ5zXxd4u0m68EfEXxD4SmlYNp2sz2z7TgEI5UGiPXp1VStxgqAAQoyPzFe1HDQaPHq4iam0fqvof7cH7PF9ahv+FoW9uiKFT7RGysR9Sua7P4Y/tH/Brx/qDaV4P+Jum3l2wLJbi5HmNjkkKQDX4/ReILyZAsk4AByoEag49zjNa3h/xbrem+JdN13QtQawvLS6jKXFs2wqAwy1TLC66ISxdlY9UW4EfzbiD9alhkkaN5XkOApK896zVm+YKrE88kdq6P4ceF9R8e+N9K8E6TCJLjVL2K2jQgnBdwoNcc5cqPXjTR+j3/AAS2+Fkngr9n+58danZiO+8TagzROQQTbJgLweK+jZGWORZGbIB547VF4Z8P6d4Q8K6X4P0WAR2mlafHbwKDnhVC5zT7i3k2ltpII4OMZriUtdS2krn5zf8ABSrwXD4B+Oa6vZpsg1q0+1MFGAJC5V6+dl1mNW2tLwTyAcGvun/grH8OY9d+FWn/ABBs1YXGiXSxTkDgxSjk1+dttqjNGrSMCWAJwe9dtObsRTjrqb+raosluyxtliQAwOcVw/iIJJI0jdfcVtTaizRlWXBI4Oe9cz4guJFUuvIYkHB6VvzS5VY1UYp7HNasNsjGNQCTnI4zWay7WKsxJ/lV7UL5dxVs/Ws+a6jX5upPc1i3K5okm7CNIkf3mJ5zj0pGmYOGjJ/A5qrNdMW2KoxntToWLNubIGc8cVvBNu5lU00RraZcKzDc33jyD1Brq9F+ZQzc881yuiwiSQFVPXPNdfo9oyqrbep5rc5m3c+iv+CcnxGi+HP7TumRXUwW31yylsJctjcz7SlfqZrBht2EccZVurEtnJr8nP2G/Al545/ak8IWNqv7uy1OO8u3IOFiiO9unNfrLrUUeoXEkkMikBsqynOBiocb7blRTaMO+uPL64OMdBzWP4ihfVNMkt1YgKN5AOAdoJwa09ShlhVlkUnA4I5BrNt5mbfHNkBgVJAzgHIpqNkawsmrnNW8C6lZFbdlby2JQdcsBkVX02/FndJO3AIKsGHODVXRbibR/El94bmmO6IEpkffxg5qHXLqSHUZG2fJIA4I45JOao3ir7m2dasJtVis4Zh58q5AJxuwM1BcMq6rLNGwLNISxHc8VyupahG11aXUakSW0wcEdW5BwO9dPdKbeY/LgBsD2oE9GU/ipatrfwr1SzVgZI41mUAdNjbq8+8JX32rw/ZxNw6QBDz0x0r06GGHWdMu9MmyEubd4gQO5FeSeCI2s4J9PuF2zQXRR+OmABQOKbPW9E1ZZ40VpdwCABgODxW7DdNHEMtkHpk5xXD+H7po0Vd2Mcc8V1VjfeZbqu7Jxjk0Ab1rMs0IZiM45NVL66+zSKu7kngZxRptxuUx4wQeme1VNcZpLqJY2zsHzDHQkiobdtDJ7s0luFaNW6dxkcGpFuNv3ZM5OKpQyYhCq3I9qFmZWO1jkH0wTzWUXaSY1dMdfTNtLMxrPa4ZWPzHOfXtU9xMzEqzEd8Edayrq4ZZvL3HGc+ma3umrjbTZbaRpFOGJGOnSsy6ma3m/IHNWvMZY/lbPHrWZqEytOVdsHAxg0ytncpeNvCtp430gWpkWO8gXdbTEcEd1Nc38KvihdeHLhvCHiZWRBIEhaViDG3oc11Udx5MnLHrkEHmuP8Ai34QbUrI+KNCj/0i3TN1DGuC6jJDDHNBSdz2OxulZNyuCrAFXXoQelVtSuNkw2sQAc5BwQa8r+D3xpi1C2i0LX7ry5oV2R725cc9K9F1K4kWMu3OOhHcUBZ3POfjz4d+3BddtYSjzQ4nkDYDMD8teQaE1xJpxjkjfk8Pnk5A4r3rxlp8PiXRLnS5pghkgZYnK7tpx1xXhuh2N9pt5JoGoRlZYnJYMcAnjoal26miSkzy39omONdKtbqGZZHt7lUldWB2g5OCa8wt7xmXa3UdxX0F8S/hazeGdYk07zJFubKSWGEJkh1XcBXzVZXTxrtkUhl+V8jkEV87mNPVSR7WCqacrN2C8jVtrMevrmvV/wBk66VfijPM0jJFb6PNPJtPBwyKM14zb3G6QMrcZzjOMivTfgZdSaVpvizxHDIUkt9CMEUh42llZq5cGv3l0bYj4Tz3xpdSeJfiDrPitoSp1DVJLlFYZI3OWAr2f9m6xkuI73xHJHyIhDE4HTJycV5JNZ+XbrM2cqmSSO/Wve/gdpq6Z8NLFVUhrlmlc4wepAr6Gk7o8uo7SsdssxjVWZhkHgkdKk+2SM33s4P0qjIW3BVbr0qe2jZmAUck/lWpkdHo7/6OqqucnOfSp9SuFjtRGrHJPJPUCqmns0UIVuw7HFRaleNJII+AFHBx1oM5v3S3ZW/nQGTbzk4BHSs7UIla8CspJQ5HYetdRo+lr/wj0VxIu2SQFsHqRniud1KLbdttUElueOlBhezGRyMzbWXp7U+5Zlj27s/oaSKD+Js8ngjtUN0zK23kgc9TQWRSSSM27ccDuKq3U0hQr2HOR1qSS4wpT2qtcTKqk9SfTmlcCurSDLbhgc5PXFVmkViW3d6l81eV7deuKiZozltuT1rJ25gi7SVyFrhlk29+B1q9ptw7Md7HJ6duaoTKvmbmXA9enFT2ciqp2nocDtiqNt0X5roKx+bJ5xz0NYviGT7ZZzWigZmgZOfUjFW5ppFyzN9Oay9Qmk3BmX+IEc0m0jJwUXc4j4YSQ2umTaFtIezvCJSDgENgV31vNFDGtvaoEToFU8CvMtIvrvRfitq+jLNuSffMsRXOTwQQa73S7ySTa0jEv9MYoTuKKuzbt7dppFVeCTnJGRWh4gvP7K0F1t1JlmHlRspwFyOTUGj27Mv2iRuMAAk9ai1pRfTLDuYIg6g5Jpl8q2Rm6TFJDGrMpAAAGT0FaUMkizA7jgngVBdtH5irCoXjOAMCn2Mkcl8bdm+eMZZc8jNZSSbFNeZ2PhHT7K/ulja1QzY3hnQHheSOa6y48H6FqcMTTaRAWjJIKRhc5x7ZrhtJ1KTTbiK8tZCskLAgA4yO4r1bSbq21Owg1G0UiO4jDqDjKnuOKxcbaHJJO2hzq/D7w8JA39hQEgcbk706TwjpiMGXSrdcHHywgDFdO0O5iu0gDj0pklqirtbGeowOam5im7HOx+G9PVg39nW2exMC5zTl0O3tY2jtbGBA2CQsCgH9K2JLduPlPHQjtTZIWWP5vQDr1NFtbiT1PEfjx4ak0/xPofiqBUCLJ9nkQDG3JzkV0un7vLhY5UAggBugzV34y6S2qeGFuFjJawvEkJA5KnKmsfSZ2uLNJJF2MyBiAc8kZqY3U0Xurn5vft2eF5PB37W/iKOG3aKDUSl9CCDhzIi7mFeam42qGHscjtX0r/wVh8LnT/iP4V8fQkAajpT2koC8ho3BHNfMFrI02CzAD3OM19JhZRlSR8/jrwrGratvjDevPXFaNjIytk4PcfWsqA7VXcTgD061oW8zKu5WKjORitpw0uckasVo9T1+WZV+ZW744OK+jP8AgmX4Ut9a+Mtx8RdTgdrfw5aGSFlIwJ3YqnWvmC6ulW3Zo5CDghcHvjiv0D/Yo8Dn4c/APT1vIQt7rMjXs7bgcIxGwV8vWkuh9jGLsfTLfFvUYVmjs7y7QSkEMYo+MHjAJqC6+MOssp3SSyK/3leCMfh1rgWv5m+6w4qKbUJFUKrEZ644rlc+XcHEP2kdcHxQ+CniHwdqEbNJLZM8IKKuGRd69DX5ZSLJb3EsbsQUlwR6dK/SL4o+NdO8FeANT8Q3rFgkJjjRW5ZiQBX53+Lre1XV7q8tlCpLcOwAGCRu4rajUfNudNOikuYzftEnG7GMdaytclbaVbkEHpxV4SKw+VgMcYNVNUVZIx1IGTn0NejD3tTOo1DSxyt9GvmHoCDkY9ayrxZEk2tnGcj6Vs6tBtmZo24znntWZdb5FKs2cZOBxihp3JhLRlBWbzCq8DP0q1axtIwVVyMjp0JqFY2abaF6nqOtbWh2KyONykjoOeprendIwcnfc0tFsVj2NtwO3ua6zSYdyrHH0GPaqGl6OrRqzMRjAwO9blnZrb2zNGvKpgH1rRKxk99T7R/4JEfDeT+1fFXxdvoWBtrVNPsmI+Vmdg74719qQ3VwqtJAykgcDtXkH/BP3wOvgn9k3R1mtQlzrNxLfyk9SHbCmvV4fMhYsvrjFMa5rpmfqnja3sboQ6yohYuAWfEeB9DUkc1nf24vdNu4riJud8LbgPrVfxxFpmr2EVhqMKtKG3RsoAZQPQ4ritQ03W/Dl22o+HtRcRMwBAcllz/eX7tBsmnqV/itHNo/jK18R2v3ZIUBIbowJ3VL4it4bq1M0MnzRsGUgZ3KaseJrpvF+gPbzzBZgVeNAAAHXJIrIsbyRdKis7hQHjjCZxjIHSg0V20ch4kvbywl/tGGQkxMrRjHTBzivSIdSh1nw7Z63DGF+2W+8BTnBPBrzzxNB51vcWrxsGCEptPIIBxXRfCLVGvvASabcLh7C5eEH1Q/OM0FPY3NLuGgbazA4cEAjPNecX9ncaH8Q7yzZcCeV5VYc7lYFga71ZVjmO7gE8A9q4/4kq0PinTdXicZa2MTccEhsUAupraPfNGxXf2BGDiui0nUnZflbkHB5rj7eZVwy5ABwM9cVr6PfbZPLZuCARn1oCx2+j3W6Q+/qe1WdQj3MJuc46+tYmj3u24VtxxnJwa3pmWSDcvPAPSpdlqZzVmVrWRmbaWwB09uakZVaQvuyc5GKqrJ5c23jr07irCkswb3zWIhl4rLDuZue2R1rB1CZo7jczEHjGO1bd3cMreXtOMYyDisDXYZJLhZouMqQRnFXB6WBXjIni1DdGN2SfasbXLqRrrzFYgEYx0wauW+5VKycd8461R1qNWjEitk78ex4NamnQYt00keN2TwMg5qS3uGhb5lDBlIKt0IPY1UhkURrtwe30qSWZY1HTP060CV9jz/AMf+AG0fWTq2iWxe1uS0pRAT5LLy1dR4H+JceswjTdWYpdSqTvI+ViOlaF9cQzwNDOoZJFKup7givPfEehrpNyG0yGRIFXcrCQsUOTxzzQXvoei6hdSR7o24DZAOcYrktQ0W3utTe+ZV3tgbwvIAGKu+H/Ey+J9At7u8kzcwgxTHuxHfirG2ORwu0A/pipkrjg1zHL6tM1jG9synMmY9o7E9K+N/iZE2k+O9X02ZT5i6hI5yeTubPNfcGqaPHJcNMsIILbgDzg5zXzl+2J8KIVvoPiroFrgMFg1SKPA+bor4rzcZTVWDO3DVVGpoeKQ3TRqNzAc5616r8NldfgLq2otHiTUdVESvnlkUqO1eJalfeQ25ZMgLkY717po9jdaF8DPCmiTSEtfIb5mXuGJcZrz8JBczsd9aTcdWYslislq8aqCWG1Qe+eK998K6S2ieGNP0uTAe3s0EgAwAxGTXlnw78Pzaz4qslW2EkNvMs85k+6AORnmvZbqTcz3DKQCST7V69NWicFSUXIbDIGlC7eg656VpWMK+YshUZHvyKy9HjkuGMzLwTgE9xW7bwtGobtweO1amVyy2I487ug6DtVLc1xcFlxyeCB0pLy8MeY1YgZxgelSaQrzXaKqgHIJzzigyctbHb2dutvokMcbMwSEKNwwc5NcjfLI14xZduT068V2UlxHHpQt1hIYIAg3YxXHXkkkt20sigc4AXoBQYu61HRx7AflOf1qjdM3mFV61oJG7x53YHXj1qnJA3mFtvPv1oKXNuUZI1VTuYZPI5xVO4XC+vU59q0biNmYtyMH0qjcMwY9evGB0qJPoNO5Qmj2sPL9M59KaVZVDdc+lPuNy/NjvnpTFZvL3be/fvSKjC5BdbOHUkEnnPap7fasYb8z3qvIzNJ8y8A5471ajVdoZlO3qB1qXJWNIe7JpkV1I3KpzjvWVqjFV3DuM5rZuI1aPcqkADNYmrTKy+X1I6Z6io3d2PW1meXePdUXw58VtK11rcuJrQRyANtLFm25zivSNDjaa6KxqTlvlHqO1eZftB2scemaZrrfK1vdrGCOCMsTXqHgqb7RpltqTMCZ4w2AMY9KqMmlcIx5UdS95HY6f5kigCNAAAcZPYVn2skl5MZOxOcD1qrrWpNcXCWQclFIKqB1bpWppMaw2wZ15IyfUVVyZNLUbdR29qjXUzBFjUkkjkgVl+FbiSb7ReXUieY8oAA4IzkmrmvRvMoWTIB5Az0NZmhQ/6VKsmQFUcjuc1EtGZPmerOq0+ZpMMrEgEgc4rv8A4VeIGhnfw1dNhJyZbVic7WAGVrznTZCG+XnHGa2LK8mhljuoZCksTh4mB6EHNJxTRnKOh7LLG0bFWzxwR6GopArfw9+Cf51Do+u2+u6Zb6rb7ALiIM6qfuN/EKnZlZRtUHHQAVhNanPKO3YY8as/Xr1wcVBNtVSu7Ppg81M0itlmXBwe/WopI2dg23AyOh60k1cj3b3Oe8ZWKahpVxZq20yW74JGRnGRXnWhXC+XGsjY3IAMHNetaoqLCrNCGC5ByM8Ec15MLWTTb+W1aML5U7KAD2DcYpNroXGS5dD5+/4Kn+E11f4A6V4jit1abSvEKAS9SiOj7hmvhKxkWSFZo8lWwQcc1+m37ZXhZvGf7MXirSImCy29g17GWHBMOJMV+YujsrWkSq2AEAxn0617uXtezseNmNK7UuprQybl+7+QqxDOyudvIPUd6pw/Ljcox0FWY/L27txBBxxXoO1tTymm9bn/2Q==" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 4px solid #DBEAFE; margin-bottom: 1.25rem;">'
        else:
            bavan_avatar_html = '<div style="width: 100px; height: 100px; border-radius: 50%; background-color: #EFF6FF; color: #2563EB; font-weight: bold; font-size: 2rem; display: flex; align-items: center; justify-content: center; border: 4px solid #DBEAFE; margin: 0 auto 1.25rem auto;">BS</div>'
            
        st.markdown(f"""
        <div class="saas-card" style="text-align: center; padding: 3rem 2rem;">
            <div style="display: flex; justify-content: center;">
                {bavan_avatar_html}
            </div>
            <h3 style="color: #1F2937; font-weight: 800; font-size: 1.4rem; margin: 0 0 0.25rem 0;">Bavan shree N</h3>
            <p style="color: #2563EB; font-weight: 700; font-size: 0.95rem; margin: 0 0 0.5rem 0;">Machine Learning Specialist & Pipeline Engineer</p>
            <span style="display: inline-block; background-color: rgba(37, 99, 235, 0.1); color: #2563EB; font-size: 0.8rem; font-weight: 700; padding: 0.3rem 1rem; border-radius: 30px; margin-bottom: 1.5rem;">Student Developer</span>
            <p style="color: #4B5563; font-size: 0.92rem; line-height: 1.6; max-width: 480px; margin: 0 auto 2rem auto; text-align: center;">
                Expert in ML workflow engineering and data preprocessing pipelines. Focuses on feature extraction, threshold tuning for high-accuracy facial recognition, and backend state management.
            </p>
            <div style="display: flex; justify-content: center; gap: 1rem;">
                <a href="https://linkedin.com" target="_blank" style="text-decoration: none; color: #64748B; font-weight: 600; font-size: 0.85rem; border: 1px solid #E5E7EB; padding: 0.5rem 1.2rem; border-radius: 30px; transition: all 0.2s ease;">LinkedIn</a>
                <a href="https://github.com" target="_blank" style="text-decoration: none; color: #64748B; font-weight: 600; font-size: 0.85rem; border: 1px solid #E5E7EB; padding: 0.5rem 1.2rem; border-radius: 30px; transition: all 0.2s ease;">GitHub</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_login_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🔑</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0 0 0.25rem 0;'>Sign In to Dashboard</h2>
        <p style='color: #64748B; font-size: 0.95rem; margin: 0;'>Welcome back! Please enter your details.</p>
    </div>
    """, unsafe_allow_html=True)
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
                        st.query_params.clear()
                        st.rerun()
                    except Exception as e:
                        import requests
                        if isinstance(e, requests.exceptions.ConnectionError) or "Failed to establish a new connection" in str(e) or "Max retries exceeded" in str(e):
                            st.error("❌ Connection to the backend server failed. Please make sure the FastAPI backend server is running (port 8000).")
                        else:
                            st.error(f"Authentication failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.85rem; color: #64748B; margin-top: 1rem;'>Don't have an account? <a href='?nav=Register' style='color: #2563EB; text-decoration: none; font-weight: 600;'>Create one</a></p>", unsafe_allow_html=True)

def render_register_section():
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">📝</div>
        <h2 style='color: #1F2937; font-family: "Inter", sans-serif; font-weight: 800; font-size: 1.8rem; margin: 0 0 0.25rem 0;'>Create New Account</h2>
        <p style='color: #64748B; font-size: 0.95rem; margin: 0;'>Fill in the details to create your account.</p>
    </div>
    """, unsafe_allow_html=True)
    
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
                    elif not re.search(r"\d", password):
                        st.error("Password must contain at least one number.")
                    elif not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
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
                            st.error(f"Failed to set password: {e}")


inject_css()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "approval_status" not in st.session_state:
    st.session_state.approval_status = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home / Scanner"
if "registration_step" not in st.session_state:
    st.session_state.registration_step = "form"  # "form", "enroll", "password"
if "captcha_data" not in st.session_state:
    st.session_state.captcha_data = None
if "reg_user_id" not in st.session_state:
    st.session_state.reg_user_id = None
if "scanning" not in st.session_state:
    st.session_state.scanning = False
if "show_register_prompt" not in st.session_state:
    st.session_state.show_register_prompt = False
if "checkout_prompt" not in st.session_state:
    st.session_state.checkout_prompt = False
if "checkout_queue" not in st.session_state:
    st.session_state.checkout_queue = []
if "checkout_user_id" not in st.session_state:
    st.session_state.checkout_user_id = None
if "checkout_name" not in st.session_state:
    st.session_state.checkout_name = ""
if "scan_feedback" not in st.session_state:
    st.session_state.scan_feedback = ""


# Sidebar Navigation
st.sidebar.markdown(f"<h2 style='text-align: center; color: #1F2937;'>📷 Face Attendance</h2>", unsafe_allow_html=True)

# Connection Status Indicator
is_connected = api.check_health()
if is_connected:
    st.sidebar.markdown(
        "<div style='text-align: center;'><span class='status-badge status-approved' style='background-color: #28a745 !important; color: #FFFFFF !important; border-color: #28a745 !important;'>● Online</span></div>", 
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        "<div style='text-align: center;'><span class='status-badge status-rejected'>● Offline (Check Backend Server)</span></div>", 
        unsafe_allow_html=True
    )

st.sidebar.write("---")

# Navigation buttons
if not st.session_state.authenticated:
    page_options = ["Home / Scanner", "Login", "Register"]
else:
    if st.session_state.user_role == "Admin":
        page_options = ["Admin Dashboard", "Home / Scanner", "Profile", "Report"]
    elif st.session_state.user_role == "User":
        page_options = ["User Dashboard", "Home / Scanner", "Profile"]
    else:  # Registered / Pending Approval
        page_options = ["Pending Dashboard", "Home / Scanner", "Profile"]

for p in page_options:
    if st.sidebar.button(p, key=f"nav_{p}"):
        st.session_state.last_page_tracker = st.session_state.current_page
        st.session_state.current_page = p
        st.rerun()

if st.session_state.authenticated:
    st.sidebar.write("---")
    st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_role})")
    if st.sidebar.button("Logout", key="btn_logout"):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.session_state.user_id = None
        st.session_state.approval_status = None
        st.session_state.current_page = "Home / Scanner"
        api.clear_token()
        st.rerun()

render_navbar()

# --- PAGES ---

# A. FEATURE PAGE
if st.session_state.current_page == "Feature":
    render_features_section()
elif st.session_state.current_page == "Techstack":
    render_techstack_section()
elif st.session_state.current_page == "Comment":
    render_comments_section()
elif st.session_state.current_page == "Team":
    render_team_section()
elif st.session_state.current_page == "Home / Scanner":
    render_hero()
    render_scanner_section()
    render_stats_section()
elif st.session_state.current_page in ["Login", "Register"]:
    col_login, col_register = st.columns([1, 1.2])
    with col_login:
        render_login_section()
    with col_register:
        render_register_section()
elif st.session_state.current_page == "User Dashboard":
    st.subheader("👤 User Attendance Dashboard")
    
    # Shift Reference Banner
    st.info("🕒 **Active Shift:** 09:00 AM - 04:00 PM | **Grace Period:** 30 Mins (Late check-in triggers after 09:30 AM)")
    
    try:
        stats = api.get_user_dashboard_stats(st.session_state.user_id)
        
        # Top Stats Greetings
        st.markdown(f"### Welcome back, **{stats.get('name')}**")
        
        # Check if face profile expired
        if stats.get("needs_face_update"):
            st.warning("⚠️ Your face profile was last updated more than 90 days ago. To maintain high recognition accuracy, please update your face profile now.")
            if st.button("Update Face Profile Now", type="primary", key="btn_trigger_face_update"):
                st.session_state.update_face_pose_idx = 0
                st.session_state.update_face_captures = {}
                st.session_state.current_page = "Update Face Profile"
                st.rerun()
                
        # History table records first (to calculate hours)
        history = api.get_user_attendance_history(st.session_state.user_id)
        
        # Calculate Total & Avg Work Hours & Late Days
        total_hours = 0.0
        avg_hours = 0.0
        late_days_count = 0
        if history:
            valid_days_count = 0
            for row in history:
                ch_in = row.get("check_in", "-")
                ch_out = row.get("check_out", "-")
                if ch_in != "-" and ch_out != "-":
                    try:
                        fmt = "%I:%M %p"
                        t1 = datetime.strptime(ch_in, fmt)
                        t2 = datetime.strptime(ch_out, fmt)
                        dur = (t2 - t1).total_seconds() / 3600.0
                        if dur > 0:
                            total_hours += dur
                            valid_days_count += 1
                    except Exception:
                        pass
                
                # Late check-in tracking (cutoff at 09:30 AM)
                if ch_in != "-":
                    try:
                        fmt = "%I:%M %p"
                        chk_time = datetime.strptime(ch_in, fmt).time()
                        late_cutoff = datetime.strptime("09:30 AM", fmt).time()
                        if chk_time > late_cutoff:
                            late_days_count += 1
                    except Exception:
                        pass
            if valid_days_count > 0:
                avg_hours = total_hours / valid_days_count
        
        # 7 Metric Cards Grid
        col1, col2, col3, col_late, col4, col5, col6 = st.columns(7)
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Verification Status</p>
                <span class='status-badge status-approved'>{stats.get('approval_status')}</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Present Days</p>
                <p class='stat-number'>{stats.get('present_days')}</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Absent Days</p>
                <p class='stat-number'>{stats.get('absent_days')}</p>
            </div>
            """, unsafe_allow_html=True)
        with col_late:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Late Days</p>
                <p class='stat-number' style='color: #e65100;'>{late_days_count}</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Attendance Rate</p>
                <p class='stat-number'>{stats.get('percentage')}%</p>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Total Hours (Month)</p>
                <p class='stat-number'>{total_hours:.1f}h</p>
            </div>
            """, unsafe_allow_html=True)
        with col6:
            st.markdown(f"""
            <div class='metric-card'>
                <p class='stat-label'>Avg Daily Hours</p>
                <p class='stat-number'>{avg_hours:.1f}h</p>
            </div>
            """, unsafe_allow_html=True)
            
        # Attendance Status Today
        st.markdown("### 📅 Today's Timestamps")
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            st.markdown(f"<div class='metric-card'><p class='stat-label'>Status</p><h4>{stats.get('today_status')}</h4></div>", unsafe_allow_html=True)
        with t_col2:
            st.markdown(f"<div class='metric-card'><p class='stat-label'>Entry Time</p><h4>{stats.get('entry_time') or '-'}</h4></div>", unsafe_allow_html=True)
        with t_col3:
            st.markdown(f"<div class='metric-card'><p class='stat-label'>Leaving Time</p><h4>{stats.get('leaving_time') or '-'}</h4></div>", unsafe_allow_html=True)
            
        # Live Session Progress Tracker
        if stats.get("today_status") == "Checked In" and stats.get("entry_time"):
            try:
                entry_str = stats.get("entry_time")
                now_dt = datetime.now()
                entry_time_parsed = datetime.strptime(entry_str, "%I:%M %p").replace(year=now_dt.year, month=now_dt.month, day=now_dt.day)
                elapsed = now_dt - entry_time_parsed
                seconds = elapsed.total_seconds()
                if seconds > 0:
                    h, m = divmod(int(seconds) // 60, 60)
                    st.info(f"⏱️ **Live Session Tracker:** You checked in at **{entry_str}** and have been active for **{h}h {m}m** today.")
            except Exception as e:
                logger.error(f"Error calculating elapsed workday time: {e}")
            
        # Monthly Percentage Progress Bar
        st.write("---")
        st.markdown("### 📊 Month Attendance Rate")
        st.progress(stats.get('percentage') / 100.0)
        
        # Monthly Attendance Rate Plotly Chart
        if history:
            import plotly.express as px
            chart_df = pd.DataFrame(history)
            if not chart_df.empty and 'date' in chart_df.columns and 'status' in chart_df.columns:
                chart_df = chart_df.sort_values(by="date")
                chart_df['Attendance Value (%)'] = chart_df['status'].apply(lambda x: 100 if x in ['Present', 'Late'] else 0)
                
                fig = px.bar(
                    chart_df,
                    x="date",
                    y="Attendance Value (%)",
                    color="status",
                    color_discrete_map={"Present": "#10b981", "Late": "#f59e0b", "Absent": "#ef4444"},
                    labels={"date": "Date", "Attendance Value (%)": "Status Rate (%)", "status": "Status"},
                    title="Daily Attendance Status (Current Month)"
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=40, b=10),
                    height=280,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, range=[0, 110])
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # History table
        st.markdown("### 📜 Recent Logs")
        if not history:
            st.info("No attendance records found.")
        else:
            import pandas as pd
            df = pd.DataFrame(history)
            
            def color_status(val):
                if val == 'Present':
                    return 'background-color: #E8F5E9; color: #2E7D32; font-weight: bold;'
                elif val == 'Late':
                    return 'background-color: #FFF3E0; color: #E65100; font-weight: bold;'
                elif val == 'Absent':
                    return 'background-color: #FFEBEE; color: #C62828; font-weight: bold;'
                return ''
                
            if hasattr(df.style, 'map'):
                styled_df = df.style.map(color_status, subset=['status'])
            else:
                styled_df = df.style.applymap(color_status, subset=['status'])
                
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Export CSV Download Button
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Logs to CSV",
                data=csv_data,
                file_name=f"attendance_history_{st.session_state.user_id}.csv",
                mime="text/csv",
                key="btn_download_user_logs"
            )
            
        # Self-Service Dispute expander
        st.write("---")
        with st.expander("📝 Request Attendance Correction"):
            st.write("If you missed a clock-in/out or need a record override, please submit a correction request to the administrator:")
            with st.form("dispute_correction_form"):
                dispute_date = st.date_input("Date of Attendance", key="disp_date")
                dispute_type = st.selectbox("Correction Type", ["Forgot to scan in", "Forgot to scan out", "Misread by AI sensor"], key="disp_type")
                disp_in_time = st.text_input("Correct Check-In Time (HH:MM AM/PM)", value="09:00 AM", key="disp_in")
                disp_out_time = st.text_input("Correct Check-Out Time (HH:MM AM/PM)", value="05:00 PM", key="disp_out")
                dispute_reason = st.text_area("Reason/Justification for Correction", key="disp_reason")
                
                submit_dispute = st.form_submit_button("Submit Request")
                if submit_dispute:
                    if not dispute_reason.strip():
                        st.error("Please provide a reason for the request.")
                    else:
                        import os
                        import csv
                        csv_path = r"D:\New folder\pending_corrections.csv"
                        headers = ["user_id", "user_name", "date", "correction_type", "requested_check_in", "requested_check_out", "reason", "status", "created_at"]
                        file_exists = os.path.exists(csv_path)
                        
                        try:
                            # Save to CSV
                            with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
                                writer = csv.DictWriter(f, fieldnames=headers)
                                if not file_exists:
                                    writer.writeheader()
                                writer.writerow({
                                    "user_id": st.session_state.user_id,
                                    "user_name": stats.get("name"),
                                    "date": str(dispute_date),
                                    "correction_type": dispute_type,
                                    "requested_check_in": disp_in_time,
                                    "requested_check_out": disp_out_time,
                                    "reason": dispute_reason.strip(),
                                    "status": "Pending",
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                            
                            # Also keep in session state
                            if "correction_requests" not in st.session_state:
                                st.session_state.correction_requests = []
                            st.session_state.correction_requests.append({
                                "user_id": st.session_state.user_id,
                                "user_name": stats.get("name"),
                                "date": str(dispute_date),
                                "type": dispute_type,
                                "requested_check_in": disp_in_time,
                                "requested_check_out": disp_out_time,
                                "reason": dispute_reason.strip(),
                                "status": "Pending"
                            })
                            st.success("✅ Correction request submitted to the Administrator successfully!")
                        except Exception as csv_err:
                            st.error(f"Failed to submit correction request: {csv_err}")
                        
    except Exception as e:
        st.error(f"Could not load dashboard stats: {e}")

# 5. PENDING USER DASHBOARD
elif st.session_state.current_page == "Pending Dashboard":
    col_left, col_mid, col_right = st.columns([1, 1.8, 1])
    with col_mid:
        st.markdown("<h2 style='text-align: center; color: #1F2937; font-family: \"Outfit\", sans-serif; font-weight: 800; margin-top: 1.5rem; margin-bottom: 1.5rem;'>⏳ Account Status</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #1F2937;'>⏳ Waiting for Admin Approval</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #1F2937;'>Your face profiles and registration details have been submitted.</p>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #1F2937;'>An administrator needs to verify and approve your account before you can mark attendance.</p>", unsafe_allow_html=True)
            
            # Center the button using a columns trick
            _, btn_col, _ = st.columns([1, 2, 1])
            with btn_col:
                if st.button("Refresh Approval Status", use_container_width=True):
                    # Relogin mock to pull latest role status
                    st.info("Re-checking status...")
                    try:
                        # Check profile status directly from JWT token decode or call API
                        stats = api.get_user_dashboard_stats(st.session_state.user_id)
                        if stats.get("approval_status") == "Approved":
                            st.session_state.approval_status = "Approved"
                            st.session_state.user_role = "User"
                            st.session_state.current_page = "User Dashboard"
                            st.success("Congratulations! Your account has been approved.")
                            time.sleep(2.0)
                            st.rerun()
                        else:
                            st.warning("Your account is still in Pending status.")
                    except Exception as e:
                        st.error(f"Check failed: {e}")

# 6. ADMIN DASHBOARD
elif st.session_state.current_page == "Admin Dashboard":
    # Header and Settings Button side-by-side
    col_title, col_settings_btn = st.columns([5, 1])
    with col_title:
        st.subheader(" Administrative Console")
    with col_settings_btn:
        with st.popover("⚙️ Settings", use_container_width=True):
            st.write("Configure office timings:")
            try:
                current_settings = api.get_attendance_settings()
                start_time = current_settings.get("start_time", "09:00")
                end_time = current_settings.get("end_time", "18:00")
                grace_period = current_settings.get("grace_period_minutes", 30)
                
                # Parse 24h start_time and end_time to parts
                def parse_24h_to_parts(t_str: str):
                    try:
                        dt = datetime.strptime(t_str, "%H:%M")
                        return dt.strftime("%I"), dt.strftime("%M"), dt.strftime("%p")
                    except Exception:
                        return "09", "00", "AM"
                
                start_h, start_m, start_p = parse_24h_to_parts(start_time)
                end_h, end_m, end_p = parse_24h_to_parts(end_time)
                
                st.markdown("**Office Start Time**")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    new_start_h = st.selectbox("Hour", [f"{i:02d}" for i in range(1, 13)], index=int(start_h)-1, key="start_hour")
                with sc2:
                    new_start_m = st.selectbox("Minute", [f"{i:02d}" for i in range(60)], index=int(start_m), key="start_minute")
                with sc3:
                    new_start_p = st.selectbox("Period", ["AM", "PM"], index=0 if start_p == "AM" else 1, key="start_period")
                    
                st.markdown("**Office End Time**")
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    new_end_h = st.selectbox("Hour", [f"{i:02d}" for i in range(1, 13)], index=int(end_h)-1, key="end_hour")
                with ec2:
                    new_end_m = st.selectbox("Minute", [f"{i:02d}" for i in range(60)], index=int(end_m), key="end_minute")
                with ec3:
                    new_end_p = st.selectbox("Period", ["AM", "PM"], index=0 if end_p == "AM" else 1, key="end_period")
                
                new_grace = st.number_input("Grace Period (Minutes)", min_value=0, max_value=480, value=grace_period, step=5, key="grace_period_input")
                
                if st.button("💾 Save Settings", type="primary", use_container_width=True, key="btn_save_time_settings"):
                    try:
                        # Combine to 24h format for database save
                        dt_start = datetime.strptime(f"{new_start_h}:{new_start_m} {new_start_p}", "%I:%M %p")
                        dt_end = datetime.strptime(f"{new_end_h}:{new_end_m} {new_end_p}", "%I:%M %p")
                        new_start_str = dt_start.strftime("%H:%M")
                        new_end_str = dt_end.strftime("%H:%M")
                        api.save_attendance_settings(new_start_str, new_end_str, int(new_grace))
                        st.success("✅ Time settings updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save settings: {e}")
                
                st.markdown("---")
                st.markdown("#### Current Settings")
                def to_12h_format(t_str: str) -> str:
                    try:
                        return datetime.strptime(t_str, "%H:%M").strftime("%I:%M %p")
                    except Exception:
                        return t_str
                st.markdown(f"**Start:** {to_12h_format(start_time)}  \n**End:** {to_12h_format(end_time)}  \n**Grace:** {grace_period} min")
                st.markdown("*Late check-in:* After start time + grace period")
                st.markdown("*Half-day:* Check-in after dynamic midpoint")
                
                st.markdown("---")
                st.markdown("#### 🔄 Model Utilities")
                if st.button("🔄 Rebuild Face Embeddings Cache", use_container_width=True, key="btn_rebuild_face_cache"):
                    try:
                        with st.spinner("Rebuilding known faces embeddings cache..."):
                            api.rebuild_face_cache()
                        st.toast("✅ Face embeddings cache rebuilt successfully!")
                        st.success("Face cache updated!")
                    except Exception as e:
                        st.error(f"Failed to rebuild cache: {e}")
                
            except Exception as e:
                st.error(f"Failed to load settings: {e}")
    # Check if admin user needs face update
    try:
        admin_user_stats = api.get_user_dashboard_stats(st.session_state.user_id)
        if admin_user_stats.get("needs_face_update"):
            st.warning("⚠️ Your face profile was last updated more than 90 days ago. To maintain high recognition accuracy, please update your face profile now.")
            if st.button("Update Face Profile Now", type="primary", key="btn_admin_face_update"):
                st.session_state.update_face_pose_idx = 0
                st.session_state.update_face_captures = {}
                st.session_state.current_page = "Update Face Profile"
                st.rerun()
    except Exception as e:
        logger.error(f"Error checking face update status for admin: {e}")
        
    # Load statistics
    try:
        stats = api.get_admin_stats()
        
        # Admin panels tabs
        tab_part, tab_admin_att, tab_overview, tab_audit = st.tabs([
            "👥 Participation", 
            "🛡️ Admin Attendance", 
            "📈 Attendance Overview", 
            "📜 System Audit Logs"
        ])
        
        with tab_part:
            st.markdown("<div id='participation-tab-marker'></div>", unsafe_allow_html=True)
            # Initialize active view in state if not present (defaults to None, so no list displays until clicked)
            if "active_part_view" not in st.session_state:
                st.session_state.active_part_view = None
                
            # Clickable metric buttons
            part_col1, part_col2, part_col3, part_col4 = st.columns(4)
            with part_col1:
                type_users = "primary" if st.session_state.active_part_view == "Total Users" else "secondary"
                total_all_users = stats.get("total_users", 0)
                if st.button(f"👥 Total Users ({total_all_users})", key="btn_part_total_users", type=type_users):
                    st.session_state.active_part_view = "Total Users"
                    st.rerun()
            with part_col2:
                type_admins = "primary" if st.session_state.active_part_view == "Total Admins" else "secondary"
                if st.button(f"🛡️ Total Admins ({stats.get('total_admins', 0)})", key="btn_part_total_admins", type=type_admins):
                    st.session_state.active_part_view = "Total Admins"
                    st.rerun()
            with part_col3:
                type_pending = "primary" if st.session_state.active_part_view == "Pending Approval" else "secondary"
                if st.button(f"⏳ Pending Approval ({stats.get('pending_users', 0)})", key="btn_part_pending", type=type_pending):
                    st.session_state.active_part_view = "Pending Approval"
                    st.rerun()
            with part_col4:
                type_approved = "primary" if st.session_state.active_part_view == "Approved Account" else "secondary"
                if st.button(f"✅ Approved Account ({stats.get('approved_users', 0)})", key="btn_part_approved", type=type_approved):
                    st.session_state.active_part_view = "Approved Account"
                    st.rerun()
                    
            if st.session_state.active_part_view:
                col_title, col_close = st.columns([5, 1])
                with col_title:
                    st.markdown(f"### 📍 {st.session_state.active_part_view} database")
                with col_close:
                    if st.button("❌ Close List", key="btn_close_part_view"):
                        st.session_state.active_part_view = None
                        st.rerun()
                        
                users_list = api.get_admin_users_list()
                
                # Action logic in state
                if "admin_confirm_action" in st.session_state:
                    act = st.session_state.admin_confirm_action
                    st.warning(f"⚠️ Confirm action: **{act['action'].upper()}** on user **{act['name']}**?")
                    
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        if st.button("Confirm Action", key="btn_confirm_act"):
                            try:
                                if act['action'] == "delete":
                                    api.remove_user(act['id'])
                                else:
                                    api.modify_user_role(act['id'], act['action'])
                                st.success("Action processed successfully.")
                                del st.session_state.admin_confirm_action
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Action failed: {e}")
                    with c_col2:
                        if st.button("Cancel", key="btn_cancel_act"):
                            del st.session_state.admin_confirm_action
                            st.rerun()
                            
                # Filter and render list based on active view
                if st.session_state.active_part_view == "Total Users":
                    display_list = [u for u in users_list if u["role"] == "User"]
                elif st.session_state.active_part_view == "Total Admins":
                    display_list = [u for u in users_list if u["role"] == "Admin"]
                elif st.session_state.active_part_view == "Pending Approval":
                    display_list = [u for u in users_list if u["approval_status"] == "Pending"]
                elif st.session_state.active_part_view == "Approved Account":
                    display_list = [u for u in users_list if u["approval_status"] == "Approved"]
                
                if not display_list:
                    st.info(f"No accounts found for {st.session_state.active_part_view}.")
                else:
                    for u in display_list:
                        if st.session_state.active_part_view == "Pending Approval":
                            with st.container(border=True):
                                st.markdown(f"**Name**: {u['name']} | **Email**: {u['email']} | **Phone**: {u['phone_number']}")
                                app_col1, app_col2 = st.columns(2)
                                with app_col1:
                                    if st.button("Approve & Enroll", key=f"btn_approve_{u['id']}"):
                                        try:
                                            api.approve_user(u['id'])
                                            st.success(f"Approved {u['name']}!")
                                            time.sleep(1.0)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))
                                with app_col2:
                                    if st.button("Reject Request", key=f"btn_reject_{u['id']}"):
                                        try:
                                            api.reject_user(u['id'])
                                            st.warning(f"Rejected {u['name']}!")
                                            time.sleep(1.0)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))
                        else:
                            with st.expander(f"{u['name']} ({u['role']}) - Status: {u['approval_status']}"):
                                st.write(f"Email: **{u['email']}** | Phone: **{u['phone_number']}**")
                                st.write(f"Month Present: **{u['present_days']}** | Absent: **{u['absent_days']}** | Attendance Rate: **{u['percentage']}%**")
                                
                                # Registered Facial Templates preview status
                                with st.container(border=True):
                                    st.markdown("##### 🔑 Registered Face ID Templates")
                                    st.success("✅ Facial Recognition Templates Enrolled: 5/5 poses registered successfully")
                                    st.caption("*Standard, Look Left, Look Right, Upward, Downward/Smile* templates cache is active.")
                                
                                # Action operations buttons
                                act_col1, act_col2, act_col3, act_col4 = st.columns(4)
                                with act_col1:
                                    if u['role'] != "Admin":
                                        if st.button("👑 Make Admin", key=f"btn_admin_{u['id']}"):
                                            st.session_state.admin_confirm_action = {"id": u['id'], "name": u['name'], "action": "make_admin"}
                                            st.rerun()
                                with act_col2:
                                    if u['role'] != "User":
                                        if st.button("👤 Convert to User", key=f"btn_user_{u['id']}"):
                                            st.session_state.admin_confirm_action = {"id": u['id'], "name": u['name'], "action": "convert_user"}
                                            st.rerun()
                                with act_col3:
                                    if u['role'] != "Registered":
                                        if st.button("📝 Convert to Reg (Pending)", key=f"btn_reg_{u['id']}"):
                                            st.session_state.admin_confirm_action = {"id": u['id'], "name": u['name'], "action": "convert_registered"}
                                            st.rerun()
                                with act_col4:
                                    if st.button("❌ Permanently Remove", key=f"btn_remove_{u['id']}"):
                                        st.session_state.admin_confirm_action = {"id": u['id'], "name": u['name'], "action": "delete"}
                                        st.rerun()
                                        
        with tab_admin_att:
            st.markdown("### 🛡️ Administrator Attendance Console")
            admin_stats = api.get_admin_attendance_stats()
            
            adm_col1, adm_col2, adm_col3, adm_col4 = st.columns(4)
            with adm_col1:
                st.markdown(f"<div class='metric-card'><p class='stat-label'>Current Month Rate</p><p class='stat-number'>{admin_stats.get('current_month_percentage')}%</p></div>", unsafe_allow_html=True)
            with adm_col2:
                st.markdown(f"<div class='metric-card'><p class='stat-label'>Before Month Rate</p><p class='stat-number'>{admin_stats.get('previous_month_percentage')}%</p></div>", unsafe_allow_html=True)
            with adm_col3:
                st.markdown(f"<div class='metric-card'><p class='stat-label'>Current Year Rate</p><p class='stat-number'>{admin_stats.get('current_year_percentage')}%</p></div>", unsafe_allow_html=True)
            with adm_col4:
                st.markdown(f"<div class='metric-card'><p class='stat-label'>Before Year Rate</p><p class='stat-number'>{admin_stats.get('previous_year_percentage')}%</p></div>", unsafe_allow_html=True)
                
            # Table removed to prevent duplication. Only one unified Today's Attendance Board is displayed in Overview tab.
                
        with tab_overview:
            try:
                overview = api.get_attendance_overview_stats()
            except Exception as e:
                st.error(f"Failed to load attendance overview: {e}")
                overview = {}

            summary = overview.get("summary_today", {})
            
            # 5 Clickable KPI Metric Button Cards (preserving layout size)
            if "admin_selected_kpi" not in st.session_state:
                st.session_state.admin_selected_kpi = None

            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1:
                st.markdown("<style>div[class*='st-key-btn_kpi_total'] button { border-left-color: #3b82f6 !important; }</style>", unsafe_allow_html=True)
                if st.button(f"👥 Total Users\n{summary.get('total_strength', 0)}", key="btn_kpi_total", use_container_width=True):
                    st.session_state.admin_selected_kpi = "total_users" if st.session_state.admin_selected_kpi != "total_users" else None
                    st.rerun()
            with m_col2:
                st.markdown("<style>div[class*='st-key-btn_kpi_present'] button { border-left-color: #10b981 !important; }</style>", unsafe_allow_html=True)
                if st.button(f"✅ Present Today\n{summary.get('present_count', 0)}", key="btn_kpi_present", use_container_width=True):
                    st.session_state.admin_selected_kpi = "present_today" if st.session_state.admin_selected_kpi != "present_today" else None
                    st.rerun()
            with m_col3:
                st.markdown("<style>div[class*='st-key-btn_kpi_absent'] button { border-left-color: #ef4444 !important; }</style>", unsafe_allow_html=True)
                if st.button(f"❌ Absent Today\n{summary.get('absent_count', 0)}", key="btn_kpi_absent", use_container_width=True):
                    st.session_state.admin_selected_kpi = "absent_today" if st.session_state.admin_selected_kpi != "absent_today" else None
                    st.rerun()
            with m_col4:
                st.markdown("<style>div[class*='st-key-btn_kpi_late'] button { border-left-color: #f59e0b !important; }</style>", unsafe_allow_html=True)
                if st.button(f"⏰ Late Today\n{summary.get('late_count', 0)}", key="btn_kpi_late", use_container_width=True):
                    st.session_state.admin_selected_kpi = "late_today" if st.session_state.admin_selected_kpi != "late_today" else None
                    st.rerun()
            with m_col5:
                st.markdown("<style>div[class*='st-key-btn_kpi_pct'] button { border-left-color: #8b5cf6 !important; }</style>", unsafe_allow_html=True)
                if st.button(f"📊 Attendance Rate\n{summary.get('total_attendance_pct', 0.0)}%", key="btn_kpi_pct", use_container_width=True):
                    st.session_state.admin_selected_kpi = "attendance_pct" if st.session_state.admin_selected_kpi != "attendance_pct" else None
                    st.rerun()

            # Render the drill-down tables based on selected KPI
            selected_kpi = st.session_state.get("admin_selected_kpi")
            if selected_kpi:
                import pandas as pd
                status_board = overview.get("status_board", [])
                
                with st.container(border=True):
                    if selected_kpi == "total_users":
                        st.markdown("#### 👥 System Total Users")
                        kpi_df = []
                        for item in status_board:
                            kpi_df.append({
                                "Name": item["name"],
                                "Email": item["email"],
                                "Role": item["role"]
                            })
                        if kpi_df:
                            st.dataframe(pd.DataFrame(kpi_df), use_container_width=True, hide_index=True)
                        else:
                            st.info("No users found.")
                            
                    elif selected_kpi == "present_today":
                        st.markdown("#### ✅ Present Today (User / Admin)")
                        kpi_df = []
                        for item in status_board:
                            if item["status"] in ("Present", "Late", "Half Day", "Something wrong"):
                                kpi_df.append({
                                    "Name": item["name"],
                                    "Email": item["email"],
                                    "Role": item["role"],
                                    "Check-In": item["check_in"],
                                    "Check-Out": item["check_out"],
                                    "Status": item["status"]
                                })
                        if kpi_df:
                            st.dataframe(pd.DataFrame(kpi_df), use_container_width=True, hide_index=True)
                        else:
                            st.info("No users present today.")
                            
                    elif selected_kpi == "absent_today":
                        st.markdown("#### ❌ Absent Today (User / Admin)")
                        kpi_df = []
                        for item in status_board:
                            if item["status"] == "Absent":
                                kpi_df.append({
                                    "Name": item["name"],
                                    "Email": item["email"],
                                    "Role": item["role"],
                                    "Status": "Absent"
                                })
                        if kpi_df:
                            st.dataframe(pd.DataFrame(kpi_df), use_container_width=True, hide_index=True)
                        else:
                            st.info("No users absent today.")
                            
                    elif selected_kpi == "late_today":
                        st.markdown("#### ⏰ Late Check-Ins Today")
                        kpi_df = []
                        for item in status_board:
                            if item["status"] == "Late":
                                kpi_df.append({
                                    "Name": item["name"],
                                    "Email": item["email"],
                                    "Role": item["role"],
                                    "Check-In": item["check_in"],
                                    "Status": "Late"
                                })
                        if kpi_df:
                            st.dataframe(pd.DataFrame(kpi_df), use_container_width=True, hide_index=True)
                        else:
                            st.info("No late arrivals today.")
                            
                    elif selected_kpi == "attendance_pct":
                        st.markdown("#### 📊 Monthly Attendance Percentage")
                        top_rankings = overview.get("top_attendance", [])
                        kpi_df = []
                        for item in top_rankings:
                            kpi_df.append({
                                "Employee Name": item["name"],
                                "Department": item["department"],
                                "Attendance Rate": item["rate"],
                                "Present Days": item["present_days"],
                                "Late Days": item["late_days"]
                            })
                        if kpi_df:
                            st.dataframe(pd.DataFrame(kpi_df), use_container_width=True, hide_index=True)
                        else:
                            st.info("No attendance percentage records found.")
                    
                    if st.button("Close Details List ✕", key="btn_close_kpi_details", type="primary"):
                        st.session_state.admin_selected_kpi = None
                        st.rerun()
                
            # Graph starts immediately below cards. Removed st.markdown("---") and headers.
            filter_col1, filter_col2 = st.columns([3, 1])
            with filter_col1:
                st.write("")
            with filter_col2:
                period = st.selectbox("Filter by:", ["This Week", "This Month", "This Year"], index=1, key="graph_filter")
            
            try:
                period_map = {"This Week": "week", "This Month": "month", "This Year": "year"}
                graph_response = api.get_attendance_graph_data(period_map.get(period, "month"))
                
                if graph_response and "labels" in graph_response and len(graph_response["labels"]) > 0:
                    import pandas as pd
                    import altair as alt
                    
                    df = pd.DataFrame({
                        "date": graph_response["labels"],
                        "Present": graph_response["present"],
                        "Absent": graph_response["absent"],
                        "Late": graph_response["late"],
                        "Half Day": graph_response.get("half_day", [0] * len(graph_response["labels"]))
                    })
                    
                    # Smooth stacked area chart with rounded borders & Tailwind HSL colors
                    area_chart = alt.Chart(df).transform_fold(
                        ["Present", "Absent", "Late", "Half Day"],
                        as_=["Status", "Count"]
                    ).mark_area(opacity=0.6, interpolate='monotone').encode(
                        x=alt.X("date:N", title="Date"),
                        y=alt.Y("Count:Q", stack="zero", title="Count"),
                        color=alt.Color("Status:N", scale=alt.Scale(
                            domain=["Present", "Absent", "Late", "Half Day"],
                            range=["#10b981", "#ef4444", "#f59e0b", "#3b82f6"]
                        )),
                        tooltip=["date:N", "Status:N", "Count:Q"]
                    ).properties(
                        height=250
                    ).configure_view(
                        strokeWidth=0,
                        cornerRadius=8
                    )
                    
                    st.altair_chart(area_chart, use_container_width=True)
                else:
                    st.info("No attendance trend data available for the selected period.")
            except Exception as e:
                st.warning(f"Could not load attendance trends: {e}")
                

            st.markdown("---")

            st.markdown("### 🏆 Top Attendance Ranking (This Month)")
            top_rankings = overview.get("top_attendance", [])
            top_rankings_filtered = [r for r in top_rankings if r.get("department") != "Administration"]
            
            if not top_rankings_filtered:
                st.info("No monthly rankings available for users.")
            else:
                html_table_rank = """<table style='width: 100%; border-collapse: collapse; margin-top: 10px; color: #1F2937; font-family: sans-serif;'>
<thead>
<tr style='background-color: #1F2937; color: #FFFFFF; text-align: left; font-weight: bold;'>
<th style='padding: 10px; border: 1px solid #1F2937;'>Rank</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Employee Name</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Attendance %</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Present Days</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Late Days</th>
</tr>
</thead>
<tbody>"""
                for rank, item in enumerate(top_rankings_filtered, 1):
                    html_table_rank += f"""<tr style='background-color: #FFFFFF; border-bottom: 1px solid #1F2937;'>
<td style='padding: 10px; border: 1px solid #1F2937;'><b>{rank}</b></td>
<td style='padding: 10px; border: 1px solid #1F2937;'><b>{item['name']}</b><br><span style='font-size: 0.8rem; color: #666666;'>{item['department']}</span></td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['rate']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['present_days']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['late_days']}</td>
</tr>"""
                html_table_rank += "</tbody></table>"
                st.markdown(html_table_rank, unsafe_allow_html=True)
                

            st.markdown("---")

            st.markdown("### 📅 Today's Attendance Board")
            status_board = overview.get("status_board", [])
            if not status_board:
                st.info("No approved accounts found in system.")
            else:
                html_table = """<table style='width: 100%; border-collapse: collapse; margin-top: 10px; color: #1F2937; font-family: sans-serif;'>
<thead>
<tr style='background-color: #1F2937; color: #FFFFFF; text-align: left; font-weight: bold;'>
<th style='padding: 10px; border: 1px solid #1F2937;'>Name</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Email</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Role</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Check-In</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Check-Out</th>
<th style='padding: 10px; border: 1px solid #1F2937;'>Status</th>
</tr>
</thead>
<tbody>"""
                for item in status_board:
                    status_text = item.get("status", "Absent")
                    
                    if status_text == "Present":
                        status_badge = "<span style='background-color: #E8F5E9; color: #2E7D32; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;'>Present</span>"
                    elif status_text == "Late":
                        status_badge = "<span style='background-color: #FFF3E0; color: #E65100; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;'>Late</span>"
                    elif status_text == "Half Day":
                        status_badge = "<span style='background-color: #FFF3E0; color: #F57C00; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;'>Half Day</span>"
                    elif status_text in ("Something wrong", "Somthing wrong"):
                        status_badge = "<span style='background-color: #FFEBEE; color: #C62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;'>Something wrong</span>"
                    else:  # Absent
                        status_badge = "<span style='background-color: #FFEBEE; color: #C62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem;'>Absent</span>"
                        
                    html_table += f"""<tr style='background-color: #FFFFFF; border-bottom: 1px solid #1F2937;'>
<td style='padding: 10px; border: 1px solid #1F2937;'><b>{item['name']}</b></td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['email']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['role']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['check_in']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{item['check_out']}</td>
<td style='padding: 10px; border: 1px solid #1F2937;'>{status_badge}</td>
</tr>"""
                html_table += "</tbody></table>"
                st.markdown(html_table, unsafe_allow_html=True)
                
                # Manual Attendance Override
                st.write("")
                with st.expander("✍️ Manual Attendance Override"):
                    st.write("Over-write check-in or check-out stamps for any approved user:")
                    try:
                        all_users = api.get_admin_users_list()
                        approved_users = [u for u in all_users if u["approval_status"] == "Approved"]
                    except Exception:
                        approved_users = []
                        
                    if not approved_users:
                        st.info("No approved users available.")
                    else:
                        with st.form("manual_override_form"):
                            override_user = st.selectbox(
                                "Select Employee",
                                options=approved_users,
                                format_func=lambda x: f"{x['name']} ({x['email']})",
                                key="override_user_select"
                            )
                            override_date = st.date_input("Date", value=datetime.today().date(), key="override_date_picker")
                            
                            col_ov1, col_ov2 = st.columns(2)
                            with col_ov1:
                                override_in = st.text_input("Check-In Time (HH:MM in 24h format, or '-')", value="09:00", key="override_check_in")
                            with col_ov2:
                                override_out = st.text_input("Check-Out Time (HH:MM in 24h format, or '-')", value="17:00", key="override_check_out")
                                
                            override_status = st.selectbox(
                                "Status Override",
                                ["Present", "Late", "Half Day", "Absent"],
                                key="override_status_select"
                            )
                            
                            submit_override = st.form_submit_button("💾 Apply Manual Override")
                            if submit_override:
                                try:
                                    api.override_attendance(
                                        user_id=override_user["id"],
                                        date_str=str(override_date),
                                        check_in=override_in,
                                        check_out=override_out,
                                        status=override_status
                                    )
                                    st.success(f"✅ Successfully overrode attendance for {override_user['name']}!")
                                    time.sleep(1.0)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to override attendance: {e}")

            st.markdown("---")

            st.markdown("### 📸 Recent Scanner Activity")
            recent_list = overview.get("recent_attendance", [])
            if not recent_list:
                st.info("No recent scans recorded today.")
            else:
                for item in recent_list:
                    with st.container(border=True):
                        r_img_col, r_content_col = st.columns([1, 7])
                        with r_img_col:
                            img_path = item.get("image")
                            if img_path and Path(img_path).exists():
                                st.image(img_path, width=42)
                            else:
                                st.markdown("<div style='font-size: 1.8rem; display: flex; align-items: center; justify-content: center; height: 42px; width: 42px; border: 1px solid #1F2937; border-radius: 4px;'>👤</div>", unsafe_allow_html=True)
                        with r_content_col:
                            card_html = f"""
                            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; color: #1F2937; font-family: 'Inter', sans-serif; height: 42px;">
                                <div style="min-width: 0; display: flex; flex-direction: column; justify-content: center; flex-grow: 1;">
                                    <span style="font-weight: 700; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: 'Outfit', sans-serif;">{item['name']}</span>
                                    <span style="font-size: 0.8rem; color: #666666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">ID: STU{100+item['user_id']}</span>
                                </div>
                                <div style="display: flex; align-items: center; flex-shrink: 0; margin-left: 12px; height: 100%;">
                                    <span style="font-size: 0.85rem; color: #666666; margin-right: 12px; white-space: nowrap; font-family: 'Inter', sans-serif;">{item['time']}</span>
                                    <span style="background-color: #E8F5E9; color: #2E7D32; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; white-space: nowrap; font-family: 'Outfit', sans-serif;">Present</span>
                                </div>
                            </div>
                            """
                            st.markdown(card_html, unsafe_allow_html=True)


        with tab_audit:
            st.markdown("### Admin Action Logs")
            
            st.markdown("#### 📜 Audit Logs")
            audit_logs = api.get_audit_logs()
            if not audit_logs:
                st.info("No audit logs found.")
            else:
                st.table(audit_logs)
                
                # Print button to download PDF
                try:
                    pdf_bytes = generate_audit_pdf(audit_logs)
                    st.download_button(
                        label="🖨️ Print Audit Logs (PDF)",
                        data=pdf_bytes,
                        file_name="system_audit_logs.pdf",
                        mime="application/pdf"
                    )
                except Exception as ex:
                    st.error(f"Error generating PDF: {ex}")
    except Exception as e:
        st.error(f"Failed to load administrative console: {e}")

# 7. USER PROFILE PAGE
elif st.session_state.current_page == "Profile":
    st.subheader("👤 Account Profile Details")
    
    try:
        stats = api.get_user_dashboard_stats(st.session_state.user_id)
        
        # Check if face profile expired
        if stats.get("needs_face_update"):
            st.warning("⚠️ Your face profile was last updated more than 90 days ago. To maintain high recognition accuracy, please update your face profile now.")
            if st.button("Update Face Profile Now", type="primary", key="btn_profile_face_update"):
                st.session_state.update_face_pose_idx = 0
                st.session_state.update_face_captures = {}
                st.session_state.current_page = "Update Face Profile"
                st.rerun()
        
        if st.session_state.get("editing_profile"):
            with st.container(border=True):
                st.markdown("### ✏️ Edit Profile Details")
                with st.form("edit_profile_form"):
                    new_name = st.text_input("Name", value=stats.get("name"))
                    new_email = st.text_input("Email Address", value=stats.get("email"))
                    new_phone = st.text_input("Phone Number", value=stats.get("phone_number"))
                    new_department = st.text_input("Department", value=(stats.get("department") or "").upper(), placeholder="e.g. ENGINEERING, HR, SALES")
                    new_department = new_department.upper() if new_department else ""  # Auto-capitalize
                    
                    new_photo = st.file_uploader("Upload New Profile Photo (Optional, Max 5MB)", type=["jpg", "jpeg", "png"])
                    if new_photo is not None:
                        if new_photo.size > 5 * 1024 * 1024:
                            st.error("❌ File size exceeds the 5MB limit. Please select a smaller image.")
                            new_photo = None
                    
                    st.text_input("System Role", value=st.session_state.user_role, disabled=True)
                    st.text_input("Status", value=stats.get("approval_status"), disabled=True)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        save_btn = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
                    with btn_col2:
                        cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
                        
                    if save_btn:
                        if not new_name or not new_email or not new_phone:
                            st.error("Name, Email, and Phone Number cannot be empty.")
                        else:
                            photo_bytes = None
                            if new_photo is not None:
                                photo_bytes = new_photo.read()
                            try:
                                api.update_profile(
                                    user_id=st.session_state.user_id,
                                    name=new_name,
                                    email=new_email,
                                    phone_number=new_phone,
                                    department=new_department,
                                    image_bytes=photo_bytes
                                )
                                st.session_state.username = new_name
                                st.success("🎉 Profile updated successfully!")
                                st.session_state.editing_profile = False
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update profile: {e}")
                    if cancel_btn:
                        st.session_state.editing_profile = False
                        st.rerun()
        else:
            with st.container(border=True):
                col_left, col_right = st.columns([2, 1])
                
                with col_left:
                    st.markdown(f"### **{stats.get('name')}**")
                    st.write(f"Email Address: **{stats.get('email')}**")
                    st.write(f"Phone Number: **{stats.get('phone_number')}**")
                    st.write(f"Department: **{stats.get('department') or 'Not set'}**")
                    st.write(f"System Role: **{st.session_state.user_role}**")
                    st.write(f"Status: **{stats.get('approval_status')}**")
                    
                    st.write("")
                    if st.button("Update Profile", key="btn_trigger_profile_update", type="primary", use_container_width=True):
                        st.session_state.editing_profile = True
                        st.rerun()
                        
                with col_right:
                    st.write("📷 **Profile Template**")
                    profile_image_path = stats.get("profile_image")
                    
                    if profile_image_path and Path(profile_image_path).exists():
                        st.image(str(profile_image_path), use_container_width=True, caption="Approved face template")
                    else:
                        st.markdown("""
                        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; 
                                    height: 180px; width: 100%; border: 2px dashed #cbd5e1; border-radius: 12px; background-color: #f8fafc; text-align: center;'>
                            <span style='font-size: 3.5rem; color: #94a3b8;'>👤</span>
                            <span style='font-size: 0.85rem; color: #64748b; font-weight: 500; padding: 0 5px;'>No approved profile image found</span>
                        </div>
                        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Failed to fetch profile: {e}")

# 8. UPDATE FACE PROFILE PAGE
elif st.session_state.current_page == "Update Face Profile":
    col_left, col_mid, col_right = st.columns([1, 1.8, 1])
    with col_mid:
        st.markdown("<h2 style='text-align: center; color: #1F2937; font-family: \"Outfit\", sans-serif; font-weight: 800;'>🔄 Update Face Profile</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### 👤 Face Re-Enrollment Process")
            st.markdown("Please align your face in front of the camera and perform the rotations as indicated below.")
        
            # Poses list we need to cycle
            poses_cycle = ["front", "left", "right", "up", "down"]
        
            # Track index in state
            if "update_face_pose_idx" not in st.session_state:
                st.session_state.update_face_pose_idx = 0
                st.session_state.update_face_captures = {}
            
            current_pose = poses_cycle[st.session_state.update_face_pose_idx]
        
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
            progress_placeholder.write(f"Progress: **{st.session_state.update_face_pose_idx} / 5** poses captured.")
        
            # Enrollment Camera display loop
            frame_placeholder = st.empty()
            status_placeholder = st.empty()
        
            start_capture = st.button("Start Re-Enrollment Camera")
        
            if start_capture:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("Cannot access camera.")
                else:
                    last_call = 0.0
                    try:
                        while st.session_state.update_face_pose_idx < len(poses_cycle):
                            ret, frame = cap.read()
                            if not ret:
                                time.sleep(0.05)
                                continue
                            
                            frame = cv2.flip(frame, 1)
                            clean_frame = frame.copy()
                        
                            # Highlight guide boxes
                            h, w, _ = frame.shape
                            cv2.rectangle(frame, (int(w*0.3), int(h*0.2)), (int(w*0.7), int(h*0.8)), (255, 255, 255), 2)
                            cv2.putText(frame, f"POSE: {current_pose.upper()}", (int(w*0.3), int(h*0.2)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                            frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
                        
                            # Try sending frame for pose validation
                            now_time = time.time()
                            if now_time - last_call >= 0.8:
                                last_call = now_time
                            
                                _, img_encoded = cv2.imencode('.jpg', clean_frame)
                                image_bytes = img_encoded.tobytes()
                            
                                try:
                                    status_placeholder.info(f"Scanning for {current_pose.upper()} pose...")
                                    api.upload_enrollment_pose(st.session_state.user_id, current_pose, image_bytes)
                                
                                    # Success! Save frame and step index
                                    st.session_state.update_face_captures[current_pose] = True
                                    st.session_state.update_face_pose_idx += 1
                                
                                    # Update progress dynamically
                                    progress_placeholder.write(f"Progress: **{st.session_state.update_face_pose_idx} / 5** poses captured.")
                                
                                    status_placeholder.success(f"✓ Captured {current_pose.upper()}!")
                                    time.sleep(1.0)
                                
                                    if st.session_state.update_face_pose_idx < len(poses_cycle):
                                        current_pose = poses_cycle[st.session_state.update_face_pose_idx]
                                        # Update instruction dynamically
                                        instruction_placeholder.info(f"👉 **Current Action**: **{current_pose.upper()}** - {pose_instructions[current_pose]}")
                                    else:
                                        break
                                except Exception as e:
                                    # Show error description returned by pose classifier
                                    status_placeholder.warning(str(e))
                                
                            time.sleep(0.03)
                    finally:
                        cap.release()
                        frame_placeholder.empty()
                
                    # Check if all completed
                    if st.session_state.update_face_pose_idx >= 5:
                        status_placeholder.info("Finalizing face profiles...")
                        try:
                            api.complete_enrollment(st.session_state.user_id)
                            st.success("🎉 Face profile updated successfully!")
                            
                            # Clean up states
                            if "update_face_pose_idx" in st.session_state:
                                del st.session_state.update_face_pose_idx
                            if "update_face_captures" in st.session_state:
                                del st.session_state.update_face_captures
                            
                            time.sleep(2.0)
                            # Redirect back to User Dashboard or Admin Dashboard depending on role
                            if st.session_state.user_role == "Admin":
                                st.session_state.current_page = "Admin Dashboard"
                            else:
                                st.session_state.current_page = "User Dashboard"
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                        
            if st.button("Cancel & Return to Dashboard"):
                if "update_face_pose_idx" in st.session_state:
                    del st.session_state.update_face_pose_idx
                if "update_face_captures" in st.session_state:
                    del st.session_state.update_face_captures
                if st.session_state.user_role == "Admin":
                    st.session_state.current_page = "Admin Dashboard"
                else:
                    st.session_state.current_page = "User Dashboard"
                st.rerun()

# ─────────────────────────────────────────
# 10. REPORT PAGE  (Admin only)
# ─────────────────────────────────────────
elif st.session_state.current_page == "Report":
    from fpdf import FPDF
    import io

    col_left, col_mid, col_right = st.columns([1, 2.5, 1])
    with col_mid:
        st.markdown(
            "<h2 style='text-align:center;font-family:Outfit,sans-serif;font-weight:800;"
            "margin-top:1.5rem;margin-bottom:0.5rem;'>📋 Attendance Report</h2>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center;color:#555;margin-bottom:1.5rem;'>"
            "Select a date to view and download the full attendance record.</p>",
            unsafe_allow_html=True
        )

        with st.container(border=True):
            # ── Date picker + Year/Month selectors ─────────────────────────
            st.markdown("### 📅 Select Date")
            import calendar
            from calendar import monthrange

            today = datetime.today()
            years = list(range(today.year - 5, today.year + 3))
            cols = st.columns([1, 1, 3])
            with cols[0]:
                selected_year = st.selectbox("Year", years, index=years.index(today.year), label_visibility="collapsed")
            with cols[1]:
                month_names = list(calendar.month_name)[1:]
                selected_month_idx = st.selectbox("Month", month_names, index=today.month - 1, label_visibility="collapsed")
                selected_month = month_names.index(selected_month_idx) + 1
            with cols[2]:
                # default day: keep current day when selecting current month/year, otherwise day=1
                default_day = today.day if (selected_year == today.year and selected_month == today.month) else 1
                # ensure day is valid for the selected month/year
                max_day = monthrange(selected_year, selected_month)[1]
                default_day = min(default_day, max_day)
                selected_date = st.date_input(
                    "Choose a date",
                    value=datetime(selected_year, selected_month, default_day).date(),
                    label_visibility="collapsed"
                )

            fetch_btn = st.button("🔍 View Report", type="primary", use_container_width=True)

        # Bulk Export Date Range
        st.write("---")
        with st.container(border=True):
            st.markdown("### 📥 Bulk Master CSV Export")
            st.write("Extract complete HR attendance spreadsheet for a date range:")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                start_range = st.date_input("Start Date", value=today.date() - timedelta(days=7), key="bulk_start_range")
            with col_b2:
                end_range = st.date_input("End Date", value=today.date(), key="bulk_end_range")
                
            if st.button("📊 Generate Bulk CSV", use_container_width=True, key="btn_generate_bulk_csv"):
                try:
                    with st.spinner("Compiling database records..."):
                        bulk_records = api.get_attendance_report_range(start_range.strftime("%Y-%m-%d"), end_range.strftime("%Y-%m-%d"))
                    
                    if bulk_records:
                        import pandas as pd
                        bulk_df = pd.DataFrame(bulk_records)
                        csv_data = bulk_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Master CSV Report",
                            data=csv_data,
                            file_name=f"master_attendance_report_{start_range}_to_{end_range}.csv",
                            mime="text/csv",
                            key="btn_download_bulk_csv"
                        )
                        st.success("✅ CSV generated successfully! Click the download button above.")
                    else:
                        st.warning("No records found in this range.")
                except Exception as e:
                    st.error(f"Failed to generate bulk report: {e}")

        if fetch_btn or st.session_state.get("report_date_loaded"):
            # Store the date so the report stays visible after fetch
            if fetch_btn:
                st.session_state.report_date_loaded = selected_date.strftime("%Y-%m-%d")
            
            date_str = st.session_state.report_date_loaded

            try:
                records = api.get_attendance_report(date_str)
            except Exception as e:
                st.error(f"❌ Failed to load report: {e}")
                records = []

            if records is not None:
                display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %B %Y")

                # ── Summary counts ──────────────────────────────────────
                total     = len(records)
                present   = sum(1 for r in records if "Present" in r.get("status", ""))
                absent    = sum(1 for r in records if r.get("status") == "Absent")
                not_leave = sum(1 for r in records if "Not Leave" in r.get("status", ""))

                st.markdown(f"### 📊 Report for **{display_date}**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Members", total)
                m2.metric("Present", present)
                m3.metric("Absent", absent)

                st.write("")

                # ── Table ────────────────────────────────────────────────
                if records:
                    # Colour the status column
                    def status_badge(s):
                        if s == "Present":
                            return "🟢 Present"
                        elif s == "Absent":
                            return "🔴 Absent"
                        else:
                            return f"⚪ {s}"

                    table_rows = []
                    for idx, r in enumerate(records, 1):
                        table_rows.append({
                            "#":         idx,
                            "Name":      r.get("name", "-"),
                            "Role":      r.get("role", "-"),
                            "Check In":  r.get("check_in", "-"),
                            "Check Out": r.get("check_out", "-"),
                            "Status":    status_badge(r.get("status", "-"))
                        })

                    st.dataframe(
                        table_rows,
                        use_container_width=True,
                        hide_index=True
                    )

                    # ── PDF Generation ───────────────────────────────────
                    st.write("")
                    st.markdown("---")
                    st.markdown("#### ⬇️ Download Report")

                    def generate_pdf(records, date_label, summary):
                        pdf = FPDF()
                        pdf.set_auto_page_break(auto=True, margin=15)
                        pdf.add_page()

                        # Header
                        pdf.set_font("Helvetica", "B", 18)
                        pdf.cell(0, 10, "Face AI Attendance System", ln=True, align="C")
                        pdf.set_font("Helvetica", "", 12)
                        pdf.cell(0, 8, f"Attendance Report  -  {date_label}", ln=True, align="C")
                        pdf.ln(4)

                        # Divider
                        pdf.set_draw_color(0, 0, 0)
                        pdf.set_line_width(0.5)
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(4)

                        # Summary box
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.set_fill_color(240, 240, 240)
                        pdf.cell(45, 8, f"Total: {summary['total']}", border=1, fill=True)
                        pdf.cell(45, 8, f"Present: {summary['present']}", border=1, fill=True)
                        pdf.cell(45, 8, f"Absent: {summary['absent']}", border=1, fill=True)
                        pdf.cell(45, 8, f"Not Left: {summary['not_leave']}", border=1, fill=True, ln=True)
                        pdf.ln(4)

                        # Table header
                        col_w = [10, 55, 22, 28, 28, 40]
                        headers = ["#", "Name", "Role", "Check In", "Check Out", "Status"]
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.set_fill_color(30, 30, 30)
                        pdf.set_text_color(255, 255, 255)
                        for w, h in zip(col_w, headers):
                            pdf.cell(w, 8, h, border=1, fill=True, align="C")
                        pdf.ln()

                        # Table rows
                        pdf.set_font("Helvetica", "", 9)
                        pdf.set_text_color(0, 0, 0)
                        for idx, r in enumerate(records, 1):
                            # Alternate row fill
                            if idx % 2 == 0:
                                pdf.set_fill_color(245, 245, 245)
                                fill = True
                            else:
                                fill = False

                            status_raw = r.get("status", "-")
                            # Plain status text for PDF (no emoji)
                            if status_raw == "Present":
                                status_txt = "Present"
                            elif status_raw == "Absent":
                                status_txt = "Absent"
                            else:
                                status_txt = status_raw

                            row_data = [
                                str(idx),
                                r.get("name", "-")[:28],
                                r.get("role", "-"),
                                r.get("check_in", "-"),
                                r.get("check_out", "-"),
                                status_txt
                            ]
                            for w, val in zip(col_w, row_data):
                                pdf.cell(w, 7, val, border=1, fill=fill, align="C")
                            pdf.ln()

                        # Footer
                        pdf.ln(6)
                        pdf.set_font("Helvetica", "I", 8)
                        pdf.set_text_color(120, 120, 120)
                        pdf.cell(0, 6, f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}  |  Face AI Attendance System", align="C")

                        return pdf.output()

                    summary = {
                        "total":     total,
                        "present":   present,
                        "absent":    absent,
                        "not_leave": not_leave
                    }

                    pdf_bytes = generate_pdf(records, display_date, summary)
                    filename  = f"attendance_report_{date_str}.pdf"

                    st.download_button(
                        label="⬇️  Download PDF Report",
                        data=bytes(pdf_bytes),
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                else:
                    st.info("No Records Found")

