import streamlit as st
import pandas as pd
from datetime import datetime
import os
import hashlib
import altair as alt

# --- Configuration ---
BP_DATA_FILE = "bp_readings.csv"
USER_DATA_FILE = "user_credentials.csv"

# --- Data Persistence Functions ---

def load_data(file_path, columns, default_data=None):
    """Loads a CSV file into a DataFrame, or creates an empty one if not found."""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        if default_data is None:
            return pd.DataFrame(columns=columns)
        else:
            df = pd.DataFrame(default_data, columns=columns)
            df.to_csv(file_path, index=False)
            return df

def save_data(df, file_path):
    """Saves DataFrame to a CSV file."""
    df.to_csv(file_path, index=False)

def hash_password(password):
    """Hashes the password for secure storage (basic hashing)."""
    return hashlib.sha256(password.encode()).hexdigest()

# Load user data (username, name, password_hash)
USER_COLS = ['username', 'name', 'password_hash']
users_df = load_data(USER_DATA_FILE, USER_COLS)

# Load BP readings (user, timestamp, systolic, diastolic, pulse)
BP_COLS = ['username', 'timestamp', 'systolic', 'diastolic', 'pulse', 'category']
bp_df = load_data(BP_DATA_FILE, BP_COLS)

# Convert timestamp to datetime if the file was loaded
if not bp_df.empty:
    bp_df['timestamp'] = pd.to_datetime(bp_df['timestamp'])

# --- BP Categorization Logic (AHA/ACC 2017 Guidelines) ---

def get_bp_category(systolic, diastolic):
    """Determines the BP category based on SBP and DBP."""
    if systolic is None or diastolic is None:
        return "Invalid"
    
    s = int(systolic)
    d = int(diastolic)
    
    # Hypertensive Crisis (Seek immediate medical attention)
    if s >= 180 or d >= 120:
        return "Hypertensive Crisis"
    # Stage 2 Hypertension
    elif s >= 140 or d >= 90:
        return "Stage 2 Hypertension"
    # Stage 1 Hypertension
    elif s >= 130 or d >= 80:
        return "Stage 1 Hypertension"
    # Elevated
    elif s >= 120 and d < 80:
        return "Elevated"
    # Normal
    elif s < 120 and d < 80:
        return "Normal"
    else:
        # Fallback for mixed or unusual readings (e.g., S<120 and D>=90)
        return "Atypical Reading"

def get_category_color(category):
    """Maps BP category to a color for visual emphasis."""
    # Updated color palette for better visual distinction
    colors = {
        "Normal": "#10B981", # Emerald Green
        "Elevated": "#F59E0B", # Amber Yellow
        "Stage 1 Hypertension": "#EF4444", # Red-Orange
        "Stage 2 Hypertension": "#DC2626", # Deep Red
        "Hypertensive Crisis": "#991B1B", # Dark Maroon
        "Atypical Reading": "#3B82F6", # Blue
        "Invalid": "#6B7280" # Gray
    }
    return colors.get(category, "#6B7280")

# --- Streamlit UI Components and Logic ---

def handle_auth(is_sidebar=False):
    """
    Handles user login and sign up.
    If is_sidebar is True, renders a small status/logout button (used after login).
    If False, renders the full centralized login form (used before login).
    Returns True if logged in, False otherwise.
    """
    global users_df 
    
    # Initialization
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['user_name_full'] = None

    if st.session_state['logged_in']:
        # Always show status and logout button in the sidebar when logged in
        st.sidebar.title("👤 Session")
        st.sidebar.success(f"Welcome back, **{st.session_state['username']}**!")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.session_state['user_name_full'] = None
            st.rerun()
        return True
    
    if not is_sidebar:
        # --- Centralized Login/Signup UI (Main Page) ---
        
        # Center the content using columns
        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_center:
            st.header("Access Your Tracker")
            st.markdown("---")
            
            choice = st.radio("Select Action", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed")
            st.markdown("---")

            if choice == "Login":
                st.subheader("🔒 Login")
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type='password', key="login_pw")
                
                if st.button("Access Account", use_container_width=True, type="primary"):
                    user_record = users_df[users_df['username'] == username]
                    
                    if not user_record.empty:
                        stored_hash = user_record['password_hash'].iloc[0]
                        input_hash = hash_password(password)
                        
                        if stored_hash == input_hash:
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = username
                            st.session_state['user_name_full'] = user_record['name'].iloc[0] # Store full name
                            st.success("Logged in successfully! Redirecting...")
                            st.rerun()
                        else:
                            st.error("Incorrect Password.")
                    else:
                        st.error("Username not found.")
                        
            elif choice == "Sign Up":
                st.subheader("✨ Create Account")
                new_username = st.text_input("New Username", key="signup_user")
                new_name = st.text_input("Your Full Name", key="signup_name")
                new_password = st.text_input("New Password", type='password', key="signup_pw")
                
                if st.button("Create New Account", use_container_width=True, type="primary"):
                    if new_username in users_df['username'].values:
                        st.error("Username already exists.")
                    elif not new_username or not new_password or not new_name:
                        st.error("Please fill in all fields.")
                    else:
                        new_hash = hash_password(new_password)
                        new_user = pd.DataFrame([{'username': new_username, 'name': new_name, 'password_hash': new_hash}])
                        
                        users_df = pd.concat([users_df, new_user], ignore_index=True)
                        save_data(users_df, USER_DATA_FILE)
                        
                        st.success(f"Account created for {new_username}! Please switch to the Login tab.")
                        
    return st.session_state['logged_in']

def log_reading_page():
    """Form to log a new blood pressure reading."""
    global bp_df 

    st.header("✍️ Record New Reading")
    st.markdown("---")

    col_s, col_d, col_p = st.columns(3)
    
    with col_s:
        # Added value=None to ensure the field is empty on first load
        systolic = st.number_input("Systolic (SBP / mmHg)", min_value=50, max_value=300, step=1, key="systolic_input", help="The top number. Pressure when heart beats.", value=None)
    with col_d:
        # Added value=None to ensure the field is empty on first load
        diastolic = st.number_input("Diastolic (DBP / mmHg)", min_value=30, max_value=200, step=1, key="diastolic_input", help="The bottom number. Pressure when heart rests.", value=None)
    with col_p:
        # Added value=None to ensure the field is empty on first load
        pulse = st.number_input("Pulse (BPM)", min_value=30, max_value=250, step=1, key="pulse_input", help="Heart beats per minute.", value=None)
    
    st.markdown("---")
    
    col_date, col_time, col_cat = st.columns([1, 1, 2])
        
    with col_date:
        date_time = st.date_input("Date", datetime.now().date())
    with col_time:
        time_val = st.time_input("Time", datetime.now().time())

    # Combine date and time
    reading_time = datetime.combine(date_time, time_val)
    
    # Calculate category for immediate feedback
    current_category = get_bp_category(systolic, diastolic)
    with col_cat:
        st.markdown(f"**Calculated Category:**")
        # --- ENHANCED UI FOR CATEGORY CARD ---
        st.markdown(f"""
        <div style='
            background-color:{get_category_color(current_category)}; 
            padding: 12px; /* Slightly more padding */
            border-radius: 12px; /* Increased rounding */
            color: white; 
            text-align: center; 
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2); /* Added shadow for depth */
            font-size: 1.1rem;
        '>
            {current_category}
        </div>
        """, unsafe_allow_html=True)
        # --- END ENHANCED UI ---


    st.markdown("---")
    if st.button("💾 Save Reading & View Insights", use_container_width=True, type="primary"):
        if systolic and diastolic:
            new_reading = pd.DataFrame([{
                'username': st.session_state['username'],
                'timestamp': reading_time,
                'systolic': systolic,
                'diastolic': diastolic,
                'pulse': pulse,
                'category': current_category
            }])
            
            bp_df = pd.concat([bp_df, new_reading], ignore_index=True)
            bp_df['timestamp'] = pd.to_datetime(bp_df['timestamp'])
            save_data(bp_df, BP_DATA_FILE)
            
            st.success("Reading successfully logged! Redirecting to Insights...")
            # Automatically switch to the Insights page after logging
            st.session_state['page'] = "Insights & History"
            st.rerun() 
        else:
            st.error("Please enter both Systolic and Diastolic values.")
            
    with st.expander("ℹ️ Blood Pressure Categories (AHA/ACC 2017)"):
        st.markdown("""
        | Category | Systolic (mmHg) | AND/OR | Diastolic (mmHg) | Color |
        | :--- | :--- | :--- | :--- | :--- |
        | **Normal** | Less than 120 | AND | Less than 80 | :green[●] |
        | **Elevated** | 120–129 | AND | Less than 80 | :orange[●] |
        | **Stage 1 Hypertension** | 130–139 | OR | 80–89 | :red[●] |
        | **Stage 2 Hypertension** | 140 or higher | OR | 90 or higher | :red[●] |
        | **Hypertensive Crisis** | Higher than 180 | AND/OR | Higher than 120 | :red[●] |
        """)


def insights_page(user_data):
    """Displays trends, averages, and historical readings for the user."""
    st.header("📊 Health Insights & Trend Analysis")
    
    if user_data.empty:
        st.info("No readings logged yet. Log your first reading to see insights.")
        return

    # --- Metrics ---
    st.subheader("Key Summary Metrics")
    
    avg_s = user_data['systolic'].mean().round(1)
    avg_d = user_data['diastolic'].mean().round(1)
    latest_s = user_data['systolic'].iloc[-1]
    latest_d = user_data['diastolic'].iloc[-1]
    latest_cat = user_data['category'].iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    # Custom colored metric card
    with col1:
        # --- ENHANCED UI FOR LATEST READING CARD ---
        latest_cat_color = get_category_color(latest_cat)
        st.markdown(f"""
        <div style="
            padding: 15px; 
            border-radius: 12px; /* Increased rounding */
            border-left: 6px solid {latest_cat_color}; /* Slightly thicker border */
            background-color: white; /* Clean white background */
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); /* Stronger shadow */
        ">
            <p style="font-weight: 600; margin-bottom: 0; color: #6b7280;">Latest Reading</p>
            <h3 style="margin-top: 5px; margin-bottom: 5px; color: {latest_cat_color}; font-size: 1.5rem;">{latest_s}/{latest_d} mmHg</h3>
            <p style="margin-bottom: 0;"><small>Status: <strong>{latest_cat}</strong></small></p>
        </div>
        """, unsafe_allow_html=True)
        # --- END ENHANCED UI ---

    col2.metric("Average Systolic", f"{avg_s} mmHg", "Avg SBP")
    col3.metric("Average Diastolic", f"{avg_d} mmHg", "Avg DBP")

    # --- Trend Chart ---
    st.subheader("Blood Pressure Trend Over Time")
    
    # Reshape data for Altair charting
    chart_data = user_data[['timestamp', 'systolic', 'diastolic']].melt(
        'timestamp', var_name='BP Type', value_name='mmHg'
    )
    
    # Define a custom color scale for the chart
    color_scale = alt.Scale(domain=['systolic', 'diastolic'], range=['#3B82F6', '#10B981']) # Blue for SBP, Green for DBP

    # Create the line chart with enhanced styling
    chart = alt.Chart(chart_data).mark_line(point={
        "filled": True, 
        "size": 60,
        "opacity": 1
    }).encode(
        x=alt.X('timestamp', title='Date & Time', axis=alt.Axis(format="%b %d, %I:%M %p")),
        y=alt.Y('mmHg', scale=alt.Scale(domain=[40, 200]), title='Pressure (mmHg)'),
        color=alt.Color('BP Type', scale=color_scale),
        tooltip=[
            alt.Tooltip('timestamp', title='Time', format="%Y-%m-%d %H:%M"), 
            alt.Tooltip('BP Type'), 
            alt.Tooltip('mmHg')
        ]
    ).properties(
        height=400
    ).interactive(bind_y=False) # Only zoom on X-axis, y-scale is fixed

    st.altair_chart(chart, use_container_width=True)

    # --- Category Distribution ---
    st.subheader("Distribution of Readings by Category")
    
    category_counts = user_data['category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']
    
    # Create a bar chart for distribution
    bar_chart = alt.Chart(category_counts).mark_bar().encode(
        x=alt.X('Count', title='Number of Readings'),
        y=alt.Y('Category', sort='-x'), # Sort by count descending
        color=alt.Color('Category', scale=alt.Scale(range=[get_category_color(c) for c in category_counts['Category'].unique()])),
        tooltip=['Category', 'Count']
    ).properties(
        height=300
    )
    st.altair_chart(bar_chart, use_container_width=True)

    # --- Historical Table ---
    st.subheader("Full Reading History")
    
    # Format data for display
    display_data = user_data.copy()
    display_data['Time'] = display_data['timestamp'].dt.strftime('%Y-%m-%d %I:%M %p')
    display_data = display_data[['Time', 'systolic', 'diastolic', 'pulse', 'category']]
    display_data.columns = ['Date & Time', 'Systolic', 'Diastolic', 'Pulse', 'Category']
    
    st.dataframe(
        display_data.iloc[::-1], 
        use_container_width=True, 
        hide_index=True,
        # Optional: Add formatting to highlight rows based on category if desired
    )


def main():
    """Main application loop."""
    st.set_page_config(
        page_title="Hypertension Tracker",
        page_icon="❤️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for a clean, modern look (using Tailwind-like colors/shadows)
    st.markdown("""
        <style>
        /* Deep Blue Accent: #1D4ED8 (Blue 700) */
        .stButton>button {
            border-radius: 0.75rem; /* More rounded */
            border: 1px solid #1D4ED8;
            color: white;
            background-color: #1D4ED8;
            transition: all 0.3s ease;
            /* Stronger initial shadow */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); 
        }
        .stButton>button:hover {
            background-color: #1e3a8a; /* Slightly darker on hover (Blue 800) */
            border-color: #1e3a8a;
            /* Stronger lift shadow */
            box-shadow: 0 8px 15px -3px rgba(30, 78, 215, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.1); 
            transform: translateY(-1px); /* slight lift */
        }
        h1 {
            color: #1D4ED8; /* Deep Blue for main title */
            border-bottom: 2px solid #E0E7FF;
            padding-bottom: 10px;
        }
        h2 {
            color: #1f2937; /* Darker text for headers (Gray 900) */
        }
        .stAlert {
            border-radius: 0.75rem; /* More rounded alerts */
        }
        /* Style for centered login action radio buttons */
        div[data-testid="stRadio"] > label > div:first-child {
            padding-bottom: 0px !important; 
        }
        /* Enhance the look of the native metric cards (Avg Systolic/Diastolic) */
        div[data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 0.75rem; /* More rounded cards */
            padding: 15px 20px;
            /* Subtle shadow for card depth */
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            transition: all 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            /* Slightly stronger shadow on hover */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06);
        }
        </style>
        """, unsafe_allow_html=True)

    # Application title
    st.title("Blood Pressure Tracker") 
    
    if 'page' not in st.session_state:
        st.session_state['page'] = "Log Reading" # Default starting page
    
    # Handle authentication: Renders centralized login if not logged in, 
    # or sidebar logout button if logged in.
    is_logged_in = handle_auth(is_sidebar=False)

    if is_logged_in:
        # Logged in: show main tracker content
        
        # Filter BP data for the logged-in user
        user_bp_data = bp_df[bp_df['username'] == st.session_state['username']].sort_values(by='timestamp', ascending=True)

        st.sidebar.markdown("---")
        
        # Use st.session_state['page'] for navigation
        page = st.sidebar.radio(
            "Navigation", 
            ["Log Reading", "Insights & History"],
            index=["Log Reading", "Insights & History"].index(st.session_state['page'])
        )
        st.session_state['page'] = page # Update session state

        if st.session_state['page'] == "Log Reading":
            log_reading_page()
            
        elif st.session_state['page'] == "Insights & History":
            insights_page(user_bp_data)

    else:
        # Not logged in: The centralized login form is already displayed by handle_auth(is_sidebar=False)
        st.info("Please log in or sign up above to begin tracking your blood pressure.")

if __name__ == "__main__":
    main()
