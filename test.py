import cv2
import dlib
import pickle
import numpy as np
import os
import time
from datetime import datetime
import mysql.connector
import csv
from win32com.client import Dispatch
import pandas as pd
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

cursor_employees = employees_db.cursor()
cursor_attendance = attendance_db.cursor()

video = cv2.VideoCapture(0)

# Uses Histogram of Oriented Gradients (HOG)
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

COL_NAMES = ['NAME', 'TIME']

# Set a flag to indicate whether attendance should be taken or not
take_attendance = False

# Store the timestamp of the last attendance record
last_attendance_time = time.time()

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector(gray)

    # Reset the attendance flag when a face is detected
    if len(faces) > 0:
        take_attendance = False

    for face in faces:
        x, y, w, h = face.left(), face.top(), face.width(), face.height()
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)
        ts = time.time()
        date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        exist = os.path.isfile("Attendance/Attendance_" + date + ".csv")

        schedule_query = "SELECT schedule FROM employees WHERE name = %s"
        cursor_employees.execute(schedule_query, (str(output[0]),))
        schedule = cursor_employees.fetchone()

        if schedule:
            scheduled_time = datetime.strptime(schedule[0], "%H:%M")
            attendance_time = datetime.strptime(timestamp, "%H:%M:%S")

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

        attendance = [str(output[0]), str(timestamp)]

    # If no faces are detected and the attendance flag is not set, set the flag
    if len(faces) == 0 and not take_attendance:
        take_attendance = True

    # Take attendance only when the flag is set and a certain time has passed since the last record
    if take_attendance and time.time() - last_attendance_time > 60:  # Adjust the delay as needed (60 seconds in this case)
        ts = time.time()
        date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        exist = os.path.isfile("Attendance/Attendance_" + date + ".csv")

    if exist:
        with open("Attendance/Attendance_" + date + ".csv", "+a") as csvfile:
            check = pd.read_csv("Attendance/Attendance_" + date + ".csv")
            if str(output[0]) in check.values:
                toast = Notification(app_id="Attendance already taken",
                                    title="Hello! " + str(output[0]),
                                    msg="You have already timed-in",
                                    duration="short")
                # toast.show()
                csvfile.close()
            else:
                with open("Attendance/Attendance_" + date + ".csv", "+a") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(attendance)
                csvfile.close()
    else:
        with open("Attendance/Attendance_" + date + ".csv", "a") as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(COL_NAMES)
            writer.writerow(attendance)    
        csvfile.close();            

    try:
        current_date = datetime.fromtimestamp(ts).strftime("%d_%m_%Y")
        table_name = f"attendance_table_{current_date}"
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                time VARCHAR(255),
                status VARCHAR(255)
            )
        """
        cursor_attendance.execute(create_table_query)
        attendance_db.commit()

        check_duplicate_query = f"SELECT name FROM {table_name} WHERE name = %s"
        cursor_attendance.execute(check_duplicate_query, (str(output[0]),))
        existing_name = cursor_attendance.fetchone()

        if not existing_name:
            insert_query = f"INSERT INTO {table_name} (name, time, status) VALUES (%s, %s, %s)"
            values = (str(output[0]), str(timestamp), status)
            cursor_attendance.execute(insert_query, values)
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
            print("Name already exists in attendancedb")
            toast = Notification(app_id="Attendance already taken",
                                title="Hello! " + str(output[0]),
                                msg="You have already timed-in",
                                duration="short")
            toast.show()

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    imgBackground[162:162 + 480, 55:55 + 640] = frame
    cv2.imshow("Frame", imgBackground)
    k = cv2.waitKey(1)

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

video.release()
cv2.destroyAllWindows()
