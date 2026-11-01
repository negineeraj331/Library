"""Seed data script for Athena Library Management System.

Populates library_db with initial books, students, and circulation records
conforming to MongoDB schema validation and unique indexes.
"""

from datetime import datetime, timedelta
import database

def seed():
    db = database.get_db()
    books_col, students_col, issued_col = database.get_collections()
    
    print("Initializing collections, indexes, and validators...")
    database.init_indexes(db)
    database.init_validators(db)
    database.init_librarian(db)

    applications_col = database.get_applications_col()

    # Clean existing data in core collections to ensure clean seed
    applications_col.delete_many({})
    issued_col.delete_many({})
    books_col.delete_many({})
    students_col.delete_many({})

    print("Seeding books...")
    sample_books = [
        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "category": "Computer Science",
            "publication_year": 2008,
            "year": 2008,
            "total_copies": 5,
            "available_copies": 4,  # 1 issued
            "shelf_location": "CS-A101"
        },
        {
            "title": "Introduction to Algorithms",
            "author": "Thomas H. Cormen",
            "isbn": "9780262033848",
            "category": "Computer Science",
            "publication_year": 2009,
            "year": 2009,
            "total_copies": 4,
            "available_copies": 3,  # 1 issued (overdue)
            "shelf_location": "CS-B202"
        },
        {
            "title": "Design Patterns: Elements of Reusable Object-Oriented Software",
            "author": "Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides",
            "isbn": "9780201633610",
            "category": "Computer Science",
            "publication_year": 1994,
            "year": 1994,
            "total_copies": 3,
            "available_copies": 3,
            "shelf_location": "CS-C303"
        },
        {
            "title": "Artificial Intelligence: A Modern Approach",
            "author": "Stuart Russell, Peter Norvig",
            "isbn": "9780136042594",
            "category": "Computer Science",
            "publication_year": 2020,
            "year": 2020,
            "total_copies": 6,
            "available_copies": 6,
            "shelf_location": "CS-D404"
        },
        {
            "title": "Calculus: Early Transcendentals",
            "author": "James Stewart",
            "isbn": "9781285741550",
            "category": "Mathematics",
            "publication_year": 2015,
            "year": 2015,
            "total_copies": 5,
            "available_copies": 5,
            "shelf_location": "MATH-101"
        },
        {
            "title": "Linear Algebra and Its Applications",
            "author": "Gilbert Strang",
            "isbn": "9780030105678",
            "category": "Mathematics",
            "publication_year": 2006,
            "year": 2006,
            "total_copies": 4,
            "available_copies": 4,
            "shelf_location": "MATH-205"
        },
        {
            "title": "University Physics with Modern Physics",
            "author": "Hugh D. Young, Roger A. Freedman",
            "isbn": "9780135159553",
            "category": "Physics",
            "publication_year": 2019,
            "year": 2019,
            "total_copies": 4,
            "available_copies": 3,  # 1 issued
            "shelf_location": "PHY-301"
        },
        {
            "title": "Concepts of Modern Physics",
            "author": "Arthur Beiser",
            "isbn": "9780072448481",
            "category": "Physics",
            "publication_year": 2002,
            "year": 2002,
            "total_copies": 3,
            "available_copies": 3,
            "shelf_location": "PHY-302"
        },
        {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "isbn": "9780060935467",
            "category": "Literature",
            "publication_year": 1960,
            "year": 1960,
            "total_copies": 5,
            "available_copies": 5,
            "shelf_location": "LIT-101"
        },
        {
            "title": "Electric Machinery Fundamentals",
            "author": "Stephen J. Chapman",
            "isbn": "9780073529547",
            "category": "Electrical Engineering",
            "publication_year": 2011,
            "year": 2011,
            "total_copies": 4,
            "available_copies": 4,
            "shelf_location": "EE-201"
        }
    ]

    inserted_books = []
    for b in sample_books:
        res = books_col.insert_one(b)
        b["_id"] = res.inserted_id
        inserted_books.append(b)
    print(f"Inserted {len(inserted_books)} books.")

    print("Seeding students...")
    sample_students = [
        {
            "student_id": "1000000001",
            "name": "Rahul Sharma",
            "email": "rahul.sharma@college.edu",
            "course": "B.Tech CSE",
            "contact": "9876543210",
            "password": "12345"
        },
        {
            "student_id": "1000000002",
            "name": "Priya Patel",
            "email": "priya.patel@college.edu",
            "course": "B.Tech IT",
            "contact": "9876543211",
            "password": "12345"
        },
        {
            "student_id": "1000000003",
            "name": "Amit Kumar",
            "email": "amit.kumar@college.edu",
            "course": "B.Tech ECE",
            "contact": "9876543212",
            "password": "12345"
        },
        {
            "student_id": "1000000004",
            "name": "Sneha Verma",
            "email": "sneha.verma@college.edu",
            "course": "B.Sc Mathematics",
            "contact": "9876543213",
            "password": "12345"
        },
        {
            "student_id": "1000000005",
            "name": "Rohan Gupta",
            "email": "rohan.gupta@college.edu",
            "course": "B.Tech Mechanical",
            "contact": "9876543214",
            "password": "12345"
        }
    ]

    inserted_students = []
    for s in sample_students:
        res = students_col.insert_one(s)
        s["_id"] = res.inserted_id
        inserted_students.append(s)
    print(f"Inserted {len(inserted_students)} students.")

    print("Seeding circulation (loans)...")
    now = datetime.now()
    sample_issues = [
        # 1. Active Loan (Clean Code -> Rahul Sharma)
        {
            "student_ref": inserted_students[0]["_id"],
            "student_id": inserted_students[0]["student_id"],
            "student_name": inserted_students[0]["name"],
            "book_ref": inserted_books[0]["_id"],
            "book_title": inserted_books[0]["title"],
            "book_isbn": inserted_books[0]["isbn"],
            "issue_date": now - timedelta(days=5),
            "due_date": now + timedelta(days=9),
            "return_date": None,
            "status": "Issued"
        },
        # 2. Overdue Loan (Introduction to Algorithms -> Priya Patel)
        {
            "student_ref": inserted_students[1]["_id"],
            "student_id": inserted_students[1]["student_id"],
            "student_name": inserted_students[1]["name"],
            "book_ref": inserted_books[1]["_id"],
            "book_title": inserted_books[1]["title"],
            "book_isbn": inserted_books[1]["isbn"],
            "issue_date": now - timedelta(days=20),
            "due_date": now - timedelta(days=6),
            "return_date": None,
            "status": "Issued"
        },
        # 3. Active Loan (University Physics -> Amit Kumar)
        {
            "student_ref": inserted_students[2]["_id"],
            "student_id": inserted_students[2]["student_id"],
            "student_name": inserted_students[2]["name"],
            "book_ref": inserted_books[6]["_id"],
            "book_title": inserted_books[6]["title"],
            "book_isbn": inserted_books[6]["isbn"],
            "issue_date": now - timedelta(days=3),
            "due_date": now + timedelta(days=11),
            "return_date": None,
            "status": "Issued"
        },
        # 4. Returned Loan (Calculus -> Sneha Verma)
        {
            "student_ref": inserted_students[3]["_id"],
            "student_id": inserted_students[3]["student_id"],
            "student_name": inserted_students[3]["name"],
            "book_ref": inserted_books[4]["_id"],
            "book_title": inserted_books[4]["title"],
            "book_isbn": inserted_books[4]["isbn"],
            "issue_date": now - timedelta(days=18),
            "due_date": now - timedelta(days=4),
            "return_date": now - timedelta(days=2),
            "status": "Returned"
        }
    ]

    for iss in sample_issues:
        issued_col.insert_one(iss)
    print(f"Inserted {len(sample_issues)} loan records.")

    print("Seeding sample book applications...")
    sample_applications = [
        {
            "student_ref": inserted_students[4]["_id"],  # Rohan Gupta
            "student_id": inserted_students[4]["student_id"],
            "student_name": inserted_students[4]["name"],
            "student_email": inserted_students[4]["email"],
            "book_ref": inserted_books[2]["_id"],  # Design Patterns
            "book_title": inserted_books[2]["title"],
            "book_isbn": inserted_books[2]["isbn"],
            "apply_date": now - timedelta(hours=3),
            "requested_days": 14,
            "notes": "Need this reference book for the Software Architecture semester project.",
            "status": "Pending",
            "review_date": None
        }
    ]
    for app_doc in sample_applications:
        applications_col.insert_one(app_doc)
    print(f"Inserted {len(sample_applications)} sample book applications.")

    print("\n Seed completed successfully!")
    print(f"Books count: {books_col.count_documents({})}")
    print(f"Students count: {students_col.count_documents({})}")
    print(f"Issued books count: {issued_col.count_documents({})}")
    print(f"Applications count: {applications_col.count_documents({})}")
    print(f"Librarians count: {db['librarians'].count_documents({})}")

if __name__ == "__main__":
    seed()

