import os
import json
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
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

# ---------------- LOGIN ----------------
login_manager = LoginManager(app)
login_manager.login_view = 'signup'

# ---------------- OPENAI ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        "التاريخ", "الجغرافية",
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
        "التاريخ", "الجغرافية",
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
                password=generate_password_hash(password)
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

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone = request.form['phone']

        if User.query.filter_by(phone=phone).first():
            flash("الرقم مسجل مسبقاً")
            return redirect(url_for('signup'))

        user = User(
            full_name=request.form['full_name'],
            phone=phone,
            study_year=request.form['study_year'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(phone=request.form['phone']).first()
    if user and check_password_hash(user.password, request.form['password']):
        login_user(user)
        return redirect(url_for('dashboard'))

    flash("بيانات الدخول غير صحيحة")
    return redirect(url_for('signup'))

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

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
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

    if request.method == 'POST':
        if not current_user.is_in_trial and current_user.ai_credits <= 0:
            return jsonify({"error": "انتهت فترة التجربة (شهرين) ورصيدك 0، اشترك تزيد نقاط"}), 403

        if current_user.ai_credits <= 0:
            return jsonify({"error": "رصيدك كمل. اشترك باش تزيد نقاط"}), 403

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

    return render_template('ai_room.html', subjects=subjects)

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
