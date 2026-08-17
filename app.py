import os
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import random
import sys
import time
from io import BytesIO

# PIL (Pillow) exception handling for Render deployment stability
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from flask import Flask, request, redirect, url_for, session, render_template_string, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "imana_free_interest_microfinance_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

NOTIFICATIONS = []

# --- NEON.TECH / POSTGRESQL DATABASE CONNECTION ---
DEFAULT_DB_URL = 'postgresql://neondb_owner:PAASWORDII_SIRRII_KANAAN_BAKKA_BUUSAA@ep-cool-sample-a5xyz.us-east-2.aws.neon.tech/neondb?sslmode=require'
DATABASE_URL = os.environ.get('DATABASE_URL', DEFAULT_DB_URL)

def get_db_connection(max_retries=5, delay=0.5):
    """Establishes connection to Neon.tech PostgreSQL database with retry logic"""
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise e

# --- IMAGE COMPRESSION FOR ULTRA-FAST PERFORMANCE ---
def compress_and_save_image(file_storage, target_filename, max_size=(300, 300), quality=40):
    """Aggressively compresses images for instant customer registration speed"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], target_filename)
    filename = file_storage.filename.lower()
    
    if filename.endswith('.pdf') or not HAS_PIL:
        file_storage.save(filepath)
        return target_filename

    try:
        image = Image.open(file_storage)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        image.save(filepath, "JPEG", optimize=True, quality=quality)
        return target_filename
    except Exception as e:
        print(f"Image compression error: {e}")
        file_storage.save(filepath)
        return target_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_commission(amount):
    if 1000 <= amount < 3000:
        return 50.0
    elif 3000 <= amount < 5000:
        return 100.0
    elif 7000 <= amount < 10000:
        return 200.0
    elif 10000 <= amount <= 20000:
        return 400.0
    return 0.0

def send_sms_alert(phone_number, message):
    print(f"📱 [SMS SENT TO {phone_number}]: {message}")

def add_notification(message):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    NOTIFICATIONS.insert(0, f"[{now}] {message}")
    if len(NOTIFICATIONS) > 20:
        NOTIFICATIONS.pop()

# --- DATABASE SETUP ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(100) PRIMARY KEY,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'ACTIVE'
        );
    """)

    cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
    row = cursor.fetchone()
    if row['cnt'] == 0:
        default_users = [
            ('ceo', 'ceo999', 'CEO', 'ACTIVE'),
            ('manager1', 'manager123', 'MANAGER', 'ACTIVE'),
            ('maker1', 'maker123', 'MAKER', 'ACTIVE'),
            ('auditor1', 'auditor123', 'AUDITOR', 'ACTIVE'),
            ('officer1', 'officer123', 'LOAN_OFFICER', 'ACTIVE')
        ]
        for u in default_users:
            cursor.execute("INSERT INTO users (username, password, role, status) VALUES (%s, %s, %s, %s);", u)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id VARCHAR(100) PRIMARY KEY,
            full_name VARCHAR(255),
            phone VARCHAR(100),
            gender VARCHAR(50) DEFAULT 'Dhiira',
            account_type VARCHAR(50) DEFAULT 'WADIA',
            photo_path TEXT,
            signature_path TEXT,
            national_id_path TEXT DEFAULT '',
            balance NUMERIC DEFAULT 0.0,
            status VARCHAR(50) DEFAULT 'PENDING_APPROVAL',
            freeze_status VARCHAR(50) DEFAULT 'UNFROZEN',
            freeze_reason TEXT DEFAULT '',
            created_at VARCHAR(100)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id VARCHAR(100) PRIMARY KEY,
            txn_type VARCHAR(50),
            customer_id VARCHAR(100),
            customer_name VARCHAR(255),
            target_account VARCHAR(100),
            amount NUMERIC,
            commission NUMERIC DEFAULT 0.0,
            bank_name VARCHAR(255),
            ft_reference VARCHAR(100),
            status VARCHAR(50) DEFAULT 'PENDING_MANAGER',
            created_by VARCHAR(100),
            timestamp VARCHAR(100),
            audited_status VARCHAR(50) DEFAULT 'OPEN'
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reversals (
            reversal_id VARCHAR(100) PRIMARY KEY,
            txn_id VARCHAR(100) NOT NULL,
            reason TEXT NOT NULL,
            requested_by VARCHAR(100) NOT NULL,
            manager_approved INT DEFAULT 0,
            ceo_approved INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'PENDING_APPROVAL',
            timestamp VARCHAR(100)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS islamic_financing (
            loan_id VARCHAR(100) PRIMARY KEY,
            customer_id VARCHAR(100) NOT NULL,
            customer_name VARCHAR(255),
            financing_type VARCHAR(50) NOT NULL,
            principal_amount NUMERIC NOT NULL,
            profit_margin NUMERIC DEFAULT 0.0,
            total_repayment NUMERIC NOT NULL,
            tenure_months INT,
            monthly_installment NUMERIC,
            status VARCHAR(50) DEFAULT 'PENDING_MANAGER',
            manager_approved INT DEFAULT 0,
            ceo_approved INT DEFAULT 0,
            agent_notes TEXT,
            created_by VARCHAR(100),
            timestamp VARCHAR(100)
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

init_db()

def get_bank_capital():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(amount) AS val FROM transactions WHERE status='APPROVED' AND txn_type='DEPOSIT';")
    res = cursor.fetchone()
    total_deposit = float(res['val']) if res and res['val'] is not None else 0.0
    
    cursor.execute("SELECT SUM(amount) AS val FROM transactions WHERE status='APPROVED' AND txn_type IN ('WITHDRAWAL', 'T24_TRANSFER');")
    res = cursor.fetchone()
    total_withdraw = float(res['val']) if res and res['val'] is not None else 0.0
    
    cursor.execute("SELECT SUM(balance) AS val FROM customers WHERE status='ACTIVE';")
    res = cursor.fetchone()
    total_cust_balance = float(res['val']) if res and res['val'] is not None else 0.0

    cursor.execute("SELECT SUM(commission) AS val FROM transactions WHERE status='APPROVED';")
    res = cursor.fetchone()
    total_commission = float(res['val']) if res and res['val'] is not None else 0.0

    cursor.execute("SELECT SUM(balance) AS val FROM customers WHERE status='ACTIVE' AND account_type='MUDARABA';")
    res = cursor.fetchone()
    total_mudaraba_deposits = float(res['val']) if res and res['val'] is not None else 0.0

    mudaraba_gross_profit = total_mudaraba_deposits * 0.10
    mudaraba_ceo_share = mudaraba_gross_profit * 0.50
    mudaraba_customer_share = mudaraba_gross_profit * 0.50
    
    net_capital = total_deposit - total_withdraw + total_commission
    cursor.close()
    conn.close()
    return max(0.0, net_capital), total_deposit, total_withdraw, total_cust_balance, total_commission, total_mudaraba_deposits, mudaraba_gross_profit, mudaraba_ceo_share, mudaraba_customer_share

# --- API FOR MAKER ACCOUNT & DETAILS VERIFICATION ---
@app.route('/api/verify_account/<cust_id>')
def api_verify_account(cust_id):
    if 'role' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, freeze_status, status, photo_path, signature_path, balance, phone, account_type FROM customers WHERE customer_id = %s;", (cust_id,))
    cust = cursor.fetchone()
    cursor.close()
    conn.close()

    if cust:
        if cust['freeze_status'] == 'FROZEN':
            return jsonify({"success": False, "message": f"🔒 Account ID: {cust_id} ({cust['full_name']}) UGGURAMEERA!"})
        return jsonify({
            "success": True, 
            "full_name": cust['full_name'], 
            "status": cust['status'],
            "balance": float(cust['balance']),
            "phone": cust['phone'],
            "account_type": cust['account_type'],
            "photo_path": cust['photo_path'],
            "signature_path": cust['signature_path']
        })
    return jsonify({"success": False, "message": "❌ Account ID kanaa hin argamne!"})

# --- UI TEMPLATE ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="om">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Imana Free Interest Microfinance</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f8fafc; padding-bottom: 75px; color: #0f172a; }
        nav { background: linear-gradient(135deg, #065f46, #047857); color: white; padding: 12px 16px; position: sticky; top: 0; z-index: 50; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .logo-container { display: flex; align-items: center; gap: 10px; }
        .logo-svg { width: 32px; height: 32px; fill: #fbbf24; }
        nav h1 { font-size: 15px; font-weight: 800; letter-spacing: 0.3px; color: #ffffff; }
        .role-badge { background: #0284c7; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }
        .container { max-width: 600px; margin: 0 auto; padding: 16px; }
        
        .notification-bar { background: #fef3c7; color: #92400e; padding: 8px 12px; border-radius: 8px; font-size: 11px; margin-bottom: 12px; font-weight: bold; border: 1px solid #fde68a; }

        .card-net { background: linear-gradient(135deg, #064e3b, #047857); color: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 15px -3px rgba(6,78,59,0.3); margin-bottom: 20px; }
        .card-ceo-profit { background: linear-gradient(135deg, #4c1d95, #6b21a8); color: white; border-radius: 16px; padding: 20px; box-shadow: 0 10px 15px -3px rgba(76,29,149,0.3); margin-bottom: 20px; }
        .net-title { font-size: 12px; opacity: 0.9; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
        .net-amount { font-size: 32px; font-weight: 800; color: #fbbf24; }
        .net-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; pt: 12px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; }
        
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .btn-card { background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; align-items: center; text-decoration: none; color: #334155; font-weight: bold; font-size: 13px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: 0.2s; }
        .btn-card:active { transform: scale(0.98); }
        .btn-card span.icon { font-size: 24px; margin-bottom: 8px; }
        .btn-card-ceo { background: #faf5ff; border-color: #e9d5ff; color: #581c87; }
        .btn-card-auditor { background: #fff7ed; border-color: #ffedd5; color: #c2410c; }
        .btn-card-loan { background: #f0fdf4; border-color: #bbf7d0; color: #15803d; }
        
        .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-around; padding: 10px 0; z-index: 50; }
        .bottom-nav a { text-align: center; color: #64748b; text-decoration: none; font-size: 11px; flex: 1; font-weight: 500; }
        .bottom-nav a span.icon { display: block; font-size: 18px; margin-bottom: 2px; }
        
        .box { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 16px; }
        .form-group { margin-bottom: 12px; position: relative; }
        .form-group label { display: block; font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 4px; }
        .input-field { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; outline: none; }
        .btn-submit { width: 100%; background: #047857; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; cursor: pointer; }
        
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; display: inline-block; }
        .badge-pending { background: #fef3c7; color: #92400e; }
        .badge-active { background: #dcfce7; color: #166534; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-frozen { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
        .badge-mudaraba { background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; }
        .badge-wadia { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        
        .item-card { background: white; border-radius: 12px; padding: 14px; margin-bottom: 12px; border: 1px solid #e2e8f0; }
        .img-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 10px 0; }
        .img-grid img { width: 100%; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0; loading: lazy; }
        
        .btn-action { padding: 6px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block; border:none; cursor:pointer; }
        .btn-blue { background: #2563eb; }
        .btn-green { background: #16a34a; }
        .btn-red { background: #dc2626; }
        .btn-orange { background: #ea580c; }
        .btn-purple { background: #7c3aed; }
        
        .pwd-toggle { position: absolute; right: 10px; top: 32px; cursor: pointer; user-select: none; font-size: 14px; }
        
        .modal { display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); align-items: center; justify-content: center; }
        .modal-content { background: white; padding: 20px; border-radius: 12px; max-width: 450px; width: 90%; max-height: 85vh; overflow-y: auto; }
        
        @media print {
            .bottom-nav, nav, .btn-print, .no-print { display: none !important; }
            body { padding-bottom: 0; background: white; }
            .box { border: none; box-shadow: none; }
        }
    </style>
</head>
<body>
    <nav class="no-print">
        <div class="logo-container">
            <svg class="logo-svg" viewBox="0 0 24 24">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <h1>Imana Free Interest Microfinance</h1>
        </div>
        {% if session.get('role') %}
            <div style="font-size:12px;">
                <span style="margin-right:4px;"><b>{{ session['username'] }}</b></span>
                <span class="role-badge">{{ session['role'] }}</span>
                <a href="/logout" style="color: #fca5a5; margin-left:8px; text-decoration:none;">Logout</a>
            </div>
        {% endif %}
    </nav>

    <div class="container">
        {% if notifications %}
            <div class="notification-bar no-print">
                🔔 NOTIFICATION: {{ notifications[0] }}
            </div>
        {% endif %}
        {% block content %}{% endblock %}
    </div>

    {% if session.get('role') %}
    <div class="bottom-nav no-print">
        <a href="/"><span class="icon">🏠</span>Dashboard</a>
        {% if session['role'] == 'MAKER' %}
            <a href="/register"><span class="icon">👤</span>Galmee</a>
            <a href="/transaction"><span class="icon">💸</span>Kaffaltii</a>
            <a href="/maker_receipts"><span class="icon">🧾</span>Nagahee</a>
        {% endif %}
        {% if session['role'] == 'MANAGER' %}
            <a href="/pending"><span class="icon">📋</span>Manager Appr</a>
            <a href="/reversals_list"><span class="icon">🔄</span>Reversals</a>
        {% endif %}
        {% if session['role'] == 'AUDITOR' %}
            <a href="/pending"><span class="icon">📋</span>Auditor View</a>
            <a href="/auditor_reversal_request"><span class="icon">⚠️</span>Reversal Gaafachu</a>
        {% endif %}
        {% if session['role'] in ['LOAN_OFFICER', 'CEO', 'MANAGER'] %}
            <a href="/islamic_loan"><span class="icon">📜</span>Liqaa Islaamaa</a>
        {% endif %}
        {% if session['role'] == 'CEO' %}
            <a href="/reversals_list" style="color: #581c87;"><span class="icon">🔄</span>Reversal CEO</a>
            <a href="/ceo_mudaraba_list" style="color: #581c87;"><span class="icon">🤝</span>Mudaraba List</a>
            <a href="/manage_users" style="color: #6b21a8;"><span class="icon">⚙️</span>Hojjattoota</a>
        {% endif %}
    </div>
    {% endif %}

    <script>
    function togglePasswordVisibility(inputId, toggleIconId) {
        var input = document.getElementById(inputId);
        var icon = document.getElementById(toggleIconId);
        if (input.type === "password") {
            input.type = "text";
            icon.textContent = "🙈";
        } else {
            input.type = "password";
            icon.textContent = "👁️";
        }
    }
    </script>
</body>
</html>
"""

# --- STATIC FILE SERVING ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- ROUTES & VIEWS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, role, status FROM users WHERE username = %s AND password = %s;", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if user['status'] == 'BLOCKED':
                error = "🚫 Akkaawunttii keessan UGGURAMEERA! CEO qunnamaa."
            else:
                session['username'] = user['username']
                session['role'] = user['role']
                return redirect('/')
        else:
            error = "Username ykn Password dogoggoraa!"

    err_html = f"<p style='color:red; font-size:12px; text-align:center; margin-bottom:12px;'>{error}</p>" if error else ""
    content = f"""
    <div class="box" style="margin-top: 30px; text-align: center;">
        <div style="font-size: 40px; margin-bottom: 10px;">🏦</div>
        <h2 style="font-size: 17px; margin-bottom: 4px; color:#065f46;">Imana Free Interest Microfinance</h2>
        <p style="font-size: 12px; color: #64748b; margin-bottom: 16px;">Seensa Systema (Login)</p>
        {err_html}
        <form method="POST">
            <div class="form-group" style="text-align:left;">
                <label>Username</label>
                <input type="text" name="username" placeholder="Fkn: ceo, manager1, maker1" class="input-field" required>
            </div>
            <div class="form-group" style="text-align:left;">
                <label>Password</label>
                <input type="password" id="login_password" name="password" placeholder="Password" class="input-field" required>
                <span id="login_pwd_toggle" class="pwd-toggle" onclick="togglePasswordVisibility('login_password', 'login_pwd_toggle')">👁️</span>
            </div>
            <button type="submit" class="btn-submit">Seeni (Login)</button>
        </form>
    </div>
    """
    return render_template_string(HTML_LAYOUT.replace("{% block content %}{% endblock %}", content), notifications=NOTIFICATIONS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def dashboard():
    if 'role' not in session:
        return redirect('/login')
    
    net_cap, deposits, withdraws, cust_bal, total_comm, mud_dep, mud_gross, mud_ceo, mud_cust = get_bank_capital()
    role = session['role']

    maker_btns = ""
    if role == 'MAKER':
        maker_btns = """
        <a href="/register" class="btn-card"><span class="icon">👤</span><span>Galmee Maammilaa</span></a>
        <a href="/transaction" class="btn-card"><span class="icon">💸</span><span>Deposit / Transfer / Withdraw</span></a>
        <a href="/maker_receipts" class="btn-card"><span class="icon">🧾</span><span>Nagahee Maxxansi</span></a>
        """

    manager_btns = ""
    if role == 'MANAGER':
        manager_btns = """
        <a href="/pending" class="btn-card"><span class="icon">🔍</span><span>Manager Approval</span></a>
        <a href="/reversals_list" class="btn-card"><span class="icon">🔄</span><span>Reversal Approvals</span></a>
        """

    auditor_btns = ""
    if role == 'AUDITOR':
        auditor_btns = """
        <a href="/pending" class="btn-card btn-card-auditor"><span class="icon">📋</span><span>View Maammilaa & Approve</span></a>
        <a href="/auditor_reversal_request" class="btn-card btn-card-auditor"><span class="icon">⚠️</span><span>Transaction Reversal Gaafachu</span></a>
        """

    loan_btn = ""
    if role in ['LOAN_OFFICER', 'CEO', 'MANAGER']:
        loan_btn = """
        <a href="/islamic_loan" class="btn-card btn-card-loan"><span class="icon">📜</span><span>Mudaraba & Murabaha Loan</span></a>
        """

    ceo_btn = ""
    ceo_mudaraba_dashboard = ""
    if role == 'CEO':
        ceo_mudaraba_dashboard = f"""
        <div class="card-ceo-profit">
            <div class="net-title">📊 CEO Private View: Mudaraba 50/50 Profit Share</div>
            <div class="net-amount">{mud_ceo:,.2f} Birr</div>
            <p style="font-size:11px; opacity:0.9; margin-top:4px;">Qoodda Bu'aa Baankii/CEO (50% Share)</p>
            <div class="net-grid">
                <div>📈 Waliigala Kuusaa Mudaraba: <b>{mud_dep:,.2f} Birr</b></div>
                <div>🤝 Qoodda Maammiltootaa (50%): <b>{mud_cust:,.2f} Birr</b></div>
            </div>
        </div>
        """
        ceo_btn = """
        <a href="/ceo_commission" class="btn-card btn-card-ceo"><span class="icon">💰</span><span>Comishina Guyyaa</span></a>
        <a href="/ceo_mudaraba_list" class="btn-card btn-card-ceo"><span class="icon">🤝</span><span>Mudaraba Private List</span></a>
        <a href="/ceo_blank_form" target="_blank" class="btn-card btn-card-ceo"><span class="icon">🖨️</span><span>Formii Duwwaa Maxxansi</span></a>
        <a href="/reversals_list" class="btn-card btn-card-ceo"><span class="icon">🔄</span><span>CEO Reversal Approval</span></a>
        <a href="/manage_users" class="btn-card btn-card-ceo"><span class="icon">⚙️</span><span>Bulchiinsa Hojjattootaa</span></a>
        """

    content = f"""
    {ceo_mudaraba_dashboard}

    <div class="card-net">
        <div class="net-title">Waliigala Kaabitaala Baankii (Net Capital)</div>
        <div class="net-amount">{net_cap:,.2f} Birr</div>
        <div class="net-grid">
            <div>📥 Deposit: <b>{deposits:,.2f} Birr</b></div>
            <div>📤 Withdraw/FT: <b>{withdraws:,.2f} Birr</b></div>
        </div>
    </div>

    <h3 style="font-size: 14px; margin-bottom: 12px; color: #475569;">Menu Hojii ({role})</h3>
    <div class="grid-2">
        {maker_btns}
        {manager_btns}
        {auditor_btns}
        {loan_btn}
        <a href="/customers" class="btn-card"><span class="icon">👥</span><span>Listii Maammiltootaa</span></a>
        {ceo_btn}
    </div>
    """
    return render_template_string(HTML_LAYOUT.replace("{% block content %}{% endblock %}", content), notifications=NOTIFICATIONS)

# --- LIST ALL CUSTOMERS & FREEZE MANAGEMENT ---
@app.route('/customers')
def customers():
    if 'role' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY created_at DESC;")
    cust_list = cursor.fetchall()
    cursor.close()
    conn.close()

    cards_html = ""
    for c in cust_list:
        freeze_badge = "<span class='badge badge-frozen'>🔒 FROZEN</span>" if c['freeze_status'] == 'FROZEN' else "<span class='badge badge-active'>ACTIVE</span>"
        account_badge = "badge-mudaraba" if c['account_type'] == 'MUDARABA' else "badge-wadia"
        
        freeze_form = ""
        if session['role'] == 'CEO':
            if c['freeze_status'] == 'FROZEN':
                freeze_form = f"""
                <form method="POST" action="/freeze_customer/{c['customer_id']}" style="display:inline;">
                    <input type="hidden" name="action_type" value="unfreeze">
                    <button type="submit" class="btn-action btn-green">🔓 Unfreeze</button>
                </form>
                """
            else:
                freeze_form = f"""
                <form method="POST" action="/freeze_customer/{c['customer_id']}" style="display:inline;">
                    <input type="hidden" name="action_type" value="freeze">
                    <input type="text" name="freeze_reason" placeholder="Sababa..." required style="padding:4px; font-size:11px; width:90px; border-radius:4px; border:1px solid #ccc;">
                    <button type="submit" class="btn-action btn-red">🔒 Freeze</button>
                </form>
                """

        edit_link = f'<a href="/edit_customer/{c["customer_id"]}" class="btn-action btn-blue">✏️ Edit</a>' if session['role'] == 'MANAGER' else ""

        cards_html += f"""
        <div class="item-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:12px; font-weight:bold; color:#065f46;">Acc: {c['customer_id']}</span>
                <div>
                    <span class="badge {account_badge}">{c['account_type']}</span>
                    {freeze_badge}
                </div>
            </div>
            <div style="font-size:13px; font-weight:bold; margin-top:4px;">{c['full_name']} ({c['gender']})</div>
            <div style="font-size:12px; color:#475569;">📞 {c['phone']} | Balansii: <b style="color:#065f46;">{float(c['balance']):,.2f} Birr</b></div>
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; pt:8px; border-top:1px solid #f1f5f9;">
                <div>
                    <a href="/statement/{c['customer_id']}" class="btn-action btn-purple">📜 Statement</a>
                    <a href="/print_customer_form/{c['customer_id']}" target="_blank" class="btn-action btn-orange">🖨️ Form</a>
                    {edit_link}
                </div>
                <div>
                    {freeze_form}
                </div>
            </div>
        </div>
        """

    content = f"""
    <h2 style="font-size: 16px; margin-bottom: 12px; color:#065f46;">👥 Tarree Maammiltootaa Guutuu</h2>
    {cards_html if cards_html else "<p style='text-align:center; padding:20px; color:#64748b;'>Maammilli galmaa'e hin jiru.</p>"}
    """
    return render_template_string(HTML_LAYOUT.replace("{% block content %}{% endblock %}", content), notifications=NOTIFICATIONS)

# --- USER MANAGEMENT FOR CEO ---
@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'role' not in session or session['role'] != 'CEO':
        return "🚫 Addatti CEO Qofatu Hojjattoota Bulchuu Danda'a!", 403

    msg = None
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'add':
            password = request.form.get('password', '').strip()
            role = request.form.get('role')
            try:
                cursor.execute("INSERT INTO users (username, password, role, status) VALUES (%s, %s, %s, 'ACTIVE');", (username, password, role))
                conn.commit()
                msg = f"✅ Hojjataa haaraa ({username}) milkaa'inaan galmeessiteetta!"
            except Exception as e:
                msg = f"❌ Error: Username '{username}' duraan jira Ykn dogoggora gahaa!"
        elif action in ['block', 'unblock']:
            new_st = 'BLOCKED' if action == 'block' else 'ACTIVE'
            cursor.execute("UPDATE users SET status = %s WHERE username = %s;", (new_st, username))
            conn.commit()
            msg = f"✅ Hojjataa {username} status '<b>{new_st}</b>' tii jijjiiramtteetta."

        cursor.close()
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, status FROM users;")
    users_list = cursor.fetchall()
    cursor.close()
    conn.close()

    rows_html = ""
    for u in users_list:
        btn = f'<form method="POST" style="display:inline;"><input type="hidden" name="action" value="block"><input type="hidden" name="username" value="{u["username"]}"><button class="btn-action btn-red">🚫 Ugguri</button></form>' if u['status'] == 'ACTIVE' else f'<form method="POST" style="display:inline;"><input type="hidden" name="action" value="unblock"><input type="hidden" name="username" value="{u["username"]}"><button class="btn-action btn-green">🔓 Banaa</button></form>'
        if u['username'] == 'ceo': btn = ""
        
        rows_html += f"""
        <tr style="border-bottom:1px solid #e2e8f0; font-size:12px;">
            <td style="padding:8px; font-weight:bold;">{u['username']}</td>
            <td style="padding:8px;">{u['role']}</td>
            <td style="padding:8px;"><span class="badge {'badge-active' if u['status']=='ACTIVE' else 'badge-danger'}">{u['status']}</span></td>
            <td style="padding:8px; text-align:right;">{btn}</td>
        </tr>
        """

    content = f"""
    <div class="box">
        <h2 style="font-size: 16px; color:#581c87; margin-bottom: 12px;">⚙️ Bulchiinsa Hojjattootaa (CEO Admin)</h2>
        {f"<p style='background:#dcfce7; color:#166534; padding:10px; border-radius:6px; font-size:12px; font-weight:bold; margin-bottom:12px;'>{msg}</p>" if msg else ""}

        <form method="POST">
            <input type="hidden" name="action" value="add">
            <div class="form-group">
                <label>Username Haaraa</label>
                <input type="text" name="username" required class="input-field">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="text" name="password" required class="input-field">
            </div>
            <div class="form-group">
                <label>Shoora Hojii (Role)</label>
                <select name="role" class="input-field">
                    <option value="MAKER">MAKER (Galmeessaa / Teller)</option>
                    <option value="MANAGER">MANAGER (Gulaalaa / Approver)</option>
                    <option value="AUDITOR">AUDITOR (To'ataa / Inspector)</option>
                    <option value="LOAN_OFFICER">LOAN_OFFICER (Mijjeessaa Liqaa)</option>
                </select>
            </div>
            <button type="submit" class="btn-submit" style="background:#6b21a8;">➕ Hojjataa Haaraa Galmeessi</button>
        </form>
    </div>

    <div class="box" style="padding:0; overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; text-align:left;">
            <thead>
                <tr style="background:#f8fafc; font-size:11px; color:#64748b; border-bottom:1px solid #e2e8f0;">
                    <th style="padding:8px;">Username</th>
                    <th style="padding:8px;">Role</th>
                    <th style="padding:8px;">Status</th>
                    <th style="padding:8px; text-align:right;">Tarkaanfii</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(HTML_LAYOUT.replace("{% block content %}{% endblock %}", content), notifications=NOTIFICATIONS)

# --- CEO COMMISSION VIEW ---
@app.route('/ceo_commission')
def ceo_commission():
    if 'role' not in session or session['role'] != 'CEO':
        return "🚫 Addatti CEO Qofatu Comishina Ilaala!", 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(commission) AS total FROM transactions WHERE status='APPROVED';")
    res = cursor.fetchone()
    total_comm = float(res['total']) if res and res['total'] is not None else 0.0

    cursor.execute("SELECT ft_reference, txn_type, amount, commission, timestamp FROM transactions WHERE status='APPROVED' AND commission > 0 ORDER BY timestamp DESC;")
    comm_txns = cursor.fetchall()
    cursor.close()
    conn.close()

    rows_html = ""
    for c in comm_txns:
        rows_html += f"""
        <tr style="border-bottom:1px solid #e2e8f0; font-size:12px;">
            <td style="padding:8px;">{c['timestamp']}</td>
            <td style="padding:8px; font-weight:bold;">{c['ft_reference']}</td>
            <td style="padding:8px;">{float(c['amount']):,.2f} Birr</td>
            <td style="padding:8px; font-weight:bold; color:#047857;">+{float(c['commission']):,.2f} Birr</td>
        </tr>
        """

    content = f"""
    <div class="card-ceo-profit">
        <div class="net-title">💰 Waliigala Comishina Galii Baankii</div>
        <div class="net-amount">{total_comm:,.2f} Birr</div>
        <p style="font-size:11px; opacity:0.9; margin-top:4px;">Comishina kaffaltiiwwan Withdrawal irraa walitti qabame.</p>
    </div>

    <div class="box" style="padding:0; overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; text-align:left;">
            <thead>
                <tr style="background:#f8fafc; font-size:11px; color:#64748b; border-bottom:1px solid #e2e8f0;">
                    <th style="padding:8px;">Guyyaa</th>
                    <th style="padding:8px;">Ref ID</th>
                    <th style="padding:8px;">Hamma Txn</th>
                    <th style="padding:8px;">Comishina</th>
                </tr>
            </thead>
            <tbody>
                {rows_html if rows_html else '<tr><td colspan="4" style="padding:16px; text-align:center; color:#64748b;">Comishiniin galmaa\'e hin jiru.</td></tr>'}
            </tbody>
        </table>
    </div>
    """
    return render_template_string(HTML_LAYOUT.replace("{% block content %}{% endblock %}", content), notifications=NOTIFICATIONS)

# --- SINGLE RECEIPT PRINTING ROUTE ---
@app.route('/receipt/<txn_id>')
def print_receipt(txn_id):
    if 'role' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE txn_id = %s OR ft_reference = %s;", (txn_id, txn_id))
    t = cursor.fetchone()

    if not t:
        cursor.close()
        conn.close()
        return "Transaction-ni Hin Argamne", 404

    cursor.execute("SELECT full_name, phone, account_type FROM customers WHERE customer_id = %s;", (t['customer_id'],))
    cust = cursor.fetchone()
    cursor.close()
    conn.close()

    cust_name = cust['full_name'] if cust else t['customer_name']
    phone = cust['phone'] if cust else ""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nagahee Kaffaltii - {t['ft_reference']}</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 500px; margin: 0 auto; border: 2px dashed #065f46; border-radius: 8px; background: white; }}
            .header {{ text-align: center; border-bottom: 2px solid #065f46; padding-bottom: 8px; margin-bottom: 12px; }}
            .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; line-height:1.5; }}
            .btn-print {{ background: #065f46; color: white; border: none; padding: 10px; width: 100%; font-size: 14px; font-weight: bold; cursor: pointer; border-radius: 6px; margin-top: 16px; }}
            @media print {{ .btn-print {{ display: none; }} body {{ border: none; padding: 0; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color:#065f46; margin:0; font-size:16px;">IMANA FREE INTEREST MICROFINANCE</h2>
            <p style="font-size:11px; margin-top:2px;">NAGAHEE KAFFALTII (OFFICIAL RECEIPT)</p>
        </div>

        <div class="row"><span><b>Ref ID (FT/TT):</b></span><span style="color:#065f46; font-weight:bold;">{t['ft_reference']}</span></div>
        <div class="row"><span><b>Guyyaa & Sa'aatii:</b></span><span>{t['timestamp']}</span></div>
        <div class="row"><span><b>Gosa Transaction:</b></span><span>{t['txn_type']}</span></div>
        <div class="row"><span><b>Maammila:</b></span><span>{cust_name}</span></div>
        <div class="row"><span><b>Acc ID:</b></span><span>{t['customer_id']}</span></div>
        <div class="row"><span><b>Bilbila:</b></span><span>{phone}</span></div>
        <div class="row"><span><b>Hamma Qarshii:</b></span><span style="font-size:15px; font-weight:bold; color:#065f46;">{float(t['amount']):,.2f} Birr</span></div>
        {f'<div class="row"><span><b>Comishina:</b></span><span>{float(t["commission"]):,.2f} Birr</span></div>' if float(t['commission']) > 0 else ''}
        <div class="row"><span><b>Status:</b></span><span><b>{t['status']}</b></span></div>
        <div class="row"><span><b>Hojjataa (Maker):</b></span><span>{t['created_by']}</span></div>

        <div style="margin-top: 30px; display: flex; justify-content: space-between; font-size: 11px;">
            <div>__________________<br>Mallattoo Maammilaa</div>
            <div>__________________<br>Mallattoo Teller/Maker</div>
        </div>

        <button onclick="window.print()" class="btn-print">🖨️ Nagahee Maxxansi (Print Receipt)</button>
    </body>
    </html>
    """

# --- REVERSAL APPROVAL EXECUTION ROUTE ---
@app.route('/approve_reversal/<role_type>/<rev_id>')
def approve_reversal(role_type, rev_id):
    if 'role' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.reversal_id, r.txn_id, r.manager_approved, r.ceo_approved, r.status,
               t.txn_type, t.customer_id, t.target_account, t.amount, t.commission, t.status AS txn_status
        FROM reversals r
        JOIN transactions t ON r.txn_id = t.txn_id
        WHERE r.reversal_id = %s;
    """, (rev_id,))
    rev = cursor.fetchone()

    if not rev:
        cursor.close()
        conn.close()
        return "Gaaffiin Reversal Hin Argamne", 404

    if role_type == 'manager' and session['role'] == 'MANAGER':
        cursor.execute("UPDATE reversals SET manager_approved = 1 WHERE reversal_id = %s;", (rev_id,))
        add_notification(f"Manager reversal_id {rev_id} approve godheera. CEO approval eegaa jira.")

    elif role_type == 'ceo' and session['role'] == 'CEO':
        cursor.execute("UPDATE reversals SET ceo_approved = 1, status = 'EXECUTED_REVERSED' WHERE reversal_id = %s;", (rev_id,))
        
        txn_type = rev['txn_type']
        cust_id = rev['customer_id']
        target_acc = rev['target_account']
        amount = float(rev['amount'])
        commission = float(rev['commission'])
        total_deduction = amount + commission

        if txn_type == 'DEPOSIT':
            cursor.execute("UPDATE customers SET balance = balance - %s WHERE customer_id = %s;", (amount, cust_id))
        elif txn_type == 'WITHDRAWAL':
            cursor.execute("UPDATE customers SET balance = balance + %s WHERE customer_id = %s;", (total_deduction, cust_id))
        elif txn_type == 'T24_TRANSFER':
            cursor.execute("UPDATE customers SET balance = balance + %s WHERE customer_id = %s;", (amount, cust_id))
            cursor.execute("UPDATE customers SET balance = balance - %s WHERE customer_id = %s;", (amount, target_acc))

        cursor.execute("UPDATE transactions SET status = 'REVERSED' WHERE txn_id = %s;", (rev['txn_id'],))
        add_notification(f"CEO reversal_id {rev_id} FINAL APPROVED! Transaction reversed ta'ee jira.")

    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/reversals_list')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
