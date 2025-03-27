# Academic Paper Submission and Review System

This is a web application for submitting, reviewing, and managing academic papers. The system supports three types of users: authors, reviewers, and administrators.

## Features

- User registration and authentication
- Paper submission with title, abstract, and PDF file
- Anonymous paper review system
- Role-based access control
- Paper status tracking
- Modern and responsive UI using Bootstrap

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd academic-paper-system
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create the uploads directory:
```bash
mkdir uploads
```

5. Initialize the database:
```bash
python app.py
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Register as a new user with one of the following roles:
   - Author: Can submit papers and track their status
   - Reviewer: Can review submitted papers anonymously
   - Administrator: Can manage papers and make final decisions

## Project Structure

```
academic-paper-system/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── uploads/           # Directory for uploaded papers
├── templates/         # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── submit_paper.html
│   └── review_paper.html
└── README.md
```

## Security Features

- Password hashing using Werkzeug
- Role-based access control
- Secure file upload handling
- Session management with Flask-Login

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 