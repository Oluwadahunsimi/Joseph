from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import base64
import io
from datetime import datetime
import MySQLdb.cursors


app = Flask(__name__)

app.secret_key = 'your_secret_key'

app.config['MYSQL_HOST'] = 'Joeboy.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'Joeboy'
app.config['MYSQL_PASSWORD'] = 'titilope'
app.config['MYSQL_DB'] = 'Joeboy$academic_support_system'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

def create_tables():
    with app.app_context():
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usersss (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(100),
                    name VARCHAR(255),
                    matric_no VARCHAR(50),
                    level VARCHAR(50)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    course_name VARCHAR(255) NOT NULL,
                    lecturer_id INT NOT NULL,
                    FOREIGN KEY (lecturer_id) REFERENCES usersss(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    student_id INT NOT NULL,
                    lecturer_id INT NOT NULL,
                    appointment_time DATETIME NOT NULL,
                    reason VARCHAR(255),
                    feedback TEXT,
                    PRIMARY KEY (id),
                    FOREIGN KEY (student_id) REFERENCES usersss(id),
                    FOREIGN KEY (lecturer_id) REFERENCES usersss(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    appointment_id INT UNSIGNED NOT NULL,
                    lecturer_id INT NOT NULL,
                    student_id INT NOT NULL,
                    student_name VARCHAR(255),
                    student_matric_no VARCHAR(50),
                    student_level VARCHAR(50),
                    reason VARCHAR(255),
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES usersss(id),
                    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
                    FOREIGN KEY (lecturer_id) REFERENCES usersss(id),
                    FOREIGN KEY (student_id) REFERENCES usersss(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    course_id INT NOT NULL,
                    attendance_date DATE NOT NULL,
                    present TINYINT(1) NOT NULL DEFAULT 0,
                    mark FLOAT NOT NULL DEFAULT 0,
                    FOREIGN KEY (student_id) REFERENCES usersss(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )
            """)
            mysql.connection.commit()
            cur.close()
        except AttributeError as e:
            print(f"Error: {e}. Check your MySQL configuration and ensure the MySQL server is running.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


@app.route('/')
def landing_page():
    if 'user_id' in session:
        return redirect(url_for('landing_after_login'))
    return render_template('landing.html')

@app.route('/home')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    role = request.form['role']

    if password == confirm_password:
        hashed_password = generate_password_hash(password)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO usersss (email, password, role) VALUES (%s, %s, %s)", (email, hashed_password, role))
        mysql.connection.commit()
        cur.close()
        flash("Signup successful. You can now login.")
        return redirect(url_for('home'))
    else:
        flash("Passwords do not match. Try again.")
        return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usersss WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_abbr'] = user['email'][:5].upper()
            flash(f"You were successfully logged in as {session['user_abbr']}")
            if user['role'] == 'Student':
                return redirect(url_for('student_dashboard'))
            elif user['role'] == 'Lecturer':
                return redirect(url_for('lecturer_dashboard'))
            elif user['role'] == 'Parent':
                return redirect(url_for('parent_dashboard'))
        else:
            flash("Invalid login credentials. Please try again.")
    except MySQLdb.Error as e:
        flash(f"Database connection error: {e}")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You were successfully logged out")
    return render_template('landing.html')

@app.route('/landing2')
def landing_after_login():
    if 'user_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT email FROM usersss WHERE id = %s", [session['user_id']])
        user = cur.fetchone()
        cur.close()
        user_abbr = user['email'][:5].upper() if user else ''
        return render_template('landing.html', user_abbr=user_abbr)
    else:
        return redirect(url_for('home'))

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    cur = mysql.connection.cursor()
    if session['role'] == 'Lecturer':
        lecturer_id = session['user_id']
        cur.execute("""
            SELECT notifications.*, appointments.appointment_time,
                   appointments.reason,
                   usersss.email AS student_email,
                   usersss.name AS student_name,
                   usersss.matric_no AS student_matric_no,
                   usersss.level AS student_level
            FROM notifications
            JOIN appointments ON notifications.appointment_id = appointments.id
            JOIN usersss ON appointments.student_id = usersss.id
            WHERE notifications.lecturer_id = %s AND appointments.feedback IS NULL
        """, [lecturer_id])
    elif session['role'] == 'Student':
        student_id = session['user_id']
        cur.execute("""
            SELECT notifications.*, appointments.appointment_time,
                   appointments.feedback,
                   usersss.email AS lecturer_email
            FROM notifications
            JOIN appointments ON notifications.appointment_id = appointments.id
            JOIN usersss ON appointments.lecturer_id = usersss.id
            WHERE notifications.student_id = %s
        """, [student_id])
    notifications = cur.fetchall()
    cur.close()
    return render_template('notifications.html', notifications=notifications)

@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    if 'user_id' not in session or session['role'] != 'Lecturer':
        return redirect(url_for('home'))
    feedback = request.form['feedback']
    appointment_id = request.form['appointment_id']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE appointments SET feedback = %s WHERE id = %s AND lecturer_id = %s",
                (feedback, appointment_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash("Feedback sent successfully.")
    return redirect(url_for('notifications'))

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, role FROM usersss WHERE role = 'Lecturer'")
    lecturers = cur.fetchall()
    if request.method == 'POST':
        student_id = session['user_id']
        lecturer_id = request.form['lecturer_id']
        appointment_time = request.form['appointment_time']
        reason = request.form['reason']
        cur.execute("SELECT id FROM usersss WHERE id = %s AND role = 'Lecturer'", (lecturer_id,))
        lecturer = cur.fetchone()
        if not lecturer:
            flash("Selected lecturer does not exist.")
            return redirect(url_for('appointments'))
        cur.execute("INSERT INTO appointments (student_id, lecturer_id, appointment_time, reason) VALUES (%s, %s, %s, %s)",
                    (student_id, lecturer_id, appointment_time, reason))
        mysql.connection.commit()
        appointment_id = cur.lastrowid
        cur.execute("SELECT name, matric_no, level FROM usersss WHERE id = %s", (student_id,))
        student_info = cur.fetchone()
        student_name = student_info['name']
        student_matric_no = student_info['matric_no']
        student_level = student_info['level']
        cur.execute("INSERT INTO notifications (user_id, message, is_read, appointment_id, lecturer_id, student_id, student_name, student_matric_no, student_level, reason) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (lecturer_id, reason, False, appointment_id, lecturer_id, student_id, student_name, student_matric_no, student_level, reason))
        mysql.connection.commit()
        cur.close()
        flash("Appointment requested successfully.")
        return redirect(url_for('appointments'))
    cur.close()
    return render_template('appoint.html', lecturers=lecturers)

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/scan_qr', methods=['GET', 'POST'])
def scan_qr():
    if 'user_id' not in session or session['role'] != 'Student':
        return redirect(url_for('home'))

    if request.method == 'POST':
        data = request.form.get('data')  # Extract form data
        decoded_text = data  # Get the decoded text from form data

        if decoded_text:
            # Process the decoded text here
            session['qr_data'] = decoded_text
            return redirect(url_for('mark_attendance_direct'))
        else:
            flash('No QR code data found', 'danger')
            return redirect(url_for('scan'))

    return render_template('scan.html')
@app.route('/mark_attendance_direct', methods=['POST'])
def mark_attendance_direct():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    decoded_text = session.get('qr_data')

    if decoded_text:
        # Process the decoded text here
        session.pop('qr_data', None)  # Clear the QR data from session
        # Mark attendance logic here
        flash('Attendance marked successfully.', 'success')
        return redirect(url_for('attendance_success'))  # Redirect to the success page
    else:
        flash('No QR code data found', 'danger')
        return redirect(url_for('scan'))

@app.route('/attendance_success')
def attendance_success():
    return render_template('sucess.html')



@app.route('/generate_qr', methods=['GET', 'POST'])
def generate_qr():
    if 'user_id' not in session or session['role'] != 'Lecturer':
        return redirect(url_for('home'))

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        date = request.form.get('date')

        if not course_id or not date:
            return "Bad Request: Missing course_id or date", 400

        cur = mysql.connection.cursor()
        cur.execute("SELECT course_name FROM courses WHERE id = %s", (course_id,))
        course = cur.fetchone()

        if not course:
            return "Bad Request: Invalid course_id", 400

        course_name = course['course_name']
        lecturer_id = session['user_id']
        qr_data = f"{course_id},{course_name},{lecturer_id},{date}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill='black', back_color='white')

        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()

        cur.close()
        return render_template('generate_qr_code.html', qr_code=img_str)

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM courses WHERE lecturer_id = %s", [session['user_id']])
    courses = cur.fetchall()
    cur.close()
    return render_template('generate_qr_code.html', courses=courses)


@app.route('/get_attendance')
def get_attendance():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.name, u.level, u.matric_no, c.course_name, a.present,
               COUNT(a.present) OVER (PARTITION BY u.id, c.id) AS total_present
        FROM attendance a
        JOIN usersss u ON a.student_id = u.id
        JOIN courses c ON a.course_id = c.id
    """)
    attendance_records = cur.fetchall()
    cur.close()

    return render_template('view_attendance.html', attendance_records=attendance_records)


@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():
    data = request.form  # Assuming form data is sent via POST
    student_id = data['student_id']
    course_id = data['course_id']

    # Validate course_id existence before proceeding
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM courses WHERE id = %s", (course_id,))
    course = cur.fetchone()

    if not course:
        cur.close()
        return jsonify({'status': 'error', 'message': 'Course ID does not exist'}), 404

    # Insert attendance record
    cur.execute("""
        INSERT INTO attendance (student_id, course_id, attendance_date, present)
        VALUES (%s, %s, %s, TRUE)
    """, (student_id, course_id, datetime.date.today()))
    mysql.connection.commit()

    # Check the number of times the student has been marked present
    cur.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE student_id = %s AND course_id = %s AND present = TRUE
    """, (student_id, course_id))
    present_count = cur.fetchone()[0]

    # Fetch additional details
    cur.execute("""
        SELECT matric_no, level, courses.name as course_name
        FROM students
        JOIN courses ON students.course_id = courses.id
        WHERE students.id = %s
    """, (student_id,))
    student_details = cur.fetchone()
    cur.close()

    if not student_details:
        return jsonify({'status': 'error', 'message': 'Student details not found'}), 404

    matric_no = student_details['matric_no']
    level = student_details['level']
    course_name = student_details['course_name']

    # Send notification if the student is late
    if present_count == 0:  # Assuming student is late if present_count is zero
        send_notification_to_lecturer_and_parent(student_id, course_id, matric_no, level, course_name)

    return jsonify({'status': 'success'}), 200


def send_notification_to_lecturer_and_parent(student_id, course_id, matric_no, level):
    cur = mysql.connection.cursor()

    # Get student details
    cur.execute("SELECT name FROM usersss WHERE id = %s", (student_id,))
    student = cur.fetchone()

    # Get lecturer and parent details
    cur.execute("""
        SELECT l.email AS lecturer_email, p.email AS parent_email
        FROM courses c
        JOIN usersss l ON c.lecturer_id = l.id
        JOIN parents p ON p.student_id = %s
        WHERE c.id = %s
    """, (student_id, course_id))
    contacts = cur.fetchone()

    lecturer_email = contacts['lecturer_email']
    parent_email = contacts['parent_email']

    # Create notification messages
    message = f"Student {student['name']} (Matric No: {matric_no}, Level: {level}) missed a class."

    # Insert notifications into the database
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (student_id, message))
    mysql.connection.commit()

    # Send email notifications (assuming you have an email sending function)
    send_email(lecturer_email, 'Student Missed Class', message)
    send_email(parent_email, 'Student Missed Class', message)

    cur.close()

@app.route('/add_courses')
def add_courses():
    if 'user_id' not in session or session['role'] != 'Lecturer':
        return redirect(url_for('home'))

    lecturer_id = session['user_id']
    courses = ['CMP 401', 'CMP 407', 'CMP 314']

    cur = mysql.connection.cursor()
    for course_name in courses:
        cur.execute("INSERT INTO courses (course_name, lecturer_id) VALUES (%s, %s)", (course_name, lecturer_id))
    mysql.connection.commit()
    cur.close()

    return "Courses added successfully!"


def notify_absentees():
    with app.app_context():
        cur = mysql.connection.cursor()
        attendance_date = datetime.now().date()

        cur.execute("""
            SELECT usersss.id, usersss.email, usersss.role, courses.course_name
            FROM usersss
            JOIN attendance ON usersss.id = attendance.student_id
            JOIN courses ON attendance.course_id = courses.id
            WHERE attendance.present = 0 AND attendance.attendance_date = %s
        """, [attendance_date])
        absentees = cur.fetchall()

        for absentee in absentees:
            lecturer_email = get_lecturer_email(absentee['course_id'])
            parent_email = get_parent_email(absentee['id'])
            send_email(lecturer_email, "Student Absence Notification", f"Student {absentee['email']} missed the class for {absentee['course_name']} on {attendance_date}")
            send_email(parent_email, "Student Absence Notification", f"Your child {absentee['email']} missed the class for {absentee['course_name']} on {attendance_date}")

        cur.close()

def get_lecturer_email(course_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT usersss.email FROM usersss JOIN courses ON usersss.id = courses.lecturer_id WHERE courses.id = %s", [course_id])
    lecturer = cur.fetchone()
    cur.close()
    return lecturer['email'] if lecturer else None

def get_parent_email(student_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT email FROM usersss WHERE role = 'Parent' AND id = %s", [student_id])
    parent = cur.fetchone()
    cur.close()
    return parent['email'] if parent else None

def send_email(to, subject, body):
    print(f"Sending email to {to} with subject {subject} and body {body}")

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('landing2.html', user_abbr=session.get('user_abbr'))

@app.route('/lecturer_dashboard')
def lecturer_dashboard():
    return render_template('parent.html', user_abbr=session.get('user_abbr'))

@app.route('/parent_dashboard')
def parent_dashboard():
    return render_template('parents.html', user_abbr=session.get('user_abbr'))


if __name__ == '__main__':
    app.run(debug=True)



