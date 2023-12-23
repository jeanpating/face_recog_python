import cv2
import dlib
import pickle
import numpy as np
import os
import time
from datetime import datetime
import mysql.connector
from win32com.client import Dispatch
from winotify import Notification
from sklearn.neighbors import KNeighborsClassifier

def speak(str1):
    speak = Dispatch(("SAPI.SpVoice"))
    speak.Speak(str1)

# Connect to MySQL databases
employees_db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="employeesdb"
)

attendance_db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="attendancedb"
)

schedule_db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="scheduledb"
)

cursor_employees = employees_db.cursor()
cursor_attendance = attendance_db.cursor()
cursor_schedule = schedule_db.cursor()

video = cv2.VideoCapture(0)

# Create a face detector using dlib
face_detector = dlib.get_frontal_face_detector()

with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)
with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

print('Shape of Faces matrix --> ', FACES.shape)

knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

imgBackground = cv2.imread("background.png")

# Initialize attendance list outside the loop
attendance = []

# Dictionary to track attendance attempts
attendance_attempts = {}

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Use dlib face detector
    faces = face_detector(gray)

    # Use a single timestamp for the entire frame
    ts = time.time()
    date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
    timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S") 
    exist = os.path.isfile("Attendance/Attendance_" + date + ".csv")

    for face in faces:
        x, y, w, h = face.left(), face.top(), face.width(), face.height()
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)

        # Fetch the employee's schedule from the 'employeesdb' database
        schedule_query = "SELECT am_time_in FROM employee_schedule WHERE name = %s"
        cursor_schedule.execute(schedule_query, (str(output[0]),))
        schedule = cursor_schedule.fetchone()

        if schedule:
            scheduled_time = datetime.strptime(schedule[0], "%H:%M")
            attendance_time = datetime.strptime(timestamp, "%H:%M:%S")

            # Compare attendance time with scheduled time
            if attendance_time < scheduled_time:
                status = "Early"
            elif attendance_time == scheduled_time:
                status = "On Time"
            else:
                status = "Late"

            cv2.putText(frame, f"Status: {status}", (x, y - 50), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 1)

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 2)
        cv2.rectangle(frame, (x, y-40), (x+w, y), (50, 50, 255), -1)
        cv2.putText(frame, str(output[0]), (x, y-15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)

        # Append values to the attendance list
        key = f"{str(output[0])}_{date}"
        if key not in attendance_attempts:
            attendance_attempts[key] = 1
        else:
            attendance_attempts[key] += 1

        # Limit the attempts to a maximum of 4
        if attendance_attempts[key] > 4:
            print("Maximum attendance attempts reached for today.")
            continue

        clock_types = ['AM-TIME-IN', 'AM-TIME-OUT', 'PM-TIME-IN', 'PM-TIME-OUT']
        clock_type = clock_types[attendance_attempts[key] - 1]

        # Append values to the attendance list
        attendance.append([str(output[0]), str(timestamp), clock_type])

    imgBackground[162:162 + 480, 55:55 + 640] = frame
    cv2.imshow("Frame", imgBackground)
    k = cv2.waitKey(1)

    try:
        # Create the 'attendance' table if it doesn't exist in 'attendancedb'
        create_table_query = """
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                name VARCHAR(255),
                time VARCHAR(255),
                status VARCHAR(255),
                clock VARCHAR(255)
            )
        """
        cursor_attendance.execute(create_table_query)
        attendance_db.commit()

        # Check for duplicate record for the same person, same date, and same clock type
        check_duplicate_query = "SELECT id FROM attendance WHERE name = %s AND date = %s AND clock = %s"
        check_values = (str(output[0]), datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d"), clock_type)
        cursor_attendance.execute(check_duplicate_query, check_values)
        existing_record = cursor_attendance.fetchone()
        print(f"Existing Record ID: {existing_record}")

        # Print the raw SQL query for additional debugging
        print(f"Raw SQL Query: {cursor_attendance.statement}")

        # Check if the result is None or not
        if existing_record is None:
            # If there's no existing record for the same person, same date, and same clock type, insert a new record
            insert_query = "INSERT INTO attendance (date, name, time, status, clock) VALUES (%s, %s, %s, %s, %s)"
            insert_values = (datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d"), str(output[0]), str(timestamp), status, clock_type)
            cursor_attendance.execute(insert_query, insert_values)
            attendance_db.commit()
            print("Record inserted successfully")
            toast = Notification(app_id="Attendance Report",
                                title="Hello! " + str(output[0]),
                                msg="You are " + str(status) + "\n" +
                                    "Schedule: " + str(schedule[0]) + "\n" +
                                    "Time-in: " + str(timestamp),
                                duration="short")
            toast.show()
        else:
            print("Attendance for the same person, same date, and same clock type already exists in attendancedb")
            toast = Notification(app_id="Attendance already taken",
                                title="Hello! " + str(output[0]),
                                msg="You have already timed-in today",
                                duration="short")
            toast.show()

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    if k == ord('q'):
        break

# Close the database connections outside the loop
if 'employees_db' in locals() and employees_db.is_connected():
    cursor_employees.close()
    employees_db.close()
    print("Connection to employeesdb closed")

if 'attendance_db' in locals() and attendance_db.is_connected():
    cursor_attendance.close()
    attendance_db.close()
    print("Connection to attendancedb closed")

if 'schedule_db' in locals() and schedule_db.is_connected():
    cursor_attendance.close()
    schedule_db.close()
    print("Connection to scheduledb closed")    

video.release()
cv2.destroyAllWindows()