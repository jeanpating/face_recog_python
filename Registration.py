import re
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
from tkinter import ttk, filedialog, messagebox
import ttkthemes

class EmployeeRegistrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Registration")
        self.root.geometry("950x500")
        self.camera_opened = False
        self.camera = None
        self.picture_counter = self.load_counter()

        self.style = ttkthemes.ThemedStyle(root)
        self.style.set_theme("breeze")  

        # GUI Components
        self.label = tk.Label(root, text="Employee Registration", font=("Helvetica", 20, "bold"))
        self.label.pack(pady=10)

        separator = ttk.Separator(root, orient="horizontal")
        separator.pack(fill="x", pady=5)
        
        # Styling
        style = ttk.Style()

        # Configure the style for TButton (normal state)
        self.style.configure("TButton",
                            padding=(10, 5),       # Padding
                            font=("Helvetica", 9), # Font
                            borderwidth=2,         # Border width
                            relief="groove"        # Border style
                            )

        self.style.configure("TButton.TButton",
                            background="#4CAF50",  # Background color for normal state
                            foreground="black"     # Text color for normal state
                            )

        self.style.configure("TButton.TButton:hover",
                            background="#16ba3f",  # Background color for hover state
                            foreground="white"      # Text color for hover state
                            )

        # Create frames
        self.left_frame = ttk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=150)

        self.middle_frame = ttk.Frame(self.root)
        self.middle_frame.pack(side=tk.LEFT, fill=tk.Y, padx=0)

        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=0)

        # Subheaders
        basic_info_label = ttk.Label(self.left_frame, text="BASIC INFORMATION", font=("Helvetica", 14, "bold"))
        basic_info_label.pack(pady=10)

        upload_picture_label = ttk.Label(self.right_frame, text="UPLOAD A PICTURE", font=("Helvetica", 14, "bold"))
        upload_picture_label.pack(pady=10)

        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="employeesdb"
        )
        self.cursor = self.conn.cursor()

        # Employee table in database
        self.create_employees_table()

    def create_employees_table(self):
        # SQL query to create the "employees" table
        create_table_query = """
            CREATE TABLE IF NOT EXISTS employees (
                id INT AUTO_INCREMENT PRIMARY KEY,
                emp_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                department VARCHAR(255),
                position VARCHAR(255),
                address VARCHAR(255),
                contact_number VARCHAR(20),
                email_address VARCHAR(255),
                picture_path VARCHAR(255)
            )
        """
        try:
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Table 'employees' created successfully.")
        except Exception as e:
            print(f"Error creating table: {e}")

        # Basic information on the left
        self.full_name_entry = self.create_entry(self.left_frame, "Full Name:")
        self.emp_id_entry = self.create_entry(self.left_frame, "Employee ID:")
        self.dept_entry = self.create_entry(self.left_frame, "Department:")
        self.pos_entry = self.create_entry(self.left_frame, "Position:")
        self.address_entry = self.create_entry(self.left_frame, "Address:")
        self.contact_entry = self.create_entry(self.left_frame, "Contact Number:")
        self.email_entry = self.create_entry(self.left_frame, "Email Address:")

        # Upload pictures on the right
        self.picture_frame = ttk.Frame(self.right_frame, borderwidth=2, relief="solid", width=100, height=100)
        self.picture_frame.pack(pady=10)

        self.picture_label = tk.Label(self.picture_frame) 
        self.picture_label.pack(fill='both', expand=True)

        self.picture_button = ttk.Button(self.right_frame, text="Upload a Picture", command=self.upload_picture)
        self.picture_button.pack(pady=10)

        self.take_picture_button = ttk.Button(self.right_frame, text="Take a Picture", command=self.take_picture)
        self.take_picture_button.pack(pady=10)

        self.register_button = ttk.Button(self.right_frame, text="Register Employee", command=self.register_employee, style="TButton.TButton")
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

    def create_entry(self, frame, label_text):
        entry_frame = ttk.Frame(frame)
        entry_frame.pack(pady=5)
        label = ttk.Label(entry_frame, text=label_text, padding=(20, 0), width=15)  # Increase width for alignment
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(entry_frame)
        entry.pack(side=tk.RIGHT, padx=5)  # Add padding to entry for spacing
        return entry


    def display_picture(self, picture_path):
        image = Image.open(picture_path)

        target_width = 100  
        target_height = 100  
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

    def load_counter(self):
        try:
            with open("pictures/picture_counter.txt", "r") as file:
                return int(file.read().strip())
        except (FileNotFoundError, ValueError):
            return 1

    def save_counter(self):
        with open("pictures/picture_counter.txt", "w") as file:
            file.write(str(self.picture_counter))

    def take_picture(self):
        if not self.camera_opened:
            self.camera = cv2.VideoCapture(0)
            self.camera_opened = True
            
        ret, frame = self.camera.read()
        if ret:
            filename = f"C:/xampp/htdocs/cp2-php/profilepics/captured_picture_{self.picture_counter}.jpg"
            # Save
            cv2.imwrite(filename, frame)
            # Display
            self.display_picture(filename)
            self.picture_counter += 1
            self.save_counter()
        else:
            messagebox.showerror("Error", "Failed to capture picture.")

    def register_employee(self):
        # Fetching input data from GUI
        name = self.full_name_entry.get()
        emp_id = self.emp_id_entry.get()
        dept = self.dept_entry.get()
        pos = self.pos_entry.get()
        address = self.address_entry.get()
        contact = self.contact_entry.get()
        email = self.email_entry.get()

        # Validate Employee ID length
        if len(emp_id) != 10:
            messagebox.showerror("Error", "Employee ID must be exactly 10 characters long.")
            return
        
        if len(contact) != 11:
            messagebox.showerror("Error", "Contact number must be exactly 11 characters long.")
            return

        # Validate Email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Error", "Invalid email address format.")
            return

        # Validate Email domain
        if not email.endswith("@gmail.com") and not email.endswith("@yahoo.com") and not email.endswith("@email.com"):
            messagebox.showerror("Error", "Email address must be from either Gmail or Yahoo domains.")
            return

        if not self.picture_path:
            messagebox.showerror("Error", "Please upload a picture first.")
            return

        try:
            # Inserting data into the employeesdb database
            self.cursor.execute("""
                INSERT INTO employees 
                (emp_id, name, department, position, address, contact_number, email_address, picture_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (emp_id, name, dept, pos, address, contact, email, self.picture_path))
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

        try:
            self.cursor.execute("""
                INSERT INTO scheduledb.employees 
                (emp_id, name, picture_path, schedule)
                VALUES (%s, %s, %s, NULL)
            """, (emp_id, name, self.picture_path))
            self.conn.commit()
            print("Employee details added to the database.")
        except Exception as e:
            print(f"Error: {e}")
            self.conn.rollback()
            messagebox.showerror("Error", f"Error: {e}")

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

                # Check if crop_img is not empty before resizing
                if not crop_img.size == 0:
                    resized_img = cv2.resize(crop_img, (50, 50))
                    if len(self.faces_data) <= 100 and self.i % 10 == 0:
                        self.faces_data.append(resized_img)
                    self.i = self.i + 1
                    cv2.putText(frame, str(len(self.faces_data)) + "%", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)
                else:
                    print("Warning: frame is empty.")
                if str(len(self.faces_data)) == 100:
                    cv2.putText(frame, "100% Complete!", (50, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 255), 1)

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
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = int((screen_width - root.winfo_reqwidth()) / 2)
    y_position = int((screen_height - root.winfo_reqheight()) / 2)
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    
