# hypertension_app.py
"""
Hypertension Tracker (secure auth + security-question reset).
- File: hypertension_app.py
- Authentication: PBKDF2-HMAC-SHA256 with per-user 16-byte salt and 200k iterations
- Password reset: security question only (hashed + salted answer)
- Storage: local CSV files
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io, os, hashlib, hmac, binascii, secrets

# plotting
import matplotlib.pyplot as plt
import plotly.express as px

# optional PDF export
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# ---------------- CONFIG ----------------
USERS_FILE = "users_credentials.csv"
DATA_FILE = "hypertension_tracker_all_users.csv"
LOGO_PATH = "/mnt/data/Screenshot 2025-11-23 231526.png"  # keep or replace with your local logo path

APP_TITLE = "Hypertension Tracker"
HASH_NAME = "sha256"
ITERATIONS = 200_000
SALT_BYTES = 16

# ---------------- HASH UTILITIES ----------------
def hash_password(password: str, salt: bytes = None):
    """Return (salt_bytes, hash_bytes)."""
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(HASH_NAME, password.encode("utf-8"), salt, ITERATIONS)
    return salt, dk

def verify_password_hex(salt_hex: str, hash_hex: str, provided_password: str) -> bool:
    """Verify provided_password against stored salt_hex + hash_hex."""
    salt = binascii.unhexlify(salt_hex)
    stored_hash = binascii.unhexlify(hash_hex)
    _, new_hash = hash_password(provided_password, salt)
    return hmac.compare_digest(stored_hash, new_hash)

# ---------------- USER STORAGE ----------------
def load_users_df():
    """Load or create users DataFrame with expected columns."""
    cols = [
        "username","salt_hex","hash_hex","email",
        "sec_question","sec_ans_salt_hex","sec_ans_hash_hex"
    ]
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE, dtype=str).fillna("")
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols].copy()
    else:
        return pd.DataFrame(columns=cols)

def save_users_df(df):
    df.to_csv(USERS_FILE, index=False)

def user_exists(username: str) -> bool:
    df = load_users_df()
    return username in df["username"].values

def save_new_user(username: str, password: str, email: str = "", sec_question: str = "", sec_answer: str = ""):
    df = load_users_df()
    salt, pwdhash = hash_password(password)
    salt_hex = binascii.hexlify(salt).decode()
    hash_hex = binascii.hexlify(pwdhash).decode()

    if sec_answer:
        ans_salt, ans_hash = hash_password(sec_answer)
        ans_salt_hex = binascii.hexlify(ans_salt).decode()
        ans_hash_hex = binascii.hexlify(ans_hash).decode()
    else:
        ans_salt_hex = ""
        ans_hash_hex = ""

    new = {
        "username": username,
        "salt_hex": salt_hex,
        "hash_hex": hash_hex,
        "email": email,
        "sec_question": sec_question,
        "sec_ans_salt_hex": ans_salt_hex,
        "sec_ans_hash_hex": ans_hash_hex
    }
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    save_users_df(df)

def get_user_record(username: str):
    df = load_users_df()
    rec = df[df["username"] == username]
    if rec.empty:
        return None
    return rec.iloc[0].to_dict()

def update_user_credentials(username: str, salt_hex: str, hash_hex: str):
    df = load_users_df()
    idx = df.index[df["username"] == username]
    if len(idx) == 0:
        return False
    i = idx[0]
    df.at[i, "salt_hex"] = salt_hex
    df.at[i, "hash_hex"] = hash_hex
    save_users_df(df)
    return True

# ---------------- DATA STORAGE ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
        return df
    return pd.DataFrame(columns=["Username","Date","Systolic","Diastolic","Status"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---------------- HELPERS ----------------
def classify_bp(systolic, diastolic):
    if systolic < 120 and diastolic < 80:
        return "Normal"
    if 120 <= systolic < 130 and diastolic < 80:
        return "Elevated"
    if 130 <= systolic < 140 or 80 <= diastolic < 90:
        return "Stage 1 Hypertension"
    if systolic >= 140 or diastolic >= 90:
        return "Stage 2 Hypertension"
    return "Hypertensive Crisis"

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title=APP_TITLE, layout="centered")
st.title(APP_TITLE)

# Sidebar: authentication actions and navigation
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=120)
    st.markdown("### Account")
    action = st.selectbox("Action", ["Login", "Register", "Reset via security question", "Logout"])
    st.markdown("---")
    page = st.radio("Navigate", ["Home", "Records", "Charts", "Insights", "About"])
    st.markdown("---")
    st.write("Security: passwords are hashed + salted locally.")

# --- AUTH FLOW ---
if action == "Register":
    st.header("Create account")
    r_user = st.text_input("Username (no spaces)", key="reg_user")
    r_email = st.text_input("Email (optional)", key="reg_email")
    r_q = st.text_input("Security question (optional)", key="reg_q", placeholder="e.g., Where were you born?")
    r_ans = st.text_input("Security answer (optional)", key="reg_ans")
    r_pass = st.text_input("Password (min 8 chars)", type="password", key="reg_pass")
    r_pass2 = st.text_input("Confirm password", type="password", key="reg_pass2")
    if st.button("Create account"):
        username_val = (r_user or "").strip()
        if username_val == "" or " " in username_val:
            st.error("Choose a valid username without spaces.")
        elif len(r_pass) < 8:
            st.error("Password must be at least 8 characters.")
        elif r_pass != r_pass2:
            st.error("Passwords do not match.")
        elif user_exists(username_val):
            st.error("Username already exists.")
        else:
            save_new_user(username_val, r_pass, email=(r_email or "").strip(), sec_question=(r_q or "").strip(), sec_answer=(r_ans or "").strip())
            st.success("Account created. Use Login to sign in.")

elif action == "Login":
    st.header("Login")
    l_user = st.text_input("Username", key="login_user")
    l_pass = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        rec = get_user_record((l_user or "").strip())
        if rec is None:
            st.error("User not found.")
        else:
            ok = verify_password_hex(rec["salt_hex"], rec["hash_hex"], l_pass or "")
            if ok:
                st.session_state["username"] = rec["username"]
                st.success(f"Welcome, {rec['username']}.")
            else:
                st.error("Invalid credentials.")

elif action == "Logout":
    if st.button("Logout"):
        if "username" in st.session_state:
            del st.session_state["username"]
        st.success("Logged out.")

elif action == "Reset via security question":
    st.header("Reset password (security question)")
    ru = st.text_input("Username", key="reset_user")
    if ru:
        rec = get_user_record(ru.strip())
        if rec is None:
            st.error("User not found.")
        elif not rec.get("sec_question"):
            st.error("No security question set for this account.")
        else:
            st.info(rec["sec_question"])
            ans = st.text_input("Answer", key="reset_ans")
            newp = st.text_input("New password", type="password", key="reset_newp")
            newp2 = st.text_input("Confirm new password", type="password", key="reset_newp2")
            if st.button("Reset password"):
                if not verify_password_hex(rec["sec_ans_salt_hex"], rec["sec_ans_hash_hex"], ans or ""):
                    st.error("Incorrect security answer.")
                elif newp != newp2 or len(newp) < 8:
                    st.error("Ensure passwords match and are at least 8 characters.")
                else:
                    salt, phash = hash_password(newp)
                    salt_hex = binascii.hexlify(salt).decode()
                    hash_hex = binascii.hexlify(phash).decode()
                    update_user_credentials(rec["username"], salt_hex, hash_hex)
                    st.success("Password reset successful. Login with your new password.")

# require login for pages
if "username" not in st.session_state or not st.session_state["username"]:
    st.info("Please Login (or Register) using the sidebar to use the tracker.")
    st.stop()

username = st.session_state["username"]

# load data
df_all = load_data()
# ensure date column parse
if not df_all.empty and df_all["Date"].dtype == object:
    try:
        df_all["Date"] = pd.to_datetime(df_all["Date"])
    except Exception:
        pass

user_df = df_all[df_all["Username"] == username].copy()
if not user_df.empty:
    user_df = user_df.sort_values("Date")

# --- PAGES ---
if page == "Home":
    st.header("Add New Reading")
    with st.form("add_reading", clear_on_submit=True):
        c1, c2 = st.columns(2)
        systolic = c1.number_input("Systolic (mmHg)", min_value=60, max_value=250, step=1, value=120)
        diastolic = c2.number_input("Diastolic (mmHg)", min_value=40, max_value=150, step=1, value=80)
        submitted = st.form_submit_button("Save Reading")
        if submitted:
            status = classify_bp(int(systolic), int(diastolic))
            new_row = {
                "Username": username,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Systolic": int(systolic),
                "Diastolic": int(diastolic),
                "Status": status
            }
            df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df_all)
            st.success(f"Saved — {status}")

    st.markdown("---")
    st.subheader("Quick Summary")
    if not user_df.empty:
        avg_sys = user_df["Systolic"].astype(float).mean()
        avg_dia = user_df["Diastolic"].astype(float).mean()
        latest = user_df.iloc[-1]
        st.markdown(f"**Latest reading:** {latest['Date']} — {int(latest['Systolic'])}/{int(latest['Diastolic'])} mmHg — **{latest['Status']}**")
        st.metric("Average Systolic", f"{avg_sys:.1f} mmHg")
        st.metric("Average Diastolic", f"{avg_dia:.1f} mmHg")
    else:
        st.info("No readings yet. Add one to get started.")

elif page == "Records":
    st.header("📋 Your BP Records")
    if user_df.empty:
        st.info("No records yet.")
    else:
        st.dataframe(user_df.sort_values("Date", ascending=False), use_container_width=True)

        # Exports
        csv = user_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name=f"{username}_bp_records.csv", mime="text/csv")

        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
            user_df.to_excel(writer, index=False, sheet_name="BP_Records")
            writer.save()
        towrite.seek(0)
        st.download_button("Download Excel (.xlsx)", data=towrite, file_name=f"{username}_bp_records.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if REPORTLAB_AVAILABLE:
            # simple PDF
            def generate_pdf(user_df, username):
                buf = io.BytesIO()
                c = canvas.Canvas(buf, pagesize=letter)
                c.setFont("Helvetica-Bold", 14)
                c.drawString(40, 750, f"BP Report — {username}")
                y = 720
                for _, r in user_df.sort_values("Date", ascending=False).iterrows():
                    c.setFont("Helvetica", 10)
                    c.drawString(40, y, f"{r['Date']} — {int(r['Systolic'])}/{int(r['Diastolic'])} — {r['Status']}")
                    y -= 14
                    if y < 40:
                        c.showPage()
                        y = 750
                c.save()
                buf.seek(0)
                return buf
            pdf_buf = generate_pdf(user_df, username)
            st.download_button("Download PDF", data=pdf_buf, file_name=f"{username}_bp_report.pdf", mime="application/pdf")

elif page == "Charts":
    st.header("📈 Trends & Charts")
    if user_df.empty:
        st.info("No data yet.")
    else:
        user_df["Date"] = pd.to_datetime(user_df["Date"])
        fig = px.line(user_df, x="Date", y=["Systolic", "Diastolic"], labels={"value": "mmHg", "variable": "Measure"}, title="Systolic & Diastolic Over Time")
        st.plotly_chart(fig, use_container_width=True)

elif page == "Insights":
    st.header("🩺 Health Insights")
    if user_df.empty:
        st.info("No readings yet.")
    else:
        latest = user_df.iloc[-1]
        st.markdown(f"**Latest:** {latest['Date']} — {int(latest['Systolic'])}/{int(latest['Diastolic'])} mmHg — **{latest['Status']}**")
        if len(user_df) > 1:
            prev = user_df.iloc[-2]
            sys_delta = int(latest["Systolic"]) - int(prev["Systolic"])
            dia_delta = int(latest["Diastolic"]) - int(prev["Diastolic"])
            st.write(f"Change vs previous: Systolic {sys_delta:+} mmHg, Diastolic {dia_delta:+} mmHg")

        # 7-day average (best-effort)
        try:
            recent_7 = user_df.set_index("Date").last("7D")
        except Exception:
            recent_7 = user_df.tail(7)
        if not recent_7.empty:
            avg7_sys = recent_7["Systolic"].astype(float).mean()
            avg7_dia = recent_7["Diastolic"].astype(float).mean()
            st.write(f"7-day average: {avg7_sys:.1f}/{avg7_dia:.1f} mmHg")
            if avg7_sys >= 140 or avg7_dia >= 90:
                st.warning("7-day average indicates Stage 2 levels. See a clinician.")
            elif avg7_sys >= 130 or avg7_dia >= 80:
                st.info("7-day average in Stage 1 range. Consider lifestyle changes and review with clinician.")
            else:
                st.success("7-day average is within normal/controlled range.")

elif page == "About":
    st.header("About")
    st.markdown(
        """
        Hypertension Tracker — local Streamlit app with secure local authentication.
        - Passwords & security answers are hashed + salted (PBKDF2-HMAC-SHA256).
        - Password reset is only available via the security question set at registration.
        - Data is stored locally as CSV files: users and readings.
        """
    )
    st.code(USERS_FILE)

# --- end of file ---


