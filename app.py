from flask import Flask, jsonify, request
import jwt
import psycopg2
from functools import wraps
from datetime import datetime, timedelta

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

