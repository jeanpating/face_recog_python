import cv2
import pickle
import numpy as np
import os
import mysql.connector
from datetime import datetime

# Establish MySQL connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="employeesdb"
)

cursor = conn.cursor()

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            schedule VARCHAR(10)  -- Assuming the maximum length is 5:55
        )
    """)
    print("Table 'employees' created or already exists.")
except Exception as e:
    print(f"Error: {e}")

video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('data/haarcascade_frontalface_default.xml')

faces_data = []

i = 0
face_not_detected_count = 0
max_face_not_detected_frames = 20  # Adjust this value based on your needs

name = input("Enter Your Name: ")
emp_id = input("Enter your Employee ID: ")
hours = input("Enter Hours: ")
minutes = input("Enter Minutes: ")

# Concatenate hours and minutes with ':'
schedule = f"{hours}:{minutes}"

try:
    cursor.execute("INSERT INTO employees (emp_id, name, schedule) VALUES (%s, %s, %s)", (emp_id, name, schedule))
    conn.commit()
    print("Employee details added to the database.")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()

# Fetch the auto-incremented ID
cursor.execute("SELECT LAST_INSERT_ID()")
employee_id = cursor.fetchone()[0]
print(f"Employee ID is: {employee_id}")

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) == 0:
        face_not_detected_count += 1
    else:
        face_not_detected_count = 0

    if face_not_detected_count >= max_face_not_detected_frames:
        cv2.putText(frame, "Keep your head straight", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)

    for (x, y, w, h) in faces:
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50))
        if len(faces_data) <= 100 and i % 10 == 0:
            faces_data.append(resized_img)
        i = i + 1
        cv2.putText(frame, str(len(faces_data)), (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)
    cv2.imshow("Frame", frame)
    k = cv2.waitKey(1)
    if k == ord('q') or len(faces_data) == 100:
        break
video.release()
cv2.destroyAllWindows()

faces_data = np.asarray(faces_data)
faces_data = faces_data.reshape(100, -1)

if 'names.pkl' not in os.listdir('data/'):
    names = [name] * 100
    with open('data/names.pkl', 'wb') as f:
        pickle.dump(names, f)
else:
    with open('data/names.pkl', 'rb') as f:
        names = pickle.load(f)
    names = names + [name] * 100
    with open('data/names.pkl', 'wb') as f:
        pickle.dump(names, f)

if 'faces_data.pkl' not in os.listdir('data/'):
    with open('data/faces_data.pkl', 'wb') as f:
        pickle.dump(faces_data, f)
else:
    with open('data/faces_data.pkl', 'rb') as f:
        faces = pickle.load(f)
    faces = np.append(faces, faces_data, axis=0)
    with open('data/faces_data.pkl', 'wb') as f:
        pickle.dump(faces, f)

cursor.close()
conn.close()
