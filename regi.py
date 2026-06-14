
from flask import Flask, render_template, request, redirect, url_for, flash, session

import mysql.connector
from datetime import datetime
import qrcode
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ================= MYSQL CONNECTION =================
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Mysql@2468",
    database="parking",
    buffered=True
)
cursor = conn.cursor(dictionary=True)

# ================= HOME =================
@app.route('/')
def home():
    return redirect(url_for('register'))

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        vehicle = request.form['vehicle']
        password = request.form['password']
        


        sql = """INSERT INTO bookings (name, email, phone, vehicle_no, password)
                 VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(sql, (name, email, phone, vehicle, password))
        conn.commit()

        flash("✅ Registration successful!", "success")
        return redirect(url_for('login'))
    return render_template('regi.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

         # ---- 1️⃣ Check Admin first ----
        cursor.execute("SELECT * FROM admin WHERE email=%s AND password=%s", (email, password))
        admin = cursor.fetchone()

        if admin:
            session['admin_email'] = admin['email']
            session['is_admin'] = 1   # ← ADD THIS LINE
            flash(f"✅ Welcome Admin!", "success")
            return redirect(url_for('admin_dashboard'))


        # ----  Check Normal User ----

        cursor.execute("SELECT * FROM bookings WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()

        if user:
            # Ensure is_admin is integer 0 or 1
            is_admin = 1 if str(user.get('is_admin', 0)) == '1' else 0

            # Set session variables
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_phone'] = user['phone']
            session['user_password'] = user['password']  
            # session['is_admin'] = is_admin   

            flash(f"Welcome back, {user['name']}!", "success")

            # Redirect based on admin flag
            if is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash("❌ Invalid email or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')



# ================= ADMIN DASHBOARD =================
@app.route('/admin', methods=['GET'])
def admin_dashboard():
     # Only allow access if admin is logged in
    if 'admin_email' not in session:
        flash("❌ Access denied!", "error")
        return redirect(url_for('login'))

    # Fetch all bookings
    cursor.execute("SELECT * FROM bookings ORDER BY checkin_time DESC")
    bookings = cursor.fetchall()

    # Fetch all cities for adding new parking areas
    cursor.execute("SELECT * FROM cities")
    cities = cursor.fetchall()

    # Fetch all parking areas to show existing ones
    cursor.execute("""
        SELECT ps.*, c.city_name 
        FROM parking_slots ps 
        JOIN cities c ON ps.city_id = c.city_id
    """)
    parking_areas = cursor.fetchall()

    return render_template('admin_dashboard.html', 
                           bookings=bookings, 
                           cities=cities, 
                           parking_areas=parking_areas)


@app.route('/add_parking_area', methods=['POST'])
def add_parking_area():
    if not session.get('admin_email'):
        flash("❌ Access denied!", "error")
        return redirect(url_for('login'))

    name = request.form['name']
    slots = request.form['slots']
    city_id = request.form.get('city_id')  # from dropdown
    new_city = request.form.get('new_city').strip()  # from text input

    # ---- If admin entered a new city ----
    if new_city:
        # Check if city already exists
        cursor.execute("SELECT city_id FROM cities WHERE LOWER(city_name) = %s", (new_city.lower(),))
        city = cursor.fetchone()
        if city:
            city_id = city['city_id']  # use existing
        else:
            # Add new city
            cursor.execute("INSERT INTO cities (city_name) VALUES (%s)", (new_city,))
            conn.commit()
            city_id = cursor.lastrowid  # get the new city_id

    if not city_id:
        flash("❌ Please select or add a city!", "error")
        return redirect(url_for('admin_dashboard'))

    # ---- Add Parking Area ----
    sql = "INSERT INTO parking_slots (name, slots, city_id) VALUES (%s, %s, %s)"
    cursor.execute(sql, (name, slots, city_id))
    conn.commit()

    flash(f"✅ Parking area '{name}' added successfully!", "success")
    return redirect(url_for('admin_dashboard'))



@app.route('/edit_parking_area/<int:slot_id>', methods=['GET', 'POST'])
def edit_parking_area(slot_id):
    if not session.get('is_admin'):
        flash("❌ Access denied!", "error")
        return redirect(url_for('login'))

    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        slots = request.form['slots']
        city_id = request.form['city_id']

        cursor.execute("""
            UPDATE parking_slots
            SET name=%s, slots=%s, city_id=%s
            WHERE slot_id=%s
        """, (name, slots, city_id, slot_id))

        conn.commit()
        flash("✅ Parking area updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    cursor.execute(
        "SELECT * FROM parking_slots WHERE slot_id=%s",
        (slot_id,)
    )
    area = cursor.fetchone()

    cursor.execute("SELECT * FROM cities")
    cities = cursor.fetchall()

    return render_template(
        'edit_parking_area.html',
        area=area,
        cities=cities
    )

# Add delete route
@app.route('/delete_parking_area/<int:slot_id>')
def delete_parking_area(slot_id):
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM parking_slots WHERE slot_id=%s",
        (slot_id,)
    )
    conn.commit()

    return redirect(url_for('admin_dashboard'))



# ================= LOGOUT ROUTE =================
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash("✅ Logged out successfully!", "success")
    return redirect(url_for('login'))


# ================= INDEX =================
@app.route('/index', methods=['GET', 'POST'])
def index():
    results = None
    city = None

    if request.method == 'POST':
        city = request.form.get("city").lower()
        sql = """SELECT ps.slot_id, ps.name, ps.slots, c.city_id
                 FROM parking_slots ps
                 JOIN cities c ON ps.city_id = c.city_id
                 WHERE LOWER(c.city_name) = %s"""
        cursor.execute(sql, (city,))
        results = cursor.fetchall()

    return render_template('index.html', results=results, city=city)

# ================= SELECT TIME =================
@app.route('/select_time/<int:slot_id>/<int:city_id>', methods=['GET', 'POST'])
def select_time(slot_id, city_id):
    if request.method == 'POST':
        date = request.form['date']
        start = request.form['start_time']
        end = request.form['end_time']

        return redirect(url_for('select_slot',
                                slot_id=slot_id,
                                city_id=city_id,
                                date=date,
                                start=start,
                                end=end))
    return render_template('select_time.html')

# ================= SELECT SLOT =================
@app.route('/select_slot/<int:slot_id>/<int:city_id>', methods=['GET', 'POST'])
def select_slot(slot_id, city_id):
    date = request.args.get('date')
    start = request.args.get('start')
    end = request.args.get('end')

    # Get parking area details
    cursor.execute("SELECT slots, name FROM parking_slots WHERE slot_id=%s", (slot_id,))
    parking_area = cursor.fetchone()
    total_slots = parking_area['slots']
    area_name = parking_area['name']

    # Get booked slots using overlap logic
    query = """
    SELECT vehicle_slot
    FROM bookings
    WHERE slot_id = %s
      AND booking_date = %s
      AND checkout_time IS NULL
"""
    cursor.execute(query, (slot_id, date))
    booked = {row['vehicle_slot'] for row in cursor.fetchall()}


    if request.method == 'POST':
        selected_slots = request.form.get('selected_slots', '').split(',')
        booked_list = []

        for s in selected_slots:
            s = s.strip()
            if not s or int(s) in booked:
                continue

            vehicle_slot = int(s)

            cursor.execute("""
                INSERT INTO bookings
                (name, email, phone, vehicle_no, vehicle_slot, password,
                booking_date, start_time, end_time, slot_id, city_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                session.get('user_name', 'Guest User'),
                session.get('user_email', 'guest@example.com'),
                session.get('user_phone', '9999999999'),
                session.get('vehicle_no', 'UNKNOWN'),
                vehicle_slot,
                session.get('user_password', 'guest123'),
                date,
                start,
                end,
                slot_id,
                city_id
            ))


            conn.commit()
            last_id = cursor.lastrowid
            booking_no = f"BKG{last_id:04d}"
            cursor.execute("UPDATE bookings SET booking_no=%s WHERE id=%s", (booking_no, last_id))
            conn.commit()

            # QR code generation
            os.makedirs('static/qr_codes', exist_ok=True)
            import socket
            local_ip = socket.gethostbyname(socket.gethostname())
            qr_data = f"http://{local_ip}:5000/scan_qr/{booking_no}"
            qr_path = f"static/qr_codes/{booking_no}.png"
            qrcode.make(qr_data).save(qr_path)

            booked_list.append({
                "booking_no": booking_no,
                "slot_label": f"Vehicle {s}",
                "qr_rel_path": f"qr_codes/{booking_no}.png"
            })

        if booked_list:
            return render_template('booking_tickets.html',
                                   bookings=booked_list,
                                   date=date,
                                   start=start,
                                   end=end,
                                   location=area_name)
        else:
            flash("❌ All selected slots are already booked!", "error")

    # Generate slots dynamically for frontend
    slots = [{
    "id": i,
    "name": f"Vehicle {i}",
    "booked": i in booked
} for i in range(1, total_slots + 1)]


    return render_template('select_slot.html', slots=slots, date=date, start=start, end=end)


from flask import jsonify

@app.route('/scan_qr/<booking_no>', methods=['GET','POST'])
def scan_qr(booking_no):
    # Fetch booking
    cursor.execute("SELECT * FROM bookings WHERE booking_no=%s", (booking_no,))
    booking = cursor.fetchone()



    if not booking:
        return render_template("scan_result.html", status="error", message="Booking not found")

    # === Handle Check-In ===
    if request.method == 'GET':
        if booking["checkin_time"] is None:
            checkin_time = datetime.now()
            cursor.execute("UPDATE bookings SET checkin_time=%s WHERE booking_no=%s", (checkin_time, booking_no))
            conn.commit()
            booking["checkin_time"] = checkin_time

    # === Handle Check-Out ===
    if request.method == 'POST':
        if booking["checkout_time"] is None:
            checkout_time = datetime.now()
            cursor.execute("UPDATE bookings SET checkout_time=%s WHERE booking_no=%s", (checkout_time, booking_no))
            conn.commit()
            booking["checkout_time"] = checkout_time

    return render_template("scan_result.html", status="success", booking=booking)

# ================= GET BOOKED SLOTS API =================
@app.route('/get_booked_slots', methods=['POST'])
def get_booked_slots():
    data = request.json

    city_id = data['city_id']
    booking_date = data['booking_date']
    start_time = data['start_time']
    end_time = data['end_time']

    query = """
        SELECT DISTINCT slot_id
        FROM bookings
        WHERE city_id = %s
        AND booking_date = %s
        AND start_time < %s
        AND end_time > %s
    """

    cursor.execute(query, (city_id, booking_date, end_time, start_time))
    result = cursor.fetchall()

    booked_slots = [row['slot_id'] for row in result]

    return jsonify(booked_slots)



# ================= RUN =================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


