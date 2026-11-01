"""MongoDB database connection, schema validation, and unique indexes."""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# MongoDB Connection String & Database Name
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "library_db"

_client = None
_db = None


# MongoDB $jsonSchema Collection Validators
# Enforces required fields, BSON data types, numeric limits, and enums.

# 1. Books collection validator
BOOKS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "title",
            "author",
            "isbn",
            "category",
            "publication_year",
            "total_copies",
            "available_copies",
            "shelf_location"
        ],
        "properties": {
            "title": {
                "bsonType": "string",
                "minLength": 2,
                "pattern": "^.*[a-zA-Z].*$",
                "description": "Book title must contain alphabetical letters"
            },
            "author": {
                "bsonType": "string",
                "minLength": 2,
                "pattern": "^.*[a-zA-Z].*$",
                "description": "Author must contain alphabetical letters"
            },
            "isbn": {
                "bsonType": "string",
                "minLength": 5,
                "description": "ISBN must be a string of at least 5 characters and unique"
            },
            "category": {
                "bsonType": "string",
                "minLength": 2,
                "description": "Category is required"
            },
            "publication_year": {
                "bsonType": ["int", "long"],
                "minimum": 1000,
                "description": "Publication year must be an integer of at least 1000"
            },
            "year": {
                "bsonType": ["int", "long"],
                "minimum": 1000,
                "description": "Year must be an integer of at least 1000"
            },
            "total_copies": {
                "bsonType": ["int", "long"],
                "minimum": 1,
                "description": "Total copies must be an integer of at least 1"
            },
            "available_copies": {
                "bsonType": ["int", "long"],
                "minimum": 0,
                "description": "Available copies cannot be negative"
            },
            "shelf_location": {
                "bsonType": "string",
                "minLength": 1,
                "description": "Shelf location is required"
            }
        }
    }
}

# 2. Students collection validator
STUDENTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "student_id",
            "name",
            "email",
            "course",
            "contact"
        ],
        "properties": {
            "student_id": {
                "bsonType": "string",
                "pattern": "^[0-9]{10}$",
                "description": "Student ID must be a unique 10-digit numeric string"
            },
            "name": {
                "bsonType": "string",
                "minLength": 2,
                "pattern": "^.*[a-zA-Z].*$",
                "description": "Student name must contain alphabetical letters"
            },
            "email": {
                "bsonType": "string",
                "pattern": "^.+@.+\\..+$",
                "description": "Student email must be valid and contain '@' with a domain"
            },
            "course": {
                "bsonType": "string",
                "minLength": 2,
                "description": "Course is required"
            },
            "contact": {
                "bsonType": "string",
                "pattern": "^[0-9]{10}$",
                "description": "Contact phone number must be exactly 10 numeric digits"
            },
            "password": {
                "bsonType": "string",
                "description": "Student portal login password"
            }
        }
    }
}

# 3. Issued books collection validator
ISSUED_BOOKS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "student_ref",
            "student_id",
            "student_name",
            "book_ref",
            "book_title",
            "issue_date",
            "due_date",
            "status"
        ],
        "properties": {
            "student_ref": {
                "bsonType": "objectId",
                "description": "student_ref must be a MongoDB ObjectId"
            },
            "student_id": {
                "bsonType": "string",
                "minLength": 1,
                "description": "student_id must be a string"
            },
            "student_name": {
                "bsonType": "string",
                "minLength": 1,
                "description": "student_name must be a string"
            },
            "book_ref": {
                "bsonType": "objectId",
                "description": "book_ref must be a MongoDB ObjectId"
            },
            "book_title": {
                "bsonType": "string",
                "minLength": 1,
                "description": "book_title must be a string"
            },
            "book_isbn": {
                "bsonType": "string",
                "description": "book_isbn must be a string"
            },
            "issue_date": {
                "bsonType": "date",
                "description": "issue_date must be a BSON Date"
            },
            "due_date": {
                "bsonType": "date",
                "description": "due_date must be a BSON Date"
            },
            "return_date": {
                "bsonType": ["date", "null"],
                "description": "return_date must be a BSON Date or null"
            },
            "status": {
                "bsonType": "string",
                "enum": ["Issued", "Returned"],
                "description": "status must be either 'Issued' or 'Returned'"
            }
        }
    }
}


# 4. Book applications collection validator
BOOK_APPLICATIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "student_ref",
            "student_id",
            "student_name",
            "student_email",
            "book_ref",
            "book_title",
            "apply_date",
            "status"
        ],
        "properties": {
            "student_ref": {
                "bsonType": "objectId",
                "description": "student_ref must be a MongoDB ObjectId"
            },
            "student_id": {
                "bsonType": "string",
                "description": "student_id must be a string"
            },
            "student_name": {
                "bsonType": "string",
                "description": "student_name must be a string"
            },
            "student_email": {
                "bsonType": "string",
                "description": "student_email must be a string"
            },
            "book_ref": {
                "bsonType": "objectId",
                "description": "book_ref must be a MongoDB ObjectId"
            },
            "book_title": {
                "bsonType": "string",
                "description": "book_title must be a string"
            },
            "book_isbn": {
                "bsonType": "string",
                "description": "book_isbn must be a string"
            },
            "apply_date": {
                "bsonType": "date",
                "description": "apply_date must be a BSON Date"
            },
            "requested_days": {
                "bsonType": ["int", "long"],
                "description": "requested loan duration in days"
            },
            "notes": {
                "bsonType": "string",
                "description": "application note or purpose"
            },
            "status": {
                "bsonType": "string",
                "enum": ["Pending", "Approved", "Rejected"],
                "description": "status must be Pending, Approved, or Rejected"
            },
            "review_date": {
                "bsonType": ["date", "null"],
                "description": "date application was reviewed"
            }
        }
    }
}


def get_client():
    """Returns a singleton MongoClient instance."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    """Returns the library_db database instance and ensures indexes and schema validators exist."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[DB_NAME]
        init_indexes(_db)
        init_validators(_db)
        init_librarian(_db)
    return _db


def init_librarian(db=None):
    """Ensure default librarian account exists in MongoDB."""
    if db is None:
        db = get_db()
    try:
        if not db["librarians"].find_one({"email": "neerajnegi90451@gmail.com"}):
            # Update existing or insert new librarian record
            res = db["librarians"].update_one(
                {"email": "aniket70045@gmail.com"},
                {"$set": {
                    "email": "neerajnegi90451@gmail.com",
                    "password": "12345",
                    "name": "Neeraj Negi (Librarian)",
                    "role": "Librarian"
                }}
            )
            if res.matched_count == 0:
                db["librarians"].insert_one({
                    "email": "neerajnegi90451@gmail.com",
                    "password": "12345",
                    "name": "Neeraj Negi (Librarian)",
                    "role": "Librarian"
                })
    except Exception as err:
        print(f"[Warning] Librarian setup message: {err}")


def init_indexes(db=None):
    """Create unique indexes for ISBN, Student ID, Email, and Phone."""
    if db is None:
        db = get_db()
    try:
        db["books"].create_index("isbn", unique=True)
        db["students"].create_index("student_id", unique=True)
        db["students"].create_index("email", unique=True)
        db["students"].create_index("contact", unique=True)
        db["librarians"].create_index("email", unique=True)
        db["book_applications"].create_index([("student_id", 1), ("status", 1)])
    except Exception as err:
        print(f"[Warning] Index setup message: {err}")


def init_validators(db=None):
    """Apply strict MongoDB $jsonSchema validation across collections."""
    if db is None:
        db = get_db()
    try:
        existing = db.list_collection_names()

        collections_and_validators = [
            ("books", BOOKS_VALIDATOR),
            ("students", STUDENTS_VALIDATOR),
            ("issued_books", ISSUED_BOOKS_VALIDATOR),
            ("book_applications", BOOK_APPLICATIONS_VALIDATOR),
        ]

        for coll_name, validator in collections_and_validators:
            if coll_name not in existing:
                db.create_collection(coll_name, validator=validator)
            else:
                db.command(
                    "collMod",
                    coll_name,
                    validator=validator,
                    validationLevel="strict",
                    validationAction="error"
                )
    except Exception as err:
        print(f"[Warning] Validator setup message: {err}")


def get_collections():
    """Convenience helper returning the core collections."""
    db = get_db()
    return db["books"], db["students"], db["issued_books"]


def get_applications_col():
    """Convenience helper returning the book_applications collection."""
    db = get_db()
    return db["book_applications"]


def check_connection():
    """
    Checks if the local MongoDB server is reachable.
    Returns (True, message) or (False, error).
    """
    try:
        client = get_client()
        client.admin.command("ping")
        return True, "Successfully connected to MongoDB server."
    except (ConnectionFailure, ServerSelectionTimeoutError) as err:
        return False, f"Could not connect to MongoDB: {err}"
    except Exception as err:
        return False, f"Unexpected database error: {err}"


if __name__ == "__main__":
    status, msg = check_connection()
    print("MongoDB Status:", msg)
    if status:
        db = get_db()
        print(f"Connected to database '{db.name}'. Collections:", db.list_collection_names())
        init_validators(db)
        print("Schema validation successfully initialized.")
