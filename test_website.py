"""Comprehensive end-to-end and functional test suite for Athena Library Management System.

Tests all web routes, authentication, CRUD operations, business logic,
schema validations, and database state transitions.
"""

import sys
import unittest
from datetime import datetime, date, timedelta
from bson import ObjectId
import database
from app import app

class AthenaLibraryWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.db = database.get_db()
        cls.books_col, cls.students_col, cls.issued_col = database.get_collections()

    def test_01_unauthenticated_redirect(self):
        """Protected routes must redirect unauthenticated users to /login."""
        for endpoint in ["/", "/dashboard", "/books", "/students", "/issues", "/reports"]:
            response = self.client.get(endpoint, follow_redirects=False)
            self.assertIn(response.status_code, [302, 308], f"Failed redirect for {endpoint}")
            self.assertIn("/login", response.headers["Location"])
        print("✓ Test 1 Passed: Unauthenticated access properly guarded.")

    def test_02_login_invalid_credentials(self):
        """Invalid login credentials should fail and stay on login."""
        response = self.client.post("/login", data={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email or password", response.data)
        print("✓ Test 2 Passed: Invalid login rejected with error message.")

    def test_03_login_valid_credentials(self):
        """Valid librarian credentials should authenticate and redirect to dashboard."""
        response = self.client.post("/login", data={
            "email": "neerajnegi90451@gmail.com",
            "password": "12345"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)
        self.assertIn(b"Dashboard", response.data)
        print("✓ Test 3 Passed: Librarian successfully logged in.")

    def test_04_dashboard_metrics(self):
        """Dashboard must display accurate metrics and charts."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Total Book Titles", html)
        self.assertIn("Registered Students", html)
        self.assertIn("Currently Issued", html)
        self.assertIn("Overdue Books", html)
        self.assertIn("Category Distribution", html)
        print("✓ Test 4 Passed: Dashboard metrics rendered correctly.")

    def test_05_books_list_and_search(self):
        """Books catalog listing, searching, and filtering."""
        # 1. View all
        response = self.client.get("/books")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Clean Code", response.data)

        # 2. Search by title
        response = self.client.get("/books?search=Clean")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Clean Code", response.data)
        self.assertNotIn(b"University Physics", response.data)

        # 3. Filter by category
        response = self.client.get("/books?category=Mathematics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculus", response.data)
        self.assertNotIn(b"Clean Code", response.data)
        print("✓ Test 5 Passed: Books list, search, and category filter verified.")

    def test_06_books_crud_lifecycle(self):
        """Adding a book, editing it, checking validation, and deleting."""
        # 1. Add valid book
        add_data = {
            "title": "Automated Testing in Python",
            "author": "Guido van Rossum",
            "isbn": "9781999999999",
            "category": "Computer Science",
            "publication_year": "2023",
            "total_copies": "5",
            "shelf_location": "TEST-101"
        }
        res = self.client.post("/books/add", data=add_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"added successfully", res.data)

        book = self.books_col.find_one({"isbn": "9781999999999"})
        self.assertIsNotNone(book)
        self.assertEqual(book["available_copies"], 5)

        # 2. Duplicate ISBN rejection
        res_dup = self.client.post("/books/add", data=add_data, follow_redirects=True)
        self.assertIn(b"already registered", res_dup.data)

        # 3. Edit book
        edit_data = {
            "title": "Automated Testing in Python (2nd Edition)",
            "author": "Guido van Rossum",
            "isbn": "9781999999999",
            "category": "Computer Science",
            "publication_year": "2024",
            "total_copies": "7",
            "shelf_location": "TEST-102"
        }
        res_edit = self.client.post(f"/books/edit/{str(book['_id'])}", data=edit_data, follow_redirects=True)
        self.assertIn(b"updated successfully", res_edit.data)
        updated_book = self.books_col.find_one({"_id": book["_id"]})
        self.assertEqual(updated_book["title"], "Automated Testing in Python (2nd Edition)")
        self.assertEqual(updated_book["total_copies"], 7)
        self.assertEqual(updated_book["available_copies"], 7)

        # 4. Delete book
        res_del = self.client.post(f"/books/delete/{str(book['_id'])}", follow_redirects=True)
        self.assertIn(b"deleted successfully", res_del.data)
        self.assertIsNone(self.books_col.find_one({"_id": book["_id"]}))
        print("✓ Test 6 Passed: Book CRUD lifecycle (Add, Duplicate check, Edit, Delete) verified.")

    def test_07_students_crud_and_validation(self):
        """Student registration, unique validation, API check, edit, and deletion."""
        # 1. API check student ID
        api_res = self.client.get("/api/check_student_id?student_id=1000000001")
        self.assertEqual(api_res.get_json(), {"exists": True})
        api_res_new = self.client.get("/api/check_student_id?student_id=8888888888")
        self.assertEqual(api_res_new.get_json(), {"exists": False})

        # 2. Add student
        new_student = {
            "student_id": "8888888888",
            "name": "Arjun Kapoor",
            "email": "arjun.kapoor@college.edu",
            "course": "B.Tech AI & DS",
            "contact": "9123456780"
        }
        res = self.client.post("/students/add", data=new_student, follow_redirects=True)
        self.assertIn(b"registered with 10-digit ID", res.data)
        s_doc = self.students_col.find_one({"student_id": "8888888888"})
        self.assertIsNotNone(s_doc)

        # 3. Edit student
        edit_data = {
            "name": "Arjun K. Kapoor",
            "email": "arjun.k.kapoor@college.edu",
            "course": "B.Tech AI & Data Science",
            "contact": "9123456780"
        }
        res_edit = self.client.post(f"/students/edit/{str(s_doc['_id'])}", data=edit_data, follow_redirects=True)
        self.assertIn(b"updated successfully", res_edit.data)
        updated_s = self.students_col.find_one({"_id": s_doc["_id"]})
        self.assertEqual(updated_s["name"], "Arjun K. Kapoor")

        # 4. Delete student
        res_del = self.client.post(f"/students/delete/{str(s_doc['_id'])}", follow_redirects=True)
        self.assertIn(b"deleted successfully", res_del.data)
        self.assertIsNone(self.students_col.find_one({"_id": s_doc["_id"]}))
        print("✓ Test 7 Passed: Students management (API check, Add, Edit, Delete) verified.")

    def test_08_circulation_issue_and_return_flow(self):
        """Circulation workflow: issue book, decrement copy count, return book, increment copy count."""
        student = self.students_col.find_one({"student_id": "1000000005"})
        book = self.books_col.find_one({"isbn": "9780060935467"})  # To Kill a Mockingbird
        self.assertIsNotNone(student)
        self.assertIsNotNone(book)

        initial_copies = book["available_copies"]
        today = date.today().strftime("%Y-%m-%d")
        due = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")

        # 1. Issue book
        issue_payload = {
            "student_ref": str(student["_id"]),
            "book_ref": str(book["_id"]),
            "issue_date": today,
            "due_date": due,
            "redirect_to": "issues"
        }
        res_issue = self.client.post("/issues/add", data=issue_payload, follow_redirects=True)
        self.assertIn(b"issued to", res_issue.data)

        # Verify copy count decremented
        book_after_issue = self.books_col.find_one({"_id": book["_id"]})
        self.assertEqual(book_after_issue["available_copies"], initial_copies - 1)

        loan = self.issued_col.find_one({
            "student_ref": student["_id"],
            "book_ref": book["_id"],
            "status": "Issued"
        })
        self.assertIsNotNone(loan)

        # 2. Referential integrity: attempting to delete student with active loan must fail
        res_del_stu = self.client.post(f"/students/delete/{str(student['_id'])}", follow_redirects=True)
        self.assertIn(b"Cannot delete student", res_del_stu.data)
        self.assertIsNotNone(self.students_col.find_one({"_id": student["_id"]}))

        # 3. Return book
        res_return = self.client.post(f"/issues/return/{str(loan['_id'])}", follow_redirects=True)
        self.assertIn(b"returned successfully", res_return.data)

        # Verify copy count incremented back
        book_after_return = self.books_col.find_one({"_id": book["_id"]})
        self.assertEqual(book_after_return["available_copies"], initial_copies)

        returned_loan = self.issued_col.find_one({"_id": loan["_id"]})
        self.assertEqual(returned_loan["status"], "Returned")
        self.assertIsNotNone(returned_loan["return_date"])

        # 4. Delete the loan record
        res_del_loan = self.client.post(f"/issues/delete/{str(loan['_id'])}", follow_redirects=True)
        self.assertIn(b"deleted successfully", res_del_loan.data)
        self.assertIsNone(self.issued_col.find_one({"_id": loan["_id"]}))
        print("✓ Test 8 Passed: Full circulation workflow and referential integrity verified.")

    def test_09_reports_aggregation(self):
        """Reports page aggregation pipeline and overdue tracking."""
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Total Catalog Copies", html)
        self.assertIn("Computer Science", html)
        self.assertIn("Overdue Books Report", html)
        self.assertIn("Priya Patel", html)  # Has the overdue book from seed
        print("✓ Test 9 Passed: Reports aggregation pipeline verified.")

    def test_10_logout_workflow(self):
        """Logout must clear session and redirect to /login."""
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"You have been signed out", res_logout.data)

        # Verify subsequent dashboard request redirects to login
        res_dash = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(res_dash.status_code, 302)
        self.assertIn("/login", res_dash.headers["Location"])
        print("✓ Test 10 Passed: Logout and session invalidation verified.")

if __name__ == "__main__":
    unittest.main()
