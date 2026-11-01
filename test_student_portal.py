"""Automated test suite for Student Self-Registration, Login, Catalog, and Book Application workflows."""

import unittest
from bson import ObjectId
import database
from app import app

class StudentPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.db = database.get_db()
        cls.books_col, cls.students_col, cls.issued_col = database.get_collections()
        cls.apps_col = database.get_applications_col()

        # Clean any test artifacts for student 9999999999
        cls.issued_col.delete_many({"student_id": "9999999999"})
        cls.apps_col.delete_many({"student_id": "9999999999"})
        cls.students_col.delete_many({"student_id": "9999999999"})

    def test_01_student_registration(self):
        """Student can sign up with valid credentials."""
        # Cleanup if previously created
        self.students_col.delete_one({"student_id": "9999999999"})

        signup_data = {
            "name": "Kavya Patel",
            "student_id": "9999999999",
            "email": "kavya.patel@college.edu",
            "course": "B.Tech Computer Science",
            "contact": "9812345678",
            "password": "secretpassword",
            "confirm_password": "secretpassword"
        }
        res = self.client.post("/student/register", data=signup_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

        # Verify record in MongoDB
        student = self.students_col.find_one({"student_id": "9999999999"})
        self.assertIsNotNone(student)
        self.assertEqual(student["email"], "kavya.patel@college.edu")
        print("✓ Test 1 Passed: Student registration works and document is stored in MongoDB.")

    def test_02_student_login(self):
        """Student can log in using either email or 10-digit ID."""
        # 1. Invalid password
        res_bad = self.client.post("/student/login", data={
            "identifier": "kavya.patel@college.edu",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid Student ID/Email or Password", res_bad.data)

        # 2. Valid login
        res_ok = self.client.post("/student/login", data={
            "identifier": "9999999999",
            "password": "secretpassword"
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn(b"Welcome back, Kavya Patel", res_ok.data)
        print("✓ Test 2 Passed: Student authentication with ID/Email and password verified.")

    def test_03_student_browse_catalog_and_apply(self):
        """Logged-in student can browse catalog and submit an application for an available book."""
        # Ensure student is logged in
        self.client.post("/student/login", data={
            "identifier": "9999999999",
            "password": "secretpassword"
        })

        # Pick an available book
        book = self.books_col.find_one({"title": "Clean Code", "available_copies": {"$gt": 0}})
        self.assertIsNotNone(book)
        book_id = str(book["_id"])

        # Clean existing test apps for this student
        self.apps_col.delete_many({"student_id": "9999999999", "book_ref": book["_id"]})

        # Submit application
        apply_data = {
            "requested_days": "14",
            "notes": "Need this book for my clean architecture assignment."
        }
        res_apply = self.client.post(f"/student/apply/{book_id}", data=apply_data, follow_redirects=True)
        self.assertEqual(res_apply.status_code, 200)
        self.assertIn(b"submitted successfully", res_apply.data)

        # Verify application in MongoDB
        app_doc = self.apps_col.find_one({
            "student_id": "9999999999",
            "book_ref": book["_id"],
            "status": "Pending"
        })
        self.assertIsNotNone(app_doc)
        self.assertEqual(app_doc["book_title"], "Clean Code")
        print("✓ Test 3 Passed: Student submitted book application successfully.")

    def test_04_librarian_review_and_approval(self):
        """Librarian sees pending application, approves it, which atomically issues the book."""
        # 1. Log in as Librarian
        self.client.post("/login", data={
            "email": "neerajnegi90451@gmail.com",
            "password": "12345"
        })

        # Find the pending application from Kavya Patel
        app_doc = self.apps_col.find_one({"student_id": "9999999999", "status": "Pending"})
        self.assertIsNotNone(app_doc)
        app_id = str(app_doc["_id"])

        book_before = self.books_col.find_one({"_id": app_doc["book_ref"]})
        copies_before = book_before["available_copies"]

        # 2. Approve application
        res_approve = self.client.post(f"/applications/approve/{app_id}", follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)
        self.assertIn(b"Application approved", res_approve.data)

        # 3. Verify application status updated to Approved
        updated_app = self.apps_col.find_one({"_id": app_doc["_id"]})
        self.assertEqual(updated_app["status"], "Approved")

        # 4. Verify book available_copies decremented by 1
        book_after = self.books_col.find_one({"_id": app_doc["book_ref"]})
        self.assertEqual(book_after["available_copies"], copies_before - 1)

        # 5. Verify active loan created in issued_books
        loan = self.issued_col.find_one({
            "student_id": "9999999999",
            "book_ref": app_doc["book_ref"],
            "status": "Issued"
        })
        self.assertIsNotNone(loan)
        print("✓ Test 4 Passed: Librarian approved application, book copy atomically decremented, and loan issued.")

    def test_05_student_loan_visibility(self):
        """Student logs back in and sees the approved book in their active borrowed loans."""
        self.client.post("/student/login", data={
            "identifier": "9999999999",
            "password": "secretpassword"
        })

        res_loans = self.client.get("/student/loans")
        self.assertEqual(res_loans.status_code, 200)
        self.assertIn(b"Clean Code", res_loans.data)
        self.assertIn(b"Active Loan", res_loans.data)
        print("✓ Test 5 Passed: Approved loan shows in Student's Borrowed Books.")

    def test_06_student_logout(self):
        """Student signs out and access to /student/books is protected."""
        res_out = self.client.get("/student/logout", follow_redirects=True)
        self.assertIn(b"signed out of the Student Portal", res_out.data)

        res_guard = self.client.get("/student/books", follow_redirects=False)
        self.assertEqual(res_guard.status_code, 302)
        self.assertIn("/student/login", res_guard.headers["Location"])
        print("✓ Test 6 Passed: Student session logout and route guard verified.")

if __name__ == "__main__":
    unittest.main()
