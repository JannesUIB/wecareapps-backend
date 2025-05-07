from flask import Flask, jsonify, request
import psycopg2

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(host='localhost',
                            database='wecareapps',
                            user="postgres",
                            password="postgres")
    return conn

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
        
        print("what is the user", user)
        if user:
            result.append({
                'UserId' : user[0],
                'UserName' : user[1],
                'UserEmail' : user[2]
            })
        else:
            return jsonify({"ResponseCode": 400, "ResponseMessage": "User Not Found"}), 400    
        cur.close()
        conn.close()

        return jsonify({"ResponseCode": 200, "ResponseMessage": "Login Successfuly", "Result":result}), 200    
    except Exception as e:
        return jsonify({"ResponseCode": 400, "ResponseMessage": e}), 400


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

        print("in here?")
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

