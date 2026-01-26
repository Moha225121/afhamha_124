# Afhamha (افهمها) 🎓

**Afhamha** is an AI-powered educational assistant specifically designed for the **Libyan curriculum**. It helps students from middle school (أولى إعدادي) to high school (ثالثة ثانوي) understand their subjects through interactive AI explanations, quizzes, and progress tracking.

---

## 🚀 Features

-   **AI Tutor**: Personalized explanations using the Libyan dialect ("Libyan White Dialect") to make learning relatable and easy.
-   **Curriculum-Aligned**: Covers subjects from the official Libyan curriculum.
-   **Interactive Quizzes**: Generate quizzes for any topic to test your understanding.
-   **Progress Tracking**: Monitor study hours, points, and saved explanations.
-   **Trial Period**: 60-day trial for new users.

## 🛠️ Tech Stack

-   **Backend**: Flask (Python)
-   **Database**: SQLAlchemy with SQLite
-   **AI Engine**: OpenAI GPT-4o-mini
-   **Frontend**: HTML, Vanilla CSS (Tailored Libyan-themed design)
-   **Authentication**: Flask-Login

## 📥 Installation & Setup

### Prerequisites
- Python 3.8+
- OpenAI API Key

### Steps

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd afhamha_app
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Linux/Mac
    ```

3.  **Install dependencies**:
    ```bash
    pip install flask flask-sqlalchemy flask-login openai python-dotenv
    ```

4.  **Configure environment variables**:
    Create a `.env` file in the root directory:
    ```env
    SECRET_KEY=your-secret-key
    DATABASE_URL=sqlite:///afhamha.db
    OPENAI_API_KEY=your-openai-api-key
    ```

5.  **Initialize the database**:
    The database is automatically created when you run the app for the first time.

6.  **Run the application**:
    ```bash
    python app.py
    ```
    The app will be available at `http://127.0.0.1:8000`.

## 📂 Project Structure

-   `app.py`: Main Flask application and routes.
-   `templates/`: HTML templates for the UI.
-   `static/`: CSS, JS, and image assets.
-   `migrate_user.py`: Database migration script for adding new columns.
-   `instance/`: SQLite database storage.

## 📝 License

This project is for educational purposes.
