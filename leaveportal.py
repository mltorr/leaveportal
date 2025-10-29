import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import msal
import os
import requests
from pathlib import Path
from datetime import datetime
import calendar

# Page configuration
st.set_page_config(
    page_title="Leave Management Portal",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Azure AD app details
client_id = os.getenv('AZURE_CLIENT_ID', 'your-client-id')
client_secret = os.getenv('AZURE_CLIENT_SECRET', 'your-client-secret')
tenant_id = os.getenv('AZURE_TENANT_ID', 'your-tenant-id')
authority = f"https://login.microsoftonline.com/{tenant_id}"
redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8501')
scope = ["User.Read"]

# Initialize MSAL
try:
    msal_app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    MSAL_ENABLED = True
except Exception as e:
    MSAL_ENABLED = False
    print(f"MSAL initialization failed: {e}")

# Custom CSS for modern design
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
        --dark-bg: #1e293b;
        --light-bg: #f8fafc;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Modern card styling */
    .stCard {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .stCard:hover {
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
        transform: translateY(-2px);
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
        text-align: center;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    .status-approved {
        background-color: #d1fae5;
        color: #065f46;
    }
    
    .status-rejected {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    /* Modern buttons */
    .stButton>button {
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    /* Sidebar radio buttons - make labels white */
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] > div {
        color: white !important;
    }
    
    /* Keep button text black/dark */
    [data-testid="stSidebar"] button {
        color: #1e293b !important;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 12px;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
    
    /* Data editor styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'leaves' not in st.session_state:
    st.session_state.leaves = []
if 'users' not in st.session_state:
    st.session_state.users = {}

# Admin email
ADMIN_EMAIL = "mark.torres@btgi.com.au"

# File paths for JSON data
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
LEAVES_FILE = DATA_DIR / "leaves.json"

# Default data structures. Will automatically create data/users.json and data/leaves.json if not present.
DEFAULT_USERS = {
    "mark.torres@btgi.com.au": {
        "name": "Mark Torres",
        "email": "mark.torres@btgi.com.au",
        "role": "admin",
        "department": "Data Team",
        "position": "Data Engineer",
        "annual_leave": 10,
        "sick_leave": 5,
        "used_annual": 1,
        "used_sick": 3
    },
    "jhunriel.gaspar@btgi.com.au": {
        "name": "Jhunriel Gaspar",
        "email": "jhunriel.gaspar@btgi.com.au",
        "role": "user",
        "department": "Data Team",
        "position": "Data Engineer",
        "annual_leave": 10,
        "sick_leave": 5,
        "used_annual": 8,
        "used_sick": 2
    },
    "elsy.asmar@btgi.com.au": {
        "name": "Elsy Asmar",
        "email": "elsy.asmar@btgi.com.au",
        "role": "admin",
        "department": "Managers",
        "position": "Indirect Tax Manager",
        "annual_leave": 20,
        "sick_leave": 10,
        "used_annual": 4,
        "used_sick": 1
    },
    "aj.morong@btgi.com.au": {
        "name": "AJ Morong",
        "email": "aj.morong@btgi.com.au",
        "role": "user",
        "department": "Transformation",
        "position": "Senior Associate",
        "annual_leave": 10,
        "sick_leave": 5,
        "used_annual": 5,
        "used_sick": 2
    }
}

DEFAULT_LEAVES = [
    {
        "id": 1,
        "user_email": "jhunriel.gaspar@btgi.com.au",
        "user_name": "Jhunriel Gaspar",
        "leave_type": "Annual Leave",
        "start_date": "2025-09-15",
        "end_date": "2025-09-19",
        "days": 5,
        "reason": "Family vacation",
        "status": "Approved",
        "applied_date": "2025-08-20",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-08-21"
    },
    {
        "id": 2,
        "user_email": "jhunriel.gaspar@btgi.com.au",
        "user_name": "Jhunriel Gaspar",
        "leave_type": "Annual Leave",
        "start_date": "2025-10-10",
        "end_date": "2025-10-12",
        "days": 3,
        "reason": "Personal matters",
        "status": "Approved",
        "applied_date": "2025-09-25",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-09-26"
    },
    {
        "id": 3,
        "user_email": "jhunriel.gaspar@btgi.com.au",
        "user_name": "Jhunriel Gaspar",
        "leave_type": "Sick Leave",
        "start_date": "2025-08-05",
        "end_date": "2025-08-07",
        "days": 3,
        "reason": "Medical appointment and recovery",
        "status": "Approved",
        "applied_date": "2025-08-04",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-08-04"
    },
    {
        "id": 4,
        "user_email": "elsy.asmar@btgi.com.au",
        "user_name": "Elsy Asmar",
        "leave_type": "Annual Leave",
        "start_date": "2025-07-20",
        "end_date": "2025-07-23",
        "days": 4,
        "reason": "Summer break",
        "status": "Approved",
        "applied_date": "2025-07-01",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-07-02"
    },
    {
        "id": 5,
        "user_email": "elsy.asmar@btgi.com.au",
        "user_name": "Elsy Asmar",
        "leave_type": "Sick Leave",
        "start_date": "2025-09-08",
        "end_date": "2025-09-08",
        "days": 1,
        "reason": "Medical consultation",
        "status": "Approved",
        "applied_date": "2025-09-07",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-09-07"
    },
    {
        "id": 6,
        "user_email": "aj.morong@btgi.com.au",
        "user_name": "AJ Morong",
        "leave_type": "Annual Leave",
        "start_date": "2025-08-12",
        "end_date": "2025-08-16",
        "days": 5,
        "reason": "Attending family event",
        "status": "Approved",
        "applied_date": "2025-07-28",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-07-29"
    },
    {
        "id": 7,
        "user_email": "aj.morong@btgi.com.au",
        "user_name": "AJ Morong",
        "leave_type": "Sick Leave",
        "start_date": "2025-10-15",
        "end_date": "2025-10-16",
        "days": 2,
        "reason": "Flu symptoms",
        "status": "Approved",
        "applied_date": "2025-10-14",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-10-14"
    },
    {
        "id": 8,
        "user_email": "mark.torres@btgi.com.au",
        "user_name": "Mark Torres",
        "leave_type": "Annual Leave",
        "start_date": "2025-06-10",
        "end_date": "2025-06-10",
        "days": 1,
        "reason": "Personal appointment",
        "status": "Approved",
        "applied_date": "2025-06-05",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-06-05"
    },
    {
        "id": 9,
        "user_email": "mark.torres@btgi.com.au",
        "user_name": "Mark Torres",
        "leave_type": "Sick Leave",
        "start_date": "2025-09-20",
        "end_date": "2025-09-22",
        "days": 3,
        "reason": "Medical treatment",
        "status": "Approved",
        "applied_date": "2025-09-19",
        "reviewed_by": "Mark Torres",
        "reviewed_date": "2025-09-19"
    },
    {
        "id": 10,
        "user_email": "jhunriel.gaspar@btgi.com.au",
        "user_name": "Jhunriel Gaspar",
        "leave_type": "Annual Leave",
        "start_date": "2025-11-15",
        "end_date": "2025-11-18",
        "days": 4,
        "reason": "Extended weekend trip",
        "status": "Pending",
        "applied_date": "2025-10-28",
        "reviewed_by": None,
        "reviewed_date": None
    },
    {
        "id": 11,
        "user_email": "elsy.asmar@btgi.com.au",
        "user_name": "Elsy Asmar",
        "leave_type": "Annual Leave",
        "start_date": "2025-12-20",
        "end_date": "2025-12-31",
        "days": 12,
        "reason": "Year-end holidays",
        "status": "Pending",
        "applied_date": "2025-10-25",
        "reviewed_by": None,
        "reviewed_date": None
    }
]

# JSON file operations
def load_users():
    """Load users from JSON file"""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default users file
        save_users(DEFAULT_USERS)
        return DEFAULT_USERS.copy()

def save_users(users_data):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)

def load_leaves():
    """Load leaves from JSON file"""
    if LEAVES_FILE.exists():
        with open(LEAVES_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default leaves file
        save_leaves(DEFAULT_LEAVES)
        return DEFAULT_LEAVES.copy()

def save_leaves(leaves_data):
    """Save leaves to JSON file"""
    with open(LEAVES_FILE, 'w') as f:
        json.dump(leaves_data, f, indent=2)

# Initialize data from JSON files
if not st.session_state.users:
    st.session_state.users = load_users()
if not st.session_state.leaves:
    st.session_state.leaves = load_leaves()

# MSAL Authentication Functions
def get_auth_url():
    """Get Azure AD authentication URL"""
    auth_url = msal_app.get_authorization_request_url(scope, redirect_uri=redirect_uri)
    return auth_url

def get_token_from_code(auth_code):
    """Acquire token from authorization code"""
    token = msal_app.acquire_token_by_authorization_code(
        auth_code, 
        scopes=scope, 
        redirect_uri=redirect_uri
    )
    return token

def get_user_profile(token):
    """Retrieve user profile using the token"""
    headers = {
        'Authorization': 'Bearer ' + token['access_token']
    }
    response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
    return response.json()

def authenticate_user(user_email: str, user_name: str) -> Optional[Dict]:
    """Authenticate user and return user data"""
    # Check if user exists in our system
    if user_email in st.session_state.users:
        user = st.session_state.users[user_email]
        user['name'] = user_name  # Update name from Azure AD
        save_users(st.session_state.users)
        return user
    else:
        # Create new user if they don't exist (auto-provisioning)
        is_admin = user_email == ADMIN_EMAIL
        
        new_user = {
            "name": user_name,
            "email": user_email,
            "role": "admin" if is_admin else "user",
            "department": "Unassigned",
            "position": "Employee",
            "annual_leave": 10,
            "sick_leave": 5,
            "used_annual": 0,
            "used_sick": 0
        }
        st.session_state.users[user_email] = new_user
        save_users(st.session_state.users)
        return new_user

def mock_msal_login(email: str) -> Optional[Dict]:
    """Mock MSAL authentication for demo/development"""
    if email in st.session_state.users:
        return st.session_state.users[email]
    return None

def login_page():
    """Display login page with Microsoft authentication"""
    st.markdown("""
        <div style='text-align: center; padding: 60px 20px;'>
            <h1 style='font-size: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;'>
                BTG Leave Management Portal
            </h1>
            <p style='font-size: 1.2rem; color: #64748b; margin-bottom: 40px;'>
                Manage your leaves efficiently and stay organized
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Sign in with Microsoft (Pending)")
        st.markdown("---")
        
        # Check for authorization code in URL parameters
        query_params = st.query_params
        
        if MSAL_ENABLED and 'code' in query_params:
            # Handle OAuth callback
            auth_code = query_params['code']
            
            with st.spinner('Authenticating...'):
                try:
                    token = get_token_from_code(auth_code)
                    
                    if 'access_token' in token:
                        user_profile = get_user_profile(token)
                        user_email = user_profile.get('mail') or user_profile.get('userPrincipalName')
                        user_name = user_profile.get('displayName', 'User')
                        
                        user = authenticate_user(user_email, user_name)
                        
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.access_token = token['access_token']
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error("❌ User authentication failed.")
                    else:
                        st.error(f"❌ Authentication failed: {token.get('error_description', 'Unknown error')}")
                
                except Exception as e:
                    st.error(f"❌ Authentication error: {str(e)}")
        
        elif MSAL_ENABLED:
            st.markdown("<br>", unsafe_allow_html=True)
            auth_url = get_auth_url()
            
            st.markdown(f"""
                <a href="{auth_url}" target="_self">
                    <button style='width: 100%; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                   color: white; border: none; border-radius: 12px; font-size: 1.1rem;
                                   font-weight: 600; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                        🚀 Sign in with Microsoft
                    </button>
                </a>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("🔒 **Secure Authentication**: You will be redirected to Microsoft login.")
        
        else:
            st.warning("⚠️ **Demo Mode**: MSAL not configured. Using demo authentication.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            email = st.selectbox(
                "Select your account (Demo)",
                options=list(st.session_state.users.keys()),
                format_func=lambda x: f"{st.session_state.users[x]['name']} ({x})"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🚀 Sign in (Demo)", use_container_width=True):
                user = mock_msal_login(email)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("💡 **For Later Setup**: Configure Microsoft Authentication and Azure AD credentials in environment variables")

def get_leave_years():
    """Gets a sorted list of unique years from leave data, ensuring current/default year exists."""
    all_years_set = set()
    default_year = 2025  # Use 2025 as the default as requested
    all_years_set.add(default_year)

    # Get current year as a fallback if 2025 isn't present initially
    current_year = datetime.now().year
    all_years_set.add(current_year)

    if 'leaves' in st.session_state and st.session_state.leaves:
        for leave in st.session_state.leaves:
            try:
                # Extract year from the start_date string
                year = datetime.strptime(leave['start_date'], '%Y-%m-%d').year
                all_years_set.add(year)
            except (ValueError, KeyError):
                # Skip leaves with missing or malformed dates
                continue

    # Return sorted list, most recent first
    return sorted(list(all_years_set), reverse=True)

def get_leave_balance(user_email: str) -> Dict:
    """Calculate leave balance for a user"""
    user = st.session_state.users[user_email]
    annual_remaining = user['annual_leave'] - user['used_annual']
    sick_remaining = user['sick_leave'] - user['used_sick']
    
    return {
        "annual_total": user['annual_leave'],
        "annual_used": user['used_annual'],
        "annual_remaining": annual_remaining,
        "sick_total": user['sick_leave'],
        "sick_used": user['used_sick'],
        "sick_remaining": sick_remaining
    }

def user_dashboard():
    """Display user dashboard with year filter"""
    user = st.session_state.user

    # --- YEAR FILTER (Placed beside the welcome message) ---
    available_years = get_leave_years()
    # Find index for default year 2025, or use the latest year
    default_year = 2025
    try:
        default_index = available_years.index(default_year)
    except ValueError:
        default_index = 0

    col_header, col_year_select = st.columns([3, 1])

    with col_header:
         st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 30px; border-radius: 16px; margin-bottom: 30px; color: white; height: 100%; display: flex; flex-direction: column; justify-content: center;'>
                <h1 style='color: white; margin: 0;'>👋 Welcome back, {user['name']}!</h1>
                <p style='color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 1.1rem;'>
                    {user['position']} • {user['department']}
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_year_select:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True) # Add some top margin
        selected_year = st.selectbox(
            "📅 Select Year:",
            options=available_years,
            index=default_index,
            key="user_year_filter"
        )
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True) # Match header margin-bottom
    # --- END YEAR FILTER ---


    # --- Leave Balance (Still overall, not year-specific unless requirements change) ---
    balance = get_leave_balance(user['email'])
    st.markdown(f"#### Leave Balance Overview (Overall)") # Clarify it's overall balance
    col1_bal, col2_bal = st.columns(2)
    with col1_bal:
         st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Annual Leave</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>
                    {balance['annual_remaining']}
                </div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>
                    of {balance['annual_total']} days remaining
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col2_bal:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Sick Leave</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>
                    {balance['sick_remaining']}
                </div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>
                    of {balance['sick_total']} days remaining
                </div>
            </div>
        """, unsafe_allow_html=True)


    # --- Filter user's leaves for the selected year ---
    user_leaves_all = [l for l in st.session_state.leaves if l['user_email'] == user['email']]
    user_leaves_year = [
        l for l in user_leaves_all
        if datetime.strptime(l['start_date'], '%Y-%m-%d').year == selected_year
    ]

    # --- Stats for the selected year ---
    st.markdown(f"#### Your Stats for {selected_year}")
    col1_stats, col2_stats = st.columns(2)

    with col1_stats:
        pending_count_year = len([l for l in user_leaves_year if l['status'] == 'Pending'])
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        padding: 20px; border-radius: 16px; color: white;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Pending Requests ({selected_year})</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>
                    {pending_count_year}
                </div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>
                    awaiting approval
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2_stats:
        total_leaves_year = len(user_leaves_year)
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                        padding: 20px; border-radius: 16px; color: white;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Total Requests ({selected_year})</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>
                    {total_leaves_year}
                </div>
                 <div style='font-size: 0.85rem; opacity: 0.8;'>
                    in {selected_year}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### 📋 Your Recent Leave Requests ({selected_year})")

    if user_leaves_year:
        # Sort year-specific leaves
        df_year = pd.DataFrame(user_leaves_year)
        df_year = df_year.sort_values('applied_date', ascending=False)

        # Display top 5 from the selected year
        for _, leave in df_year.head(5).iterrows():
            status_color = {
                "Approved": "#10b981", "Rejected": "#ef4444", "Pending": "#f59e0b"
            }[leave['status']]

            st.markdown(f"""
                <div style='background: white; padding: 20px; border-radius: 12px;
                            margin: 10px 0; border-left: 4px solid {status_color};
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <div style='font-weight: 600; font-size: 1.1rem; color: #1e293b;'>
                                {leave['leave_type']}
                            </div>
                            <div style='color: #64748b; margin-top: 5px;'>
                                📅 {leave['start_date']} to {leave['end_date']} ({leave['days']} days)
                            </div>
                            <div style='color: #64748b; margin-top: 5px;'>
                                💬 {leave['reason']}
                            </div>
                        </div>
                        <div>
                            <span style='background: {status_color}; color: white;
                                        padding: 8px 16px; border-radius: 20px; font-weight: 600;'>
                                {leave['status']}
                            </span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"No leave requests found for {selected_year}.")

def apply_leave():
    """Leave application form"""
    st.markdown("### ✍️ Leave Application Form")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
            <div style='background: white; padding: 13px; border-radius: 16px;'>
        """, unsafe_allow_html=True)
        
        leave_type = st.selectbox(
            "Leave Type",
            ["Annual Leave", "Sick Leave", "Casual Leave", "Maternity/Paternity Leave", "Unpaid Leave"]
        )
        
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date", min_value=datetime.now().date())
        with col_end:
            end_date = st.date_input("End Date", min_value=start_date)
        
        days = (end_date - start_date).days + 1
        st.info(f"📊 Total days: **{days}**")
        
        reason = st.text_area("Reason for Leave", height=100)
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Submit Leave Request", use_container_width=True):
            if reason.strip():
                # Get next ID
                max_id = max([l['id'] for l in st.session_state.leaves], default=0)
                
                new_leave = {
                    "id": max_id + 1,
                    "user_email": st.session_state.user['email'],
                    "user_name": st.session_state.user['name'],
                    "leave_type": leave_type,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "days": days,
                    "reason": reason,
                    "status": "Pending",
                    "applied_date": datetime.now().strftime("%Y-%m-%d"),
                    "reviewed_by": None,
                    "reviewed_date": None
                }
                st.session_state.leaves.append(new_leave)
                save_leaves(st.session_state.leaves)
                st.success("✅ Leave request submitted successfully!")
                st.rerun()
            else:
                st.error("Please provide a reason for your leave.")
    
    with col2:
        balance = get_leave_balance(st.session_state.user['email'])
        
        st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 16px; color: white;'>
                <h4 style='color: white; margin-top: 0;'>📊 Leave Balance</h4>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
                <div style='margin: 15px 0;'>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Annual Leave</div>
                    <div style='font-size: 1.5rem; font-weight: bold;'>
                        {balance['annual_remaining']} / {balance['annual_total']} days
                    </div>
                </div>
                <div style='margin: 15px 0;'>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Sick Leave</div>
                    <div style='font-size: 1.5rem; font-weight: bold;'>
                        {balance['sick_remaining']} / {balance['sick_total']} days
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def admin_dashboard():
    """Display admin dashboard with year filter"""

    # --- YEAR FILTER (Placed beside the welcome message) ---
    available_years = get_leave_years()
    # Find index for default year 2025, or use the latest year
    default_year = 2025
    try:
        default_index = available_years.index(default_year)
    except ValueError:
        default_index = 0

    col_header, col_year_select = st.columns([3, 1])

    with col_header:
        st.markdown("""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 30px; border-radius: 16px; margin-bottom: 30px; color: white;'>
                <h1 style='color: white; margin: 0;'>👨‍💼 Admin Dashboard</h1>
                <p style='color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 1.1rem;'>
                    Manage all leave requests and view analytics
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_year_select:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True) # Add some top margin
        selected_year = st.selectbox(
            "📅 Select Year:",
            options=available_years,
            index=default_index,
            key="admin_year_filter"
        )
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True) # Match header margin-bottom
    # --- END YEAR FILTER ---
    st.markdown("#### 📊 Employees Who Applied For Leave This Month")
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    _, num_days = calendar.monthrange(current_year, current_month) # Get days in current month
    month_start_date = datetime(current_year, current_month, 1).date()
    month_end_date = datetime(current_year, current_month, num_days).date()

    leaves_this_month = []
    # Ensure leaves data exists in session state
    all_leaves_data = st.session_state.get('leaves', [])
    users_data = st.session_state.get('users', {})

    for leave in all_leaves_data:
        # Check essential keys and status
        if leave.get('status') in ['Approved', 'Pending'] and 'start_date' in leave and 'end_date' in leave:
            try:
                leave_start = datetime.strptime(leave['start_date'], '%Y-%m-%d').date()
                leave_end = datetime.strptime(leave['end_date'], '%Y-%m-%d').date()

                # Check for overlap with the current month
                if (leave_start <= month_end_date) and (leave_end >= month_start_date):
                    user_email = leave.get('user_email')
                    user_info = users_data.get(user_email)
                    position = user_info.get('position', 'N/A') if user_info else 'N/A'

                    leaves_this_month.append({
                        "Name": leave.get('user_name', 'N/A'),
                        "Position": position,
                        "Leave Start": leave['start_date'],
                        "Leave End": leave['end_date'],
                        "Date Requested": leave.get('applied_date', 'N/A'),
                        "Status": leave['status']
                    })
            except (ValueError, TypeError):
                 # Skip leaves with invalid date format or type issues
                continue

    if leaves_this_month:
        df_leaves_month = pd.DataFrame(leaves_this_month)
        # Sort by leave start date for clarity
        df_leaves_month = df_leaves_month.sort_values(by="Leave Start")
        st.dataframe(
            df_leaves_month,
            use_container_width=True,
            hide_index=True,
             column_config={
                 "Leave Start": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
                 "Leave End": st.column_config.DateColumn("End Date", format="YYYY-MM-DD"),
                 "Date Requested": st.column_config.DateColumn("Applied On", format="YYYY-MM-DD"),
             }
            )
    else:
        st.info(f"No employees found on leave for {now.strftime('%B %Y')}.") # Display current month/year

    st.markdown("<hr style='margin-top: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # --- Yearly Overview Section ---
    st.markdown("#### 📊 Yearly Overview")

    # --- YEAR FILTER ---
    available_years = get_leave_years()
    default_year = 2025
    try:
        default_index = available_years.index(default_year)
    except ValueError:
        default_index = 0 # Default to the latest year if 2025 isn't available

    # selected_year = st.selectbox(
    #     "Select Year for Overview:",
    #     options=available_years,
    #     index=default_index,
    #     key="admin_year_filter"
    # )

    # Filter leaves based on selected year, handling potential errors
    year_leaves = []
    for l in all_leaves_data:
        start_date_str = l.get('start_date')
        if isinstance(start_date_str, str):
            try:
                if datetime.strptime(start_date_str, '%Y-%m-%d').year == selected_year:
                    year_leaves.append(l)
            except ValueError:
                continue # Skip leaves with invalid date format

    pending_leaves = [l for l in year_leaves if l.get('status') == 'Pending']
    approved_leaves = [l for l in year_leaves if l.get('status') == 'Approved']
    rejected_leaves = [l for l in year_leaves if l.get('status') == 'Rejected']

    # --- Stat Cards (Using Year Filtered Data) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 16px; color: white; height: 100%;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Total Requests ({selected_year})</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>{len(year_leaves)}</div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>in {selected_year}</div>
            </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 20px; border-radius: 16px; color: white; height: 100%;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Pending Approval</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>{len(pending_leaves)}</div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>needs action</div>
            </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); padding: 20px; border-radius: 16px; color: white; height: 100%;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Approved</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>{len(approved_leaves)}</div>
                 <div style='font-size: 0.85rem; opacity: 0.8;'>in {selected_year}</div>
            </div>""", unsafe_allow_html=True)
    with col4:
        # Active Employees count is not year-specific
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 16px; color: white; height: 100%;'>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Active Employees</div>
                <div style='font-size: 2rem; font-weight: bold; margin: 10px 0;'>{len(users_data)}</div>
                <div style='font-size: 0.85rem; opacity: 0.8;'>total users</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Charts (Using Year Filtered Data) ---
    col1_chart, col2_chart = st.columns(2)

    with col1_chart:
        st.markdown(f"##### 📊 Leave Types Distribution ({selected_year})")
        valid_leaves_for_pie = [l for l in year_leaves if 'leave_type' in l]
        if valid_leaves_for_pie:
            leave_type_counts = pd.DataFrame(valid_leaves_for_pie)['leave_type'].value_counts()
            if not leave_type_counts.empty:
                fig_pie = px.pie(
                    values=leave_type_counts.values, names=leave_type_counts.index,
                    color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.4,
                    title=f"Leave Types in {selected_year}"
                )
                fig_pie.update_layout(showlegend=True, height=350, margin=dict(t=40, b=10, l=10, r=10), title_x=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                 st.info(f"No valid leave type data found for {selected_year}.")
        else:
            st.info(f"No leave data with leave types found for {selected_year}.")

    with col2_chart:
        st.markdown(f"##### 📈 Leave Status Overview ({selected_year})")
        if year_leaves: # Check if there are any leaves for the year at all
            status_data = {"Status": ["Pending", "Approved", "Rejected"],
                           "Count": [len(pending_leaves), len(approved_leaves), len(rejected_leaves)]}
            df_status = pd.DataFrame(status_data)
            # Filter out statuses with zero count for a cleaner bar chart if desired
            # df_status = df_status[df_status['Count'] > 0]

            if not df_status.empty:
                fig_bar = px.bar(
                    df_status, x="Status", y="Count", color="Status",
                    color_discrete_map={"Pending": "#f59e0b", "Approved": "#10b981", "Rejected": "#ef4444"},
                    title=f"Leave Statuses in {selected_year}"
                )
                fig_bar.update_layout(showlegend=False, height=350, margin=dict(t=40, b=10, l=10, r=10), title_x=0.5)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                 st.info(f"No leave status data to plot for {selected_year}.") # Should not happen if year_leaves is not empty
        else:
            st.info(f"No leave data to plot status for {selected_year}.")

    st.markdown(f"##### 📅 Monthly Leave Trends ({selected_year})")
    # Prepare data for trend chart, ensuring dates are valid
    valid_leaves_for_trend = []
    for l in year_leaves:
        start_date_str = l.get('start_date')
        if isinstance(start_date_str, str):
            try:
                month_obj = pd.to_datetime(start_date_str)
                l['month_obj'] = month_obj # Add parsed date object
                valid_leaves_for_trend.append(l)
            except (ValueError, TypeError):
                continue # Skip invalid dates

    df_valid_trends = pd.DataFrame(valid_leaves_for_trend)

    if not df_valid_trends.empty:
        # Create a full year's month range to ensure all months are shown
        all_months_in_year = pd.date_range(start=f'{selected_year}-01-01', end=f'{selected_year}-12-31', freq='MS') # MS = Month Start
        # Resample requires a datetime index
        monthly_data = df_valid_trends.set_index('month_obj').resample('MS').size().reindex(all_months_in_year, fill_value=0).reset_index(name='count')
        monthly_data['month'] = monthly_data['index'].dt.strftime('%Y-%m') # Format month for x-axis label

        fig_line = px.line(
            monthly_data, x='month', y='count', markers=True, line_shape='spline',
            title=f"Monthly Leave Requests in {selected_year}",
            labels={'count': 'Number of Leaves'}
        )
        fig_line.update_traces(line_color='#667eea', marker=dict(size=8))
        fig_line.update_layout(
            xaxis_title="Month", yaxis_title="Number of Leaves", height=350,
            margin=dict(t=40, b=10, l=10, r=10), title_x=0.5
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info(f"No valid leave data to display monthly trends for {selected_year}.")

def manage_leaves():
    """Admin page to manage all leaves"""
    st.markdown("### 📋 Manage Leave Requests")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Approved", "Rejected"])
    with col2:
        user_filter = st.selectbox("Filter by User", ["All"] + [u['name'] for u in st.session_state.users.values()])
    with col3:
        leave_type_filter = st.selectbox("Filter by Type", ["All", "Annual Leave", "Sick Leave", "Casual Leave", "Maternity/Paternity Leave", "Unpaid Leave"])
    
    filtered_leaves = st.session_state.leaves.copy()
    
    if status_filter != "All":
        filtered_leaves = [l for l in filtered_leaves if l['status'] == status_filter]
    if user_filter != "All":
        filtered_leaves = [l for l in filtered_leaves if l['user_name'] == user_filter]
    if leave_type_filter != "All":
        filtered_leaves = [l for l in filtered_leaves if l['leave_type'] == leave_type_filter]
    
    st.markdown(f"**Showing {len(filtered_leaves)} leave request(s)**")
    st.markdown("<br>", unsafe_allow_html=True)
    
    for leave in sorted(filtered_leaves, key=lambda x: x['applied_date'], reverse=True):
        status_color = {
            "Approved": "#10b981",
            "Rejected": "#ef4444",
            "Pending": "#f59e0b"
        }[leave['status']]
        
        with st.container():
            st.markdown(f"""
                <div style='background: white; padding: 20px; border-radius: 12px; 
                            margin: 10px 0; border-left: 4px solid {status_color};
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <div style='display: flex; justify-content: space-between; align-items: start;'>
                        <div style='flex: 1;'>
                            <div style='font-weight: 600; font-size: 1.1rem; color: #1e293b;'>
                                {leave['user_name']} - {leave['leave_type']}
                            </div>
                            <div style='color: #64748b; margin-top: 8px;'>
                                📅 {leave['start_date']} to {leave['end_date']} ({leave['days']} days)
                            </div>
                            <div style='color: #64748b; margin-top: 5px;'>
                                💬 Reason: {leave['reason']}
                            </div>
                            <div style='color: #94a3b8; margin-top: 5px; font-size: 0.9rem;'>
                                Applied on: {leave['applied_date']}
                            </div>
                        </div>
                        <div style='text-align: right;'>
                            <span style='background: {status_color}; color: white; 
                                         padding: 8px 16px; border-radius: 20px; font-weight: 600;
                                         display: inline-block; margin-bottom: 10px;'>
                                {leave['status']}
                            </span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if leave['status'] == 'Pending':
                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{leave['id']}"):
                        for l in st.session_state.leaves:
                            if l['id'] == leave['id']:
                                l['status'] = 'Approved'
                                l['reviewed_by'] = st.session_state.user['name']
                                l['reviewed_date'] = datetime.now().strftime("%Y-%m-%d")
                                
                                user_email = l['user_email']
                                if l['leave_type'] == 'Annual Leave':
                                    st.session_state.users[user_email]['used_annual'] += l['days']
                                elif l['leave_type'] == 'Sick Leave':
                                    st.session_state.users[user_email]['used_sick'] += l['days']
                                
                                save_leaves(st.session_state.leaves)
                                save_users(st.session_state.users)
                                break
                        st.success(f"Leave request approved!")
                        st.rerun()
                
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{leave['id']}"):
                        for l in st.session_state.leaves:
                            if l['id'] == leave['id']:
                                l['status'] = 'Rejected'
                                l['reviewed_by'] = st.session_state.user['name']
                                l['reviewed_date'] = datetime.now().strftime("%Y-%m-%d")
                                save_leaves(st.session_state.leaves)
                                break
                        st.warning(f"Leave request rejected.")
                        st.rerun()
            
            elif leave['status'] in ['Approved', 'Rejected']:
                st.markdown(f"""
                    <div style='color: #64748b; font-size: 0.9rem; margin-top: 10px;'>
                        ✓ Reviewed by {leave['reviewed_by']} on {leave['reviewed_date']}
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

def view_employees():
    """Admin page to view all employees and their year-specific leave balances"""
    st.markdown("### 👥 Employee Leave Overview")

    # --- YEAR FILTER ---
    available_years = get_leave_years()
    default_year = 2025
    try:
        default_index = available_years.index(default_year)
    except ValueError:
        default_index = 0

    selected_year = st.selectbox(
        "📅 Select Year:",
        options=available_years,
        index=default_index,
        key="employee_year_filter"
    )
    st.markdown("<hr style='margin-top: 0; margin-bottom: 20px;'>", unsafe_allow_html=True)
    # --- END YEAR FILTER ---

    st.markdown(f"#### Data for {selected_year}")

    employees_data = []
    all_leaves_data = st.session_state.get('leaves', [])
    users_data = st.session_state.get('users', {})

    # Pre-filter leaves for the selected year for efficiency
    leaves_in_year = []
    for l in all_leaves_data:
        start_date_str = l.get('start_date')
        if isinstance(start_date_str, str):
             try:
                if datetime.strptime(start_date_str, '%Y-%m-%d').year == selected_year:
                    leaves_in_year.append(l)
             except ValueError:
                 continue # Skip invalid date format

    for email, user in users_data.items():
        # Filter leaves for the current user AND selected year
        user_leaves_year = [l for l in leaves_in_year if l.get('user_email') == email]
        approved_user_leaves_year = [l for l in user_leaves_year if l.get('status') == 'Approved']

        # Calculate year-specific usage
        year_specific_annual_used = sum(l.get('days', 0) for l in approved_user_leaves_year if l.get('leave_type') == 'Annual Leave')
        year_specific_sick_used = sum(l.get('days', 0) for l in approved_user_leaves_year if l.get('leave_type') == 'Sick Leave')

        # Use total allocated leave from the user profile (ensure it's an int, default to 0)
        annual_allocated = int(user.get('annual_leave', 0))
        sick_allocated = int(user.get('sick_leave', 0))

        # Calculate year-specific remaining balances
        year_specific_annual_remaining = annual_allocated - year_specific_annual_used
        year_specific_sick_remaining = sick_allocated - year_specific_sick_used

        # Calculate year-specific request counts
        year_specific_total_requests = len(user_leaves_year)
        year_specific_pending = len([l for l in user_leaves_year if l.get('status') == 'Pending'])

        employees_data.append({
            "Name": user.get('name', 'N/A'),
            "Email": email,
            "Department": user.get('department', 'N/A'),
            "Position": user.get('position', 'N/A'),
            f"Annual Used ({selected_year})": year_specific_annual_used,
            f"Annual Remaining ({selected_year})": year_specific_annual_remaining,
            "Annual Allocated": annual_allocated,
            f"Sick Used ({selected_year})": year_specific_sick_used,
            f"Sick Remaining ({selected_year})": year_specific_sick_remaining,
            "Sick Allocated": sick_allocated,
            f"Total Requests ({selected_year})": year_specific_total_requests,
            f"Pending ({selected_year})": year_specific_pending
        })

    df = pd.DataFrame(employees_data)

    # --- FIX: Convert max values to standard int ---
    # Calculate max values safely, converting potential numpy types to int
    # Use 1 as a fallback if the DataFrame is empty or max calculation fails
    max_annual_allocated = 1
    if not df.empty and "Annual Allocated" in df.columns:
        try:
             # Ensure the column exists and has values before calling max()
             if not df["Annual Allocated"].empty:
                 max_annual_allocated = int(max(df["Annual Allocated"].max(), 1)) # Convert here
        except Exception: # Catch potential errors during max()
             pass # Keep the default value of 1

    max_sick_allocated = 1
    if not df.empty and "Sick Allocated" in df.columns:
         try:
             if not df["Sick Allocated"].empty:
                 max_sick_allocated = int(max(df["Sick Allocated"].max(), 1)) # Convert here
         except Exception:
             pass
    # --- END FIX ---


    # Adjust dataframe display configuration for new columns
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Department": st.column_config.TextColumn("Department", width="small"),
            "Position": st.column_config.TextColumn("Position", width="medium"),
             f"Annual Remaining ({selected_year})": st.column_config.ProgressColumn(
                f"Annual Rem. ({selected_year})",
                help=f"Remaining Annual Leave days for {selected_year} (based on total allocation)",
                format="%d days",
                min_value=0,
                max_value=max_annual_allocated, # Use converted int value
            ),
             f"Sick Remaining ({selected_year})": st.column_config.ProgressColumn(
                f"Sick Rem. ({selected_year})",
                help=f"Remaining Sick Leave days for {selected_year} (based on total allocation)",
                format="%d days",
                min_value=0,
                max_value=max_sick_allocated, # Use converted int value
            ),
             f"Annual Used ({selected_year})": st.column_config.NumberColumn(f"Annual Used ({selected_year})", format="%d days"),
             f"Sick Used ({selected_year})": st.column_config.NumberColumn(f"Sick Used ({selected_year})", format="%d days"),
             "Annual Allocated": st.column_config.NumberColumn("Annual Alloc.", format="%d days"),
             "Sick Allocated": st.column_config.NumberColumn("Sick Alloc.", format="%d days"),
             f"Total Requests ({selected_year})": st.column_config.NumberColumn(f"Total Req. ({selected_year})"),
             f"Pending ({selected_year})": st.column_config.NumberColumn(f"Pending ({selected_year})"),
        }
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### 📊 Department-wise Leave Analysis ({selected_year})")

    dept_data_year = {}
    # Iterate through users to ensure all departments are potentially included
    for email, user in users_data.items():
        dept = user.get('department', 'Unassigned')
        if dept not in dept_data_year:
            dept_data_year[dept] = {
                'total_employees': 0, # Count employees in dept regardless of leave
                'year_annual_used': 0,
                'year_sick_used': 0
            }
        dept_data_year[dept]['total_employees'] += 1

    # Aggregate year-specific leave usage by department from approved leaves
    for leave in leaves_in_year:
         if leave.get('status') == 'Approved':
            user_email = leave.get('user_email')
            if user_email and user_email in users_data:
                dept = users_data[user_email].get('department', 'Unassigned')
                if dept in dept_data_year:
                    leave_days = leave.get('days', 0)
                    if leave.get('leave_type') == 'Annual Leave':
                        dept_data_year[dept]['year_annual_used'] += leave_days
                    elif leave.get('leave_type') == 'Sick Leave':
                        dept_data_year[dept]['year_sick_used'] += leave_days

    dept_df_list = []
    for dept, data in dept_data_year.items():
        total_employees_in_dept = data.get('total_employees', 0)
        if total_employees_in_dept > 0:
            avg_annual = round(data.get('year_annual_used', 0) / total_employees_in_dept, 1)
            avg_sick = round(data.get('year_sick_used', 0) / total_employees_in_dept, 1)
        else:
            avg_annual = 0
            avg_sick = 0

        dept_df_list.append({
            'Department': dept,
            'Employees': total_employees_in_dept,
            f'Avg Annual Used ({selected_year})': avg_annual,
            f'Avg Sick Used ({selected_year})': avg_sick,
            f'Total Leave Days ({selected_year})': data.get('year_annual_used', 0) + data.get('year_sick_used', 0)
        })

    dept_df_year = pd.DataFrame(dept_df_list)

    if not dept_df_year.empty:
        # Filter out departments with 0 employees if desired before plotting
        # dept_df_year = dept_df_year[dept_df_year['Employees'] > 0]

        fig_dept = px.bar(
            dept_df_year,
            x='Department',
            y=[f'Avg Annual Used ({selected_year})', f'Avg Sick Used ({selected_year})'],
            barmode='group',
            color_discrete_sequence=['#667eea', '#f093fb'],
            labels={ "value": "Average Days Used per Employee", "variable": "Leave Type"},
            title=f"Department Leave Usage Analysis for {selected_year}"
        )
        fig_dept.update_layout(
            xaxis_title="Department", yaxis_title="Average Days Used",
            legend_title="Leave Type", height=400, title_x=0.5
        )
        st.plotly_chart(fig_dept, use_container_width=True)
    else:
        st.info(f"No department leave data to display for {selected_year}.")

def manage_users():
    """Admin page to manage users (add, edit, delete)"""
    st.markdown("### 👥 User Management")
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["➕ Add User", "✏️ Edit User", "🗑️ Delete User"])
    
    # Tab 1: Add User
    with tab1:
        st.markdown("#### Add New User")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
                <div style='background: white; padding: 20px; border-radius: 16px;'>
            """, unsafe_allow_html=True)
            
            new_name = st.text_input("Full Name*", key="add_name")
            new_email = st.text_input("Email*", key="add_email", placeholder="user@btgi.com.au")
            
            col_dept, col_pos = st.columns(2)
            with col_dept:
                departments = ["Directors", "Business Heads", "Managers", "Consulting", "HR", "Sales", 
                              "Intelligence", "Recovery", "Transformation", "Data Team", "Bisaya (9th Floor)"]
                new_department = st.selectbox("Department*", departments, key="add_dept")
            with col_pos:
                new_position = st.text_input("Position*", key="add_pos")
            
            col_role, col_al = st.columns(2)
            with col_role:
                new_role = st.selectbox("Role*", ["user", "admin"], key="add_role")
            with col_al:
                new_annual_leave = st.number_input("Annual Leave (days)", min_value=0, max_value=30, value=10, key="add_al")
            
            new_sick_leave = st.number_input("Sick Leave (days)", min_value=0, max_value=20, value=5, key="add_sl")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("➕ Add User", use_container_width=True, type="primary"):
                if not new_name or not new_email:
                    st.error("❌ Name and Email are required!")
                elif new_email in st.session_state.users:
                    st.error("❌ User with this email already exists!")
                elif not new_email.endswith("@btgi.com.au"):
                    st.error("❌ Email must end with @btgi.com.au")
                else:
                    new_user = {
                        "name": new_name,
                        "email": new_email,
                        "role": new_role,
                        "department": new_department,
                        "position": new_position,
                        "annual_leave": new_annual_leave,
                        "sick_leave": new_sick_leave,
                        "used_annual": 0,
                        "used_sick": 0
                    }
                    st.session_state.users[new_email] = new_user
                    save_users(st.session_state.users)
                    st.success(f"✅ User {new_name} added successfully!")
                    st.rerun()
        
        with col2:
            st.markdown("""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 20px; border-radius: 16px; color: white;'>
                    <h4 style='color: white; margin-top: 0;'>📝 Instructions</h4>
                    <div style='font-size: 0.9rem; line-height: 1.6;'>
                        • All fields marked with * are required<br><br>
                        • Email must be unique and end with @btgi.com.au<br><br>
                        • Default role is 'user', change to 'admin' for admin privileges<br><br>
                        • Leave balances start at 0 used days
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # Tab 2: Edit User
    with tab2:
        st.markdown("#### Edit Existing User")
        
        user_emails = list(st.session_state.users.keys())
        selected_user_email = st.selectbox(
            "Select User to Edit",
            user_emails,
            format_func=lambda x: f"{st.session_state.users[x]['name']} ({x})",
            key="edit_select"
        )
        
        if selected_user_email:
            selected_user = st.session_state.users[selected_user_email]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("""
                    <div style='background: white; padding: 20px; border-radius: 16px;'>
                """, unsafe_allow_html=True)
                
                edit_name = st.text_input("Full Name*", value=selected_user['name'], key="edit_name")
                st.text_input("Email", value=selected_user['email'], disabled=True, key="edit_email_display")
                
                col_dept, col_pos = st.columns(2)
                with col_dept:
                    departments = ["Directors", "Business Heads", "Managers", "Consulting", "HR", "Sales", 
                                  "Intelligence", "Recovery", "Transformation", "Data Team", "Bisaya (9th Floor)"]
                    current_dept = selected_user['department'] if selected_user['department'] in departments else "Data Team"
                    edit_department = st.selectbox("Department*", departments, index=departments.index(current_dept), key="edit_dept")
                with col_pos:
                    edit_position = st.text_input("Position*", value=selected_user['position'], key="edit_pos")
                
                col_role, col_al = st.columns(2)
                with col_role:
                    edit_role = st.selectbox("Role*", ["user", "admin"], index=0 if selected_user['role'] == 'user' else 1, key="edit_role")
                with col_al:
                    edit_annual_leave = st.number_input("Annual Leave (days)", min_value=0, max_value=30, value=selected_user['annual_leave'], key="edit_al")
                
                col_sl, col_used_al = st.columns(2)
                with col_sl:
                    edit_sick_leave = st.number_input("Sick Leave (days)", min_value=0, max_value=20, value=selected_user['sick_leave'], key="edit_sl")
                with col_used_al:
                    edit_used_annual = st.number_input("Used Annual Leave", min_value=0, max_value=edit_annual_leave, value=selected_user['used_annual'], key="edit_used_al")
                
                edit_used_sick = st.number_input("Used Sick Leave", min_value=0, max_value=edit_sick_leave, value=selected_user['used_sick'], key="edit_used_sl")
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                    if not edit_name:
                        st.error("❌ Name is required!")
                    else:
                        st.session_state.users[selected_user_email]['name'] = edit_name
                        st.session_state.users[selected_user_email]['role'] = edit_role
                        st.session_state.users[selected_user_email]['department'] = edit_department
                        st.session_state.users[selected_user_email]['position'] = edit_position
                        st.session_state.users[selected_user_email]['annual_leave'] = edit_annual_leave
                        st.session_state.users[selected_user_email]['sick_leave'] = edit_sick_leave
                        st.session_state.users[selected_user_email]['used_annual'] = edit_used_annual
                        st.session_state.users[selected_user_email]['used_sick'] = edit_used_sick
                        
                        # Update current user session if editing self
                        if st.session_state.user['email'] == selected_user_email:
                            st.session_state.user = st.session_state.users[selected_user_email]
                        
                        save_users(st.session_state.users)
                        st.success(f"✅ User {edit_name} updated successfully!")
                        st.rerun()
            
            with col2:
                balance = get_leave_balance(selected_user_email)
                st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 20px; border-radius: 16px; color: white;'>
                        <h4 style='color: white; margin-top: 0;'>📊 Current Balance</h4>
                        <div style='margin: 15px 0;'>
                            <div style='font-size: 0.9rem; opacity: 0.9;'>Annual Leave</div>
                            <div style='font-size: 1.3rem; font-weight: bold;'>
                                {balance['annual_remaining']} / {balance['annual_total']} remaining
                            </div>
                        </div>
                        <div style='margin: 15px 0;'>
                            <div style='font-size: 0.9rem; opacity: 0.9;'>Sick Leave</div>
                            <div style='font-size: 1.3rem; font-weight: bold;'>
                                {balance['sick_remaining']} / {balance['sick_total']} remaining
                            </div>
                        </div>
                        <hr style='border-color: rgba(255,255,255,0.3); margin: 20px 0;'>
                        <div style='font-size: 0.85rem; opacity: 0.8;'>
                            ⚠️ Note: Email cannot be changed
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Tab 3: Delete User
    with tab3:
        st.markdown("#### Delete User")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.warning("⚠️ **Warning**: Deleting a user will permanently remove their account and all associated data.")
            
            user_emails = list(st.session_state.users.keys())
            delete_user_email = st.selectbox(
                "Select User to Delete",
                user_emails,
                format_func=lambda x: f"{st.session_state.users[x]['name']} ({x})",
                key="delete_select"
            )
            
            if delete_user_email:
                delete_user = st.session_state.users[delete_user_email]
                
                st.markdown(f"""
                    <div style='background: white; padding: 20px; border-radius: 16px; border: 2px solid #ef4444;'>
                        <h4 style='color: #ef4444; margin-top: 0;'>User Details</h4>
                        <div style='margin: 10px 0;'><strong>Name:</strong> {delete_user['name']}</div>
                        <div style='margin: 10px 0;'><strong>Email:</strong> {delete_user['email']}</div>
                        <div style='margin: 10px 0;'><strong>Department:</strong> {delete_user['department']}</div>
                        <div style='margin: 10px 0;'><strong>Position:</strong> {delete_user['position']}</div>
                        <div style='margin: 10px 0;'><strong>Role:</strong> {delete_user['role'].title()}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Confirmation checkbox
                confirm_delete = st.checkbox(f"I confirm that I want to delete {delete_user['name']}", key="confirm_delete")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("🗑️ Delete User", use_container_width=True, type="primary", disabled=not confirm_delete):
                    if delete_user_email == st.session_state.user['email']:
                        st.error("❌ You cannot delete your own account!")
                    else:
                        # Delete user
                        del st.session_state.users[delete_user_email]
                        
                        # Also delete all leave requests by this user
                        st.session_state.leaves = [l for l in st.session_state.leaves if l['user_email'] != delete_user_email]
                        
                        save_users(st.session_state.users)
                        save_leaves(st.session_state.leaves)
                        
                        st.success(f"✅ User {delete_user['name']} deleted successfully!")
                        st.rerun()
        
        with col2:
            st.markdown("""
                <div style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                            padding: 20px; border-radius: 16px; color: white;'>
                    <h4 style='color: white; margin-top: 0;'>⚠️ Deletion Info</h4>
                    <div style='font-size: 0.9rem; line-height: 1.6;'>
                        Deleting a user will:<br><br>
                        • Remove their account permanently<br><br>
                        • Delete all their leave requests<br><br>
                        • Cannot be undone<br><br>
                        • You cannot delete yourself
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # Display all users summary
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### 📋 All Users Summary")
    
    users_summary = []
    for email, user in st.session_state.users.items():
        users_summary.append({
            "Name": user['name'],
            "Email": email,
            "Department": user['department'],
            "Position": user['position'],
            "Role": user['role'].title(),
            "Annual Leave": f"{user['annual_leave']} days",
            "Sick Leave": f"{user['sick_leave']} days"
        })
    
    df_summary = pd.DataFrame(users_summary)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

def settings_page():
    """User settings page to update profile"""
    st.markdown("### ⚙️ Settings")
    
    user = st.session_state.user
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
            <div style='background: white; padding: 14px; border-radius: 16px;'>
        """, unsafe_allow_html=True)
        
        st.markdown("#### 👤 Profile Information")
        
        name = st.text_input("Full Name", value=user['name'])
        email = st.text_input("Email", value=user['email'], disabled=True)
        
        col_dept, col_pos = st.columns(2)
        with col_dept:
            departments = ["Directors", "Business Heads", "Managers", "Consulting", "HR", "Sales", 
                          "Intelligence", "Recovery", "Transformation", "Data Team", "Bisaya (9th Floor)"]
            current_dept = user['department'] if user['department'] in departments else "Data Team"
            department = st.selectbox("Department", departments, index=departments.index(current_dept))
        with col_pos:
            position = st.text_input("Position", value=user['position'])
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Save Changes", use_container_width=True):
            st.session_state.users[user['email']]['name'] = name
            st.session_state.users[user['email']]['department'] = department
            st.session_state.users[user['email']]['position'] = position
            st.session_state.user = st.session_state.users[user['email']]
            save_users(st.session_state.users)
            st.success("✅ Profile updated successfully!")
            st.rerun()
    
    with col2:
        st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 16px; color: white;'>
                <h4 style='color: white; margin-top: 0;'>👤 Account Info</h4>
                <div style='margin: 15px 0;'>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Contains Your User Information</div>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Modify or Update Your Profile</div>
                </div>
                <div style='margin: 15px 0;'>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Member Since</div>
                    <div style='font-size: 1.2rem; font-weight: bold;'>
                        January 2022
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # FIXED CODE
        # if st.button("🚪 Logout", use_container_width=True, type="secondary", key="settings_logout"):
        #     st.session_state.authenticated = False
        #     st.session_state.user = None
        #     st.rerun()

def main():
    """Main application logic"""
    
    if not st.session_state.authenticated:
        login_page()
    else:
        user = st.session_state.user
        
        with st.sidebar:
            st.markdown(f"""
                <div style='text-align: center; padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1);'>
                    <div style='font-size: 2rem; margin-bottom: 10px;'>🏖️</div>
                    <div style='font-size: 1.2rem; font-weight: bold; color: white;'>BTG Leave Portal</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 12px; 
                            margin-bottom: 20px; color: white;'>
                    <div style='font-size: 0.9rem; opacity: 0.8;'>Logged in as</div>
                    <div style='font-weight: 600; margin-top: 5px;'>{user['name']}</div>
                    <div style='font-size: 0.85rem; opacity: 0.7; margin-top: 2px;'>
                        {user['position']}
                    </div>
                    <div style='font-size: 0.85rem; opacity: 0.7; margin-top: 2px;'>
                        {user['department']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if user['role'] == 'admin':
                page = st.radio(
                    "Navigation",
                    ["📊 Dashboard", "📋 Manage Leaves", "👥 Employees", "👤 User Management", "✍️ Apply Leave", "⚙️ Settings"],
                    label_visibility="collapsed"
                )
            else:
                page = st.radio(
                    "Navigation",
                    ["🏠 Dashboard", "✍️ Apply Leave", "⚙️ Settings"],
                    label_visibility="collapsed"
                )
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
        
        if user['role'] == 'admin':
            if page == "📊 Dashboard":
                admin_dashboard()
            elif page == "📋 Manage Leaves":
                manage_leaves()
            elif page == "👥 Employees":
                view_employees()
            elif page == "👤 User Management":
                manage_users()
            elif page == "✍️ Apply Leave":
                apply_leave()
            elif page == "⚙️ Settings":
                settings_page()
        else:
            if page == "🏠 Dashboard":
                user_dashboard()
            elif page == "✍️ Apply Leave":
                apply_leave()
            elif page == "⚙️ Settings":
                settings_page()

if __name__ == "__main__":
    main()
