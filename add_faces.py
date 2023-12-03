import cv2
import dlib
import pickle
import numpy as np
import os
import mysql.connector
import tkinter as tk
from tkinter import messagebox
from imutils import face_utils
from PIL import Image, ImageTk
from tkinter import filedialog


class EmployeeRegistrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Registration")

        # GUI Components
        self.label = tk.Label(root, text="Employee Registration", font=("Helvetica", 16))
        self.label.pack(pady=10)

        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="employeesdb"
        )
        self.cursor = self.conn.cursor()

        # Create the "employees" table if it doesn't exist
        self.create_employees_table()

        # ... (your existing code)

    def create_employees_table(self):
        # SQL query to create the "employees" table
        create_table_query = """
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                department VARCHAR(255),
                address VARCHAR(255),
                contact_number VARCHAR(20),
                email_address VARCHAR(255),
                schedule VARCHAR(10),
                final_schedule VARCHAR(10),
                picture_path VARCHAR(255)
            )
        """
        try:
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Table 'employees' created successfully.")
        except Exception as e:
            print(f"Error creating table: {e}")

        self.full_name_entry = self.create_entry("Full Name:")
        self.emp_id_entry = self.create_entry("Employee ID:")
        self.dept_entry = self.create_entry("Department:")
        self.address_entry = self.create_entry("Address:")
        self.contact_entry = self.create_entry("Contact Number:")
        self.email_entry = self.create_entry("Email Address:")

        self.starting_hours_entry = self.create_entry("Starting Hours:")
        self.starting_minutes_entry = self.create_entry("Starting Minutes:")
        self.final_hours_entry = self.create_entry("Final Hours:")
        self.final_minutes_entry = self.create_entry("Final Minutes:")

        self.picture_label = tk.Label(root)
        self.picture_label.pack()

        self.picture_button = tk.Button(root, text="Upload a Picture", command=self.upload_picture)
        self.picture_button.pack(pady=10)

        self.take_picture_button = tk.Button(root, text="Take a Picture", command=self.take_picture)
        self.take_picture_button.pack(pady=10)

        self.register_button = tk.Button(root, text="Register Employee", command=self.register_employee)
        self.register_button.pack(pady=20)

        # Database Connection
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="employeesdb"
        )
        self.cursor = self.conn.cursor()

        # Face Recognition Components
        self.p = "shape_predictor_68_face_landmarks.dat"
        self.video = cv2.VideoCapture(0)
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(self.p)

        self.faces_data = []
        self.i = 0
        self.face_not_detected_count = 0
        self.max_face_not_detected_frames = 20

        # Additional variable to store picture path
        self.picture_path = ""

        # Additional variable to store camera status
        self.camera_opened = False
        self.camera = None

    def create_entry(self, label_text):
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        label = tk.Label(frame, text=label_text)
        label.pack(side=tk.LEFT)
        entry = tk.Entry(frame)
        entry.pack(side=tk.RIGHT)
        return entry

    def display_picture(self, picture_path):
        image = Image.open(picture_path)

        # Resize the image to fit the label
        target_width = 100  # Set the desired width (adjust as needed)
        target_height = 100  # Set the desired height (adjust as needed)
        image = image.resize((target_width, target_height), Image.ANTIALIAS)

        image = ImageTk.PhotoImage(image)
        self.picture_label.configure(image=image)
        self.picture_label.image = image

    def upload_picture(self):
        file_path = filedialog.askopenfilename(title="Select a Picture", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            self.picture_path = file_path
            self.display_picture(self.picture_path)
            messagebox.showinfo("Picture Uploaded", "Employee picture uploaded successfully.")

    def take_picture(self):
        if not self.camera_opened:
            self.camera = cv2.VideoCapture(0)
            self.camera_opened = True

        ret, frame = self.camera.read()
        if ret:
            cv2.imwrite("pictures/captured_picture.jpg", frame)
            self.display_picture("pictures/captured_picture.jpg")
        else:
            messagebox.showerror("Error", "Failed to capture picture.")

    def register_employee(self):
        # Fetching input data from GUI
        name = self.full_name_entry.get()
        emp_id = self.emp_id_entry.get()
        dept = self.dept_entry.get()
        address = self.address_entry.get()
        contact = self.contact_entry.get()
        email = self.email_entry.get()

        starting_hours = self.starting_hours_entry.get()
        starting_minutes = self.starting_minutes_entry.get()
        final_hours = self.final_hours_entry.get()
        final_minutes = self.final_minutes_entry.get()

        starting_schedule = f"{starting_hours}:{starting_minutes}"
        final_schedule = f"{final_hours}:{final_minutes}"

        if not self.picture_path:
            messagebox.showerror("Error", "Please upload or take a picture first.")
            return

        try:
            # Inserting data into the database
            self.cursor.execute("""
                INSERT INTO employees 
                (emp_id, name, department, address, contact_number, email_address, schedule, final_schedule, picture_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (emp_id, name, dept, address, contact, email, starting_schedule, final_schedule, self.picture_path))
            self.conn.commit()
            messagebox.showinfo("Success", "Employee details added to the database.")
        except Exception as e:
            print(f"Error: {e}")
            self.conn.rollback()
            messagebox.showerror("Error", f"Error: {e}")

        # Fetch the auto-incremented ID
        self.cursor.execute("SELECT LAST_INSERT_ID()")
        employee_id = self.cursor.fetchone()[0]
        print(f"Employee ID is: {employee_id}")

        # Face Recognition
        while True:
            ret, frame = self.video.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)

            if len(faces) == 0:
                self.face_not_detected_count += 1
            else:
                self.face_not_detected_count = 0

            if self.face_not_detected_count >= self.max_face_not_detected_frames:
                cv2.putText(frame, "Keep your head straight", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)

            for face in faces:
                x, y, w, h = face.left(), face.top(), face.width(), face.height()
                crop_img = frame[y:y + h, x:x + w, :]
                resized_img = cv2.resize(crop_img, (50, 50))
                if len(self.faces_data) <= 100 and self.i % 10 == 0:
                    self.faces_data.append(resized_img)
                self.i = self.i + 1
                cv2.putText(frame, str(len(self.faces_data)), (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)

            for (i, faces) in enumerate(faces):
                shape = self.predictor(gray, faces)
                shape = face_utils.shape_to_np(shape)
                for (x, y) in shape:
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            cv2.imshow("Frame", frame)
            k = cv2.waitKey(1)
            if k == ord('q') or len(self.faces_data) == 100:
                break

        self.video.release()
        cv2.destroyAllWindows()

        self.faces_data = np.asarray(self.faces_data)
        self.faces_data = self.faces_data.reshape(100, -1)

        # Saving data to pickle files
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
                pickle.dump(self.faces_data, f)
        else:
            with open('data/faces_data.pkl', 'rb') as f:
                faces = pickle.load(f)
            faces = np.append(faces, self.faces_data, axis=0)
            with open('data/faces_data.pkl', 'wb') as f:
                pickle.dump(faces, f)

        self.cursor.close()
        self.conn.close()

    def on_closing(self):
        if self.camera_opened:
            self.camera.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = EmployeeRegistrationApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
