# afhamha_124
A website for an education platform in Libya

## Overview
Afhamha (افهمها) is a Libyan educational platform that provides high-quality online learning resources for students. The platform features a modern, responsive design with full Arabic language support (RTL).

## Features
- 🌐 Bilingual support (Arabic & English)
- 📱 Responsive design for all devices
- 🎨 Modern UI with smooth animations
- 📚 Course catalog with multiple subjects
- 🔒 Secure configuration options

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Moha225121/afhamha_124.git
cd afhamha_124
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Development Mode

To run with debug mode enabled:
```bash
FLASK_DEBUG=1 python app.py
```

## Project Structure
```
afhamha_124/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── index.html       # Homepage
│   ├── about.html       # About page
│   └── courses.html     # Courses page
└── README.md            # This file
```

## Available Routes
- `/` - Homepage with platform overview
- `/courses` - Browse available courses
- `/about` - Learn about the platform

## Technologies Used
- **Backend**: Flask 3.0.0
- **Frontend**: HTML5, CSS3 (with Google Fonts - Cairo)
- **Language**: Python 3.x

## License
© 2024 Afhamha. All rights reserved.
