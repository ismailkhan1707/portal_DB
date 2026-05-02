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

# Helper functions to check who is logged in
def is_student():
    return 'user_id' in session and session['role'] == 'student'

def is_faculty():
    return 'user_id' in session and session['role'] == 'faculty'

def is_librarian():
    return 'user_id' in session and session['role'] == 'librarian'


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
        role     = request.form['role']

        cur = mysql.connection.cursor()

        # Query different table based on selected role
        if role == 'student':
            cur.execute("SELECT * FROM students WHERE email = %s", (email,))
        elif role == 'faculty':
            cur.execute("SELECT * FROM faculty WHERE email = %s", (email,))
        elif role == 'librarian':
            cur.execute("SELECT * FROM librarians WHERE email = %s", (email,))
        else:
            flash('Please select a valid role.', 'danger')
            return render_template('login.html')

        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[4], password):
            # Save login info in session
            session['user_id']   = user[0]
            session['user_name'] = user[1]
            session['role']      = role

            # Send to correct dashboard
            if role == 'student':
                return redirect(url_for('student_dashboard'))
            elif role == 'faculty':
                return redirect(url_for('faculty_dashboard'))
            elif role == 'librarian':
                return redirect(url_for('librarian_dashboard'))
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
# ROUTE: Librarian Registration
# ─────────────────────────────────────────────────────────────
@app.route('/register/librarian', methods=['GET', 'POST'])
def register_librarian():
    if request.method == 'POST':
        full_name    = request.form['full_name']
        email        = request.form['email']
        librarian_id = request.form['librarian_id']
        password     = request.form['password']

        # Validate fields
        errors = []
        if not full_name.strip():
            errors.append('Full name is required.')
        if not email.strip() or '@' not in email:
            errors.append('Valid email is required.')
        if not librarian_id.strip():
            errors.append('Librarian ID is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register_librarian.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO librarians (full_name, email, librarian_id, password)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, librarian_id, hashed_pw))
            mysql.connection.commit()
            flash('Librarian account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email or Librarian ID already exists.', 'danger')
        finally:
            cur.close()

    return render_template('register_librarian.html')


# ─────────────────────────────────────────────────────────────
# ROUTE: Librarian Dashboard
# ─────────────────────────────────────────────────────────────
@app.route('/dashboard/librarian')
def librarian_dashboard():
    if not is_librarian():
        flash('Please log in as a librarian.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Fetch librarian info
    cur.execute("SELECT * FROM librarians WHERE id = %s", (session['user_id'],))
    librarian = cur.fetchone()

    cur.close()

    return render_template('librarian_dashboard.html', librarian=librarian)

# ═════════════════════════════════════════════════════════════
# STEP 2 — BOOK MANAGEMENT
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# ROUTE: View All Books + Search
# ─────────────────────────────────────────────────────────────
@app.route('/books')
def view_books():
    # Any logged in user can view books
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    # Get search and sort values from the URL
    # e.g. /books?search=python&sort=author
    search = request.args.get('search', '')
    sort   = request.args.get('sort', 'title')

    # Only allow these columns for sorting (security)
    if sort not in ['title', 'author', 'category']:
        sort = 'title'

    cur = mysql.connection.cursor()

    if search:
        # % means "anything" in SQL
        # So %python% matches "Learn Python", "Python Basics" etc.
        like  = f'%{search}%'
        query = f"""
            SELECT * FROM books
            WHERE title LIKE %s
               OR author LIKE %s
               OR category LIKE %s
               OR isbn LIKE %s
            ORDER BY {sort}
        """
        cur.execute(query, (like, like, like, like))
    else:
        cur.execute(f"SELECT * FROM books ORDER BY {sort}")

    books = cur.fetchall()
    cur.close()

    return render_template('books.html', books=books, search=search, sort=sort)


# ─────────────────────────────────────────────────────────────
# ROUTE: Add Book
# ─────────────────────────────────────────────────────────────
@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    # Only librarians can add books
    if not is_librarian():
        flash('Only librarians can add books.', 'danger')
        return redirect(url_for('view_books'))

    if request.method == 'POST':
        title     = request.form['title'].strip()
        author    = request.form['author'].strip()
        category  = request.form['category'].strip()
        isbn      = request.form['isbn'].strip()
        publisher = request.form['publisher'].strip()
        year      = request.form['year'].strip()
        quantity  = request.form['quantity'].strip()

        # ── Validation ───────────────────────────────────────
        errors = []

        if not title:
            errors.append('Book title is required.')
        if not author:
            errors.append('Author name is required.')
        if year and (not year.isdigit() or not (1000 <= int(year) <= 2100)):
            errors.append('Please enter a valid year (e.g. 2023).')
        if not quantity or not quantity.isdigit() or int(quantity) < 1:
            errors.append('Quantity must be at least 1.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            # Send form data back so user doesn't retype everything
            return render_template('add_book.html', form_data=request.form)
        # ─────────────────────────────────────────────────────

        year     = int(year) if year else None
        quantity = int(quantity)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO books
                    (title, author, category, isbn, publisher, year, quantity, available)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, author, category, isbn, publisher, year, quantity, quantity))
            # available = quantity when first added
            # because all copies are available at the start
            mysql.connection.commit()
            flash(f'Book "{title}" added successfully!', 'success')
            return redirect(url_for('view_books'))
        except:
            flash('A book with this ISBN already exists.', 'danger')
            return render_template('add_book.html', form_data=request.form)
        finally:
            cur.close()

    return render_template('add_book.html', form_data={})


# ─────────────────────────────────────────────────────────────
# ROUTE: Edit Book
# ─────────────────────────────────────────────────────────────
@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if not is_librarian():
        flash('Only librarians can edit books.', 'danger')
        return redirect(url_for('view_books'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        title     = request.form['title'].strip()
        author    = request.form['author'].strip()
        category  = request.form['category'].strip()
        publisher = request.form['publisher'].strip()
        year      = request.form['year'].strip()
        quantity  = request.form['quantity'].strip()

        # Validation
        errors = []
        if not title:
            errors.append('Book title is required.')
        if not author:
            errors.append('Author name is required.')
        if year and (not year.isdigit() or not (1000 <= int(year) <= 2100)):
            errors.append('Please enter a valid year.')
        if not quantity or not quantity.isdigit() or int(quantity) < 1:
            errors.append('Quantity must be at least 1.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
            book = cur.fetchone()
            cur.close()
            return render_template('edit_book.html', book=book)

        year     = int(year) if year else None
        quantity = int(quantity)

        try:
            cur.execute("""
                UPDATE books
                SET title=%s, author=%s, category=%s,
                    publisher=%s, year=%s, quantity=%s
                WHERE book_id=%s
            """, (title, author, category, publisher, year, quantity, book_id))
            mysql.connection.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('view_books'))
        except:
            flash('Error updating book.', 'danger')
        finally:
            cur.close()

    else:
        # GET — load current book data into the form
        cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book = cur.fetchone()
        cur.close()

        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('view_books'))

        return render_template('edit_book.html', book=book)


# ─────────────────────────────────────────────────────────────
# ROUTE: Delete Book
# ─────────────────────────────────────────────────────────────
@app.route('/books/delete/<int:book_id>', methods=['GET', 'POST'])
def delete_book(book_id):
    if not is_librarian():
        flash('Only librarians can delete books.', 'danger')
        return redirect(url_for('view_books'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        try:
            cur.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            mysql.connection.commit()
            flash('Book deleted successfully.', 'success')
        except:
            flash('Cannot delete — this book has issue records attached.', 'danger')
        finally:
            cur.close()
        return redirect(url_for('view_books'))

    else:
        # GET — show confirmation page first
        cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book = cur.fetchone()
        cur.close()

        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('view_books'))

        return render_template('delete_book.html', book=book)

# ═════════════════════════════════════════════════════════════
# STEP 3 — MEMBER MANAGEMENT
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# ROUTE: View All Members
# ─────────────────────────────────────────────────────────────
@app.route('/members')
def view_members():
    if not is_librarian():
        flash('Only librarians can manage members.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # JOIN fetches member info combined with their actual details
    # from either students or faculty table using UNION
    # UNION combines two SELECT results into one list
    cur.execute("""
        SELECT
            lm.id,
            lm.user_type,
            lm.user_id,
            s.full_name,
            s.email,
            s.student_id AS ref_id,
            lm.member_since
        FROM library_members lm
        JOIN students s ON lm.user_id = s.id AND lm.user_type = 'student'

        UNION

        SELECT
            lm.id,
            lm.user_type,
            lm.user_id,
            f.full_name,
            f.email,
            f.employee_id AS ref_id,
            lm.member_since
        FROM library_members lm
        JOIN faculty f ON lm.user_id = f.id AND lm.user_type = 'faculty'

        ORDER BY full_name
    """)
    members = cur.fetchall()
    cur.close()

    return render_template('view_members.html', members=members)


# ─────────────────────────────────────────────────────────────
# ROUTE: Add Member
# ─────────────────────────────────────────────────────────────
@app.route('/members/add', methods=['GET', 'POST'])
def add_member():
    if not is_librarian():
        flash('Only librarians can add members.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Load all students and faculty for the dropdowns
    cur.execute("SELECT id, full_name, email, student_id FROM students ORDER BY full_name")
    students = cur.fetchall()

    cur.execute("SELECT id, full_name, email, employee_id FROM faculty ORDER BY full_name")
    faculty_list = cur.fetchall()

    if request.method == 'POST':
        user_type = request.form['user_type']  # 'student' or 'faculty'
        user_id   = request.form['user_id']    # the id from their table

        # Validation
        if not user_type or not user_id:
            flash('Please select a user type and a person.', 'danger')
            return render_template('add_member.html',
                                   students=students,
                                   faculty_list=faculty_list)

        try:
            cur.execute("""
                INSERT INTO library_members (user_id, user_type)
                VALUES (%s, %s)
            """, (user_id, user_type))
            mysql.connection.commit()
            flash('Member added to library successfully!', 'success')
            return redirect(url_for('view_members'))
        except:
            # UNIQUE constraint triggers if same person added twice
            flash('This person is already a library member.', 'danger')
        finally:
            cur.close()

    cur.close()
    return render_template('add_member.html',
                           students=students,
                           faculty_list=faculty_list)


# ─────────────────────────────────────────────────────────────
# ROUTE: Remove Member
# ─────────────────────────────────────────────────────────────
@app.route('/members/delete/<int:member_id>', methods=['GET', 'POST'])
def delete_member(member_id):
    if not is_librarian():
        flash('Only librarians can remove members.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        try:
            cur.execute("DELETE FROM library_members WHERE id = %s", (member_id,))
            mysql.connection.commit()
            flash('Member removed from library.', 'success')
        except:
            flash('Cannot remove — this member has active borrowed books.', 'danger')
        finally:
            cur.close()
        return redirect(url_for('view_members'))

    else:
        # GET — fetch member details to show on confirmation page
        # We use a UNION again to get their name regardless of type
        cur.execute("""
            SELECT lm.id, lm.user_type, s.full_name, s.email
            FROM library_members lm
            JOIN students s ON lm.user_id = s.id AND lm.user_type = 'student'
            WHERE lm.id = %s

            UNION

            SELECT lm.id, lm.user_type, f.full_name, f.email
            FROM library_members lm
            JOIN faculty f ON lm.user_id = f.id AND lm.user_type = 'faculty'
            WHERE lm.id = %s
        """, (member_id, member_id))
        member = cur.fetchone()
        cur.close()

        if not member:
            flash('Member not found.', 'danger')
            return redirect(url_for('view_members'))

        return render_template('delete_member.html', member=member)

# ═════════════════════════════════════════════════════════════
# STEP 4 — ISSUE BOOK SYSTEM
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# HELPER: Get library_member id for logged in student/faculty
# ─────────────────────────────────────────────────────────────
def get_member_id():
    # Checks if the currently logged in student or faculty
    # is registered as a library member
    # Returns their library_members.id or None if not a member
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM library_members
        WHERE user_id = %s AND user_type = %s
    """, (session['user_id'], session['role']))
    member = cur.fetchone()
    cur.close()
    return member[0] if member else None


# ─────────────────────────────────────────────────────────────
# ROUTE: Issue Book (Librarian directly issues to a member)
# ─────────────────────────────────────────────────────────────
@app.route('/issue', methods=['GET', 'POST'])
def issue_book():
    if not is_librarian():
        flash('Only librarians can issue books directly.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        member_id  = request.form['member_id']
        book_id    = request.form['book_id']
        issue_date = request.form['issue_date']
        due_date   = request.form['due_date']

        # ── CORE LOGIC ────────────────────────────────────────

        # Step 1: Check book exists
        cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book = cur.fetchone()
        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('issue_book'))

        # Step 2: Check availability
        if book[8] <= 0:
            flash(f'Sorry, "{book[1]}" has no available copies.', 'danger')
            return redirect(url_for('issue_book'))

        # Step 3: Check member exists
        cur.execute("SELECT * FROM library_members WHERE id = %s", (member_id,))
        member = cur.fetchone()
        if not member:
            flash('Member not found.', 'danger')
            return redirect(url_for('issue_book'))

        # Step 4: Check due date is after issue date
        if due_date <= issue_date:
            flash('Due date must be after the issue date.', 'danger')
            return redirect(url_for('issue_book'))

        # Step 5: Insert issue record
        cur.execute("""
            INSERT INTO issued_books
                (member_id, book_id, issue_date, due_date, issued_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (member_id, book_id, issue_date, due_date, session['user_id']))

        # Step 6: Reduce available count by 1
        cur.execute("""
            UPDATE books SET available = available - 1
            WHERE book_id = %s
        """, (book_id,))

        mysql.connection.commit()
        flash(f'Book "{book[1]}" issued successfully!', 'success')
        cur.close()
        return redirect(url_for('issue_book'))

    # ── GET: Load page data ───────────────────────────────────

    # Load all library members with their names for the dropdown
    cur.execute("""
        SELECT lm.id, s.full_name, s.student_id, 'student' as type
        FROM library_members lm
        JOIN students s ON lm.user_id = s.id AND lm.user_type = 'student'

        UNION

        SELECT lm.id, f.full_name, f.employee_id, 'faculty' as type
        FROM library_members lm
        JOIN faculty f ON lm.user_id = f.id AND lm.user_type = 'faculty'

        ORDER BY full_name
    """)
    members = cur.fetchall()

    # Only show books that have available copies
    cur.execute("""
        SELECT book_id, title, author, available
        FROM books
        WHERE available > 0
        ORDER BY title
    """)
    books = cur.fetchall()

    # Load all issued books with names using JOIN
    cur.execute("""
        SELECT
            ib.id,
            COALESCE(s.full_name, f.full_name) AS member_name,
            lm.user_type,
            b.title,
            b.author,
            ib.issue_date,
            ib.due_date,
            ib.returned
        FROM issued_books ib
        JOIN library_members lm ON ib.member_id = lm.id
        LEFT JOIN students s ON lm.user_id = s.id AND lm.user_type = 'student'
        LEFT JOIN faculty f ON lm.user_id = f.id AND lm.user_type = 'faculty'
        JOIN books b ON ib.book_id = b.book_id
        ORDER BY ib.created_at DESC
    """)
    # COALESCE returns the first non-null value
    # So if student name is null, it uses faculty name
    issued = cur.fetchall()

    cur.close()
    return render_template('issue_book.html',
                           members=members,
                           books=books,
                           issued=issued)


# ─────────────────────────────────────────────────────────────
# ROUTE: Return a Book
# ─────────────────────────────────────────────────────────────
@app.route('/issue/return/<int:issue_id>')
def return_book(issue_id):
    if not is_librarian():
        flash('Only librarians can process returns.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM issued_books WHERE id = %s", (issue_id,))
    record = cur.fetchone()
    # record tuple:
    # [0]=id [1]=member_id [2]=book_id [3]=issue_date
    # [4]=due_date [5]=returned [6]=issued_by [7]=created_at

    if not record:
        flash('Issue record not found.', 'danger')
    elif record[5]:
        flash('This book has already been returned.', 'warning')
    else:
        # Mark as returned
        cur.execute("""
            UPDATE issued_books SET returned = TRUE
            WHERE id = %s
        """, (issue_id,))
        # Add copy back to available count
        cur.execute("""
            UPDATE books SET available = available + 1
            WHERE book_id = %s
        """, (record[2],))
        mysql.connection.commit()
        flash('Book returned successfully!', 'success')

    cur.close()
    return redirect(url_for('issue_book'))


# ─────────────────────────────────────────────────────────────
# ROUTE: Borrow Request (Student/Faculty requests a book)
# ─────────────────────────────────────────────────────────────
@app.route('/borrow/request', methods=['GET', 'POST'])
def borrow_request():
    if not is_student() and not is_faculty():
        flash('Please log in as a student or faculty.', 'danger')
        return redirect(url_for('login'))

    # Check they are a registered library member
    member_id = get_member_id()
    if not member_id:
        flash('You are not registered as a library member. Please ask the librarian to add you.', 'warning')
        return redirect(url_for('student_dashboard') if is_student() else url_for('faculty_dashboard'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        book_id      = request.form['book_id']
        request_date = request.form['request_date']

        # Check book availability
        cur.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book = cur.fetchone()

        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('borrow_request'))

        if book[8] <= 0:
            flash(f'Sorry, "{book[1]}" is currently not available.', 'danger')
            return redirect(url_for('borrow_request'))

        # Check if they already have a pending request for same book
        cur.execute("""
            SELECT id FROM borrow_requests
            WHERE member_id = %s AND book_id = %s AND status = 'pending'
        """, (member_id, book_id))
        existing = cur.fetchone()

        if existing:
            flash('You already have a pending request for this book.', 'warning')
            return redirect(url_for('borrow_request'))

        # Insert the request
        cur.execute("""
            INSERT INTO borrow_requests (member_id, book_id, request_date)
            VALUES (%s, %s, %s)
        """, (member_id, book_id, request_date))
        mysql.connection.commit()
        flash('Borrow request submitted! The librarian will process it soon.', 'success')
        cur.close()
        return redirect(url_for('borrow_request'))

    # Load available books for dropdown
    cur.execute("""
        SELECT book_id, title, author, available
        FROM books WHERE available > 0
        ORDER BY title
    """)
    books = cur.fetchall()

    # Load this member's own requests
    cur.execute("""
        SELECT
            br.id,
            b.title,
            b.author,
            br.request_date,
            br.status
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.book_id
        WHERE br.member_id = %s
        ORDER BY br.created_at DESC
    """, (member_id,))
    my_requests = cur.fetchall()
    cur.close()

    return render_template('borrow_request.html',
                           books=books,
                           my_requests=my_requests)


# ─────────────────────────────────────────────────────────────
# ROUTE: Manage Borrow Requests (Librarian approves/rejects)
# ─────────────────────────────────────────────────────────────
@app.route('/borrow/manage')
def manage_requests():
    if not is_librarian():
        flash('Only librarians can manage borrow requests.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
            br.id,
            COALESCE(s.full_name, f.full_name) AS member_name,
            lm.user_type,
            b.title,
            b.author,
            b.available,
            br.request_date,
            br.status
        FROM borrow_requests br
        JOIN library_members lm ON br.member_id = lm.id
        LEFT JOIN students s ON lm.user_id = s.id AND lm.user_type = 'student'
        LEFT JOIN faculty f ON lm.user_id = f.id AND lm.user_type = 'faculty'
        JOIN books b ON br.book_id = b.book_id
        ORDER BY
            CASE br.status WHEN 'pending' THEN 1
                           WHEN 'approved' THEN 2
                           ELSE 3 END,
            br.created_at DESC
    """)
    # Pending requests always show first, then approved, then rejected
    requests = cur.fetchall()
    cur.close()

    return render_template('manage_requests.html', requests=requests)


# ─────────────────────────────────────────────────────────────
# ROUTE: Approve a Borrow Request
# ─────────────────────────────────────────────────────────────
@app.route('/borrow/approve/<int:request_id>')
def approve_request(request_id):
    if not is_librarian():
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Load the request
    cur.execute("SELECT * FROM borrow_requests WHERE id = %s", (request_id,))
    req = cur.fetchone()
    # req tuple:
    # [0]=id [1]=member_id [2]=book_id [3]=request_date [4]=status

    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('manage_requests'))

    if req[4] != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('manage_requests'))

    # Check book is still available
    cur.execute("SELECT * FROM books WHERE book_id = %s", (req[2],))
    book = cur.fetchone()

    if book[8] <= 0:
        flash(f'Cannot approve — "{book[1]}" has no available copies.', 'danger')
        return redirect(url_for('manage_requests'))

    from datetime import date, timedelta
    today    = date.today()
    due_date = today + timedelta(days=14)
    # Default 2 week loan period

    # Create the issue record
    cur.execute("""
        INSERT INTO issued_books
            (member_id, book_id, issue_date, due_date, issued_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (req[1], req[2], today, due_date, session['user_id']))

    # Reduce available count
    cur.execute("""
        UPDATE books SET available = available - 1
        WHERE book_id = %s
    """, (req[2],))

    # Mark request as approved
    cur.execute("""
        UPDATE borrow_requests SET status = 'approved'
        WHERE id = %s
    """, (request_id,))

    mysql.connection.commit()
    flash(f'Request approved! "{book[1]}" issued for 14 days.', 'success')
    cur.close()
    return redirect(url_for('manage_requests'))


# ─────────────────────────────────────────────────────────────
# ROUTE: Reject a Borrow Request
# ─────────────────────────────────────────────────────────────
@app.route('/borrow/reject/<int:request_id>')
def reject_request(request_id):
    if not is_librarian():
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE borrow_requests SET status = 'rejected'
        WHERE id = %s AND status = 'pending'
    """, (request_id,))
    mysql.connection.commit()
    cur.close()

    flash('Request rejected.', 'info')
    return redirect(url_for('manage_requests'))

# ─────────────────────────────────────────────────────────────
# START THE APP
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
    # debug=True means:
    # 1. The server auto-restarts when you save changes
    # 2. You see detailed error messages in the browser
    # (Turn debug=False before publishing your project!)