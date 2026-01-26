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
        {'id': 1, 'title': 'الرياضيات', 'description': 'دروس الرياضيات من الأساسيات إلى المستوى المتقدم'},
        {'id': 2, 'title': 'العلوم', 'description': 'الفيزياء والكيمياء والأحياء'},
        {'id': 3, 'title': 'اللغات', 'description': 'دورات اللغة العربية والإنجليزية'},
        {'id': 4, 'title': 'التاريخ', 'description': 'التاريخ الليبي والعالمي'},
    ]
    return render_template('courses.html', courses=courses_list)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
