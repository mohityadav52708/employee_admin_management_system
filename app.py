from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import datetime
import bcrypt
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import cloudinary
import xlsxwriter
import cloudinary.uploader
from flask import send_file
import pandas as pd
from bson.objectid import ObjectId
from bson import ObjectId
import datetime
from datetime import datetime, timedelta
from datetime import datetime
from io import BytesIO
from flask_cors import CORS
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB Configuration
uri = "mongodb+srv://whitedevil7628:mohit038@cluster1.oohsn.mongodb.net/myDatabase?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["endsem"]
users_collection = db["users"]
attendance_collection = db["attendance"]
# Email Configuration
app.config['MAIL_USERNAME'] = 'librarymanagementprjoect@gmail.com'
app.config['MAIL_PASSWORD'] = 'ykqy zkvd zzak ujpa'
CORS(app)  # Enable CORS for front-end communication
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
cloudinary.config(
    cloud_name="dxoxq2pe1",
    api_key="329235461831941",
    api_secret="--HbEmUPXfkxokCWL0NWQmbvNaY"
)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        flash("Please log in to update your profile.", "danger")
        return redirect(url_for('login'))

    user = users_collection.find_one({"email": session['user']})

    # Fetch notifications from home route logic
    user_email = session['user']

    task_status_counts = {
        "Pending": db.tasks.count_documents({"employee_email": user_email, "status": "Pending"})
    }

    leave_status_counts = {
        "Pending": db.leave_requests.count_documents({"employee_email": user_email, "status": "Pending"})
    }

    review_status_counts = {
        "Pending": db.complaints.count_documents({"employee_email": user_email, "status": "Pending"})
    }

    if request.method == 'POST':
        username = request.form['username']
        department = request.form['department']
        phone = request.form['phone']

        update_data = {
            "username": username,
            "department": department,
            "phone": phone
        }

        # ✅ Upload Profile Image to Cloudinary
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file:
                upload_result = cloudinary.uploader.upload(file)
                profile_image_url = upload_result['secure_url']  # Cloudinary URL
                update_data["profile_image"] = profile_image_url

        # ✅ Update User in MongoDB
        users_collection.update_one({"email": session['user']}, {"$set": update_data})
        user = users_collection.find_one({"email": session['user']})
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template(
        'profile.html',
        user=user,
        username=user.get('username', 'User'),
        task_status_counts=task_status_counts,
        leave_status_counts=leave_status_counts,
        review_status_counts=review_status_counts
    )

@app.route('/admin/employees')
def admin_employees():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))

    employees = list(users_collection.find({"role": "employee"}))
    return render_template('admin_employees.html', employees=employees)

# Helper Functions
def send_email(email, subject, body):
    port = 587
    smtp_server = "smtp.gmail.com"
    sender_email = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())

def generate_otp():
    return ''.join(random.choices(string.digits, k=6)) 


# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username=request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # Get role (admin or employee)
        
        # Check if the role is admin and if an admin already exists
        if role == 'admin':
            admin_exists = users_collection.find_one({"role": "admin"})
            if admin_exists:
                flash('An admin already exists. Only one admin is allowed.', 'danger')
                return redirect(url_for('signup')) 
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        if users_collection.find_one({"email": email}):
            flash('Email already registered.', 'danger')
        else:
            if role == 'admin' or users_collection.count_documents({}) == 0:
                role = 'admin'
            else:
                role = 'employee'
            otp = generate_otp()
            # role = 'admin' if users_collection.count_documents({}) == 0 else 'employee'
            users_collection.insert_one({
                "username":username,
                "email": email,
                "password": hashed_password,
                "otp": otp,
                "verified": False,
                "role": role
            })
            send_email(email, "Email Verification", f"Your OTP is: {otp}")
            flash('OTP sent to your email.', 'info')
            return redirect(url_for('verify_otp', email=email))
    return render_template('signup.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    if request.method == 'POST':
        otp = request.form['otp']
        user = users_collection.find_one({"email": email})

        if user and user['otp'] == otp:
            users_collection.update_one({"email": email}, {"$set": {"verified": True}})
            flash('Email verified successfully.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP.', 'danger')
    return render_template('verify_otp.html', email=email)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = users_collection.find_one({"email": email})

        if user:
            otp = generate_otp()
            users_collection.update_one({"email": email}, {"$set": {"otp": otp}})
            send_email(email, "Password Reset", f"Your OTP for password reset is: {otp}")
            flash('OTP sent to your email.', 'info')
            return redirect(url_for('reset_password', email=email))
        else:
            flash('Email not found.', 'danger')
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email')
    if request.method == 'POST':
        otp = request.form['otp']
        new_password = request.form['new_password']
        user = users_collection.find_one({"email": email})

        if user and user['otp'] == otp:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            users_collection.update_one({"email": email}, {"$set": {"password": hashed_password, "otp": None}})
            flash('Password reset successful.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP.', 'danger')
    return render_template('reset_password.html', email=email)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        portal = request.args.get('portal', 'employee')  # Default portal is 'employee'

        user = users_collection.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['user'] = email
            session['role'] = user.get('role', 'employee')

            # Access control: Ensure correct portal login
            if portal == 'admin' and session['role'] != 'admin':
                return render_template('login.html', alert_message="Access denied. Only admin can access this page.")

            if portal == 'employee' and session['role'] != 'employee':
                return render_template('login.html', alert_message="Access denied. Only employees can access this page.")

            # Mark employee as Online & log attendance
            if session['role'] == 'employee':
                today = datetime.today().strftime('%Y-%m-%d')
                login_time = datetime.now()

                attendance_collection.update_one(
                    {"email": email, "date": today},
                    {"$set": {"status": "Online", "login_time": login_time}},
                    upsert=True
                )

            # Redirect based on user role
            return redirect(url_for('admin_home' if session['role'] == 'admin' else 'home'))

        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/request-leave', methods=['GET', 'POST'])
def request_leave():
    if 'user' in session and session.get('role') == 'employee':
        # Fetch leave history for the employee
        employee_email = session['user']
        leave_requests = db.leave_requests.find({"employee_email": employee_email})
        user = users_collection.find_one({"email": session['user']})
        username = user['username']
        # Convert MongoDB cursor to a list for easy rendering in template
        leave_requests_list = list(leave_requests)

        if request.method == 'POST':
            leave_type = request.form['leave_type']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            reason = request.form['reason']

            leave_request = {
                "employee_email": session['user'],
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "status": "Pending"
            }

            # Insert the leave request into the database
            db.leave_requests.insert_one(leave_request)

            # Send email to admin about the leave request
            admin = users_collection.find_one({"role": "admin"})
            if admin:
                send_email(admin['email'], "New Leave Request", f"A new leave request has been made by {session['user']}. Please review it.")
            
            flash('Leave request submitted successfully!', 'success')
            return redirect(url_for('request_leave'))
            
        # Render the page with the leave requests
        return render_template('request_leave.html', leave_requests=leave_requests_list,username=username)

    else:
        flash('You must be logged in as an employee to request leave.', 'danger')
        return redirect(url_for('login'))

@app.route('/admin-leave-requests', methods=['GET', 'POST'])
def admin_leave_requests():
    if 'user' in session and session.get('role') == 'admin':
        pending_leave_requests = db.leave_requests.find({"status": "Pending"})

        # Now: Filter approved or rejected leaves of last 15 days
        all_leave_requests = list(db.leave_requests.find({"status": {"$in": ["Approved", "Rejected"]}}))

        # Prepare a list for recent leave history
        recent_leave_history = []
        today = datetime.today()
        fifteen_days_ago = today - timedelta(days=15)

        for leave in all_leave_requests:
            try:
                # Parse start_date string into datetime
                leave_start_date = datetime.strptime(leave['start_date'], "%Y-%m-%d")

                # Check if leave is in the last 15 days
                if leave_start_date >= fifteen_days_ago:
                    recent_leave_history.append(leave)

            except Exception as e:
                print(f"Error parsing leave start_date: {e}")

        if request.method == 'POST':
            leave_id = request.form['leave_id']
            action = request.form['action']

            leave_request = db.leave_requests.find_one({"_id": ObjectId(leave_id)})
            if leave_request:
                if action == 'approve':
                    db.leave_requests.update_one({"_id": ObjectId(leave_id)}, {"$set": {"status": "Approved"}})
                    send_email(leave_request['employee_email'], "Leave Request Approved",
                               f"Your leave request from {leave_request['start_date']} to {leave_request['end_date']} has been approved.")
                elif action == 'reject':
                    db.leave_requests.update_one({"_id": ObjectId(leave_id)}, {"$set": {"status": "Rejected"}})
                    send_email(leave_request['employee_email'], "Leave Request Rejected",
                               f"Your leave request from {leave_request['start_date']} to {leave_request['end_date']} has been rejected.")

                flash('Leave request processed successfully.', 'success')
                return redirect(url_for('admin_leave_requests'))

        user = users_collection.find_one({"email": session['user']})
        username = user['username']

        return render_template('admin_leave_requests.html',
                               leave_requests=pending_leave_requests,
                               leave_history=recent_leave_history,
                               username=username)
    else:
        flash('Access denied. Only admin can view leave requests.', 'danger')
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if 'user' in session:
        email = session['user']
        today = datetime.today().strftime('%Y-%m-%d')

        # Mark employee as Offline & log logout time
        login_record = attendance_collection.find_one({"email": email, "date": today})
        if login_record and "login_time" in login_record:
            logout_time = datetime.now()
            duration = logout_time - login_record["login_time"]

            attendance_collection.update_one(
                {"email": email, "date": today},
                {"$set": {"status": "Offline", "logout_time": logout_time, "duration": str(duration)}}
            )

    session.clear()
    return redirect(url_for('login'))
@app.route('/admin_home')
def admin_home():
    if 'user' in session and session.get('role') == 'admin':
        today = datetime.today().strftime('%Y-%m-%d')

        # Currently online employees
        online_employees = list(attendance_collection.find({"status": "Online", "date": today}))
        for emp in online_employees:
            emp_user = users_collection.find_one({"email": emp["email"]})
            emp["name"] = emp_user.get("username", "N/A")
            emp["duration"] = str(datetime.now() - emp.get("login_time"))

        # Attendance records for online employees only
        attendance_records = [
            {
                "email": emp["email"],
                "date": emp["date"],
                "login_time": emp.get("login_time"),
                "logout_time": None,
                "duration": emp["duration"],
                "status": "Online"
            } for emp in online_employees
        ]

        offline_count = attendance_collection.count_documents({"status": "Offline", "date": today})
        username = users_collection.find_one({"email": session["user"]})["username"]

        # Online names & emails
        online_names_emails = [
            f"{emp['email']} ({emp['name']})"
            for emp in online_employees
        ]
        online_count = len(online_employees)

        # ✅ Notification counts
        task_status_counts = {
            "Pending": db.tasks.count_documents({"status": "Pending"}),
            "In Progress": db.tasks.count_documents({"status": "In Progress"}),
            "Completed": db.tasks.count_documents({"status": "Completed"})
        }

        leave_status_counts = {
            "Pending": db.leave_requests.count_documents({"status": "Pending"}),
            "Approved": db.leave_requests.count_documents({"status": "Approved"}),
            "Rejected": db.leave_requests.count_documents({"status": "Rejected"})
        }

        review_status_counts = {
            "Pending": db.complaints.count_documents({"status": "Pending"}),
            "Resolved": db.complaints.count_documents({"status": "Resolved"}),
            "Rejected": db.complaints.count_documents({"status": "Rejected"})
        }

        attendance_counts = {
            "Online": online_count,
            "Offline": offline_count
        }

        return render_template(
            'admin_home.html',
            online_employees=online_employees,
            online_count=online_count,
            offline_count=offline_count,
            attendance_records=attendance_records,
            username=username,
            online_names_emails=online_names_emails,
            task_status_counts=task_status_counts,
            leave_status_counts=leave_status_counts,
            review_status_counts=review_status_counts,
            attendance_counts=attendance_counts
        )
    else:
        flash('Access denied. Only admin can access this page.', 'danger')
        return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user' in session and session.get('role') == 'employee':
        user_email = session['user']
        user = users_collection.find_one({"email": user_email})
        username = user.get('username', 'User')

        today = datetime.today().strftime('%Y-%m-%d')
        online_employees = []
        attendance_records = []

        # Online session info
        online_record = attendance_collection.find_one({
            "email": user_email,
            "status": "Online",
            "date": today
        })

        if online_record:
            online_employees.append({
                "email": user_email,
                "login_time": online_record.get("login_time"),
                "date": online_record.get("date"),
                "duration": str(datetime.now() - online_record.get("login_time")),
                "status": "Online"
            })
            attendance_records = online_employees

        # ✅ Employee-specific notifications (FIXED)
        task_status_counts = {
            "Pending": db.tasks.count_documents({"employee_email": user_email, "status": "Pending"})
        }

        leave_status_counts = {
            "Pending": db.leave_requests.count_documents({"employee_email": user_email, "status": "Pending"})
        }

        review_status_counts = {
            "Pending": db.complaints.count_documents({"employee_email": user_email, "status": "Pending"})
        }

        return render_template(
            'home.html',
            username=username,
            user=user,
            online_employees=online_employees,
            attendance_records=attendance_records,
            task_status_counts=task_status_counts,
            leave_status_counts=leave_status_counts,
            review_status_counts=review_status_counts,
            active_page='home'
        )
    else:
        flash('Access denied. Please log in as an employee.', 'danger')
        return redirect(url_for('login'))



@app.route('/complaints', methods=['GET', 'POST'])
def complaints():
    if 'user' in session and session.get('role') == 'employee':
        if request.method == 'POST':
            complaint_title = request.form['title']
            complaint_description = request.form['description']
            timestamp = datetime.now()

            # Insert the complaint into the database
            complaint = {
                "employee_email": session['user'],
                "title": complaint_title,
                "description": complaint_description,
                "status": "Pending",
                "response": None,
                "timestamp": timestamp
            }
            db.complaints.insert_one(complaint)

            flash('Complaint submitted successfully!', 'success')
            return redirect(url_for('complaints'))
        user = users_collection.find_one({"email": session['user']})
        username = user['username']
        # Retrieve all complaints submitted by the current employee
        user_complaints = list(db.complaints.find({"employee_email": session['user']}))
        return render_template('complaints.html', complaints=user_complaints,username=username)
    else:
        flash('You must be logged in as an employee to submit complaints.', 'danger')
        return redirect(url_for('login'))




@app.route('/admin-complaints', methods=['GET', 'POST'])
def admin_complaints():
    if 'user' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            complaint_id = request.form['complaint_id']
            action = request.form['action']
            response = request.form.get('response', '')  # Optional response from admin

            # Find the complaint and update the status and response
            if action == 'resolve':
                db.complaints.update_one(
                    {"_id": ObjectId(complaint_id)},
                    {"$set": {"status": "Resolved", "response": response}}
                )
                flash('Complaint resolved successfully.', 'success')
            elif action == 'reject':
                db.complaints.update_one(
                    {"_id": ObjectId(complaint_id)},
                    {"$set": {"status": "Rejected", "response": response}}
                )
                flash('Complaint rejected successfully.', 'info')
            return redirect(url_for('admin_complaints'))
        
        # Retrieve all pending complaints
        complaints = list(db.complaints.find({"status": "Pending"}))
        user = users_collection.find_one({"email": session['user']})
        username = user['username']
        return render_template('admin_complaints.html', complaints=complaints,username=username)
    else:
        flash('Access denied. Only admin can manage complaints.', 'danger')
        return redirect(url_for('login'))
@app.route('/employee-details', methods=['GET'])
def employee_details():
    if 'user' in session and session.get('role') == 'admin':
        # Fetch all employee details (excluding admin)
        employees = list(users_collection.find({"role": "employee"}))
        today = datetime.today().strftime('%Y-%m-%d')
        attendance_records = {
            record["email"]: record["status"]
            for record in attendance_collection.find({"date": today})
        }

        user = users_collection.find_one({"email": session['user']})
        username = user['username']

        # Append attendance status to each employee record
        for emp in employees:
            emp["availability"] = attendance_records.get(emp["email"], "Offline")
        return render_template('employee_details.html', employees=employees, username=username)
    else:
        flash('Access denied. Only admin can view employee details.', 'danger')
        return redirect(url_for('login'))

@app.route('/assign-task', methods=['POST'])
def assign_task():
    if 'user' in session and session.get('role') == 'admin':
        employee_email = request.form['employee_email']
        task_title = request.form['task_title']
        task_description = request.form['task_description']
        due_date = request.form['due_date']

        db.tasks.insert_one({
            "employee_email": employee_email,
            "title": task_title,
            "description": task_description,
            "due_date": due_date,
            "status": "Pending"
        })

        flash('Task assigned successfully!', 'success')
        return redirect(url_for('admin_home'))

@app.route('/tasks', methods=['GET'])
def tasks():
    if 'user' in session:
        user = users_collection.find_one({"email": session['user']})
        username = user['username']
        if session['role'] == 'admin':
            tasks = list(db.tasks.find())
            return render_template('admin_tasks.html', tasks=tasks,username=username)
        elif session['role'] == 'employee':
            tasks = list(db.tasks.find({"employee_email": session['user']}))
            return render_template('employee_tasks.html', tasks=tasks,username=username)

@app.route('/update-task-status', methods=['POST'])
def update_task_status():
    if 'user' in session and session.get('role') == 'employee':
        task_id = request.form['task_id']
        status = request.form['status']
        db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": status}})
        flash('Task status updated successfully!', 'success')
        return redirect(url_for('tasks'))
@app.route('/get-availability', methods=['GET'])
def get_availability():
    if 'user' in session:
        user = users_collection.find_one({"email": session['user']})
        return {"available": user.get("available", False)}
    return {"error": "Unauthorized"}, 401

@app.route('/toggle-availability', methods=['POST'])
def toggle_availability():
    if 'user' in session:
        user = users_collection.find_one({"email": session['user']})
        new_status = not user.get("available", False)
        users_collection.update_one({"email": session['user']}, {"$set": {"available": new_status}})
        return {"available": new_status}
    return {"error": "Unauthorized"}, 401

@app.route('/admin/attendance')
def admin_attendance():
    if 'user' in session and session.get('role') == 'admin':
        attendance_records = list(attendance_collection.find())
        return render_template('admin_attendance.html', attendance_records=attendance_records)
    else:
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
# @app.route('/export_online_employees')
# def export_online_employees():
#     records = attendance_collection.find({})  # Fetch all historical records
#     data = []

#     for record in records:
#         user = users_collection.find_one({"email": record["email"]})
#         login = record.get("login_time")
#         logout = record.get("logout_time")
#         if login and logout:
#             duration = str(logout - login)
#         elif login:
#             duration = str(datetime.now() - login)
#         else:
#             duration = "N/A"

#         data.append({
#             "Name": user.get("username", "N/A"),
#             "Email": record["email"],
#             "Date": record.get("date", "N/A"),
#             "Login Time": login.strftime('%Y-%m-%d %H:%M:%S') if login else "",
#             "Logout Time": logout.strftime('%Y-%m-%d %H:%M:%S') if logout else "Still Online",
#             "Duration": duration,
#             "Status": record.get("status", "N/A")
#         })

#     df = pd.DataFrame(data)
#     output = BytesIO()
#     df.to_excel(output, index=False)
#     output.seek(0)
#     return send_file(output, as_attachment=True, download_name="employee_attendance_history.xlsx")
from flask import send_file
import pandas as pd
from io import BytesIO

@app.route('/export_online_employees')
def export_online_employees():
    try:
        # Get all records (historical login/logout records)
        records = list(attendance_collection.find())

        export_data = []
        for rec in records:
            export_data.append({
                "Name": users_collection.find_one({"email": rec["email"]}).get("username", "N/A"),
                "Email": rec["email"],
                "Date": rec["date"],
                "Login Time": rec["login_time"].strftime("%Y-%m-%d %H:%M:%S") if rec.get("login_time") else "N/A",
                "Logout Time": rec["logout_time"].strftime("%Y-%m-%d %H:%M:%S") if rec.get("logout_time") else "N/A",
                "Duration": rec.get("duration", "N/A"),
                "Status": rec.get("status", "N/A")
            })

        df = pd.DataFrame(export_data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Employee History')

        output.seek(0)
        return send_file(output, as_attachment=True, download_name="employee_history.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route('/performance')
def performance():
    if 'user' not in session or session.get('role') != 'admin':
        
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    employees = list(users_collection.find({"role": "employee"}))
    performance_data = []

    for emp in employees:
        email = emp["email"]
        total_tasks = db.tasks.count_documents({"employee_email": email})
        completed_tasks = db.tasks.count_documents({"employee_email": email, "status": "Completed"})
        complaints = db.complaints.count_documents({"employee_email": email})
        leaves = db.leave_requests.count_documents({"employee_email": email})

        performance_data.append({
            "username": emp.get("username", "N/A"),
            "email": email,
            "tasks_total": total_tasks,
            "tasks_completed": completed_tasks,
            "completion_percent": round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0,
            "complaints": complaints,
            "leaves": leaves,
            "profile_image": emp.get("profile_image"),
            "department": emp.get("department", "N/A")
        })

    # Sort for top performer and top 3
    top_performer = max(performance_data, key=lambda x: x['completion_percent'], default=None)
    top_3_employees = sorted(performance_data, key=lambda x: x['completion_percent'], reverse=True)[:3]
    
    # Compute average
    average_completion = round(
        sum(emp['completion_percent'] for emp in performance_data) / len(performance_data),
        1
    ) if performance_data else 0
    user = users_collection.find_one({"email": session['user']})
    username = user['username']
    return render_template(
        'performance.html',
        employees=performance_data,
        top_performer=top_performer,
        average_completion=average_completion,
        top_3_employees=top_3_employees,
        username=username
    )
@app.route('/download_performance_data', methods=['POST'])
def download_performance_data():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    employees = list(users_collection.find({"role": "employee"}))
    performance_data = []

    for emp in employees:
        email = emp["email"]
        total_tasks = db.tasks.count_documents({"employee_email": email})
        completed_tasks = db.tasks.count_documents({"employee_email": email, "status": "Completed"})
        complaints = db.complaints.count_documents({"employee_email": email})
        leaves = db.leave_requests.count_documents({"employee_email": email})

        performance_data.append({
            "Username": emp.get("username", "N/A"),
            "Email": email,
            "Department": emp.get("department", "N/A"),
            "Total Tasks": total_tasks,
            "Completed Tasks": completed_tasks,
            "Completion %": round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0,
            "Complaints": complaints,
            "Leaves": leaves,
        })

    # Convert to DataFrame and export to Excel
    df = pd.DataFrame(performance_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Performance Report')

    output.seek(0)
    return send_file(output,
                     download_name="performance_report.xlsx",
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
if __name__ == '__main__':
    app.run(debug=True)