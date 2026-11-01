# 📚 Athena Library Management System
### Intelligent NoSQL Databases Project (Python Flask + MongoDB & PyMongo)

A beginner-friendly Library Management System built for a college practical exam and viva demonstration. The project demonstrates direct **MongoDB CRUD operations** and a simple **aggregation pipeline** using pure **PyMongo**, presented through a clean, modern web interface built with **Python Flask, HTML5, CSS3, and JavaScript**.

---

## 📌 1. Project Introduction & Objectives

### Introduction
The **Athena Library Management System** is a college-level web application designed to demonstrate how a document-oriented NoSQL database (MongoDB) stores and manages data. It avoids complicated Object-Document Mappers (ODMs) and interacts directly with MongoDB Community Server using the official `pymongo` driver.

### Main Objectives:
1. **Demonstrate Direct PyMongo CRUD Operations**:
   - **Create**: `insert_one()` for adding books, students, and circulation records.
   - **Read**: `find()` and `find_one()` for viewing and searching.
   - **Update**: `update_one()` with `$set` for editing details, and `$inc` for copy counts.
   - **Delete**: `delete_one()` for removing records.
2. **Demonstrate a MongoDB Aggregation Pipeline**:
   - Group books by category and count the number of books in each category using `aggregate()`.
3. **Data Integrity & Copy Tracking**:
   - When a book is issued, its available copy count automatically decreases by 1.
   - When a book is returned, its available copy count increases by 1.
   - Books or students with active loans cannot be deleted.

---

## 🛠️ 2. Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | Python 3 & Flask | Simple routes and request handling |
| **Database** | MongoDB Community Server | Local database running at `mongodb://localhost:27017/` |
| **Database Driver** | PyMongo | Direct MongoDB queries (no MongoEngine or ORM) |
| **Frontend** | HTML5, CSS3, JavaScript | Simple forms, tables, and modal dialogs |
| **Icons & Charts** | Font Awesome 6 & Chart.js | Clean visual interface |

---

## 📂 3. Project Structure

```text
Library/
│
├── app.py                      # Flask routes, authentication guard, PyMongo database operations
├── database.py                 # MongoDB connection, strict $jsonSchema validators, unique indexes
├── requirements.txt            # Required Python packages (Flask, pymongo)
├── README.md                   # Setup instructions and viva preparation
│
├── templates/                  # HTML5 Jinja2 Templates
│   ├── base.html               # Main layout, librarian sidebar badge & sign-out button
│   ├── login.html              # Dedicated Librarian Login Portal
│   ├── dashboard.html          # Overview metric cards, category chart & recent activity
│   ├── books.html              # Books catalog: Add, View, Search, Edit, Fast Issue, Delete
│   ├── students.html           # Students directory: Register, Search, Permanent ID, Edit, Delete
│   ├── issue_books.html        # Circulation: Issue, Return, ISBN Search, Restricted Edit
│   └── reports.html            # Category aggregation and overdue reports
│
└── static/                     # CSS styling and JavaScript
    ├── style.css               # Clean, modern responsive stylesheet
    └── script.js               # Modal dialog interactions and notification auto-dismissal
```

---

## 🔐 4. Librarian Authentication & Credentials

The application is secured with librarian login authentication. All management routes require an active session.

- **Login URL:** `http://127.0.0.1:5000/login`
- **Librarian Email:** `neerajnegi90451@gmail.com`
- **Password:** `12345`

*Stored in MongoDB collection: `librarians` with unique index on `email`.*

### 🎓 4.1 Student Self-Service Portal
Students can register, browse the catalog, and apply for book loans:

- **Student Sign Up:** `http://127.0.0.1:5000/student/register`
- **Student Login:** `http://127.0.0.1:5000/student/login`
- **Sample Student Accounts:**
  - Email: `rahul.sharma@college.edu` (or ID: `1000000001`), Password: `12345`
  - Email: `priya.patel@college.edu` (or ID: `1000000002`), Password: `12345`
- **Application Workflow:**
  - Student browses books and clicks **"Apply for Book"**.
  - A record is created in MongoDB collection `book_applications` with status `"Pending"`.
  - The Librarian sees pending applications on the Dashboard and under **Issue & Return Books**, where they can click **"Approve & Issue"** (which automatically decrements book copies and issues the loan) or **"Reject"**.

---

## 🗄️ 5. MongoDB Database & Collection Design

- **Database Name:** `library_db`
- **Connection String:** `mongodb://localhost:27017/`

### 1. `books` Collection
```json
{
  "_id": ObjectId("..."),
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "isbn": "9780132350884",
  "category": "Computer Science",
  "publication_year": 2008,
  "total_copies": 5,
  "available_copies": 4,
  "shelf_location": "CS-A101"
}
```
*Index:* Unique index on `isbn`.

### 2. `students` Collection
```json
{
  "_id": ObjectId("..."),
  "student_id": "STU001",
  "name": "Rahul Sharma",
  "email": "rahul.sharma@college.edu",
  "course": "B.Tech CSE",
  "contact": "9876543210"
}
```
*Index:* Unique index on `student_id`.

### 3. `issued_books` Collection
```json
{
  "_id": ObjectId("..."),
  "student_ref": ObjectId("..."),
  "student_id": "STU001",
  "student_name": "Rahul Sharma",
  "book_ref": ObjectId("..."),
  "book_title": "Clean Code",
  "issue_date": ISODate("2026-10-24T00:00:00Z"),
  "due_date": ISODate("2026-11-07T00:00:00Z"),
  "return_date": null,
  "status": "Issued"
}
```

---

## ⚡ 5. PyMongo CRUD Operations in Code

| Action | PyMongo Method | Example Code in `app.py` |
| :--- | :--- | :--- |
| **Add Book** | `insert_one()` | `books_col.insert_one(book_data)` |
| **View Books** | `find()` | `books_col.find(query).sort("title", 1)` |
| **Find One Book** | `find_one()` | `books_col.find_one({"_id": ObjectId(book_id)})` |
| **Edit Book** | `update_one()` | `books_col.update_one({"_id": oid}, {"$set": update_data})` |
| **Delete Book** | `delete_one()` | `books_col.delete_one({"_id": oid})` |
| **Issue Book** | `insert_one()` + `update_one()` | Decrement copy: `books_col.update_one({"_id": b_oid}, {"$inc": {"available_copies": -1}})` |
| **Return Book** | `update_one()` + `update_one()` | Increment copy: `books_col.update_one({"_id": b_oid}, {"$inc": {"available_copies": 1}})` |
| **Category Report** | `aggregate()` | Group by category: `books_col.aggregate(pipeline)` |

---

## 🔬 6. MongoDB Aggregation Pipeline Example

On the **Reports** page, books are grouped by category using PyMongo's `aggregate()`:

```python
pipeline = [
    # Stage 1: Group books by category and count titles and copies
    {
        "$group": {
            "_id": "$category",
            "titles_count": {"$sum": 1},
            "total_copies": {"$sum": "$total_copies"},
            "available_copies": {"$sum": "$available_copies"}
        }
    },
    # Stage 2: Sort categories by number of titles in descending order
    {
        "$sort": {"titles_count": -1}
    }
]

category_summary = list(books_col.aggregate(pipeline))
```

---

## 💻 7. Installation & Setup Instructions (Windows)

### Step 1: Make sure MongoDB is running
Check MongoDB service in PowerShell:
```powershell
Get-Service -Name "*mongo*"
```
If stopped, start it:
```powershell
net start MongoDB
```

### Step 2: Open terminal in project folder
```powershell
cd c:\Users\aniket\Desktop\Library
```

### Step 3: Install dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Load sample data
Run the seed script to insert 10 books, 5 students, and 3 loans:
```powershell
python seed_data.py
```

### Step 5: Run the web application
```powershell
python app.py
```

Open your browser and visit:
👉 **`http://127.0.0.1:5000`**

---

## ⚠️ 8. Common Errors & Solutions

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `ServerSelectionTimeoutError` | MongoDB service is not started. | Run `net start MongoDB` as Administrator. |
| `DuplicateKeyError` | Trying to use an existing ISBN or Student ID. | Enter a unique ISBN or Student ID. |
| `Cannot delete book` | Book is currently issued to a student. | Return the book first under **Issue & Return Books**. |
| `Port 5000 in use` | Another Flask instance is already running. | Close other running Python terminal windows. |

---

## 🎓 9. Viva Questions & Answers for College Practical Exam

### Q1. What is MongoDB and how does it differ from SQL?
**Answer:** MongoDB is a document-oriented NoSQL database. It stores data in flexible BSON documents rather than relational tables with fixed rows and columns.

### Q2. What is PyMongo?
**Answer:** PyMongo is the official Python library that allows Python applications to connect to MongoDB and execute queries directly.

### Q3. What is an `ObjectId` in MongoDB?
**Answer:** `ObjectId` is a 12-byte unique identifier generated by MongoDB for the `_id` field of every document, acting as the primary key.

### Q4. What is the difference between `insert_one()` and `insert_many()`?
**Answer:** `insert_one()` inserts a single document into a collection, while `insert_many()` inserts a list of documents in a single operation.

### Q5. How does this project enforce unique values for ISBN and Student ID?
**Answer:** By creating unique indexes using `db.books.create_index("isbn", unique=True)` and `db.students.create_index("student_id", unique=True)`. If a duplicate value is submitted, MongoDB raises a `DuplicateKeyError`.

### Q6. How does search work in this project?
**Answer:** We use MongoDB's `$regex` operator with the case-insensitive option (`$options: "i"`) inside an `$or` query to match titles, authors, or ISBN numbers.

### Q7. What is the difference between `$set` and `$inc` in `update_one()`?
**Answer:** `$set` replaces specific fields with new values (like updating a book's title), while `$inc` atomically increments or decrements a numeric field by a number (like decreasing available copies by -1).

### Q8. Why is `$inc` used when issuing or returning books?
**Answer:** `$inc` performs the calculation directly inside the database atomically, preventing race conditions if multiple loans are updated at the same time.

### Q9. How is referential integrity maintained without foreign keys?
**Answer:** Before deleting a book or student, Python queries `issued_books.count_documents({"status": "Issued"})`. If active loans exist, deletion is blocked to prevent orphaned records.

### Q10. Explain the aggregation pipeline used on the Reports page.
**Answer:** It uses two stages:
1. `$group`: Groups documents by the `$category` field and calculates the total count with `{"$sum": 1}`.
2. `$sort`: Sorts the resulting categories in descending order based on title count.

### Q11. How are dates stored in MongoDB?
**Answer:** Dates are stored as BSON Date values using Python's `datetime` objects. This allows comparison queries, such as finding overdue books where `due_date < datetime.now()`.

### Q12. What happens when a book is issued?
**Answer:**
1. A loan record is inserted into `issued_books` with `status: "Issued"`.
2. The book's `available_copies` is decreased by 1 using `{"$inc": {"available_copies": -1}}`.

### Q13. What happens when a book is returned?
**Answer:**
1. The loan record is updated to `status: "Returned"` with the current `return_date`.
2. The book's `available_copies` is increased by 1 using `{"$inc": {"available_copies": 1}}`.

### Q14. What happens if an active issue record is deleted?
**Answer:** If deleted while still active, 1 available copy is restored to the associated book before the record is deleted.

### Q15. Why use PyMongo directly instead of an ODM like MongoEngine?
**Answer:** Using PyMongo directly demonstrates understanding of raw MongoDB queries, operators (`$set`, `$inc`, `$regex`), and aggregation pipelines, which is the main goal of the database assignment.

### Q16. How does the dashboard handle an empty database?
**Answer:** It checks document counts and shows zeros along with an informative message, preventing errors or crashes.
