import os
import json
import re
from datetime import datetime, timedelta
from time import sleep

from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from openai import OpenAI

# ================= LOAD ENV =================
load_dotenv()

# ================= APP =================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "secret-key")

# ================= DATABASE =================
database_url = os.getenv("DATABASE_URL", "sqlite:///afhamha.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ================= LOGIN =================
login_manager = LoginManager(app)
login_manager.login_view = "signup"

# ================= OPENAI =================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# ================= ADMIN =================
def _get_admin_phones():
    phones = set()
    for key in ["ADMIN_PHONE", "ADMIN1_PHONE", "ADMIN2_PHONE"]:
        val = os.getenv(key)
        if val:
            phones.add(val.strip())
    return phones

def is_admin_user(user):
    return bool(user and user.is_authenticated and user.phone in _get_admin_phones())

# ================= CURRICULUM =================
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
    ]
}

SUBJECT_ICONS = {
    "لغة عربية": "📖",
    "تربية إسلامية": "🕌",
    "رياضيات": "📐",
    "العلوم": "🧪",
    "جغرافيا": "🌍",
    "تاريخ": "🏛️",
    "الحاسوب": "💻",
    "لغة إنجليزية": "🇬🇧"
}

# ================= REFERENCES =================
STUDY_YEAR_REFERENCE_FOLDER = {
    "أولى إعدادي": "7th_grade",
    "ثانية إعدادي": "8th_grade",
    "ثالثة إعدادي": "9th_grade"
}

REFERENCE_FILES = {
    "7th_grade": {
        "لغة عربية": [{"label": "كتاب اللغة العربية", "file": "Arabic.pdf"}],
        "لغة إنجليزية": [{"label": "كتاب اللغة الإنجليزية", "file": "English.pdf"}],
        "رياضيات": [{"label": "كتاب الرياضيات", "file": "Math.pdf"}],
        "العلوم": [{"label": "كتاب العلوم", "file": "Science.pdf"}],
    }
}

def build_references_map(study_year):
    folder = STUDY_YEAR_REFERENCE_FOLDER.get(study_year)
    if not folder:
        return {}
    subject_refs = REFERENCE_FILES.get(folder, {})
    refs_map = {}
    for subject, files in subject_refs.items():
        refs_map[subject] = [
            {
                "label": f["label"],
                "url": url_for("static", filename=f"References/{folder}/{f['file']}")
            }
            for f in files
        ]
    return refs_map

# ================= MODELS =================
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
        return datetime.utcnow() < self.joined_at + timedelta(days=60)

class Explanation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    subject = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# ================= INIT DB =================
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.context_processor
def inject_admin_flag():
    return {"is_admin": is_admin_user(current_user)}

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        phone = request.form["phone"]
        if User.query.filter_by(phone=phone).first():
            flash("الرقم مسجل مسبقاً")
            return redirect(url_for("signup"))

        user = User(
            full_name=request.form["full_name"],
            phone=phone,
            study_year=request.form["study_year"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("signup.html")

@app.route("/login", methods=["POST"])
def login():
    user = User.query.filter_by(phone=request.form["phone"]).first()
    if user and check_password_hash(user.password, request.form["password"]):
        login_user(user)
        return redirect(url_for("dashboard"))
    flash("بيانات الدخول غير صحيحة")
    return redirect(url_for("signup"))

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    subjects = [{
        "name": s,
        "icon": SUBJECT_ICONS.get(s, "📘"),
        "count": Explanation.query.filter_by(
            user_id=current_user.id,
            subject=s
        ).count()
    } for s in CURRICULUM.get(current_user.study_year, [])]

    stats = {
        "explanations": Explanation.query.filter_by(user_id=current_user.id).count(),
        "points": current_user.points,
        "study_hours": round(current_user.study_hours, 1)
    }

    return render_template(
        "dashboard.html",
        subjects=subjects,
        stats=stats
    )

# ================= AI ROOM =================
@app.route("/ai-room", methods=["GET", "POST"])
@login_required
def ai_room():
    subjects = CURRICULUM.get(current_user.study_year, [])
    references_map = build_references_map(current_user.study_year)

    if request.method == "POST":
        if not current_user.is_in_trial and current_user.ai_credits <= 0:
            return jsonify({"error": "انتهى الرصيد"}), 403

        data = request.json
        subject = data.get("subject", "")
        query = data.get("query", "")

        prompt = f"""
المادة: {subject}
الصف: {current_user.study_year}
السؤال: {query}

التعليمات:
1. اشرح باللهجة الليبية البيضاء.
2. استخدم Markdown.
3. اقترح 3 أسئلة اختيار من متعدد.

الرد يكون JSON فقط:
{{
 "explanation": "...",
 "quiz": [
   {{"question": "...", "options": ["A","B","C","D"], "correct": 0}}
 ]
}}
"""

        try:
            thread = client.beta.threads.create()

            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )

            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            while run.status in ("queued", "in_progress"):
                sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            messages = client.beta.threads.messages.list(thread_id=thread.id)
            answer = messages.data[0].content[0].text.value
            ai_data = json.loads(answer)

            exp = Explanation(
                title=f"{subject}: {query}",
                subject=subject,
                content=ai_data.get("explanation", ""),
                user_id=current_user.id
            )
            db.session.add(exp)

            current_user.ai_credits -= 5
            current_user.points += 10
            current_user.study_hours += 0.25
            db.session.commit()

            return jsonify(ai_data)

        except Exception as e:
            print("AI ERROR:", e)
            return jsonify({"error": "AI error"}), 500

    return render_template(
        "ai_room.html",
        subjects=subjects,
        references_map=references_map
    )

# ================= API =================
@app.route("/api/explanations")
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
            "date": e.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for e in explanations
    ])

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
