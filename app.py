from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    """Render the homepage for the education platform"""
    return render_template('index.html')

@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@app.route('/courses')
def courses():
    """Render the courses page"""
    courses_list = [
        {'id': 1, 'title': 'Mathematics', 'description': 'Basic to advanced mathematics'},
        {'id': 2, 'title': 'Science', 'description': 'Physics, Chemistry, and Biology'},
        {'id': 3, 'title': 'Languages', 'description': 'Arabic and English language courses'},
        {'id': 4, 'title': 'History', 'description': 'Libyan and World History'},
    ]
    return render_template('courses.html', courses=courses_list)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
