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

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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

# ---------------- AI ROOM ----------------
@app.route('/ai-room', methods=['GET', 'POST'])
@login_required
def ai_room():
    subjects = CURRICULUM.get(current_user.study_year, [])

    if request.method == 'POST':
        if not current_user.is_in_trial and current_user.ai_credits <= 0:
            return jsonify({"error": "انتهت فترة التجربة (شهرين) ورصيدك 0، اشترك تزيد نقاط"}), 403

        if current_user.ai_credits <= 0:
            return jsonify({"error": "رصيدك خلص، اشترك باش تزيد نقاط"}), 403

        data = request.json
        subject = data.get("subject")
        query = data.get("query")

        prompt = f"""
اشرح موضوع ({query}) في مادة ({subject}) لطلاب ({current_user.study_year}) في المنهج الليبي.

التعليمات:
1. استعمل اللهجة الليبية البيضاء (البسيطة والمفهومة) وكأنك مدرس ليبي خبير يحبب الطالب في المادة.
2. الشرح لازم يكون مفصل ومنظم باستعمال Markdown (عناوين، نقاط، خط عريض).
3. استند على المنهج الدراسي الليبي والمعلومات الصحيحة.
4. بعد الشرح، اقترح 3 أسئلة اختيار من متعدد (Quiz) للتأكد من الفهم.

رد عليا بصيغة JSON فقط كالتالي:
{{
 "explanation": "الشرح هنا بتنسيق Markdown مفصل...",
 "quiz": [
   {{"question": "السؤال الأول؟", "options": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"], "correct": 0}},
   ...
 ]
}}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "أنت 'افهمها وفهمني'، مدرس ليبي عبقري ومحبوب، تشرح المنهج الليبي بطريقة مشوقة وبسيطة جداً بالعامية الليبية."},
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
