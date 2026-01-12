# KEC – Django E-Commerce Web Application

KEC is a full-stack e-commerce web application developed using **Django**.  
This project was built as part of my college learning and focuses on real-world features like product listing, authentication, admin management, payments, and REST APIs.

The goal of this project was to understand how a complete web application is designed, developed, secured, and deployed.

---

##  Features

- User authentication (login, logout)
- Product listing and shop page
- Admin panel for managing products and users
- Cart and order management
- Razorpay payment gateway integration
- REST APIs using Django REST Framework
- Email notifications
- Secure handling of sensitive data using environment variables
- Responsive UI using HTML, CSS, and JavaScript

---

##  Tech Stack

- **Backend:** Django, Django REST Framework  
- **Frontend:** HTML, CSS, JavaScript  
- **Database:** SQLite (for development)  
- **Payments:** Razorpay  
- **Email:** SMTP (Gmail)  
- **Deployment:** PythonAnywhere  

---
##  Project Structure
KEC/
│── adminpanel/
│── store/
│── templates/
│── static/
│── KEC/
│── manage.py
│── requirements.txt
│── README.md


##  Installation & Setup (Local)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kec-project.git
cd kec-project

2. Create and activate virtual environment:

python -m venv venv
venv\Scripts\activate

3. Install dependencies:

pip install -r requirements.txt


4. Run migrations:

python manage.py migrate


5. Create superuser:

python manage.py createsuperuser


6. Start the server:

python manage.py runserver
-----
 Environment Variables

For security reasons, sensitive information is not stored in the repository.

The following environment variables must be set:

DJANGO_SECRET_KEY

RAZORPAY_KEY_ID

RAZORPAY_KEY_SECRET

EMAIL_HOST_USER

EMAIL_HOST_PASSWORD
-----
Deployment

This project is deployed on PythonAnywhere.

Key deployment steps:

Debug mode disabled

Secrets moved to environment variables

Static files collected using collectstatic

Database and media files excluded from GitHub
-----
 Notes

SQLite is used only for development.

Database files and secret keys are ignored using .gitignore.

This project is intended for learning and demonstration purposes.
-----
 Author

Purv Ranpariya
B.Tech Computer Engineering Student
Interested in Python, Django, Backend Development


