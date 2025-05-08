import os
import psycopg2
from PIL import Image, ImageDraw, ImageFont
from flask_bcrypt import Bcrypt
import bcrypt
import random
import string

# Path to save generated images
output_dir = "/home/sgeede/Documents/generated_images/"

# Create directory if it doesn't exist
import os
os.makedirs(output_dir, exist_ok=True)

conn = psycopg2.connect(
        host="localhost",
        database="wecareapps",
        user="postgres",
        password="postgres")

# Open a cursor to perform database operations
cur = conn.cursor()

# Execute a command: this creates a new table
cur.execute('DROP TABLE IF EXISTS users CASCADE;')
cur.execute('DROP TABLE IF EXISTS doctor CASCADE;')
cur.execute('DROP TABLE IF EXISTS appointments CASCADE;')
cur.execute('DROP TABLE IF EXISTS receipts CASCADE;')
cur.execute('DROP TABLE IF EXISTS global_setting CASCADE;')

cur.execute('CREATE TABLE users (id serial PRIMARY KEY,'
            'username varchar (150) NOT NULL,'
            'email varchar (150) NOT NULL,'
            'password varchar (150) NOT NULL,'
            'mobile_refresh_token varchar NULL);' 
            )

cur.execute('CREATE TABLE doctor (id serial PRIMARY KEY,'
            'username varchar (150) NOT NULL,'
            'email varchar (150) NOT NULL,'
            'password varchar (150) NOT NULL,' 
            'session_time_start integer NOT NULL,' 
            'session_time_end integer NOT NULL,'
            'session_interval integer NOT NULL);' 
            )

cur.execute('''
    CREATE TABLE appointments (
        id SERIAL PRIMARY KEY,
        appointment_date DATE NOT NULL,
        doctor_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        child_name VARCHAR(150) NOT NULL,
        description VARCHAR(150) NOT NULL,
        session_time_start TIMESTAMP NOT NULL,
        session_time_end TIMESTAMP NOT NULL,
        status VARCHAR(50),
        CONSTRAINT fk_doctor FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE CASCADE,
        CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
''')

cur.execute('''
    CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL,
    booking_fees INTEGER NOT NULL, 
    extra_fees INTEGER NOT NULL,
    medicine_fees INTEGER NOT NULL,
    status VARCHAR(50),
    CONSTRAINT fk_appointments FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE);
''')

cur.execute('''
    CREATE TABLE global_setting (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value INTEGER NOT NULL
);
''')

cur.execute('''
    CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    receipt_id INTEGER NOT NULL,
    image BYTEA,
    CONSTRAINT fk_receipts FOREIGN KEY (receipt_id) REFERENCES receipts(id) ON DELETE CASCADE);
''')


data = [
  ('Patrick Pratama Hendri', '1200005.patrick@email.com', 'zedkxdrnfplsuchj'),
  ('Sandy Putra Efendi', '5220015.sandy@email.com', 'fnbxucrruuqsozmu'),
  ('Sandy Alferro Dion', '5220021.sandy@email.com', 'ygebkxnuemntwhkf'),
  ('Herman', '7180066.herman@email.com', 'hkcywyqiiujdfjnm'),
  ('Jetset', '2231002.jetset@email.com', 'xdthygofxlxaqnew'),
  ('Erwin', '2231061.erwin@email.com', 'ecdnjcjaicqdwqaj'),
  ('Fernando Jose', '2231064.fernando@email.com', 'hqbqfjfzjjzzjepz'),
  ('Deric Cahyadi', '2231065.deric@email.com', 'ktirmfdzoybvmnzd'),
  ('Muhammad Arif Guntara', '2231068.muhammad@email.com', 'ahnuofyytgeutqjs'),
  ('Dedy Susanto', '2231098.dedy@email.com', 'uskanhqmkedzclat'),
  ('Wirianto', '2231109.wirianto@email.com', 'wpjtkmqyjsgdkiyv'),
  ('Mellberg Limanda', '2231127.mellberg@email.com', 'lubjqacedhagdwtb'),
  ('Christoper', '2231129.christoper@email.com', 'nyxpcneduxunvihh'),
  ('Brian Tracia Bahagia', '2231004.brian@email.com', 'aswflebuuyssawod'),
  ('Vincent Claudius Santoso', '2231007.vincent@email.com', 'rgqprrqsjyhpslzn'),
  ('Inov Susanto', '2231009.inov@email.com', 'npfedgljmjatptpl'),
  ('Paerin', '2231048.paerin@email.com', 'souuabtteyanpqqn'),
  ('Risna Yunita', '2231055.risna@email.com', 'drexluacuoimvkos'),
  ('Jannes Velando', '2231059.jannes@email.com', 'udjdyxjiqxnspubt'),
  ('Yulsen', '2231006.yulsen@email.com', 'hlcgxmhcxehsxxro'),
  ('Wilson', '2231073.wilson@email.com', 'vybqntzjbdcyzqph'),
  ('Chelsea', '2231086.chelsea@email.com', 'osihzmhtpsubduny'),
  ('Fransisco', '2231089.fransisco@email.com', 'giywaxjydmlrozca'),
  ('Isaac Julio Herodion', '2231105.isaac@email.com', 'fwlvhcfxbqvrqydv'),
  ('Rubin', '2231119.rubin@email.com', 'llusiypxidxsdsma'),
  ('Kevin Gernaldi', '2231120.kevin@email.com', 'upwshrboztnuuwft'),
  ('Darren Huang', '2231135.darren@email.com', 'qeifqrytwzonkolc'),
  ('Stanley', '2231163.stanley@email.com', 'nqqmpffxgzpmptzj'),
  ('Fajar Anugrah', '2231198.fajar@email.com', 'bbgzvaxnsinyefvt'),
  ('Kelvin Tang', '2231206.kelvin@email.com', 'kmuzoqckcmsotuih'),
  ('Wike Orize', '3170028.wike@email.com', 'sqmvpdexbaizokyv'),
  ('Abdurrakhman Alhakim', '09200101.abdurrakhman@email.com', 'qbomdmuwxtgguzut')
]

for record in data:
  cur.execute(
      "INSERT INTO users (username,email,password) VALUES (%s, %s, %s)",
      record
  )

cur.execute('''
    INSERT INTO doctor (username, email, password, session_time_start, session_time_end, session_interval)
    VALUES 
        ('Dr. Yusuf', 'yusuf@clinic.com', 'pass123', 1, 8, 1),
        ('Dr. Wafiq', 'wafiq@clinic.com', 'secure456', 9, 17, 2),  
        ('Dr. Idris', 'idris@clinic.com', 'mypassword', 17, 23, 3);
''')

cur.execute('''
    INSERT INTO global_setting (key, value) VALUES
    ('booking_fees', 200000),
    ('extra_fees', 150000),
    ('medicine', 100000);

''')

conn.commit()

cur.close()
conn.close()