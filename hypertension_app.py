"""
Hypertension Tracker — Clean White + Blue redesign
Drop this file into your Streamlit app folder and run: streamlit run app.py
Requirements: streamlit, pandas, altair, plotly
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import hashlib

# ----------------------------
# Helper utilities
# ----------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str, users: dict) -> bool:
    """
    users: dict mapping username -> hashed_password
    """
    return users.get(username) == hash_password(password)

def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "records" not in st.session_state:
        # small sample schema; in production, load from DB/CSV
        st.session_state.records = pd.DataFrame(
            columns=["timestamp", "username", "systolic", "diastolic", "category"]
        )

def save_reading(username, s, d):
    # classifies based on simplified AHA categories
    s = int(s)
    d = int(d)
    if s < 120 and d < 80:
        cat = "Normal"
    elif (120 <= s < 130) and d < 80:
        cat = "Elevated"
    elif (130 <= s < 140) or (80 <= d < 90):
        cat = "Stage 1 Hypertension"
    else:
        cat = "Stage 2 Hypertension"
    record = {
        "timestamp": datetime.now(),
        "username": username,
        "systolic": s,
        "diastolic": d,
        "category": cat,
    }
    st.session_state.records = pd.concat(
        [st.session_state.records, pd.DataFrame([record])],
        ignore_index=True,
    )

# ----------------------------
# Styling (Clean white + blue)
# ----------------------------
st.set_page_config(page_title="Hypertension Tracker", layout="wide", page_icon="🫀")
st.markdown(
    """
    <style>
    /* Page background */
    .reportview-container, .main {
        background-color: #ffffff;
    }
    /* Sidebar */
    .css-1d391kg { padding-top: 1rem; }
    .stSidebar { background-color: #f7fbff; }
    /* Big header */
    .big-title {
        font-size:34px;
        font-weight:700;
        color:#0b3d91;
        margin-bottom: 0;
    }
    .sub-title {
        font-size:18px;
        color:#1f3f7a;
        margin-top: 4px;
        margin-bottom: 24px;
    }
    /* Card */
    .card {
        border:1px solid #e6eef8;
        border-radius:10px;
        padding:18px;
        background: #ffffff;
        box-shadow: 0 1px 6px rgba(16,42,88,0.04);
    }
    /* Buttons */
    .stButton>button {
        background-color:#0b60d1;
        color: white;
        border-radius:8px;
        padding:8px 14px;
        font-weight:600;
    }
    .small-muted {
        color:#6b7280;
        font-size:13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Initialize
# ----------------------------
init_session_state()

# ----------------------------
# Credentials - use st.secrets in production!
# For demo, create default user stored in code (please move to secrets)
# ----------------------------
# Use st.secrets["users"] in production. Example secrets.toml:
# [users]
# admin = "sha256-hash-here"
default_users = {
    # username: hashed_password  (change these; use st.secrets for production)
    "admin": hash_password("adminpassword"),
}

# If the app is deployed to Streamlit Cloud, add production users to st.secrets["users"]
if "users" in st.secrets:
    # expect st.secrets["users"] to be dict username -> plain-text password
    users = {
        u: hash_password(p)
        for u, p in st.secrets["users"].items()
    }
else:
    users = default_users

# ----------------------------
# Sidebar - navigation & account
# ----------------------------
with st.sidebar:
    st.markdown("## Account")
    action = st.selectbox("Action", options=["Login", "Logout", "Create sample data"])
    st.markdown("---")
    st.markdown("## Navigate")
    nav = st.radio("", options=["Home", "Records", "Charts", "Insights", "About"])
    st.markdown("---")
    st.markdown('<div class="small-muted">Security note: store production credentials in <code>st.secrets</code>.</div>', unsafe_allow_html=True)

# Sidebar actions
if action == "Logout":
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "login"

if action == "Create sample data":
    # create a few sample readings for visual testing (only if empty)
    if st.session_state.records.empty:
        sample = pd.DataFrame([
            {"timestamp": datetime.now(), "username": "admin", "systolic": 118, "diastolic": 76, "category": "Normal"},
            {"timestamp": datetime.now(), "username": "admin", "systolic": 132, "diastolic": 84, "category": "Stage 1 Hypertension"},
            {"timestamp": datetime.now(), "username": "admin", "systolic": 140, "diastolic": 92, "category": "Stage 2 Hypertension"},
        ])
        st.session_state.records = pd.concat([st.session_state.records, sample], ignore_index=True)
        st.success("Sample records added. Use 'Logout' to reset.")

# Map radio nav to page
st.session_state.page = nav.lower()

# ----------------------------
# Pages
# ----------------------------
def page_login():
    st.markdown('<div class="big-title">Hypertension Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Secure tracking · Understand trends · Improve outcomes</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.empty()  # left space
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Login")
        username = st.text_input("Username", value="", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        if st.button("Login"):
            if check_credentials(username.strip(), password.strip(), users):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.success(f"Welcome, {st.session_state.username}.")
                # change page to home after login
                st.session_state.page = "home"
                st.experimental_rerun()
            else:
                st.error("Invalid credentials. For production, add users to `st.secrets['users']`.")
        st.markdown('</div>', unsafe_allow_html=True)

def page_home():
    st.markdown('<div class="big-title">Hypertension Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Quickly add readings and see trends</div>', unsafe_allow_html=True)

    # Welcome / Banner
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"**Welcome, {st.session_state.username or 'User'}.**")
    st.markdown("Use the form below to add a new blood pressure reading. Fields start empty to avoid accidental submissions.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")

    # Add reading card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Add New Reading")
    with st.form("add_reading", clear_on_submit=False):
        c1, c2, c3 = st.columns([1, 1, 0.6])
        with c1:
            sys_txt = st.text_input("Systolic (mmHg)", key="systolic_input", placeholder="e.g., 120")
        with c2:
            dia_txt = st.text_input("Diastolic (mmHg)", key="diastolic_input", placeholder="e.g., 80")
        with c3:
            st.write("")  # spacing
            st.write("")
        submitted = st.form_submit_button("Save Reading")
        if submitted:
            # Validations
            if not st.session_state.logged_in:
                st.error("Please login before saving a reading.")
            else:
                if sys_txt.strip() == "" or dia_txt.strip() == "":
                    st.error("Both systolic and diastolic are required.")
                else:
                    try:
                        s_val = int(float(sys_txt))
                        d_val = int(float(dia_txt))
                        if s_val <= 0 or d_val <= 0:
                            raise ValueError
                        save_reading(st.session_state.username, s_val, d_val)
                        st.success(f"Saved: {s_val}/{d_val} mmHg.")
                        # clear inputs
                        st.session_state["systolic_input"] = ""
                        st.session_state["diastolic_input"] = ""
                        st.experimental_rerun()
                    except ValueError:
                        st.error("Enter valid numeric values for systolic and diastolic.")

    st.markdown("</div>", unsafe_allow_html=True)

    # Quick Summary (last 5)
    st.write("")
    st.subheader("Quick Summary")
    recent = st.session_state.records[st.session_state.records["username"] == st.session_state.username].sort_values(by="timestamp", ascending=False).head(5)
    if recent.empty:
        st.info("No readings yet. Add your first reading above.")
    else:
        # show table
        df_display = recent.copy()
        df_display["timestamp"] = pd.to_datetime(df_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        st.table(df_display[["timestamp", "systolic", "diastolic", "category"]].reset_index(drop=True))

def page_records():
    st.header("Records")
    user_records = st.session_state.records
    if st.session_state.username:
        user_records = user_records[user_records["username"] == st.session_state.username]
    if user_records.empty:
        st.info("No records to show.")
        return
    user_records = user_records.sort_values(by="timestamp", ascending=False)
    # Filters
    col1, col2 = st.columns([2, 1])
    with col1:
        date_from = st.date_input("From", value=None)
        date_to = st.date_input("To", value=None)
    with col2:
        if st.button("Delete all my records"):
            st.session_state.records = st.session_state.records[st.session_state.records["username"] != st.session_state.username]
            st.success("Deleted your records.")
            st.experimental_rerun()
    st.dataframe(user_records.reset_index(drop=True))

def page_charts():
    st.header("Charts")
    df = st.session_state.records.copy()
    if df.empty:
        st.info("No data to plot. Add readings on the Home page.")
        return
    # filter to current user
    if st.session_state.username:
        df = df[df["username"] == st.session_state.username]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    base = alt.Chart(df).encode(x=alt.X("timestamp:T", title="Date"))
    line = base.mark_line(point=True).encode(
        y=alt.Y("systolic:Q", title="Systolic (mmHg)"),
        tooltip=["timestamp:T", "systolic", "diastolic", "category"]
    ).properties(width=800, height=300)
    line2 = base.mark_line(point=True, color="#0b60d1").encode(
        y=alt.Y("diastolic:Q", title="Diastolic (mmHg)"),
        tooltip=["timestamp:T", "systolic", "diastolic", "category"]
    )
    st.altair_chart(line + line2, use_container_width=True)

    # Category distribution
    cat = df.groupby("category").size().reset_index(name="count")
    chart = alt.Chart(cat).mark_bar().encode(
        x="category:N",
        y="count:Q",
        color=alt.Color("category:N", legend=None)
    ).properties(width=600, height=250)
    st.altair_chart(chart, use_container_width=False)

def page_insights():
    st.header("Insights")
    df = st.session_state.records.copy()
    if df.empty:
        st.info("No data yet.")
        return
    if st.session_state.username:
        df = df[df["username"] == st.session_state.username]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    last_30_days = df[df["timestamp"] >= (datetime.now() - pd.Timedelta(days=30))]
    st.metric("Readings (30d)", last_30_days.shape[0])
    if not last_30_days.empty:
        avg_sys = int(last_30_days["systolic"].mean())
        avg_dia = int(last_30_days["diastolic"].mean())
        st.metric("Avg BP (30d)", f"{avg_sys}/{avg_dia} mmHg")
    st.write("")
    st.write("Top categories in your data:")
    st.write(df["category"].value_counts())

def page_about():
    st.header("About")
    st.markdown(
        """
        **Hypertension Tracker**
        
        A small, clean tool to log blood pressure readings, classify them, and surface trends.
        
        Built with a clean White + Blue hospital-inspired UI for clear readability.
        
        **Notes**
        - For production: move authentication to st.secrets or a proper user database.
        - Persist records to an external DB (SQLite/Postgres) or to a CSV in cloud storage.
        """
    )

# ----------------------------
# Router
# ----------------------------
page = st.session_state.page

if page == "login":
    page_login()
elif page == "home":
    if not st.session_state.logged_in:
        st.warning("Please login first.")
        page_login()
    else:
        page_home()
elif page == "records":
    if not st.session_state.logged_in:
        st.warning("Please login first.")
        page_login()
    else:
        page_records()
elif page == "charts":
    if not st.session_state.logged_in:
        st.warning("Please login first.")
        page_login()
    else:
        page_charts()
elif page == "insights":
    if not st.session_state.logged_in:
        st.warning("Please login first.")
        page_login()
    else:
        page_insights()
elif page == "about":
    page_about()
else:
    st.write("Page not found.")
