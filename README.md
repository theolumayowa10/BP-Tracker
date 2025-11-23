# BP-Tracker
Blood Pressure Tracker (Streamlit Web App)

A simple, secure blood pressure tracker built with **Python + Streamlit**.  
Users can create accounts, log in, record blood pressure readings, monitor trends, and download their records.

---

## 🚀 Features

### 🔐 Authentication
- User registration  
- Secure login  
- Password hashing (PBKDF2-HMAC-SHA256)  
- Password reset via security question  

### 📊 Blood Pressure Tracking
- Add readings (Systolic, Diastolic)  
- Automatic hypertension classification  
- View records in table format  
- Download CSV / Excel / PDF  

### 📈 Data Visualization
- Line charts for BP trends  
- Systolic & Diastolic comparison  
- Health insights  

---

## 📦 Installation (Local)

```bash
git clone https://github.com/theolumayowa10/BP-Tracker
cd BP-Tracker
pip install -r requirements.txt
streamlit run hypertension_app.py
