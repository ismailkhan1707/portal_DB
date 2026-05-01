# ─────────────────────────────────────────────────────────────
# IMPORTS — Loading the tools we need
# ─────────────────────────────────────────────────────────────
from flask import Flask, render_template, request, redirect, url_for, session, flash
# Flask        — the main framework
# render_template — loads an HTML file and sends it to the browser
# request      — lets us read data from forms
# redirect     — sends the user to a different page
# url_for      — generates a URL for a route by its function name
# session      — stores login info temporarily
# flash        — shows one-time messages (like "Login successful!")

from flask_mysqldb import MySQL
# MySQL        — connects Flask to our MySQL database

from flask_bcrypt import Bcrypt
# Bcrypt       — encrypts passwords


# ─────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
# Creates your Flask application
# __name__ tells Flask where to find your project files

app.config.from_object('config.Config')
# Loads settings from config.py

mysql = MySQL(app)
# Connects MySQL to the app

bcrypt = Bcrypt(app)
# Connects Bcrypt to the app


# ─────────────────────────────────────────────────────────────
# ROUTE 1: Home Page
# ─────────────────────────────────────────────────────────────
@app.route('/')
# The @app.route('/') is called a "decorator"
# It tells Flask: "when someone visits the homepage (/), run this function"
def index():
    return render_template('index.html')
    # Loads and sends the index.html file to the browser


# ─────────────────────────────────────────────────────────────
# ROUTE 2: Student Registration
# ─────────────────────────────────────────────────────────────
@app.route('/register/student', methods=['GET', 'POST'])
# methods=['GET', 'POST'] means this page handles two situations:
# GET  = someone just visits the page (show the empty form)
# POST = someone submitted the form (process the data)
def register_student():
    if request.method == 'POST':
        # The form was submitted — read the values the user typed
        full_name  = request.form['full_name']
        email      = request.form['email']
        student_id = request.form['student_id']
        password   = request.form['password']
        major      = request.form['major']

        # ADD this line after major = request.form['major']
        gpa = request.form.get('gpa') or None
        # .get() is used instead of [] because gpa is optional
        # 'or None' means if left empty, save it as NULL in database

        # Encrypt the password before saving
        # NEVER save plain text passwords in a database!
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        # generate_password_hash turns "mypassword" into something like:
        # "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

        # Connect to the database
        cur = mysql.connection.cursor()
        # cursor() is like opening a channel to send SQL commands

        try:
            # INSERT INTO adds a new row to the students table
            # %s are placeholders — Flask fills them in safely
            # (This prevents SQL injection attacks)
            cur.execute("""
                INSERT INTO students (full_name, email, student_id, password, major, gpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (full_name, email, student_id, hashed_pw, major, gpa))
            
            mysql.connection.commit()
            # commit() actually saves the changes to the database
            # Without this line, the INSERT would be lost!

            flash('Registration successful! Please log in.', 'success')
            # flash() stores a message that shows up once on the next page
            # 'success' is the category — used for green color in Bootstrap

            return redirect(url_for('login'))
            # Send the user to the login page

        except Exception as e:
            # If something went wrong (e.g., duplicate email), show an error
            flash('Email or Student ID already exists.', 'danger')

        finally:
            cur.close()
            # Always close the database connection when done

    # If it's a GET request (page visit), just show the empty form
    return render_template('register_student.html')


# ─────────────────────────────────────────────────────────────
# ROUTE 3: Faculty Registration
# ─────────────────────────────────────────────────────────────
@app.route('/register/faculty', methods=['GET', 'POST'])
def register_faculty():
    # First, get the list of departments to show in a dropdown
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM departments")
    departments = cur.fetchall()
    # fetchall() returns all rows as a list of tuples:
    # [(1, 'Computer Science'), (2, 'Mathematics'), ...]
    cur.close()

    if request.method == 'POST':
        full_name     = request.form['full_name']
        email         = request.form['email']
        employee_id   = request.form['employee_id']
        password      = request.form['password']
        department_id = request.form['department_id']
        title         = request.form['title']

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO faculty (full_name, email, employee_id, password, department_id, title)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (full_name, email, employee_id, hashed_pw, department_id, title))
            mysql.connection.commit()
            flash('Faculty registration successful!', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email or Employee ID already exists.', 'danger')
        finally:
            cur.close()

    # Pass departments list to the HTML template
    return render_template('register_faculty.html', departments=departments)


# ─────────────────────────────────────────────────────────────
# ROUTE 4: Login
# ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        role     = request.form['role']  # Did they select Student or Faculty?

        cur = mysql.connection.cursor()

        # Search the correct table based on role
        if role == 'student':
            cur.execute("SELECT * FROM students WHERE email = %s", (email,))
        else:
            cur.execute("SELECT * FROM faculty WHERE email = %s", (email,))

        user = cur.fetchone()
        # fetchone() returns one row, or None if not found
        # A student row looks like: (1, 'Ali Khan', 'ali@email.com', 'S001', 'hashedpw', 'CS', 3.8, ...)
        cur.close()

        if user and bcrypt.check_password_hash(user[4], password):
            # user[4] is the password column (0=id, 1=name, 2=email, 3=student_id, 4=password)
            # check_password_hash compares the typed password with the encrypted one
            
            # Save user info in session (like giving them a login badge)
            session['user_id']   = user[0]   # their database ID
            session['user_name'] = user[1]   # their name
            session['role']      = role       # 'student' or 'faculty'

            if role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('faculty_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


# ─────────────────────────────────────────────────────────────
# ROUTE 5: Student Dashboard
# ─────────────────────────────────────────────────────────────
@app.route('/dashboard/student')
def student_dashboard():
    # Protect this page — if not logged in, redirect to login
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (session['user_id'],))
    student = cur.fetchone()
    cur.close()

    # Pass student data to the HTML template
    return render_template('student_dashboard.html', student=student)


# ─────────────────────────────────────────────────────────────
# ROUTE 6: Faculty Dashboard
# ─────────────────────────────────────────────────────────────
@app.route('/dashboard/faculty')
def faculty_dashboard():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculty WHERE id = %s", (session['user_id'],))
    faculty = cur.fetchone()

    # Faculty can see all students
    cur.execute("SELECT full_name, student_id, email, major, gpa FROM students")
    students = cur.fetchall()
    cur.close()

    return render_template('faculty_dashboard.html', faculty=faculty, students=students)


# ─────────────────────────────────────────────────────────────
# ROUTE 7: Logout
# ─────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    # Removes all session data — user is now logged out
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────────────────────
# START THE APP
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
    # debug=True means:
    # 1. The server auto-restarts when you save changes
    # 2. You see detailed error messages in the browser
    # (Turn debug=False before publishing your project!)