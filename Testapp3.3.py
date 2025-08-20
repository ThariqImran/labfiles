from pymongo import MongoClient
from subcode import sub_code # This import access the sub_code dictionary and they are in the format of {'subject_code': credit_hours} about 232 items.
import customtkinter as ctk


# Initialize the MongoDB client and database
client=MongoClient('mongodb://localhost:27017/')
db=client['test']
# Search box and button

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")


# --- UI Setup ---
app = ctk.CTk()
app.geometry("1280x720")
app.title("Database Viewer")

# Configure grid layout: 1 row, 2 columns (left: 35%, right: 65%)
app.grid_columnconfigure(0, weight=35)
app.grid_columnconfigure(1, weight=65)
app.grid_rowconfigure(0, weight=1)

# Right: Scrollable frame for data
data_frame = ctk.CTkScrollableFrame(app, width=800, height=700)
data_frame.grid(row=0, column=1, sticky="nsew", padx=(20,10), pady=20)

# Left: Action buttons
action_frame = ctk.CTkFrame(app, width=400, height=700)
action_frame.grid(row=0, column=0, sticky="nsew", padx=(10,20), pady=20)
# Store current document _id and entry widgets
search_var = ctk.StringVar()
current_doc_id = None
entry_widgets = {}

GRADE_POINTS = {
    "O": 10,
    "A+": 9,
    "A": 8,
    "B+": 7,
    "B": 6,
    "C": 5,
    "U": 0,
    "SA": 0,
    "WD": 0
}
def calculate_gpa(student_doc, sem_num):
    subjects = student_doc.get("semesters", {}).get(sem_num, {}).get("subjects", [])
    total_points = sum(GRADE_POINTS.get(s["grade"], 0) * s["credits"] for s in subjects)
    total_credits = sum(s["credits"] for s in subjects)
    gpa = round(total_points / total_credits, 2) if total_credits else 0
    db.students.update_one(
        {"_id": student_doc["_id"]},
        {"$set": {f"semesters.{sem_num}.gpa": gpa}}
    )
    return gpa

def calculate_cgpa(student_doc):
    all_subjects = []
    for sem in student_doc.get("semesters", {}).values():
        all_subjects.extend(sem.get("subjects", []))
    total_points = sum(GRADE_POINTS.get(s["grade"], 0) * s["credits"] for s in all_subjects)
    total_credits = sum(s["credits"] for s in all_subjects)
    cgpa = round(total_points / total_credits, 2) if total_credits else 0
    db.students.update_one({"_id": student_doc["_id"]}, {"$set": {"cgpa": cgpa}})
    return cgpa

def open_student_window(student_doc):
    popup = ctk.CTkToplevel(app)
    popup.geometry("800x600")
    popup.title(f"Manage {student_doc['name']} - {student_doc['rollno']}")

    def show_semester_ui(sem_num):
        # Clear previous widgets FIRST
        for widget in popup.winfo_children():
            widget.destroy()
        refreshed_doc = db.students.find_one({"_id": student_doc["_id"]})
        gpa = calculate_gpa(refreshed_doc, sem_num)
        cgpa = calculate_cgpa(refreshed_doc)
        ctk.CTkLabel(popup, text=f"GPA: {gpa} | CGPA: {cgpa}").pack(pady=5)

        semester_data = refreshed_doc.get("semesters", {}).get(sem_num, {})
        # Helper to get subjects for each exam
        def get_exam_subjects(exam):
            return semester_data.get(exam, [])

        # Display IAT/Model sections
        for exam in ["IAT1", "IAT2", "ModelExam"]:
            ctk.CTkLabel(popup, text=f"{exam} Subjects (Marks out of 100)").pack(pady=5)
            exam_subjects = get_exam_subjects(exam)
            exam_vars = []
            for idx, subj in enumerate(exam_subjects):
                frame = ctk.CTkFrame(popup)
                frame.pack(fill="x", padx=10, pady=2)
                code_var = ctk.StringVar(value=subj["code"])
                marks_var = ctk.StringVar(value=str(subj.get("marks", "")))
                code_entry = ctk.CTkEntry(frame, textvariable=code_var, width=100, state="disabled")
                code_entry.pack(side="left", padx=5)
                marks_entry = ctk.CTkEntry(frame, textvariable=marks_var, width=80)
                marks_entry.pack(side="left", padx=5)
                exam_vars.append((code_var, marks_var, frame))

                def delete_subject(idx=idx):
                    # Remove subject from all three exams
                    for ex in ["IAT1", "IAT2", "ModelExam"]:
                        subjects = semester_data.get(ex, [])
                        if idx < len(subjects):
                            subjects.pop(idx)
                            db.students.update_one(
                                {"_id": student_doc["_id"]},
                                {"$set": {f"semesters.{sem_num}.{ex}": subjects}}
                            )
                    show_semester_ui(sem_num)

                del_btn = ctk.CTkButton(frame, text="Delete", command=delete_subject)
                del_btn.pack(side="left", padx=5)

            def save_exam_marks():
                for idx, (code_var, marks_var, _) in enumerate(exam_vars):
                    code = code_var.get().upper()
                    try:
                        marks = int(marks_var.get())
                    except ValueError:
                        marks = 0
                    exam_subjects[idx]["marks"] = marks
                db.students.update_one(
                    {"_id": student_doc["_id"]},
                    {"$set": {f"semesters.{sem_num}.{exam}": exam_subjects}}
                )
                show_semester_ui(sem_num)

            ctk.CTkButton(popup, text=f"Save {exam} Marks", command=save_exam_marks).pack(pady=5)

            # Only add subject button under IAT1
            if exam == "IAT1":
                def add_exam_subject():
                    sub_code_var = ctk.StringVar()
                    add_frame = ctk.CTkFrame(popup)
                    add_frame.pack(fill="x", padx=10, pady=2)
                    ctk.CTkLabel(add_frame, text="Subject Code").pack(side="left")
                    ctk.CTkEntry(add_frame, textvariable=sub_code_var, width=100).pack(side="left", padx=5)
                    def save_new_subject():
                        code = sub_code_var.get().upper()
                        # Add to all three exams
                        for ex in ["IAT1", "IAT2", "ModelExam"]:
                            subjects = semester_data.get(ex, [])
                            if not any(s["code"].upper() == code for s in subjects):
                                subjects.append({"code": code, "marks": 0})
                                db.students.update_one(
                                    {"_id": student_doc["_id"]},
                                    {"$set": {f"semesters.{sem_num}.{ex}": subjects}}
                                )
                        show_semester_ui(sem_num)
                    ctk.CTkButton(add_frame, text="Add Subject", command=save_new_subject).pack(side="left", padx=5)
                add_exam_subject()

        ctk.CTkLabel(popup, text=f"Semester {sem_num} Subjects").pack(pady=10)

        student = db.students.find_one({"_id": student_doc["_id"]})
        subjects = student.get("semesters", {}).get(sem_num, {}).get("subjects", [])

        # Store variables for all subject widgets
        subject_vars = []
        for idx, subj in enumerate(subjects):
            frame = ctk.CTkFrame(popup)
            frame.pack(fill="x", padx=10, pady=2)
            code_var = ctk.StringVar(value=subj["code"])
            grade_var = ctk.StringVar(value=subj["grade"])
            code_entry = ctk.CTkEntry(frame, textvariable=code_var, width=100)
            code_entry.pack(side="left", padx=5)
            grade_combo = ctk.CTkComboBox(frame, values=list(GRADE_POINTS.keys()), variable=grade_var, width=80)
            grade_combo.pack(side="left", padx=5)
            subject_vars.append((code_var, grade_var, frame))

            def delete_subject(idx=idx, frame=frame):
                student = db.students.find_one({"_id": student_doc["_id"]})
                subjects = student.get("semesters", {}).get(sem_num, {}).get("subjects", [])
                if idx < len(subjects):
                    subjects.pop(idx)
                    db.students.update_one(
                        {"_id": student_doc["_id"]},
                        {"$set": {f"semesters.{sem_num}.subjects": subjects}}
                    )
                    frame.destroy()
                    show_semester_ui(sem_num)

            del_btn = ctk.CTkButton(frame, text="Delete", command=delete_subject)
            del_btn.pack(side="left", padx=5)

        # Save All button to save all edited subjects
        def save_all_subjects():
            new_subjects = []
            for code_var, grade_var, _ in subject_vars:
                code = code_var.get().upper()
                grade = grade_var.get()
                credits = sub_code.get(code, 3)
                # Prevent duplicate codes
                if not any(s["code"].upper() == code for s in new_subjects):
                    new_subjects.append({"code": code, "grade": grade, "credits": credits})
            db.students.update_one(
                {"_id": student_doc["_id"]},
                {"$set": {f"semesters.{sem_num}.subjects": new_subjects}}
            )
            show_semester_ui(sem_num)

        ctk.CTkButton(popup, text="Save All", command=save_all_subjects).pack(pady=10)

        # Add subject UI
        code_var = ctk.StringVar()
        grade_var = ctk.StringVar(value="O")
        ctk.CTkLabel(popup, text="Subject Code").pack()
        ctk.CTkEntry(popup, textvariable=code_var).pack()
        ctk.CTkLabel(popup, text="Grade").pack()
        ctk.CTkComboBox(popup, values=list(GRADE_POINTS.keys()), variable=grade_var).pack()

        def save_subject():
            sub_code_val = code_var.get().upper()
            grade_val = grade_var.get()
            credits = sub_code.get(sub_code_val, 3)
            # Fetch current subjects
            student = db.students.find_one({"_id": student_doc["_id"]})
            subjects = student.get("semesters", {}).get(sem_num, {}).get("subjects", [])
            # Remove any subject with same code (case-insensitive)
            subjects = [s for s in subjects if s["code"].upper() != sub_code_val]
            # Add/replace subject
            subjects.append({"code": sub_code_val, "grade": grade_val, "credits": credits})
            db.students.update_one(
                {"_id": student_doc["_id"]},
                {"$set": {f"semesters.{sem_num}.subjects": subjects}}
            )
            show_semester_ui(sem_num)

        ctk.CTkButton(popup, text="Add Subject", command=save_subject).pack(pady=10)

    def add_semester():
        sem_var = ctk.StringVar(value="1")
        sem_combo = ctk.CTkComboBox(popup, values=[str(i) for i in range(1, 9)], variable=sem_var)
        sem_combo.pack(pady=10)
        def select_semester():
            sem_num = sem_var.get()
            student = db.students.find_one({"_id": student_doc["_id"]})
            semesters = student.get("semesters", {})
            if sem_num not in semesters:
                db.students.update_one(
                    {"_id": student_doc["_id"]},
                    {"$set": {f"semesters.{sem_num}": {"subjects": [], "gpa": None}}}
                )
            show_semester_ui(sem_num)
        ctk.CTkButton(popup, text="Select Semester", command=select_semester).pack(pady=5)

    ctk.CTkButton(popup, text="Add Semester", command=add_semester).pack(pady=10)

def fetch_data():
    collection = db['students']
    data = collection.find()
    return list(data)

def display_data():
    # Clear previous widgets
    for widget in data_frame.winfo_children():
        widget.destroy()
    data = fetch_data()
    for idx, item in enumerate(data):
        # Only show ObjectId, name, rollno, department
        display_text = f"ID: {item.get('_id', '')} | Name: {item.get('name', '')} | Roll No: {item.get('rollno', '')} | Dept: {item.get('department', '')}"
        label = ctk.CTkLabel(data_frame, text=display_text, anchor="w", justify="left")
        label.pack(fill="x", padx=5, pady=2)


# Action buttons on the right
#query_button = ctk.CTkButton(action_frame, text="Query", command=lambda: print("Query clicked"))
#query_button.pack(pady=10, fill="x")


def clear_action_frame(exclude_widgets):
    """Helper to clear action_frame except widgets in exclude_widgets."""
    for widget in action_frame.winfo_children():
        if widget not in exclude_widgets:
            widget.destroy()

def show_edit_fields(document):

    global current_doc_id, entry_widgets, add_new_button
    exclude = [search_entry, search_button, view_db_button, add_new_button, delete_button]
    clear_action_frame(exclude)
    entry_widgets = {}
    current_doc_id = document["_id"]
    edit_label = ctk.CTkLabel(action_frame, text="Edit Student Data", font=("Arial", 16, "bold"))
    edit_label.pack(pady=(5,10), fill="x")
    for key, value in document.items():
        if key == "_id" or key == "semesters" or key == "cgpa":
            continue
        label = ctk.CTkLabel(action_frame, text=key)
        label.pack(pady=(2,0), fill="x")
        entry = ctk.CTkEntry(action_frame)
        entry.insert(0, str(value))
        entry.pack(pady=(0,5), fill="x")
        entry_widgets[key] = entry
    commit_btn = ctk.CTkButton(action_frame, text="Commit Changes", command=commit_changes)
    commit_btn.pack(pady=10, fill="x")
    score_btn = ctk.CTkButton(action_frame, text="Student Score", command=lambda: open_student_window(document))
    score_btn.pack(pady=10, fill="x")
    # Add Delete button
    if delete_button:
        delete_button.pack_forget()
        delete_button.pack(pady=10, fill="x")
    if add_new_button:
        add_new_button.pack_forget()
        add_new_button.pack(pady=10, fill="x")

def commit_changes():
    global current_doc_id, entry_widgets
    if not current_doc_id:
        return
    updates = {}
    for key, entry in entry_widgets.items():
        val = entry.get()
        if key in ["name", "rollno", "department"]:
            val = val.upper()
        updates[key] = val
    collection = db['students']
    collection.update_one({"_id": current_doc_id}, {"$set": updates})
    display_data()  # Refresh left panel

def show_add_fields():
    global add_new_button
    exclude = [search_entry, search_button, view_db_button, add_new_button, delete_button]
    clear_action_frame(exclude)
    add_entries = {}
    add_label = ctk.CTkLabel(action_frame, text="Adding Student Data", font=("Arial", 16, "bold"))
    add_label.pack(pady=(5,10), fill="x")
    for field in ["name", "department", "rollno"]:
        label = ctk.CTkLabel(action_frame, text=field)
        label.pack(pady=(2,0), fill="x")
        entry = ctk.CTkEntry(action_frame)
        entry.pack(pady=(0,5), fill="x")
        add_entries[field] = entry
    def submit_new(): 
        collection = db['students']
        new_doc = {}
        for k, v in add_entries.items():
            val = v.get()
            if k in ["name", "rollno", "department"]:
                val = val.upper()
            new_doc[k] = val
        # Check for existing rollno (case-insensitive)
        if collection.find_one({'rollno': {'$regex': f'^{new_doc["rollno"]}$', '$options': 'i'}}):
            for widget in data_frame.winfo_children():
                widget.destroy()
            error_msg = "Add failed: Roll No already exists. Delete or use a different Roll No."
            label = ctk.CTkLabel(data_frame, text=error_msg, text_color="red", font=("Arial", 15, "bold"))
            label.pack(pady=20)
            return
        collection.insert_one(new_doc)
        display_data()
        clear_action_frame(exclude)
        if add_new_button:
            add_new_button.pack_forget()
            add_new_button.pack(pady=10, fill="x")
        if delete_button:
            delete_button.pack_forget()
            delete_button.pack(pady=10, fill="x")
    submit_btn = ctk.CTkButton(action_frame, text="Submit", command=submit_new)
    submit_btn.pack(pady=10, fill="x")
    if add_new_button:
        add_new_button.pack_forget()
        add_new_button.pack(pady=10, fill="x")
    if delete_button:
        delete_button.pack_forget()
        delete_button.pack(pady=10, fill="x")

def delete_selected():
    global current_doc_id
    if current_doc_id:
        collection = db['students']
        collection.delete_one({"_id": current_doc_id})
        display_data()
        # Clear edit fields after delete
        exclude = [search_entry, search_button, view_db_button, add_new_button, delete_button]
        clear_action_frame(exclude)
        if add_new_button:
            add_new_button.pack_forget()
            add_new_button.pack(pady=10, fill="x")
        if delete_button:
            delete_button.pack_forget()
            delete_button.pack(pady=10, fill="x")
        current_doc_id = None

def search_data(event=None):
    query = search_var.get().strip()
    for widget in data_frame.winfo_children():
        widget.destroy()
    if not query:
        display_data()
        return
    collection = db['students']
    data = []
    # Case-insensitive rollno search
    data = list(collection.find({'rollno': {'$regex': f'^{query}$', '$options': 'i'}}))
    if not data:
        # Try _id
        from bson import ObjectId
        try:
            data = list(collection.find({'_id': ObjectId(query)}))
        except Exception:
            pass
    if not data:
        # Try name regex (case-insensitive)
        data = list(collection.find({'name': {'$regex': query, '$options': 'i'}}))
    if not data:
        label = ctk.CTkLabel(data_frame, text="No results found.")
        label.pack(pady=10)
    else:
        for idx, item in enumerate(data):
            # Only show ObjectId, name, rollno, department
            display_text = f"ID: {item.get('_id', '')} | Name: {item.get('name', '')} | Roll No: {item.get('rollno', '')} | Dept: {item.get('department', '')}"
            label = ctk.CTkLabel(data_frame, text=display_text, anchor="w", justify="left")
            label.pack(fill="x", padx=5, pady=2)
        if len(data) == 1:
            show_edit_fields(data[0])
        else:
            if add_new_button:
                add_new_button.pack_forget()
                add_new_button.pack(pady=10, fill="x")

search_entry = ctk.CTkEntry(action_frame, textvariable=search_var, placeholder_text="Search by name or ID")
search_entry.pack(pady=(0,5), fill="x")
search_entry.bind("<Return>", search_data)

search_button = ctk.CTkButton(action_frame, text="Search", command=search_data)
search_button.pack(pady=(0,10), fill="x")

view_db_button = ctk.CTkButton(action_frame, text="View Database", command=display_data)
view_db_button.pack(pady=10, fill="x")

# Remove Change & Save button, add Delete button
delete_button = ctk.CTkButton(action_frame, text="Delete", command=delete_selected)
# Don't pack here; pack in show_edit_fields when needed

add_new_button = ctk.CTkButton(action_frame, text="Add New", command=show_add_fields)
add_new_button.pack(pady=10, fill="x")

# Start the application
app.mainloop()
# Close the MongoDB client when the application exits
client.close()




