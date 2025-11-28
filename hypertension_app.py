"""
Hypertension Tracker — Clean White + Blue with local JSON users + security-question reset

Usage:
    pip install streamlit pandas altair
    streamlit run app.py

Files created/used:
    - users.json     : stores registered users (hashed)
    - records.json   : stores BP readings
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, Any

# -------------------------
# Configuration / Constants
# -------------------------
USERS_FILE = Path("users.json")
RECORDS_FILE = Path("records.json")

SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What is your favourite food?",
    "What city were you born in?",
    "What was your childhood nickname?"
]

# -------------------------
# Utility functions
# -------------------------
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    else:
        return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_users() -> Dict[str, Dict[str, Any]]:
    """Return dict: username -> {password: <hash>, qid: <int>, answer: <hash> }"""
    return load_json(USERS_FILE, {})

def save_users(users: Dict[str, Dict[str, Any]]):
    save_json(USERS_FILE, users)

def load_records() -> pd.DataFrame:
    data = load_json(RECORDS_FILE, [])
    if not data:
        return pd.DataFrame(columns=["timestamp", "username", "systolic", "diastolic", "category"])
    df = pd.DataFrame(data)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

def save_records(df: pd.DataFrame):
    df_to_save = df.copy()
    # convert timestamps to ISO
    if "timestamp" in df_to_save.columns:
        df_to_save["timestamp"] = df_to_save["timestamp"].apply(lambda x: pd.to_datetime(x).isoformat())
    save_json(RECORDS_FILE, df_to_save.to_dict(orient="records"))

def classify_bp(s: int, d: int) -> str:
    # Simplified AHA categories
    if s < 120 and d < 80:
        return "Normal"
    if 120 <= s < 130 and d < 80:
        return "Elevated"
    if (130 <= s < 140) or (80 <= d < 90):
        return "Stage 1 Hypertension"
    return "Stage 2 Hypertension"

# -------------------------
# Session state initialization
# -------------------------
def init_session():
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "users" not in st.session_state:
        st.session_state.users = load_users()
    if "records" not in st.session_state:
        st.session_state.records = load_records()

init_session()

# -------------------------
# Styling: Clean White + Blue
# -------------------------
st.set_page_config(page_title="Hypertension Tracker", layout="wide", page_icon="🫀")

st.markdown(
    """
    <style>
    /* Background & font */
    .reportview-container, .main {
        background-color: #ffffff;
    }
    /* Sidebar */
    .stSidebar {
        background-color: #f5f9ff;
    }
    /* Titles */
    .big-title {
        font-size:32px;
        font-weight:700;
        color:#0b3d91;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size:15px;
        color:#1f3f7a;
        margin-top: 0px;
        margin-bottom: 18px;
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
    .stTextInput>div>input, .stNumberInput>div>input {
        border-radius:8px;
        padding:10px;
    }
    .small-muted {
        color:#6b7280;
        font-size:13px;
    }
    </style>
    """, unsafe_allow_html=True
)

# -------------------------
# Sidebar (Navigation + Account)
# -------------------------
with st.sidebar:
    st.markdown("## Account")
    account_action = st.selectbox("Action", options=["Login", "Sign up", "Forgot password", "Logout"])
    st.markdown("---")
    st.markdown("## Navigate")
    nav = st.radio("", options=["Home", "Add Reading", "Records", "Charts", "Insights", "About"])
    st.markdown("---")
    st.markdown('<div class="small-muted">Security: passwords & answers are hashed locally. For production use a DB.</div>', unsafe_allow_html=True)

# Handle Logout action early
if account_action == "Logout":
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "home"
    # continue to show home (no message)

# Map navigation to page
st.session_state.page = nav.lower().replace(" ", "_")

# -------------------------
# Auth pages: Sign up / Login / Forgot
# -------------------------
def signup_ui():
    st.markdown('<div class="big-title">Create account</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Register to store your readings and see personalized insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("signup_form"):
        uname = st.text_input("Choose a username", value="", placeholder="e.g., mayowa")
        pwd = st.text_input("Password", type="password", placeholder="Create a secure password")
        pwd2 = st.text_input("Confirm password", type="password", placeholder="Repeat the password")
        qid = st.selectbox("Security question", options=list(range(len(SECURITY_QUESTIONS))), format_func=lambda i: SECURITY_QUESTIONS[i])
        ans = st.text_input("Answer to security question", placeholder="Type an answer you'll remember")
        submitted = st.form_submit_button("Create account")
        if submitted:
            users = st.session_state.users
            if not uname or not pwd or not pwd2 or not ans:
                st.error("All fields are required.")
            elif uname in users:
                st.error("Username already exists. Choose a different username.")
            elif pwd != pwd2:
                st.error("Passwords do not match.")
            else:
                users[uname] = {
                    "password": sha256(pwd),
                    "qid": int(qid),
                    "answer": sha256(ans.strip().lower())
                }
                save_users(users)
                st.session_state.users = users
                st.success("Account created. You can now log in.")
                st.session_state.page = "add_reading"
                st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def login_ui():
    st.markdown('<div class="big-title">Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Access your readings and insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("login_form"):
        uname = st.text_input("Username", value="", placeholder="Enter your username")
        pwd = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login")
        if submitted:
            users = st.session_state.users
            if uname not in users or users[uname]["password"] != sha256(pwd):
                st.error("Invalid username or password.")
            else:
                st.session_state.logged_in = True
                st.session_state.username = uname
                st.success(f"Welcome, {uname}.")
                # Move user to Add Reading after login
                st.session_state.page = "add_reading"
                st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def forgot_ui():
    st.markdown('<div class="big-title">Reset password</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Reset using your security question</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("forgot_form"):
        uname = st.text_input("Username", value="", placeholder="Enter your username")
        if uname and uname in st.session_state.users:
            qid = st.session_state.users[uname]["qid"]
            st.markdown(f"**Security question:** {SECURITY_QUESTIONS[qid]}")
            ans = st.text_input("Answer to security question", placeholder="Type your answer")
            new_pwd = st.text_input("New password", type="password", placeholder="Enter a new password")
            new_pwd2 = st.text_input("Confirm new password", type="password", placeholder="Repeat new password")
        else:
            # show unpopulated fields but disable until valid username entered
            st.info("Enter your username above to see your security question.")
            ans = ""
            new_pwd = ""
            new_pwd2 = ""
        submitted = st.form_submit_button("Reset password")
        if submitted:
            users = st.session_state.users
            if uname not in users:
                st.error("Username not found.")
            else:
                if not ans or not new_pwd or not new_pwd2:
                    st.error("All fields are required.")
                elif new_pwd != new_pwd2:
                    st.error("Passwords do not match.")
                elif users[uname]["answer"] != sha256(ans.strip().lower()):
                    st.error("Incorrect answer to security question.")
                else:
                    users[uname]["password"] = sha256(new_pwd)
                    save_users(users)
                    st.session_state.users = users
                    st.success("Password reset successful. Please login with your new password.")
                    st.session_state.page = "home"
                    st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Main page components
# -------------------------
def header():
    st.markdown('<div class="big-title">Hypertension Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Simple logs · Clear trends · Better awareness</div>', unsafe_allow_html=True)

def add_reading_ui():
    header()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Add New Reading")
    with st.form("reading_form"):
        col1, col2, col3 = st.columns([1,1,0.6])
        with col1:
            systolic = st.text_input("Systolic (mmHg)", value="", placeholder="e.g., 120", key="systolic")
        with col2:
            diastolic = st.text_input("Diastolic (mmHg)", value="", placeholder="e.g., 80", key="diastolic")
        with col3:
            st.write("")  # empty for spacing
        submit = st.form_submit_button("Save reading")
        if submit:
            if not st.session_state.logged_in:
                st.error("Please login to save readings.")
            else:
                if not systolic.strip() or not diastolic.strip():
                    st.error("Systolic and diastolic are required.")
                else:
                    try:
                        s_val = int(float(systolic))
                        d_val = int(float(diastolic))
                        if s_val <= 0 or d_val <= 0:
                            raise ValueError
                        category = classify_bp(s_val, d_val)
                        # append to records
                        df = st.session_state.records.copy()
                        new = {
                            "timestamp": datetime.now(),
                            "username": st.session_state.username,
                            "systolic": s_val,
                            "diastolic": d_val,
                            "category": category
                        }
                        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                        st.session_state.records = df
                        save_records(df)
                        st.success(f"Saved {s_val}/{d_val} mmHg — {category}.")
                        # clear inputs
                        st.session_state["systolic"] = ""
                        st.session_state["diastolic"] = ""
                        st.experimental_rerun()
                    except ValueError:
                        st.error("Enter valid numeric values for BP (e.g., 120).")
    st.markdown('</div>', unsafe_allow_html=True)

    # Quick summary
    st.write("")
    st.subheader("Quick summary (latest 5 readings)")
    df_user = st.session_state.records
    if st.session_state.username:
        df_user = df_user[df_user["username"] == st.session_state.username]
    if df_user.empty:
        st.info("No readings yet. Add your first reading above.")
    else:
        df_show = df_user.sort_values("timestamp", ascending=False).head(5).copy()
        df_show["timestamp"] = pd.to_datetime(df_show["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        st.table(df_show[["timestamp", "systolic", "diastolic", "category"]].reset_index(drop=True))

def records_ui():
    st.header("Records")
    df = st.session_state.records.copy()
    if st.session_state.username:
        df = df[df["username"] == st.session_state.username]
    if df.empty:
        st.info("No records to show.")
        return
    df = df.sort_values("timestamp", ascending=False)
    st.dataframe(df.reset_index(drop=True))

def charts_ui():
    st.header("Charts")
    df = st.session_state.records.copy()
    if st.session_state.username:
        df = df[df["username"] == st.session_state.username]
    if df.empty:
        st.info("No data to plot.")
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    base = alt.Chart(df).encode(x=alt.X("timestamp:T", title="Date"))
    line_s = base.mark_line(point=True).encode(
        y=alt.Y("systolic:Q", title="Systolic (mmHg)"),
        tooltip=["timestamp:T", "systolic", "diastolic", "category"]
    )
    line_d = base.mark_line(point=True, color="#0b60d1").encode(
        y=alt.Y("diastolic:Q", title="Diastolic (mmHg)"),
        tooltip=["timestamp:T", "systolic", "diastolic", "category"]
    )
    st.altair_chart(line_s + line_d, use_container_width=True)

    cat = df.groupby("category").size().reset_index(name="count")
    bar = alt.Chart(cat).mark_bar().encode(x="category:N", y="count:Q", color="category:N")
    st.altair_chart(bar, use_container_width=True)

def insights_ui():
    st.header("Insights")
    df = st.session_state.records.copy()
    if st.session_state.username:
        df = df[df["username"] == st.session_state.username]
    if df.empty:
        st.info("No insights yet.")
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    last30 = df[df["timestamp"] >= (datetime.now() - pd.Timedelta(days=30))]
    st.metric("Readings (30d)", last30.shape[0])
    if not last30.empty:
        avg_s = int(last30["systolic"].mean())
        avg_d = int(last30["diastolic"].mean())
        st.metric("Avg BP (30d)", f"{avg_s}/{avg_d} mmHg")
    st.write("Category distribution:")
    st.write(df["category"].value_counts())

def about_ui():
    st.header("About")
    st.markdown(
        """
        **Hypertension Tracker** – minimal, clean tool to log blood pressure readings and view trends.
        
        **Notes**
        - Users and readings are stored locally in `users.json` and `records.json`.
        - For production durability use a database (SQLite/Postgres) and secure secrets.
        - Passwords and security answers are hashed locally (SHA-256).
        """
    )

# -------------------------
# Router & account action handling
# -------------------------
# If user selected account actions from sidebar, prioritize rendering that flow
if account_action == "Sign up":
    signup_ui()
elif account_action == "Login":
    login_ui()
elif account_action == "Forgot password":
    forgot_ui()
else:
    # Normal navigation-based pages
    page = st.session_state.page
    if page == "home":
        header()
        if st.session_state.logged_in:
            st.success(f"Welcome back, {st.session_state.username}.")
        else:
            st.info("Sign up or log in to save readings and view personalized insights.")
    elif page == "add_reading":
        add_reading_ui()
    elif page == "records":
        if not st.session_state.logged_in:
            st.warning("Please login to view your records.")
        else:
            records_ui()
    elif page == "charts":
        if not st.session_state.logged_in:
            st.warning("Please login to view charts.")
        else:
            charts_ui()
    elif page == "insights":
        if not st.session_state.logged_in:
            st.warning("Please login to view insights.")
        else:
            insights_ui()
    elif page == "about":
        about_ui()
    else:
        st.write("Page not found.")

# -------------------------
# End of app
# -------------------------
