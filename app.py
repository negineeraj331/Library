"""Library Management System Flask application and database operations."""

import random
from datetime import datetime, date, timedelta
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, WriteError, OperationFailure
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

from database import get_collections, check_connection, get_db, get_applications_col

app = Flask(__name__)
app.secret_key = "library-secret-key"


# Authentication Guard & Context Processors
@app.before_request
def require_login():
    """Route security guard for librarian and student portals."""
    public_paths = [
        "/login",
        "/static",
        "/student/login",
        "/student/register",
        "/api/check_student_id"
    ]
    if request.path == "/" or any(request.path.startswith(p) for p in public_paths):
        return None

    # Student portal routes
    if request.path == "/student" or request.path.startswith("/student/"):
        if not session.get("student_logged_in"):
            flash("Please sign in as a student to access the Student Portal.", "info")
            return redirect(url_for("student_login"))
        return None

    # Librarian management routes
    if not session.get("logged_in"):
        return redirect(url_for("login"))


# Template Helper Filters
@app.template_filter("pretty_date")
def pretty_date(val):
    """Format datetime for clean display in HTML tables."""
    if isinstance(val, (datetime, date)):
        return val.strftime("%b %d, %Y")
    return str(val)[:10] if val else "—"


@app.template_filter("format_date")
def format_date(val):
    """Format date for HTML date inputs (YYYY-MM-DD)."""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10] if val else ""


@app.context_processor
def inject_status():
    """Provides system online status and librarian session info to base.html on every page."""
    connected, _ = check_connection()
    return {
        "db_connected": connected,
        "current_user_email": session.get("user_email", "neerajnegi90451@gmail.com"),
        "current_user_name": session.get("user_name", "Neeraj Negi (Librarian)")
    }


# Librarian & Student Authentication (Sign In Portal)
@app.route("/login", methods=["GET", "POST"])
def login():
    """Sign In Portal for Librarians and Students."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # Query MongoDB collection 'librarians' using find_one
        db = get_db()
        librarian = db["librarians"].find_one({"email": email, "password": password})

        if librarian or (email == "neerajnegi90451@gmail.com" and password == "12345"):
            session["logged_in"] = True
            session["user_email"] = email
            session["user_name"] = librarian.get("name", "Neeraj Negi (Librarian)") if librarian else "Neeraj Negi (Librarian)"
            flash(f"Welcome back, {session['user_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Access is restricted to authorized librarians.", "error")
            return render_template("login.html", active_tab="librarian")

    active_tab = request.args.get("tab", "librarian")
    return render_template("login.html", active_tab=active_tab)


@app.route("/logout")
def logout():
    """Clear librarian session and redirect to login."""
    session.clear()
    flash("You have been signed out of the Librarian portal.", "info")
    return redirect(url_for("login"))


# Entry & Authentication Landing Route
@app.route("/")
def home():
    """Initial landing route: redirects first-time visitors to the Login/Register page."""
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    books_col, students_col, issued_col = get_collections()
    now = datetime.now()

    # 1. MongoDB count_documents for key metrics
    total_books = books_col.count_documents({})
    total_students = students_col.count_documents({})
    issued_count = issued_col.count_documents({"status": "Issued"})
    overdue_count = issued_col.count_documents({"status": "Issued", "due_date": {"$lt": now}})

    # 2. MongoDB aggregation to sum copy totals directly in database
    copies_agg = list(books_col.aggregate([
        {
            "$group": {
                "_id": None,
                "total_stock": {"$sum": "$total_copies"},
                "total_available": {"$sum": "$available_copies"}
            }
        }
    ]))
    total_copies_stock = copies_agg[0]["total_stock"] if copies_agg else 0
    available_copies = copies_agg[0]["total_available"] if copies_agg else 0

    # 3. Recent records using find(), sort(), and limit()
    recent_books = list(books_col.find().sort("_id", -1).limit(5))
    recent_issues = list(issued_col.find().sort("_id", -1).limit(5))

    # 4. Aggregation pipeline for category summary chart
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}, "total_copies": {"$sum": "$total_copies"}}},
        {"$sort": {"count": -1}}
    ]
    categories_agg = list(books_col.aggregate(pipeline))

    # 5. Pending student book applications count
    applications_col = get_applications_col()
    pending_applications_count = applications_col.count_documents({"status": "Pending"})

    return render_template(
        "dashboard.html",
        total_books=total_books,
        total_students=total_students,
        available_copies=available_copies,
        total_copies_stock=total_copies_stock,
        issued_count=issued_count,
        overdue_count=overdue_count,
        recent_books=recent_books,
        recent_issues=recent_issues,
        categories_agg=categories_agg,
        pending_applications_count=pending_applications_count
    )


# Books Management (CRUD)
@app.route("/books")
def books_list():
    books_col, students_col, _ = get_collections()
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    # Build MongoDB query filter
    query = {}
    if category and category != "All":
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
            {"isbn": {"$regex": search, "$options": "i"}}
        ]

    books = list(books_col.find(query).sort("title", 1))
    categories = sorted(books_col.distinct("category"))
    students = list(students_col.find().sort("name", 1))

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        students=students,
        search_query=search,
        selected_category=category,
        today_date=date.today().strftime("%Y-%m-%d"),
        default_due_date=(date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    )


@app.route("/books/add", methods=["POST"])
def add_book():
    books_col, _, _ = get_collections()

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    isbn = request.form.get("isbn", "").strip()
    category = request.form.get("category", "").strip()
    shelf_location = request.form.get("shelf_location", "").strip()
    year_str = request.form.get("publication_year", "")
    copies_str = request.form.get("total_copies", "")

    # Parse numeric values
    try:
        publication_year = int(year_str)
        total_copies = int(copies_str)
    except (ValueError, TypeError):
        flash("Publication year and total copies must be valid numbers.", "error")
        return redirect(url_for("books_list"))

    book_data = {
        "title": title,
        "author": author,
        "isbn": isbn,
        "category": category,
        "publication_year": publication_year,
        "year": publication_year,
        "total_copies": total_copies,
        "available_copies": total_copies,
        "shelf_location": shelf_location
    }

    # Insert record and let MongoDB $jsonSchema & unique index validate
    try:
        books_col.insert_one(book_data)
        flash(f"Book '{title}' added successfully!", "success")
    except DuplicateKeyError:
        flash(f"This ISBN '{isbn}' is already registered and already exists in the catalog.", "error")
    except (WriteError, OperationFailure):
        flash("Book details are invalid. Please check required fields, publication year (>= 1000), and total copies (>= 1).", "error")

    return redirect(url_for("books_list"))


@app.route("/books/edit/<book_id>", methods=["POST"])
def edit_book(book_id):
    books_col, _, issued_col = get_collections()
    try:
        obj_id = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID.", "error")
        return redirect(url_for("books_list"))

    current_book = books_col.find_one({"_id": obj_id})
    if not current_book:
        flash("Book not found.", "error")
        return redirect(url_for("books_list"))

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    isbn = request.form.get("isbn", "").strip()
    category = request.form.get("category", "").strip()
    shelf_location = request.form.get("shelf_location", "").strip()
    year_str = request.form.get("publication_year", "")
    copies_str = request.form.get("total_copies", "")

    try:
        publication_year = int(year_str)
        new_total = int(copies_str)
    except (ValueError, TypeError):
        flash("Publication year and total copies must be valid numbers.", "error")
        return redirect(url_for("books_list"))

    # Business rule: Cannot reduce total copies below currently issued count
    issued = current_book.get("total_copies", 0) - current_book.get("available_copies", 0)
    if new_total < issued:
        flash(f"Cannot set total copies to {new_total}. {issued} copy(ies) are currently issued.", "error")
        return redirect(url_for("books_list"))

    new_available = new_total - issued

    update_data = {
        "title": title,
        "author": author,
        "isbn": isbn,
        "category": category,
        "publication_year": publication_year,
        "year": publication_year,
        "total_copies": new_total,
        "available_copies": new_available,
        "shelf_location": shelf_location
    }

    try:
        books_col.update_one({"_id": obj_id}, {"$set": update_data})
        # Synchronise updated book title and ISBN across loan records
        issued_col.update_many(
            {"book_ref": obj_id},
            {"$set": {"book_title": title, "book_isbn": isbn}}
        )
        flash(f"Book '{title}' updated successfully!", "success")
    except DuplicateKeyError:
        flash(f"This ISBN '{isbn}' is already registered and already exists in the catalog.", "error")
    except (WriteError, OperationFailure):
        flash("Book details are invalid. Publication year must be at least 1000 and total copies at least 1.", "error")

    return redirect(url_for("books_list"))


@app.route("/books/delete/<book_id>", methods=["GET", "POST"])
def delete_book(book_id):
    books_col, _, issued_col = get_collections()
    try:
        obj_id = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID.", "error")
        return redirect(url_for("books_list"))

    book = books_col.find_one({"_id": obj_id})
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("books_list"))

    # Clean up any associated circulation records for this book to maintain referential cleanliness
    issued_col.delete_many({"$or": [{"book_ref": obj_id}, {"book_title": book.get("title", "")}]})

    result = books_col.delete_one({"_id": obj_id})
    if result.deleted_count > 0:
        flash(f"Book '{book.get('title')}' deleted successfully.", "success")
    else:
        flash("Book could not be deleted.", "error")
    return redirect(url_for("books_list"))


# Students Management (CRUD)
def generate_student_id(students_col=None):
    """Generate a unique 10-digit numeric student ID."""
    if students_col is None:
        _, students_col, _ = get_collections()
    while True:
        candidate_id = str(random.randint(1000000000, 9999999999))
        if not students_col.find_one({"student_id": candidate_id}):
            return candidate_id


@app.route("/api/check_student_id")
def check_student_id():
    """Check if a student ID already exists in MongoDB."""
    _, students_col, _ = get_collections()
    sid = request.args.get("student_id", "").strip()
    if not sid:
        return jsonify({"exists": False})
    exists = students_col.count_documents({"student_id": sid}) > 0
    return jsonify({"exists": exists})


@app.route("/students")
def students_list():
    _, students_col, _ = get_collections()
    search = request.args.get("search", "").strip()

    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"student_id": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"course": {"$regex": search, "$options": "i"}}
        ]

    students = list(students_col.find(query).sort("name", 1))
    new_student_id = generate_student_id(students_col)

    return render_template(
        "students.html",
        students=students,
        search_query=search,
        new_student_id=new_student_id,
        form_data={},
        student_id_error=None,
        open_add_modal=False
    )


@app.route("/students/add", methods=["POST"])
def add_student():
    _, students_col, _ = get_collections()

    name = request.form.get("name", "").strip()
    student_id = request.form.get("student_id", "").strip()
    email = request.form.get("email", "").strip()
    course = request.form.get("course", "").strip()
    contact = request.form.get("contact", "").strip()

    # Generate random unique 10-digit ID if empty
    if not (student_id and student_id.isdigit() and len(student_id) == 10):
        student_id = generate_student_id(students_col)

    student_data = {
        "student_id": student_id,
        "name": name,
        "email": email,
        "course": course,
        "contact": contact
    }

    form_cache = {
        "student_id": student_id,
        "name": name,
        "email": email,
        "course": course,
        "contact": contact
    }

    # Pre-check if Student ID already exists in MongoDB
    if students_col.count_documents({"student_id": student_id}) > 0:
        students = list(students_col.find().sort("name", 1))
        return render_template(
            "students.html",
            students=students,
            search_query="",
            new_student_id=generate_student_id(students_col),
            open_add_modal=True,
            form_data=form_cache,
            student_id_error=f"Student ID '{student_id}' already exists! Please enter a different ID or click 🔄 to generate one."
        )

    try:
        students_col.insert_one(student_data)
        flash(f"Student '{name}' registered with 10-digit ID {student_id}!", "success")
        return redirect(url_for("students_list"))
    except DuplicateKeyError as err:
        err_msg = str(err)
        students = list(students_col.find().sort("name", 1))
        if "student_id" in err_msg:
            return render_template(
                "students.html",
                students=students,
                search_query="",
                new_student_id=generate_student_id(students_col),
                open_add_modal=True,
                form_data=form_cache,
                student_id_error=f"Student ID '{student_id}' already exists! Please enter a different ID or click 🔄."
            )
        elif "email" in err_msg:
            flash(f"Email '{email}' is already registered to another student.", "error")
            return render_template(
                "students.html",
                students=students,
                search_query="",
                new_student_id=generate_student_id(students_col),
                open_add_modal=True,
                form_data=form_cache,
                student_id_error=None
            )
        elif "contact" in err_msg:
            flash(f"Phone number '{contact}' is already registered to another student.", "error")
            return render_template(
                "students.html",
                students=students,
                search_query="",
                new_student_id=generate_student_id(students_col),
                open_add_modal=True,
                form_data=form_cache,
                student_id_error=None
            )
        else:
            flash("Duplicate information entered.", "error")
            return redirect(url_for("students_list"))
    except (WriteError, OperationFailure):
        flash("Student details are invalid: Phone number must be exactly 10 digits and email must contain '@'.", "error")
        return redirect(url_for("students_list"))


@app.route("/students/edit/<student_id>", methods=["POST"])
def edit_student(student_id):
    _, students_col, issued_col = get_collections()
    try:
        obj_id = ObjectId(student_id)
    except Exception:
        flash("Invalid student ID.", "error")
        return redirect(url_for("students_list"))

    existing_student = students_col.find_one({"_id": obj_id})
    if not existing_student:
        flash("Student not found.", "error")
        return redirect(url_for("students_list"))

    # Student ID is permanent once generated and cannot be modified
    fixed_sid = existing_student.get("student_id")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    course = request.form.get("course", "").strip()
    contact = request.form.get("contact", "").strip()

    update_data = {
        "student_id": fixed_sid,
        "name": name,
        "email": email,
        "course": course,
        "contact": contact
    }

    try:
        students_col.update_one({"_id": obj_id}, {"$set": update_data})
        # Synchronise student details in active loans
        issued_col.update_many(
            {"student_ref": obj_id, "status": "Issued"},
            {"$set": {"student_id": fixed_sid, "student_name": name}}
        )
        flash(f"Student '{name}' updated successfully!", "success")
    except DuplicateKeyError as err:
        err_msg = str(err)
        if "email" in err_msg:
            flash(f"Email '{email}' is already registered to another student.", "error")
        elif "contact" in err_msg:
            flash(f"Phone number '{contact}' is already registered to another student.", "error")
        else:
            flash("Duplicate information entered.", "error")
    except (WriteError, OperationFailure):
        flash("Student details are invalid: Phone number must be exactly 10 digits and email must contain '@'.", "error")

    return redirect(url_for("students_list"))


@app.route("/students/delete/<student_id>", methods=["GET", "POST"])
def delete_student(student_id):
    _, students_col, issued_col = get_collections()
    try:
        obj_id = ObjectId(student_id)
    except Exception:
        flash("Invalid student ID.", "error")
        return redirect(url_for("students_list"))

    # Referential integrity: check active loans using count_documents()
    active_loans = issued_col.count_documents({"student_ref": obj_id, "status": "Issued"})
    if active_loans > 0:
        flash(f"Cannot delete student: {active_loans} book(s) are currently issued to them.", "error")
        return redirect(url_for("students_list"))

    result = students_col.delete_one({"_id": obj_id})
    if result.deleted_count > 0:
        flash("Student deleted successfully.", "success")
    else:
        flash("Student not found.", "error")
    return redirect(url_for("students_list"))


# Issued Books Management (Circulation & Full CRUD)
@app.route("/issues")
def issues_list():
    books_col, students_col, issued_col = get_collections()
    now = datetime.now()
    status_filter = request.args.get("status", "All").strip()
    search = request.args.get("search", "").strip()

    # Build status query
    query = {}
    if status_filter == "Issued":
        query["status"] = "Issued"
    elif status_filter == "Returned":
        query["status"] = "Returned"
    elif status_filter == "Overdue":
        query["status"] = "Issued"
        query["due_date"] = {"$lt": now}

    # Search filter matching student, book title, or ISBN
    if search:
        matching_books = list(books_col.find(
            {"$or": [
                {"isbn": {"$regex": search, "$options": "i"}},
                {"title": {"$regex": search, "$options": "i"}}
            ]},
            {"_id": 1}
        ))
        matching_book_ids = [b["_id"] for b in matching_books]

        query["$or"] = [
            {"student_name": {"$regex": search, "$options": "i"}},
            {"student_id": {"$regex": search, "$options": "i"}},
            {"book_title": {"$regex": search, "$options": "i"}},
            {"book_isbn": {"$regex": search, "$options": "i"}},
            {"book_ref": {"$in": matching_book_ids}}
        ]

    issues = list(issued_col.find(query).sort("issue_date", -1))
    books = list(books_col.find().sort("title", 1))
    books_isbn_map = {b["_id"]: b.get("isbn", "") for b in books}

    for iss in issues:
        due = iss.get("due_date")
        iss["is_overdue"] = (iss.get("status") == "Issued" and isinstance(due, datetime) and due < now)
        iss["days_overdue"] = max(1, (now - due).days) if iss["is_overdue"] else 0
        if not iss.get("book_isbn") and iss.get("book_ref") in books_isbn_map:
            iss["book_isbn"] = books_isbn_map[iss["book_ref"]]

    students = list(students_col.find().sort("name", 1))

    # Pending student applications
    applications_col = get_applications_col()
    pending_applications = list(applications_col.find({"status": "Pending"}).sort("apply_date", -1))

    return render_template(
        "issue_books.html",
        issues=issues,
        students=students,
        books=books,
        pending_applications=pending_applications,
        selected_status=status_filter,
        search_query=search,
        today_date=date.today().strftime("%Y-%m-%d"),
        default_due_date=(date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    )


@app.route("/issues/add", methods=["POST"])
def add_issue():
    books_col, students_col, issued_col = get_collections()
    student_ref = request.form.get("student_ref")
    book_ref = request.form.get("book_ref")
    issue_date_str = request.form.get("issue_date")
    due_date_str = request.form.get("due_date")
    redirect_target = request.form.get("redirect_to", "issues")

    dest_url = url_for("books_list") if redirect_target == "books" else url_for("issues_list")

    try:
        student_obj = ObjectId(student_ref)
        book_obj = ObjectId(book_ref)
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d")
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        flash("Please provide valid student, book, and dates.", "error")
        return redirect(dest_url)

    student = students_col.find_one({"_id": student_obj})
    book = books_col.find_one({"_id": book_obj})

    if not student or not book:
        flash("Student or book record not found.", "error")
        return redirect(dest_url)

    # 1. Use conditional MongoDB update to reserve an available copy atomically
    reserve_result = books_col.update_one(
        {
            "_id": book["_id"],
            "available_copies": {"$gt": 0}
        },
        {
            "$inc": {"available_copies": -1}
        }
    )

    if reserve_result.modified_count == 0:
        flash(f"No copies of '{book['title']}' are currently available for issue.", "error")
        return redirect(dest_url)

    # 2. Insert loan record
    issue_data = {
        "student_ref": student["_id"],
        "student_id": student["student_id"],
        "student_name": student["name"],
        "book_ref": book["_id"],
        "book_title": book["title"],
        "book_isbn": book.get("isbn", ""),
        "issue_date": issue_date,
        "due_date": due_date,
        "return_date": None,
        "status": "Issued"
    }

    try:
        issued_col.insert_one(issue_data)
        flash(f"Book '{book['title']}' issued to {student['name']} ({student['student_id']})!", "success")
    except Exception as err:
        # Rollback copy reservation if issue insertion fails
        books_col.update_one({"_id": book["_id"]}, {"$inc": {"available_copies": 1}})
        flash(f"Could not issue book: Document failed validation. ({err})", "error")

    return redirect(dest_url)


@app.route("/issues/return/<issue_id>", methods=["POST"])
def return_issue(issue_id):
    books_col, _, issued_col = get_collections()
    try:
        obj_id = ObjectId(issue_id)
    except Exception:
        flash("Invalid loan record ID.", "error")
        return redirect(url_for("issues_list"))

    # Atomically mark as Returned only if currently Issued
    issue = issued_col.find_one_and_update(
        {
            "_id": obj_id,
            "status": "Issued"
        },
        {
            "$set": {
                "status": "Returned",
                "return_date": datetime.now()
            }
        }
    )

    if not issue:
        flash("This book is already returned or record was not found.", "error")
        return redirect(url_for("issues_list"))

    # Increase available copies only because status update succeeded
    books_col.update_one({"_id": issue["book_ref"]}, {"$inc": {"available_copies": 1}})
    flash(f"Book '{issue['book_title']}' returned successfully!", "success")
    return redirect(url_for("issues_list"))


@app.route("/issues/edit/<issue_id>", methods=["POST"])
def edit_issue(issue_id):
    books_col, _, issued_col = get_collections()
    try:
        obj_id = ObjectId(issue_id)
        due_date = datetime.strptime(request.form.get("due_date", ""), "%Y-%m-%d")
        new_status = request.form.get("status", "Issued")
    except (ValueError, TypeError):
        flash("Please provide a valid due date.", "error")
        return redirect(url_for("issues_list"))

    issue = issued_col.find_one({"_id": obj_id})
    if not issue:
        flash("Loan record not found.", "error")
        return redirect(url_for("issues_list"))

    old_status = issue.get("status", "Issued")
    book_id = issue.get("book_ref")

    # Maintain copy counts using conditional updates and $inc:
    # 1. Issued -> Returned: restore 1 copy
    if old_status == "Issued" and new_status == "Returned":
        books_col.update_one({"_id": book_id}, {"$inc": {"available_copies": 1}})
        return_date = datetime.now()

    # 2. Returned -> Issued: reserve 1 copy
    elif old_status == "Returned" and new_status == "Issued":
        res = books_col.update_one(
            {"_id": book_id, "available_copies": {"$gt": 0}},
            {"$inc": {"available_copies": -1}}
        )
        if res.modified_count == 0:
            flash(f"Cannot set to Issued: No copies currently available for '{issue.get('book_title')}'.", "error")
            return redirect(url_for("issues_list"))
        return_date = None

    else:
        return_date = issue.get("return_date")
        if new_status == "Returned" and not return_date:
            return_date = datetime.now()

    updated_data = {
        "due_date": due_date,
        "return_date": return_date,
        "status": new_status
    }

    try:
        issued_col.update_one({"_id": obj_id}, {"$set": updated_data})
        flash("Loan record updated successfully!", "success")
    except (WriteError, OperationFailure) as err:
        flash(f"Could not update loan: Document failed validation. ({err})", "error")

    return redirect(url_for("issues_list"))


@app.route("/issues/delete/<issue_id>", methods=["GET", "POST"])
def delete_issue(issue_id):
    books_col, _, issued_col = get_collections()
    try:
        obj_id = ObjectId(issue_id)
    except Exception:
        flash("Invalid loan record ID.", "error")
        return redirect(url_for("issues_list"))

    # Atomically remove issue record
    issue = issued_col.find_one_and_delete({"_id": obj_id})
    if not issue:
        flash("Loan record not found.", "error")
        return redirect(url_for("issues_list"))

    # If the deleted loan was active (Issued), restore the copy
    if issue.get("status") == "Issued":
        books_col.update_one({"_id": issue["book_ref"]}, {"$inc": {"available_copies": 1}})

    flash("Loan record deleted successfully.", "success")
    return redirect(url_for("issues_list"))


# Reports Route (Simple MongoDB Aggregation)
@app.route("/reports")
def reports():
    books_col, _, issued_col = get_collections()
    now = datetime.now()

    # 1. MongoDB Aggregation Pipeline: Group books by category
    pipeline = [
        {
            "$group": {
                "_id": "$category",
                "titles_count": {"$sum": 1},
                "total_copies": {"$sum": "$total_copies"},
                "available_copies": {"$sum": "$available_copies"}
            }
        },
        {"$sort": {"titles_count": -1}}
    ]
    category_reports = list(books_col.aggregate(pipeline))
    for c in category_reports:
        c["issued_copies"] = c["total_copies"] - c["available_copies"]

    # 2. MongoDB Aggregation for overall stock summary
    stock_agg = list(books_col.aggregate([
        {
            "$group": {
                "_id": None,
                "total_copies": {"$sum": "$total_copies"},
                "total_available": {"$sum": "$available_copies"}
            }
        }
    ]))
    total_copies = stock_agg[0]["total_copies"] if stock_agg else 0
    total_available = stock_agg[0]["total_available"] if stock_agg else 0
    total_issued = total_copies - total_available

    # 3. Overdue and returned lists with MongoDB query filters
    overdue_issues = list(issued_col.find({"status": "Issued", "due_date": {"$lt": now}}).sort("due_date", 1))
    for o in overdue_issues:
        due = o.get("due_date")
        o["days_overdue"] = max(1, (now - due).days) if isinstance(due, datetime) else 0

    recently_returned = list(issued_col.find({"status": "Returned"}).sort("return_date", -1).limit(10))

    return render_template(
        "reports.html",
        category_reports=category_reports,
        total_copies=total_copies,
        total_available=total_available,
        total_issued=total_issued,
        overdue_issues=overdue_issues,
        recently_returned=recently_returned
    )


# ==========================================================================
# LIBRARIAN ACTIONS: BOOK APPLICATION APPROVAL / REJECTION
# ==========================================================================

@app.route("/applications/approve/<app_id>", methods=["POST"])
def approve_application(app_id):
    """Librarian approves a student book application and issues the loan."""
    books_col, _, issued_col = get_collections()
    applications_col = get_applications_col()

    try:
        app_obj = ObjectId(app_id)
    except Exception:
        flash("Invalid application ID.", "error")
        return redirect(url_for("issues_list"))

    application = applications_col.find_one({"_id": app_obj, "status": "Pending"})
    if not application:
        flash("Application not found or already processed.", "error")
        return redirect(url_for("issues_list"))

    book = books_col.find_one({"_id": application["book_ref"]})
    if not book or book.get("available_copies", 0) <= 0:
        flash(f"Cannot approve: No copies of '{application['book_title']}' are currently available on shelves.", "error")
        return redirect(url_for("issues_list"))

    # Reserve 1 copy atomically in MongoDB
    reserve_res = books_col.update_one(
        {"_id": book["_id"], "available_copies": {"$gt": 0}},
        {"$inc": {"available_copies": -1}}
    )
    if reserve_res.modified_count == 0:
        flash(f"Cannot approve: No copies available for '{book['title']}'.", "error")
        return redirect(url_for("issues_list"))

    now = datetime.now()
    due = now + timedelta(days=application.get("requested_days", 14))

    loan_data = {
        "student_ref": application["student_ref"],
        "student_id": application["student_id"],
        "student_name": application["student_name"],
        "book_ref": application["book_ref"],
        "book_title": application["book_title"],
        "book_isbn": application.get("book_isbn", ""),
        "issue_date": now,
        "due_date": due,
        "return_date": None,
        "status": "Issued"
    }

    try:
        issued_col.insert_one(loan_data)
        applications_col.update_one(
            {"_id": app_obj},
            {"$set": {"status": "Approved", "review_date": now}}
        )
        flash(f"Application approved! Book '{application['book_title']}' has been officially issued to {application['student_name']}.", "success")
    except Exception as err:
        books_col.update_one({"_id": book["_id"]}, {"$inc": {"available_copies": 1}})
        flash(f"Could not issue book: {err}", "error")

    return redirect(url_for("issues_list"))


@app.route("/applications/reject/<app_id>", methods=["POST"])
def reject_application(app_id):
    """Librarian rejects a student book application."""
    applications_col = get_applications_col()

    try:
        app_obj = ObjectId(app_id)
    except Exception:
        flash("Invalid application ID.", "error")
        return redirect(url_for("issues_list"))

    res = applications_col.update_one(
        {"_id": app_obj, "status": "Pending"},
        {"$set": {"status": "Rejected", "review_date": datetime.now()}}
    )

    if res.modified_count > 0:
        flash("Student book application has been rejected.", "info")
    else:
        flash("Application not found or already processed.", "error")

    return redirect(url_for("issues_list"))


# ==========================================================================
# STUDENT SELF-SERVICE PORTAL (Sign Up, Login, Catalog & Book Applications)
# ==========================================================================

@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    """Self-service registration portal for students."""
    if session.get("student_logged_in"):
        return redirect(url_for("student_books"))

    _, students_col, _ = get_collections()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        email = request.form.get("email", "").strip().lower()
        course = request.form.get("course", "").strip()
        contact = request.form.get("contact", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        form_cache = {
            "name": name,
            "student_id": student_id,
            "email": email,
            "course": course,
            "contact": contact
        }

        # Validations
        if password != confirm_password:
            flash("Passwords do not match. Please verify your password.", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=student_id)

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=student_id)

        if not (student_id.isdigit() and len(student_id) == 10):
            flash("Student ID must be exactly 10 numeric digits.", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=generate_student_id(students_col))

        if not (contact.isdigit() and len(contact) == 10):
            flash("Contact number must be exactly 10 numeric digits.", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=student_id)

        student_data = {
            "student_id": student_id,
            "name": name,
            "email": email,
            "course": course,
            "contact": contact,
            "password": password
        }

        try:
            students_col.insert_one(student_data)
            flash("Registration successful! You can now sign in with your student credentials.", "success")
            return redirect(url_for("student_login"))
        except DuplicateKeyError as err:
            err_msg = str(err)
            if "student_id" in err_msg:
                flash(f"Student ID '{student_id}' is already registered.", "error")
            elif "email" in err_msg:
                flash(f"Email '{email}' is already registered to another account.", "error")
            elif "contact" in err_msg:
                flash(f"Contact number '{contact}' is already registered.", "error")
            else:
                flash("Duplicate student record entered.", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=generate_student_id(students_col))
        except Exception as err:
            flash(f"Registration failed: {err}", "error")
            return render_template("student_register.html", form_data=form_cache, new_student_id=student_id)

    return render_template("student_register.html", form_data={}, new_student_id=generate_student_id(students_col))


@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    """Dedicated login portal for students."""
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()

        _, students_col, _ = get_collections()
        # Look up by email or 10-digit student ID
        student = students_col.find_one({
            "$or": [
                {"email": identifier.lower()},
                {"student_id": identifier}
            ]
        })

        if student:
            # Check password, or fallback to default 12345 for seeded accounts
            expected_pwd = student.get("password", "12345")
            if password == expected_pwd:
                session["student_logged_in"] = True
                session["student_id"] = student["student_id"]
                session["student_db_id"] = str(student["_id"])
                session["student_name"] = student["name"]
                session["student_email"] = student["email"]
                flash(f"Welcome back, {student['name']}!", "success")
                return redirect(url_for("student_books"))

        flash("Invalid Student ID/Email or Password. Please try again.", "error")

    return render_template("student_login.html")


@app.route("/student/logout")
def student_logout():
    """Sign out student."""
    session.pop("student_logged_in", None)
    session.pop("student_id", None)
    session.pop("student_db_id", None)
    session.pop("student_name", None)
    session.pop("student_email", None)
    flash("You have been signed out of the Student Portal.", "info")
    return redirect(url_for("student_login"))


@app.route("/student")
@app.route("/student/dashboard")
def student_dashboard():
    return redirect(url_for("student_books"))


@app.route("/student/books")
def student_books():
    """Browse catalog and apply for book loans."""
    books_col, _, issued_col = get_collections()
    applications_col = get_applications_col()

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    query = {}
    if category and category != "All":
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
            {"isbn": {"$regex": search, "$options": "i"}}
        ]

    books = list(books_col.find(query).sort("title", 1))
    categories = sorted(books_col.distinct("category"))

    sid = session.get("student_id")
    # Identify books currently issued to this student
    active_loans = list(issued_col.find({"student_id": sid, "status": "Issued"}))
    issued_book_ids = {str(loan["book_ref"]) for loan in active_loans}

    # Identify pending applications for this student
    pending_apps = list(applications_col.find({"student_id": sid, "status": "Pending"}))
    pending_app_book_ids = {str(app["book_ref"]) for app in pending_apps}

    total_available_titles = books_col.count_documents({"available_copies": {"$gt": 0}})

    return render_template(
        "student_books.html",
        books=books,
        categories=categories,
        search_query=search,
        selected_category=category,
        issued_book_ids=issued_book_ids,
        pending_app_book_ids=pending_app_book_ids,
        active_loans_count=len(active_loans),
        pending_apps_count=len(pending_apps),
        total_available_titles=total_available_titles
    )


@app.route("/student/apply/<book_id>", methods=["POST"])
def student_apply_book(book_id):
    """Submit a loan application for a book."""
    books_col, _, issued_col = get_collections()
    applications_col = get_applications_col()

    sid = session.get("student_id")
    if not sid:
        flash("Your session has expired. Please sign in again.", "info")
        return redirect(url_for("student_login"))

    _, students_col, issued_col = get_collections()
    student_doc = students_col.find_one({"student_id": sid})
    if not student_doc:
        flash("Student profile not found. Please log in again.", "error")
        return redirect(url_for("student_login"))

    student_ref = student_doc["_id"]
    session["student_db_id"] = str(student_ref)

    try:
        book_obj = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID.", "error")
        return redirect(url_for("student_books"))

    book = books_col.find_one({"_id": book_obj})
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("student_books"))

    if book.get("available_copies", 0) <= 0:
        flash(f"Cannot apply: '{book['title']}' is currently out of stock.", "error")
        return redirect(url_for("student_books"))

    # Check if already borrowed
    if issued_col.count_documents({"student_id": sid, "book_ref": book_obj, "status": "Issued"}) > 0:
        flash(f"You already have '{book['title']}' currently issued to you.", "error")
        return redirect(url_for("student_books"))

    # Check if already pending application
    if applications_col.count_documents({"student_id": sid, "book_ref": book_obj, "status": "Pending"}) > 0:
        flash(f"You already have a pending application for '{book['title']}'.", "info")
        return redirect(url_for("student_applications"))

    try:
        requested_days = int(request.form.get("requested_days", 14))
    except (ValueError, TypeError):
        requested_days = 14

    notes = request.form.get("notes", "").strip()

    app_data = {
        "student_ref": student_ref,
        "student_id": sid,
        "student_name": student_doc.get("name", session.get("student_name", "Student")),
        "student_email": student_doc.get("email", session.get("student_email", "")),
        "book_ref": book_obj,
        "book_title": book["title"],
        "book_isbn": book.get("isbn", ""),
        "apply_date": datetime.now(),
        "requested_days": requested_days,
        "notes": notes,
        "status": "Pending",
        "review_date": None
    }

    try:
        applications_col.insert_one(app_data)
        flash(f"Application for '{book['title']}' submitted successfully! Awaiting librarian approval.", "success")
        return redirect(url_for("student_applications"))
    except Exception as err:
        flash(f"Could not submit application: {err}", "error")
        return redirect(url_for("student_books"))


@app.route("/student/applications")
def student_applications():
    """View all book applications submitted by the logged in student."""
    applications_col = get_applications_col()
    sid = session.get("student_id")
    applications = list(applications_col.find({"student_id": sid}).sort("apply_date", -1))
    pending_count = sum(1 for a in applications if a.get("status") == "Pending")

    _, _, issued_col = get_collections()
    active_loans_count = issued_col.count_documents({"student_id": sid, "status": "Issued"})

    return render_template(
        "student_applications.html",
        applications=applications,
        pending_apps_count=pending_count,
        active_loans_count=active_loans_count
    )


@app.route("/student/applications/cancel/<app_id>", methods=["POST"])
def student_cancel_application(app_id):
    """Cancel a pending book application."""
    applications_col = get_applications_col()
    sid = session.get("student_id")

    try:
        app_obj = ObjectId(app_id)
    except Exception:
        flash("Invalid application ID.", "error")
        return redirect(url_for("student_applications"))

    res = applications_col.delete_one({"_id": app_obj, "student_id": sid, "status": "Pending"})
    if res.deleted_count > 0:
        flash("Book application cancelled.", "info")
    else:
        flash("Application could not be cancelled or was already processed.", "error")

    return redirect(url_for("student_applications"))


@app.route("/student/loans")
def student_loans():
    """View borrowed books history for the logged in student."""
    _, _, issued_col = get_collections()
    applications_col = get_applications_col()
    sid = session.get("student_id")
    now = datetime.now()

    all_loans = list(issued_col.find({"student_id": sid}).sort("issue_date", -1))
    active_loans = []
    past_loans = []

    for l in all_loans:
        due = l.get("due_date")
        l["is_overdue"] = (l.get("status") == "Issued" and isinstance(due, datetime) and due < now)
        l["days_overdue"] = max(1, (now - due).days) if l["is_overdue"] else 0
        if l.get("status") == "Issued":
            active_loans.append(l)
        else:
            past_loans.append(l)

    pending_apps_count = applications_col.count_documents({"student_id": sid, "status": "Pending"})

    return render_template(
        "student_loans.html",
        active_loans=active_loans,
        past_loans=past_loans,
        active_loans_count=len(active_loans),
        pending_apps_count=pending_apps_count
    )


# Application Startup
if __name__ == "__main__":
    from database import init_indexes, init_validators, get_db
    db = get_db()
    init_indexes(db)
    init_validators(db)
    print("=" * 60)
    print("Library Management System (Flask + PyMongo)")
    print("Running on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
