from flask import Flask, request, jsonify
import sqlite3
import jwt
import datetime

SECRET_KEY = "Hexadecigon"

app = Flask(__name__)
DATABASE = "database.db"

# Utility Functions
def verify_token():
    data = request.json
    token = data.get('token')  # Get token from the request body
    if not token:
        return jsonify({"error": "Token is required"}), 401

    try:
        # Decode the token using the secret key
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return decoded_token['rollNo']
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
       
def query_db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(query, args)
    if commit:
        conn.commit()
        conn.close()
        return
    rv = cursor.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv


# Admin Routes
@app.route('/admin/login', methods=['GET'])
def admin_login():
    data = request.json
    if not data:
        return jsonify({"error":"Please provide the admin token"})
    email = data.get('email')
    password = data.get('password')
    admin = query_db("SELECT * FROM admin WHERE email = ? AND password = ?", (email, password), one=True)
    if admin:
        token = admin['token']  # Get token from the database
        return jsonify({"token": token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/admin/new-student', methods=['PUT'])
def create_student():
    data = request.json
    if not data:
        return jsonify({"error": "Please provide the admin token"}), 400
    
    # Ensure the admin token is provided
    token = data.get('token')
    if not token:
        return jsonify({"error": "Admin token is required"}), 400

    # Verify the admin token in the database
    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:  
        return jsonify({"error": "Unauthorized"}), 401
    
    # Check for required fields in the student data
    required_fields = ['rollNo', 'name', 'cnic', 'section', 'password']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    existing_student = query_db("SELECT * FROM students WHERE rollNo = ?", (data['rollNo'],), one=True)
    if existing_student:
        return jsonify({"error": f"Student with rollNo {data['rollNo']} already exists"}), 400

    # Insert the student data into the database
    query_db(
        "INSERT INTO students (rollNo, name, cnic, section, password) VALUES (?, ?, ?, ?, ?)",
        (data['rollNo'], data['name'], data['cnic'], data['section'], data['password']),
        commit=True,
    )
    
    return jsonify({"status": "Student created"}), 200

@app.route('/admin/post-diary', methods=['POST'])
def post_diary():
    data = request.json
    if not data:
        return jsonify({"error": "Please provide the admin token"}), 400
    
    # Ensure the admin token is provided
    token = data.get('token')
    if not token:
        return jsonify({"error": "Admin token is required"}), 400

    # Verify the admin token in the database
    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:  
        return jsonify({"error": "Unauthorized"}), 401

    # Check for required fields: section and text
    required_fields = ['section', 'text']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    # Insert the diary entry into the database
    query_db(
        "INSERT INTO diaries (section, text) VALUES (?, ?)",
        (data['section'], data['text']),
        commit=True,
    )
    
    return jsonify({"status": "Diary posted"}), 200

@app.route('/admin/get-section-students', methods=['GET'])
def get_section_students():
    data = request.json
    if not data:
        return jsonify({"error": "Please provide the admin token"}), 400
    
    # Ensure the admin token is provided
    token = data.get('token')
    if not token:
        return jsonify({"error": "Admin token is required"}), 400

    # Verify the admin token in the database
    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:  
        return jsonify({"error": "Unauthorized"}), 401
    
    # Check for the required 'section' field
    section = data.get('section')
    if not section:
        return jsonify({"error": "Section is required"}), 400

    # Get students from the specified section
    students = query_db("SELECT * FROM students WHERE section = ?", (section,))
    
    return jsonify([dict(student) for student in students]), 200

@app.route('/admin/mark-attendance', methods=['PUT'])
def mark_attendance():
    data = request.json
    if not data:
        return jsonify({"error": "Please provide the admin token"}), 400
    
    # Ensure the admin token is provided
    token = data.get('token')
    if not token:
        return jsonify({"error": "Admin token is required"}), 400

    # Verify the admin token in the database
    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:  
        return jsonify({"error": "Unauthorized"}), 401

    # Ensure the 'presents' field is provided
    presents = data.get('presents')
    if not presents:
        return jsonify({"error": "Presents list is required"}), 400
    
    # Ensure 'presents' is a list and not empty
    if not isinstance(presents, list) or not presents:
        return jsonify({"error": "Presents must be a non-empty list of objects with 'rollNo' and 'present'"}), 400
    
    # Validate each item in presents array
    invalid_data = []
    for entry in presents:
        if 'rollNo' not in entry or 'present' not in entry:
            invalid_data.append(entry)
        elif not isinstance(entry['present'], bool):
            invalid_data.append(entry)

    if invalid_data:
        return jsonify({"error": f"Invalid entries in presents: {invalid_data}"}), 400
    
    # Check if all roll numbers are valid
    invalid_roll_numbers = []
    for entry in presents:
        rollNo = entry['rollNo']
        student = query_db("SELECT 1 FROM students WHERE rollNo = ?", (rollNo,), one=True)
        if not student:
            invalid_roll_numbers.append(rollNo)
    
    if invalid_roll_numbers:
        return jsonify({"error": f"Invalid roll numbers: {', '.join(map(str, invalid_roll_numbers))}"}), 400

    # Mark attendance for each roll number in the presents list
    for entry in presents:
        rollNo = entry['rollNo']
        present = entry['present']
        query_db(
            "INSERT INTO attendance (rollNo, date, present) VALUES (?, DATE('now'), ?)",
            (rollNo, present),
            commit=True,
        )
    
    return jsonify({"status": "Attendance marked"}), 200

@app.route('/admin/get-all-students', methods=['GET'])
def get_all_students():
    data = request.json
    if not data:
        return jsonify({"error": "Please provide the admin token"}), 400

    token = data.get('token')

    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:  
        return jsonify({"error": "Unauthorized"}), 401
    
    students = query_db("SELECT * FROM students")
    return jsonify([dict(student) for student in students]), 200

@app.route('/admin/mark-grades', methods=['PUT'])
def mark_grades():
    data = request.json
    
    # Check if data is provided
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Ensure the admin token is provided
    token = data.get('token')
    if not token:
        return jsonify({"error": "Admin token is required"}), 400
    
    # Verify the admin token in the database
    admin_token = query_db("SELECT token FROM admin WHERE token = ?", (token,), one=True)
    if not admin_token or admin_token['token'] != token:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Check for required fields and validate
    required_fields = ['rollNo', 'term', 'percentage']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    
    if missing_fields:
        return jsonify({"error": f"Missing or empty fields: {', '.join(missing_fields)}"}), 400
    
    # Check if 'percentage' is a valid number between 0 and 100
    try:
        percentage = float(data['percentage'])
        if not (0 <= percentage <= 100):
            return jsonify({"error": "Percentage must be between 0 and 100"}), 400
    except ValueError:
        return jsonify({"error": "Percentage must be a valid number"}), 400

    # Check if the term for the given rollNo already exists
    existing_grade = query_db(
        "SELECT 1 FROM grades WHERE rollNo = ? AND term = ?",
        (data['rollNo'], data['term']),
        one=True
    )

    if existing_grade:
        # If the grade already exists for this rollNo and term, update it
        query_db(
            "UPDATE grades SET percentage = ? WHERE rollNo = ? AND term = ?",
            (data['percentage'], data['rollNo'], data['term']),
            commit=True
        )
        return jsonify({"status": "Grade updated"}), 200
    else:
        # If no existing grade, insert a new record
        query_db(
            "INSERT INTO grades (rollNo, term, percentage) VALUES (?, ?, ?)",
            (data['rollNo'], data['term'], data['percentage']),
            commit=True
        )
        return jsonify({"status": "Grade marked"}), 200


# Student Routes
@app.route('/student/get-diary', methods=['GET'])
def get_diary():
    rollNo = verify_token()  # Verify token and get rollNo
    if isinstance(rollNo, tuple):  # If error message is returned, stop the request
        return rollNo
    
    # Fetch the section for the student using the rollNo
    student = query_db("SELECT section FROM students WHERE rollNo = ?", (rollNo,), one=True)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    section = student['section']  # Extract section from the student record
    
    # Fetch the diaries for the student's section
    diaries = query_db("SELECT * FROM diaries WHERE section = ?", (section,))
    
    return jsonify([dict(diary) for diary in diaries]), 200

@app.route('/student/get-attendance', methods=['GET'])
def get_attendance():
    rollNo = verify_token()  # Verify token and get rollNo
    if isinstance(rollNo, tuple):  # If error message is returned, stop the request
        return rollNo
    
    data = request.json
    attendance = query_db("SELECT * FROM attendance WHERE rollNo = ?", (rollNo,))
    return jsonify([dict(record) for record in attendance]), 200

@app.route('/student/get-grades', methods=['GET'])
def get_grades():
    rollNo = verify_token()  # Verify token and get rollNo
    if isinstance(rollNo, tuple):  # If error message is returned, stop the request
        return rollNo
    
    data = request.json
    grades = query_db("SELECT * FROM grades WHERE rollNo = ?", (rollNo,))
    return jsonify([dict(grade) for grade in grades]), 200

# Main Function
if __name__ == '__main__':
    # Initialize Database
    with sqlite3.connect(DATABASE) as conn:
        with open('schema.sql') as f:
            conn.executescript(f.read())
    app.run(debug=True)
