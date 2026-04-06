import os
import json
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from resala_api import send_otp
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from openai import OpenAI

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- APP ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret-key')

# ---------------- DATABASE ----------------
database_url = os.getenv("DATABASE_URL", "sqlite:///afhamha.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- AUTO MIGRATION ----------------
def run_auto_migration():
    print(">>> Starting Startup Migration Check")
    try:
        from sqlalchemy import text
        with app.app_context():
            with db.engine.connect() as conn:
                # Aggressive PostgreSQL check
                is_pg = database_url.startswith("postgresql") or "db.ondigitalocean.app" in database_url
                if is_pg:
                    print(">>> Detected PostgreSQL environment. Running ALTER commands...")
                    queries = [
                        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;',
                        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;',
                        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS study_hours FLOAT DEFAULT 0.0;',
                        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE explanation ADD COLUMN IF NOT EXISTS subject VARCHAR(100);',
                        'ALTER TABLE explanation ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'
                    ]
                    for q in queries:
                        try:
                            # Using execution_options(isolation_level="AUTOCOMMIT") to ensure each ALTER runs
                            conn.execute(text(q))
                            conn.commit()
                            print(f">>> OK: {q[:40]}...")
                        except Exception as q_ex:
                            print(f">>> SKIP/FAIL: {q[:40]}... Error: {q_ex}")
                    
                    try:
                        conn.execute(text("""
                            CREATE TABLE IF NOT EXISTS lesson (
                                id SERIAL PRIMARY KEY,
                                study_year VARCHAR(50) NOT NULL,
                                subject VARCHAR(100) NOT NULL,
                                category VARCHAR(100),
                                lesson_name VARCHAR(255) NOT NULL,
                                description TEXT
                            );
                        """))
                        conn.commit()
                        print(">>> OK: CREATE TABLE lesson")
                    except Exception as l_ex:
                        print(f">>> FAIL: CREATE TABLE lesson: {l_ex}")
                else:
                    print(f">>> Detected Non-PostgreSQL (SQLite/Other). Running fallback migration check...")
                    # Fallback for SQLite (Adding columns one by one safely)
                    columns_to_add = [
                        ('joined_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                        ('points', 'INTEGER DEFAULT 0'),
                        ('study_hours', 'FLOAT DEFAULT 0.0'),
                        ('is_verified', 'BOOLEAN DEFAULT FALSE'),
                    ]
                    for col_name, col_type in columns_to_add:
                        try:
                            # Check if column exists first
                            cursor = conn.execute(text(f"PRAGMA table_info('user')"))
                            existing_cols = [row[1] for row in cursor.fetchall()]
                            if col_name not in existing_cols:
                                conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type};'))
                                conn.commit()
                                print(f">>> OK: Added {col_name} to user table")
                        except Exception as q_ex:
                            print(f">>> SKIP: {col_name} check failed: {q_ex}")
                    
                    # Also check explanation table
                    try:
                        cursor = conn.execute(text(f"PRAGMA table_info('explanation')"))
                        existing_cols = [row[1] for row in cursor.fetchall()]
                        if 'subject' not in existing_cols:
                            conn.execute(text('ALTER TABLE explanation ADD COLUMN subject VARCHAR(100);'))
                            conn.commit()
                        if 'created_at' not in existing_cols:
                            conn.execute(text('ALTER TABLE explanation ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'))
                            conn.commit()
                    except:
                        pass
        print(">>> Startup Migration Check Completed Successfully")
    except Exception as e:
        print(f">>> CRITICAL: Startup Migration Failed: {e}")

run_auto_migration()

# ---------------- LOGIN ----------------
login_manager = LoginManager(app)
login_manager.login_view = 'signup'

# ---------------- OPENAI ----------------
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None
    print("Warning: OPENAI_API_KEY not found. AI features will be disabled.")

# ---------------- ADMIN ----------------
def _get_admin_phones():
    raw = os.getenv("ADMIN_PHONES", "")
    primary = os.getenv("ADMIN_PHONE", "").strip()
    admin1 = os.getenv("ADMIN1_PHONE", "0942120212").strip()
    admin2 = os.getenv("ADMIN2_PHONE", "0910000000").strip()
    phones = {p.strip() for p in raw.split(",") if p.strip()}
    if primary:
        phones.add(primary)
    if admin1:
        phones.add(admin1)
    if admin2:
        phones.add(admin2)
    return phones

def is_admin_user(user):
    return bool(user and user.is_authenticated and user.phone in _get_admin_phones())

# ---------------- CURRICULUM ----------------
CURRICULUM = {
    "أولى إعدادي": [
        "لغة عربية", "تربية إسلامية", "رياضيات", "العلوم",
        "جغرافيا", "تاريخ", "الحاسوب", "لغة إنجليزية"
    ],
    "ثانية إعدادي": [
        "لغة عربية", "تربية إسلامية", "رياضيات", "العلوم",
        "جغرافيا", "تاريخ", "الحاسوب", "لغة إنجليزية"
    ],
    "ثالثة إعدادي": [
        "لغة عربية", "تربية إسلامية", "رياضيات", "العلوم",
        "جغرافيا", "تاريخ", "الحاسوب", "لغة إنجليزية"
    ],
    "أولى ثانوي عام": [
        "الرياضيات", "الأحياء", "التربية الإسلامية",
        "النحو والصرف والإملاء", "دراسات أدبية",
        "الكيمياء", "فيزياء", "تاريخ",
        "الجغرافية", "علم اجتماع", "لغة إنجليزية"
    ],
    "ثانية ثانوي علمي": [
        "التربية الإسلامية", "دراسات لغوية", "دراسات أدبية",
        "الرياضيات", "تقنية المعلومات", "الأحياء",
        "الفيزياء", "الإحصاء", "الكيمياء", "لغة إنجليزية"
    ],
    "ثانية ثانوي أدبي": [
        "التربية الإسلامية", "لغة إنجليزية", "بلاغة",
        "الأدب والنصوص", "المطالعة والإنشاء",
        "النحو والصرف والإملاء", "الفلسفة",
        "التاريخ", "الجغرافية", "الإحصاء",
        "تقنية المعلومات", "علم الاجتماع"
    ],
    "ثالثة ثانوي علمي": [
        "التربية الإسلامية", "دراسات لغوية", "دراسات أدبية",
        "الرياضيات", "تقنية المعلومات", "الأحياء",
        "الفيزياء", "الإحصاء", "الكيمياء", "لغة إنجليزية"
    ],
    "ثالثة ثانوي أدبي": [
        "التربية الإسلامية", "لغة إنجليزية", "بلاغة",
        "الأدب والنصوص", "المطالعة والإنشاء",
        "النحو والصرف والإملاء", "الفلسفة",
        "التاريخ", "الجغرافية", "الإحصاء",
        "تقنية المعلومات", "علم الاجتماع"
    ]
}

# ---------------- SUBJECT ICONS ----------------
SUBJECT_ICONS = {
    "لغة عربية": "📖",
    "تربية إسلامية": "🕌",
    "التربية الإسلامية": "🕌",
    "رياضيات": "📐",
    "الرياضيات": "📏",
    "العلوم": "🧪",
    "فيزياء": "⚡",
    "الفيزياء": "⚛️",
    "كيمياء": "⚗️",
    "الكيمياء": "🧪",
    "أحياء": "🧬",
    "الأحياء": "🌿",
    "جغرافيا": "🌍",
    "الجغرافية": "🗺️",
    "تاريخ": "🏛️",
    "التاريخ": "📜",
    "لغة إنجليزية": "🇬🇧",
    "الحاسوب": "💻",
    "تقنية المعلومات": "🖥️",
    "الإحصاء": "📊",
    "الفلسفة": "🤔",
    "علم اجتماع": "👥",
    "بلاغة": "📝",
    "الأدب والنصوص": "📚",
    "المطالعة والإنشاء": "✍️",
    "النحو والصرف والإملاء": "🖊️",
    "دراسات لغوية": "📘",
    "دراسات أدبية": "📕"
}

# ---------------- REFERENCES ----------------
STUDY_YEAR_REFERENCE_FOLDER = {
    "أولى إعدادي": "7th_grade",
    "ثانية إعدادي": "8th_grade",
    "ثالثة إعدادي": "9th_grade",
    "اول ثانوي" : "1st_secandory"
}

REFERENCE_FILES = {
    "7th_grade": {
        "لغة عربية": [
            {"label": "كتاب اللغة العربية", "file": "Arabic.pdf"}
        ],
        "لغة إنجليزية": [
            {"label": "كتاب اللغة الإنجليزية", "file": "English.pdf"}
        ],
        "العلوم": [
            {"label": "كتاب العلوم - الجزء الأول", "file": "Science1.pdf"},
            {"label": "كتاب العلوم - الجزء الثاني", "file": "Science2.pdf"}
        ],
        "جغرافيا": [
            {"label": "كتاب الجغرافيا", "file": "geography.pdf"}
        ],
        "تاريخ": [
            {"label": "كتاب التاريخ", "file": "history.pdf"}
        ],
        "تربية إسلامية": [
            {"label": "كتاب التربية الإسلامية", "file": "Islamic.pdf"}
        ],
        "رياضيات": [
            {"label": "كتاب الرياضيات", "file": "maths.pdf"}
        ],
        "الحاسوب": [
            {"label": "كتاب الحاسوب", "file": "computer.pdf"}
        ]
    },
    "8th_grade": {
        "لغة عربية": [
            {"label": "كتاب اللغة العربية", "file": "arabic.pdf"}
        ],
        "لغة إنجليزية": [
            {"label": "كتاب اللغة الإنجليزية", "file": "English.pdf"}
        ],
        "العلوم": [
            {"label": "كتاب العلوم - الجزء الأول", "file": "science1.pdf"},
            {"label": "كتاب العلوم - الجزء الثاني", "file": "science2.pdf"}
        ],
        "جغرافيا": [
            {"label": "كتاب الجغرافيا", "file": "geography.pdf"}
        ],
        "تاريخ": [
            {"label": "كتاب التاريخ", "file": "history.pdf"}
        ],
        "تربية إسلامية": [
            {"label": "كتاب التربية الإسلامية", "file": "Islamic.pdf"}
        ],
        "رياضيات": [
            {"label": "كتاب الرياضيات", "file": "maths.pdf"}
        ],
        "الحاسوب": [
            {"label": "كتاب الحاسوب", "file": "computer.pdf"}
        ]
    },
    "9th_grade": {
        "لغة عربية": [
            {"label": "كتاب اللغة العربية", "file": "arabic.pdf"}
        ],
        "لغة إنجليزية": [
            {"label": "كتاب اللغة الإنجليزية", "file": "english.pdf"}
        ],
        "العلوم": [
            {"label": "كتاب العلوم - الجزء الأول", "file": "science.pdf"},
            {"label": "كتاب العلوم - الجزء الثاني", "file": "science2.pdf"}
        ],
        "جغرافيا": [
            {"label": "كتاب الجغرافيا", "file": "geography.pdf"}
        ],
        "تربية إسلامية": [
            {"label": "كتاب التربية الإسلامية", "file": "Islamic.pdf"}
        ],
        "رياضيات": [
            {"label": "كتاب الرياضيات", "file": "maths.pdf"}
        ],
        "الحاسوب": [
            {"label": "كتاب الحاسوب", "file": "computer.pdf"}
        ]
    }
}

def build_references_map(study_year):
    folder = STUDY_YEAR_REFERENCE_FOLDER.get(study_year)
    if not folder:
        return {}

    subject_refs = REFERENCE_FILES.get(folder, {})
    references_map = {}
    for subject, items in subject_refs.items():
        refs = []
        for item in items:
            refs.append({
                "label": item["label"],
                "url": url_for("static", filename=f"References/{folder}/{item['file']}")
            })
        references_map[subject] = refs
    return references_map

# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    study_year = db.Column(db.String(50))
    ai_credits = db.Column(db.Integer, default=250)
    points = db.Column(db.Integer, default=0)
    study_hours = db.Column(db.Float, default=0.0)
    is_verified = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_in_trial(self):
        # 2 months = roughly 60 days
        expiry_date = self.joined_at + timedelta(days=60)
        return datetime.utcnow() < expiry_date

class Explanation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    subject = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    study_year = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))  # e.g., "القرآن الكريم", "السنة النبوية"
    lesson_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

with app.app_context():
    db.create_all()

    seed_admins = [
        {
            "phone": os.getenv("ADMIN1_PHONE", "0942120212").strip(),
            "password": os.getenv("ADMIN1_PASSWORD", "12345678").strip(),
            "name": os.getenv("ADMIN1_NAME", "Admin One").strip() or "Admin One"
        },
        {
            "phone": os.getenv("ADMIN2_PHONE", "0910000000").strip(),
            "password": os.getenv("ADMIN2_PASSWORD", "12345678").strip(),
            "name": os.getenv("ADMIN2_NAME", "Admin Two").strip() or "Admin Two"
        }
    ]

    legacy_phone = os.getenv("ADMIN_PHONE", "").strip()
    legacy_password = os.getenv("ADMIN_PASSWORD", "").strip()
    legacy_name = os.getenv("ADMIN_NAME", "Admin").strip() or "Admin"
    if legacy_phone and legacy_password:
        seed_admins.append({
            "phone": legacy_phone,
            "password": legacy_password,
            "name": legacy_name
        })

    seen_phones = set()
    for admin in seed_admins:
        phone = admin.get("phone")
        password = admin.get("password")
        name = admin.get("name")
        if not phone or not password:
            continue
        if phone in seen_phones:
            continue
        seen_phones.add(phone)
        if not User.query.filter_by(phone=phone).first():
            admin_user = User(
                full_name=name,
                phone=phone,
                study_year=None,
                password=generate_password_hash(password),
                is_verified=True
            )
            db.session.add(admin_user)
    if seen_phones:
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_admin_flag():
    return {"is_admin": is_admin_user(current_user)}

@app.before_request
def check_verification():
    # Only check if user is logged in and not on a static/excluded route
    if current_user.is_authenticated:
        # Exclude routes that don't need verification check
        excluded_routes = ['logout', 'signup', 'login', 'verify_otp', 'verify_login_otp', 'static']
        if request.endpoint not in excluded_routes and not current_user.is_verified:
            # Trigger OTP send if not already in session
            if 'pending_pin' not in session:
                pin = send_otp(current_user.phone)
                if pin:
                    session['pending_verify_user_id'] = current_user.id
                    session['pending_phone'] = current_user.phone
                    session['pending_pin'] = pin
            
            return render_template('signup.html', verify_otp=True, login_verify=True)

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone = request.form['phone'].strip()

        if User.query.filter_by(phone=phone).first():
            flash("الرقم مسجل مسبقاً")
            return redirect(url_for('signup'))

        # Send OTP
        pin = send_otp(phone)
        if not pin:
            flash("فشل إرسال رمز التحقق، تأكد من الرقم الصادر")
            return redirect(url_for('signup'))

        # Store pending user data in session
        session['pending_user'] = {
            'full_name': request.form['full_name'],
            'phone': phone,
            'study_year': request.form['study_year'],
            'password': generate_password_hash(request.form['password']),
            'pin': pin
        }
        
        return render_template('signup.html', verify_otp=True)

    return render_template('signup.html', verify_otp=False)

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    pending_user = session.get('pending_user')
    if not pending_user:
        flash("انتهت صلاحية الجلسة، يرجى المحاولة مرة أخرى")
        return redirect(url_for('signup'))

    otp_entered = request.form.get('otp', '').strip()
    
    if otp_entered == str(pending_user['pin']):
        # Create user
        user = User(
            full_name=pending_user['full_name'],
            phone=pending_user['phone'],
            study_year=pending_user['study_year'],
            password=pending_user['password'],
            is_verified=True,
            points=50 # Assigning 50 points gift
        )
        db.session.add(user)
        db.session.commit()
        
        # Clear session
        session.pop('pending_user', None)
        
        login_user(user)
        flash("تهانينا! تم تفعيل حسابك وإضافة 50 نقطة هدية لرصيدك 🎉")
        return redirect(url_for('dashboard'))
    else:
        flash("رمز التحقق غير صحيح")
        return render_template('signup.html', verify_otp=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        user = User.query.filter_by(phone=phone).first()

        if user and check_password_hash(user.password, password):
            if not user.is_verified:
                # Need to verify
                pin = send_otp(phone)
                if not pin:
                    flash("فشل إرسال رمز التحقق")
                    return redirect(url_for('signup'))
                
                session['pending_verify_user_id'] = user.id
                session['pending_phone'] = user.phone
                session['pending_pin'] = pin
                return render_template('signup.html', verify_otp=True, login_verify=True)
            
            login_user(user)
            return redirect(url_for('dashboard'))

        flash("بيانات الدخول غير صحيحة")
        return redirect(url_for('signup'))
    return redirect(url_for('signup'))

@app.route('/verify-login-otp', methods=['POST'])
def verify_login_otp():
    user_id = session.get('pending_verify_user_id')
    expected_pin = session.get('pending_pin')
    entered_otp = request.form.get('otp', '').strip()

    if not user_id or not expected_pin:
        return redirect(url_for('signup'))

    if entered_otp == str(expected_pin):
        user = User.query.get(user_id)
        if user:
            if not user.is_verified:
                user.points += 50
                user.is_verified = True
                db.session.commit()
                flash("تم إثبات ملكية الرقم وإضافة 50 نقطة هدية لرصيدك 🎉")
            
            login_user(user)
            session.pop('pending_verify_user_id', None)
            session.pop('pending_phone', None)
            session.pop('pending_pin', None)
            return redirect(url_for('dashboard'))
    
    flash("رمز التحقق غير صحيح")
    return render_template('signup.html', verify_otp=True, login_verify=True)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.password, password) and is_admin_user(user):
            login_user(user)
            return redirect(url_for('admin_dashboard'))

        flash("بيانات الإدارة غير صحيحة")
        return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    subjects = []

    for s in CURRICULUM.get(current_user.study_year, []):
        subjects.append({
            "name": s,
            "icon": SUBJECT_ICONS.get(s, "📘"),
            "count": Explanation.query.filter_by(
                user_id=current_user.id,
                subject=s
            ).count()
        })

    stats = {
        "explanations": Explanation.query.filter_by(user_id=current_user.id).count(),
        "points": current_user.points,
        "study_hours": round(current_user.study_hours, 1)
    }

    return render_template(
        'dashboard.html',
        subjects=subjects,
        stats=stats
    )

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if not is_admin_user(current_user):
        flash("غير مصرح لك بالدخول")
        return redirect(url_for('dashboard'))

    total_users = User.query.count()
    total_ai_requests = Explanation.query.count()
    phone_query = request.args.get('phone', '').strip()
    name_query = request.args.get('name', '').strip()
    found_users = []
    if phone_query or name_query:
        query = User.query
        if phone_query:
            query = query.filter(User.phone.ilike(f"%{phone_query}%"))
        if name_query:
            query = query.filter(User.full_name.ilike(f"%{name_query}%"))
        found_users = query.order_by(User.joined_at.desc()).limit(50).all()
        
        # Add AI request count for each user
        for u in found_users:
            u.ai_request_count = Explanation.query.filter_by(user_id=u.id).count()

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_ai_requests=total_ai_requests,
        phone_query=phone_query,
        name_query=name_query,
        found_users=found_users
    )

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not is_admin_user(current_user):
        flash("غير مصرح لك بالدخول")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك حذف حسابك من لوحة الإدارة")
        return redirect(url_for('admin_dashboard', phone=user.phone))

    Explanation.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("تم حذف المستخدم بنجاح")
    return redirect(url_for('admin_dashboard'))

# ---------------- AI ROOM ----------------
@app.route('/ai-room', methods=['GET', 'POST'])
@login_required
def ai_room():
    subjects = CURRICULUM.get(current_user.study_year, [])
    references_map = build_references_map(current_user.study_year)

    if request.method == 'POST':
        if not current_user.is_in_trial and current_user.ai_credits <= 0:
            return jsonify({"error": "انتهت فترة التجربة (شهرين) ورصيدك 0، اشترك تزيد نقاط"}), 403

        if current_user.ai_credits <= 0:
            return jsonify({"error": "رصيدك كمل. اشترك باش تزيد نقاط"}), 403

        if not client:
            return jsonify({"error": "خدمات الذكاء الاصطناعي معطلة حالياً. يرجى التواصل مع الإدارة."}), 500

        data = request.json
        subject = data.get("subject")
        query = data.get("query")

        # Check if this is an English subject
        is_english = "english" in subject.lower() or "إنجليزي" in subject.lower()

        # Different prompts for English vs other subjects
        if is_english:
            prompt = f"""
اشرح موضوع ({query}) في مادة ({subject}) لطلاب ({current_user.study_year}) في المنهج الليبي.

التعليمات:
1. استعمل اللهجة الليبية البيضاء (البسيطة والمفهومة) وكأنك مدرس ليبي خبير يحبب الطالب في المادة.
2. الشرح لازم يكون مفصل ومنظم باستعمال Markdown (عناوين، نقاط، خط عريض).
3. استند على المنهج الدراسي الليبي والمعلومات الصحيحة.
4. بعد الشرح، اقترح 3 أسئلة اختيار من متعدد (Quiz) للتأكد من الفهم.
5. ⚠️ مهم جداً: الشرح يكون بالعربي، لكن الأسئلة (quiz) لازم تكون بالإنجليزي بالكامل - السؤال والخيارات كلهم بالإنجليزي بدون أي حرف عربي.

رد عليا بصيغة JSON فقط كالتالي:
{{
 "explanation": "الشرح هنا بالعربي بتنسيق Markdown مفصل...",
 "quiz": [
   {{"question": "Question in English?", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "correct": 0}},
   ...
 ]
}}
"""
            system_message = "أنت 'افهمها وفهمني'، مدرس ليبي عبقري ومحبوب، تشرح اللغة الإنجليزية بطريقة مشوقة وبسيطة جداً بالعامية الليبية. الشرح يكون بالعربي، لكن الأسئلة (quiz) لازم تكون بالإنجليزي بالكامل."
        else:
            prompt = f"""
اشرح موضوع ({query}) في مادة ({subject}) لطلاب ({current_user.study_year}) في المنهج الليبي.

التعليمات:
1. استعمل اللهجة الليبية البيضاء (البسيطة والمفهومة) وكأنك مدرس ليبي خبير يحبب الطالب في المادة.
2. الشرح لازم يكون مفصل ومنظم باستعمال Markdown (عناوين، نقاط، خط عريض).
3. استند على المنهج الدراسي الليبي والمعلومات الصحيحة.
4. بعد الشرح، اقترح 3 أسئلة اختيار من متعدد (Quiz) للتأكد من الفهم.
5. مهم: اكتب الشرح بالعربي، لكن خلي الرموز الرياضية والعلمية بالإنجليزي (مثل: x, y, =, +, -, ×, ÷, etc.)

رد عليا بصيغة JSON فقط كالتالي:
{{
 "explanation": "الشرح هنا بتنسيق Markdown مفصل...",
 "quiz": [
   {{"question": "السؤال الأول؟", "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"], "correct": 0}},
   ...
 ]
}}
"""
            system_message = "أنت 'افهمها وفهمني'، مدرس ليبي عبقري ومحبوب، تشرح المنهج الليبي بطريقة مشوقة وبسيطة جداً بالعامية الليبية. تكتب الشرح بالعربي لكن تخلي الرموز الرياضية والعلمية بالإنجليزي."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            ai_data = json.loads(response.choices[0].message.content)
            
            # Save explanation to DB
            exp = Explanation(
                title=f"{subject}: {query}",
                subject=subject,
                content=ai_data["explanation"],
                user_id=current_user.id
            )
            db.session.add(exp)

            # Update user stats
            current_user.ai_credits -= 5
            current_user.points += 10
            current_user.study_hours += 0.25

            db.session.commit()
            return jsonify(ai_data)

        except Exception as e:
            print(f"AI Error: {e}")
            return jsonify({"error": "فشل توليد الشرح، جرب مرة ثانية"}), 500

    return render_template(
        'ai_room.html',
        subjects=subjects,
        references_map=references_map
    )

# ---------------- MY EXPLANATIONS ----------------
@app.route('/my-explanations')
@login_required
def my_explanations():
    explanations = (
        Explanation.query
        .filter_by(user_id=current_user.id)
        .order_by(Explanation.created_at.desc())
        .all()
    )
    return render_template('my_explanations.html', explanations=explanations)

# ---------------- API HISTORY ----------------
@app.route('/api/explanations')
@login_required
def api_explanations():
    explanations = (
        Explanation.query
        .filter_by(user_id=current_user.id)
        .order_by(Explanation.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify([
        {
            "id": e.id,
            "title": e.title,
            "content": e.content,
            "date": e.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for e in explanations
    ])

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
