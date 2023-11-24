import cv2
import pickle
import numpy as np
import os
import time
from datetime import datetime
import mysql.connector
import csv
from win32com.client import Dispatch
import pandas as pd
from winotify import Notification, audio
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
facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')

with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)
with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

print('Shape of Faces matrix --> ', FACES.shape)

knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

imgBackground = cv2.imread("background.png")

COL_NAMES = ['NAME', 'TIME']

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        crop_img = frame[y:y+h, x:x+w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)
        ts = time.time()
        date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        exist = os.path.isfile("Attendance/Attendance_" + date + ".csv")

        # Fetch the employee's schedule from the 'employeesdb' database
        schedule_query = "SELECT schedule FROM employees WHERE name = %s"
        cursor_employees.execute(schedule_query, (str(output[0]),))
        schedule = cursor_employees.fetchone()

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

        attendance = [str(output[0]), str(timestamp), status]

    imgBackground[162:162 + 480, 55:55 + 640] = frame
    cv2.imshow("Frame", imgBackground)
    k = cv2.waitKey(1)
    if k == ord('o'):
        speak("Attendance Taken..")
        time.sleep(5)
        if exist:
            with open("Attendance/Attendance_" + date + ".csv", "+a") as csvfile:
                check = pd.read_csv("Attendance/Attendance_" + date + ".csv")
                if(str(output[0]) in check.values):
                    toast = Notification(app_id="Attendance already taken",
                                    title="Hello! " + str(output[0]),
                                    msg= "You have already timed-in",
                                    duration="short")
                    toast.show()
                    csvfile.close() 
                    
                else:
                    with open("Attendance/Attendance_" + date + ".csv", "+a") as csvfile:
                        writer=csv.writer(csvfile)
                        writer.writerow(attendance)
                    csvfile.close()

        try:
            # Create the attendance_table if it doesn't exist in 'attendancedb'
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

            # Check for duplicate name
            check_duplicate_query = f"SELECT name FROM {table_name} WHERE name = %s"
            cursor_attendance.execute(check_duplicate_query, (str(output[0]),))
            existing_name = cursor_attendance.fetchone()

            if not existing_name:
                # If the name doesn't exist, insert it into the table in 'attendancedb'
                insert_query = f"INSERT INTO {table_name} (name, time, status) VALUES (%s, %s, %s)"
                values = (str(output[0]), str(timestamp), status)
                cursor_attendance.execute(insert_query, values)
                attendance_db.commit()
                print("Record inserted successfully")
            else:
                print("Name already exists in attendancedb")

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

video.release()
cv2.destroyAllWindows()
