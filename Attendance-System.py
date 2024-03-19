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
eye_cascade=cv2.CascadeClassifier('data/haarcascade_eye.xml')


with open('data/names.pkl', 'rb') as w:
    LABELS = pickle.load(w)
with open('data/faces_data.pkl', 'rb') as f:
    FACES = pickle.load(f)

print('Shape of Faces matrix --> ', FACES.shape)

knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

imgBackground = cv2.imread("background.png")

#EYE CASCADE | BLINKING
eye_flag = True
show_count = True

# Attendance attempts
attendance = []
attendance_attempts = {}

# Time interval dictionary
last_clock_in_time = {}

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Use dlib face detector
    faces = face_detector(gray)

    # Use a single timestamp for the entire frame
    ts = time.time()
    date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
    timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S") 
    #exist = os.path.isfile("Attendance/Attendance_" + date + ".csv")

    # Check if any faces are detected
    if faces:
        for face in faces:
            x, y, w, h = face.left(), face.top(), face.width(), face.height()
            crop_img = frame[y:y+h, x:x+w, :]

            try:
                # Attempt to resize the image and flatten it
                resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
            except cv2.error as e:
                print(f"Error resizing image: {e}")
                continue

            output = knn.predict(resized_img)

            #handle unknown users
            confidence = knn.predict_proba(resized_img)

            threshold = 0.8

            if np.max(confidence) < threshold:
                output = "X"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)
                cv2.rectangle(frame, (x, y-40), (x+w, y), (0, 0, 255), -1)
                cv2.putText(frame, str(output), (x, y-15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)

            # Fetch the employee's schedule from the 'employeesdb' database
            schedule_query = "SELECT am_time_in, pm_time_in FROM employee_schedule WHERE name = %s"
            cursor_schedule.execute(schedule_query, (str(output[0]),))
            schedule = cursor_schedule.fetchone()

            if schedule:
                am_time_in, pm_time_in = schedule

                scheduled_time_am = datetime.strptime(am_time_in, "%H:%M")
                scheduled_time_pm = datetime.strptime(pm_time_in, "%H:%M")
                attendance_time = datetime.strptime(timestamp, "%H:%M:%S")

                # Determine if it's AM or PM timeframe
                if 1 <= attendance_time.hour <= 11:
                    clock_type = 'AM-TIME-IN' if attendance_time < scheduled_time_am else 'AM-TIME-OUT'
                else:
                    clock_type = 'PM-TIME-IN' if attendance_time < scheduled_time_pm else 'PM-TIME-OUT'

                # Compare attendance time with scheduled time
                if 1 <= attendance_time.hour <= 11:
                    status = "Early" if attendance_time < scheduled_time_am else "On Time" if attendance_time == scheduled_time_am else "Late"
                else:
                    status = "Early" if attendance_time < scheduled_time_pm else "On Time" if attendance_time == scheduled_time_pm else "Late"

                cv2.putText(frame, f"Status: {status}", (x, y - 50), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 1)
            


            # Speak if the schedule is not set
            else:
                key = f"{str(output[0])}_{date}"
                if key not in attendance_attempts:
                    attendance_attempts[key] = 1
                else:
                    attendance_attempts[key] += 1

                    # Time interval
                    last_time = last_clock_in_time[key]
                    current_time = time.time()
                    time_difference = current_time - last_time
                    time_interval = 60  # 60 seconds for testing

                    if time_difference < time_interval:
                        print(f"Schedule not set for {output[0]}")
                        face_message = "Schedule not set for " + str(output[0])
                        cv2.putText(frame, face_message, (x, y-15), cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                        continue
                last_clock_in_time[key] = time.time()
                
                




            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 2)
            cv2.rectangle(frame, (x, y-40), (x+w, y), (50, 50, 255), -1)
            cv2.putText(frame, str(output[0]), (x, y-15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)
            face_message = "Blink to take Attendance"
            cv2.putText(frame, face_message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # EYE RECTANGLE
            eye_flag = False 
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray, 1.3, 5)

            for (ex, ey, ew, eh) in eyes:
                # Set eye_flag to True only if blinking is detected
                eye_flag = True
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (255, 255, 0), 2)

    else:
        # Display a message on the frame when no faces are detected
        no_faces_message = "No faces detected"
        cv2.putText(frame, no_faces_message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    imgBackground[162:162 + 480, 55:55 + 640] = frame
    cv2.imshow("Frame", imgBackground)
    k = cv2.waitKey(1)
    
    if eye_flag:
        show_count = True

    if show_count and not(eye_flag):
        show_count = False 

        # Skip attendance recording for unregistered person
        if output == "X":
            continue

        # Append values to the attendance list
        key = f"{str(output[0])}_{date}"
        if key not in attendance_attempts:
            attendance_attempts[key] = 1
        else:
            attendance_attempts[key] += 1

            # Time interval
            last_time = last_clock_in_time[key]
            current_time = time.time()
            time_difference = current_time - last_time

            time_interval = 10  # 10 seconds for testing

            if time_difference < time_interval:
                print(f"Time interval not reached for {output[0]}")
                # toast = Notification(app_id="Attendance Report",
                #                 title="Hello! " + str(output[0]),
                #                 msg="Time interval not reached yet",
                #                 duration="short")
                # toast.show()
                continue

        last_clock_in_time[key] = time.time()

        # Limit the attempts to a maximum of 4
        # if attendance_attempts[key] > 4:
        #     print("Maximum attendance attempts reached for today.")
        #     # Notify the user about the maximum attempts
        #     toast = Notification(app_id="Attendance Report",
        #                         title="Maximum Attempts Reached",
        #                         msg="You have reached the maximum attempts for today.",
        #                         duration="short")
        #     toast.show()
            
        #     continue

        # Determine AM or PM timeframe
        if 1 <= attendance_time.hour <= 11:
            clock_types = ['AM-TIME-IN', 'AM-TIME-OUT']
        else:
            clock_types = ['PM-TIME-IN', 'PM-TIME-OUT']

        # Set the clock_type based on the number of attempts
        try:
            clock_type = clock_types[attendance_attempts[key] - 1]
        except:
            toast = Notification(app_id="Attendance Report",
                                    title="Maximum Attempts Reached",
                                    msg="You have reached the maximum attempts for today.",
                                    duration="short")
            toast.show()
        
        # Append values to the attendance list
        attendance.append([str(output[0]), str(timestamp), clock_type])
        
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
                speak("Attendance taken for" + str(output[0]))
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
                speak("Attendance already taken for" + str(output[0]))
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
    cursor_schedule.close()
    schedule_db.close()
    print("Connection to scheduledb closed")    

video.release()
cv2.destroyAllWindows()