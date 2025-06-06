import os
from flask import Flask, jsonify, request
import jwt
import psycopg2
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
app = Flask(__name__)

SECRET_KEY = 'wecaremobileapps_secret'
REFRESH_SECRET_KEY = 'wecaremobileapps_refresh'

def _extract_token(header):
  if header and header.startswith('Bearer '):
      return header[len('Bearer '):]
  return None

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = _extract_token(request.headers.get('Authorization'))
        if not token:
            return jsonify({
                'StatusCode' : 401,
                'StatusDesc' : 'Failed, Token Is Missing',
            }), 400

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.exceptions.ExpiredSignatureError:
            return jsonify({
                'StatusCode' : 403,
                'StatusDesc' : 'Failed, Token has Expired',
            }), 400
        except jwt.exceptions.InvalidTokenError:
            return jsonify({
                'StatusCode' : 408,
                'StatusDesc' : 'Failed, Token Is Invalid',
            }), 400
        
        return f(*args, **kwargs)
    return decorator

def get_db_connection():
    conn = psycopg2.connect(host='localhost',
                            database='wecareapps',
                            user="postgres",
                            password="postgres")
    return conn

def _generate_access_token(user_id):
    payload = {
    'user_id':user_id,
    'exp': datetime.now() + timedelta(hours=1),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def _generate_refresh_token(user_id):
    payload = {
    'user_id':user_id,
    'exp': datetime.now() + timedelta(days=30),
    }
    token = jwt.encode(payload, REFRESH_SECRET_KEY, algorithm='HS256')
    return token


def get_global_value(key):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM global_setting WHERE key = %s", (key,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

# Route to handle login
@app.route('/v1/user/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['Email']
    passwords = data['Password']
    result = []
    if not email or not passwords:
        return jsonify({"ResponseCode": 400, "ResponseMessage": "Email and Password required"}), 400    
    
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection error'}), 500

        cur = conn.cursor()

        # Query the user
        cur.execute("SELECT id,username,email FROM users WHERE email = %s AND password = %s", (email,passwords))
        user = cur.fetchone()

        if user:
            # Generate Access and Refresh Token
            access_token = _generate_access_token(user[0])
            refresh_token = _generate_refresh_token(user[0])
            
            cur.execute("UPDATE users set mobile_refresh_token = %s WHERE id = %s", (refresh_token, user[0]))
            result.append({
                'UserId' : user[0],
                'UserName' : user[1],
                'UserEmail' : user[2],
                'Token' : access_token,
            })
        else:
            return jsonify({"ResponseCode": 400, "ResponseMessage": "User Not Found"}), 400    
        cur.close()
        conn.close()

        return jsonify({"ResponseCode": 200, "ResponseMessage": "Login Successfuly", "Result":result}), 200    
    except Exception as e:
        return jsonify({"ResponseCode": 400, "ResponseMessage": str(e)}), 400


# Route to handle login
@app.route('/v1/user/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['Username']
    email = data['Email']
    passwords = data['Password']

    if not email or not passwords:
        return jsonify({"ResponseCode": 400, "ResponseMessage": "Email and Password required"}), 400    
    
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection error'}), 500

        cur = conn.cursor()

        # Query the user
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            return jsonify({"ResponseCode": 400, "ResponseMessage": "Email Already Existed"}), 400
        else:
            cur.execute("INSERT INTO users (username,email,password) values (%s,%s,%s);",(username,email,passwords))

        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"ResponseCode": 200, "ResponseMessage": "Successfully Create A User"}), 200
    except Exception as e:
        return jsonify({"ResponseCode": 400, "ResponseMessage": str(e)}), 400   

@app.route('/v1/user/change_password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    user_id = data['UserID']
    old_password = data['OldPassword']
    new_password = data['NewPassword']

    if not user_id or not old_password or not new_password:
        return jsonify({"ResponseCode": 400, "ResponseMessage": "Missing Parameters"}), 400    
    
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection error'}), 500

        cur = conn.cursor()

        # Query the user
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({"ResponseCode": 400, "ResponseMessage": "User Not Found"}), 400
        else:
            if user[3] != old_password:
                return jsonify({"ResponseCode": 400, "ResponseMessage": "Old Password Doesn't Match"}), 400    
            else:
                cur.execute("UPDATE users set password = %s WHERE id = %s", (new_password, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ResponseCode": 200, "ResponseMessage": "Successfully Changed Password"}), 200
    except Exception as e:
        return jsonify({"ResponseCode": 400, "ResponseMessage": str(e)}), 400   

@app.route('/v1/core/doctors', methods=['GET'])
def get_doctors():
    data = request.get_json()
    appointment_date_str = data.get('AppointmentDate')

    try:
        appointment_date = datetime.strptime(appointment_date_str, '%m/%d/%Y').date()
    except ValueError:
        return jsonify({"ResponseCode": 400, "ResponseMessage": "Invalid date format. Use mm/dd/yyyy"}), 400

    if not appointment_date:
        return jsonify({"Response Code": 400, "Response Message": "AppointmentDate is required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT d.id, d.username, d.session_time_start, d.session_time_end, d.session_interval FROM doctor d")
        doctors = cur.fetchall()
        results = []
        now = datetime.now() + timedelta(hours=7)

        for doc_id, doc_name, doc_session_start, doc_session_end, doc_session_interval in doctors:
            open_hour = doc_session_start if doc_session_start is not None else 0
            close_hour = doc_session_end if doc_session_end is not None else 24

            # Validate open/close hour range
            if open_hour >= close_hour:
                return {
                    'error': 'Invalid open and close hours configuration.',
                    'success': False
                }

            interval_hours = doc_session_interval or 1
            schedule = []
            current_time = datetime.combine(appointment_date, datetime.min.time()) + timedelta(hours=open_hour)
            end_of_day = datetime.combine(appointment_date, datetime.min.time()) + timedelta(hours=close_hour)
 
            # Limit iterations to avoid memory overflow
            while current_time < end_of_day:
                next_time = current_time + timedelta(hours=interval_hours)
                if next_time > end_of_day:
                    next_time = end_of_day


                cur.execute("""
                    SELECT id
                    FROM appointments 
                    WHERE doctor_id = %s AND appointment_date = %s AND session_time_start < %s AND session_time_end > %s
                """, (doc_id, appointment_date, datetime.combine(appointment_date, next_time.time()), datetime.combine(appointment_date, current_time.time())))

                appointment = cur.fetchall()

                # print("booking count", booking_count)
                # Determine status: booked, active, or inactive
                if appointment_date < now.date():
                    status = 'Inactive'
                elif appointment_date == now.date() and current_time.time() < now.time():
                    status = 'Inactive'
                else:
                    status = 'Booked' if appointment else 'Available For Booking'

                schedule.append({
                    'start_time': current_time.strftime('%H:%M'),
                    'end_time': next_time.strftime('%H:%M'),
                    'status': status
                })

                current_time = next_time

                # Stop if the end of the day is reached
                if current_time.time() >= datetime.max.time():
                    break

            results.append({
                'DoctorID': doc_id,
                'DoctorName': doc_name,
                'AvailableSchedule': schedule
            })

        cur.close()
        conn.close()
        return jsonify({"Response Code": 200, "Response Result": results})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})


@app.route('/v1/core/user_appointment/<int:UserId>', methods=['GET'])
def get_user_appointments(UserId):
    if not UserId:
        return jsonify({"Response Code": 400, "Response Message": "User ID is required"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, child_name, status 
            FROM appointments 
            WHERE user_id = %s
        """, (UserId,))
        appointments = cur.fetchall()

        result = [{
            'AppointmentID': a[0],
            'ChildName': a[1],
            'Status': a[2]
        } for a in appointments]

        cur.close()
        conn.close()
        return jsonify({"Response Code": 200, "Response Result": result})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})


@app.route('/v1/core/appointment', methods=['POST'])
def create_appointment():
    data = request.get_json()
    required_fields = ['AppointmentDate', 'DoctorID', 'ParentName', 'ChildName',
                       'SessionTimeStart', 'SessionTimeEnd', 'UserID']
    
    if not all(field in data for field in required_fields):
        return jsonify({"Response Code": 400, "Response Message": "Missing required fields"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO appointments (appointment_date, doctor_id, parent_name, child_name, 
                                      session_start, session_end, user_id, description, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Pending Payment')
            RETURNING id
        """, (
            data['AppointmentDate'], data['DoctorID'], data['ParentName'], data['ChildName'],
            data['SessionTimeStart'], data['SessionTimeEnd'], data['UserID'], data.get('Description')
        ))

        appointment_id = cur.fetchone()[0]

        
        booking_fee = get_global_value('booking_fees')
        extra_fee = get_global_value('extra_fees')
        medicine_fee = get_global_value('medicine')

        cur.execute("""
            INSERT INTO receipts (appointment_id, booking_fees, extra_fees, medicine_fees, 
                                      status)
            VALUES (%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            appointment_id, booking_fee, extra_fee, medicine_fee, 'Not Paid'
        ))


        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"Response Code": 200, "Response Message": "Successfully Create Appointment", "Response Result": appointment_id})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})


@app.route('/v1/core/delete_appointment', methods=['POST'])
def delete_appointment():
    data = request.get_json()
    appointment_id = data.get('AppointmentID')

    if not appointment_id:
        return jsonify({"Response Code": 400, "Response Message": "AppointmentID required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"Response Code": 200, "Response Message": "Successfully Delete Appointment"})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})


@app.route('/v1/core/resi/<int:appointment_id>', methods=['GET'])
def get_receipt(appointment_id):
    if not appointment_id:
        return jsonify({"Response Code": 400, "Response Message": "Appointment ID is required"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT a.id, a.appointment_date, a.session_time_start, a.session_time_end, 
                   p.booking_fees, p.extra_fees, p.medicine_fees
            FROM appointments a
            JOIN receipts p ON a.id = p.appointment_id
            WHERE a.id = %s
        """, (appointment_id,))
        
        row = cur.fetchone()
        if not row:
            return jsonify({"Response Code": 404, "Response Message": "Receipt Not Found"}), 404

        result = {
            "AppointmentID": row[0],
            "SessionDate": row[1].strftime("%m/%d/%Y"),
            "BookingTime": [str(row[2]), str(row[3])],
            "PaymentDetails": {
                "BookingFees": row[4],
                "ExtraFees": row[5],
                "Medicine": row[6]
            }
        }

        cur.close()
        conn.close()
        return jsonify({"Response Code": 200, "Response Result": result})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})


@app.route('/v1/core/appointment_payment', methods=['POST'])
def upload_payment():
    try:
        if 'PaymentImage' not in request.files or 'ReceiptID' not in request.form:
            return jsonify({"Response Code": 400, "Response Message": "Missing required fields"}), 400

        image = request.files['PaymentImage']
        receipt_id = request.form['ReceiptID']

        # filename = secure_filename(image.filename)
        # image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # image.save(image_path)

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO payments (receipt_id, image)
            VALUES (%s, %s)
        """, (receipt_id, image,))  # Adjust if you separate booking vs medicine

        cur.execute("UPDATE receipts SET status = 'Checking Payment' WHERE id = %s", (receipt_id,))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"Response Code": 200, "Response Message": "Successfully Upload Receipt"})
    except Exception as e:
        return jsonify({"Response Code": 400, "Response Message": str(e)})