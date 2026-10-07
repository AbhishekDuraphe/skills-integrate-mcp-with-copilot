# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only signup and unregister controls
- Public viewing of activities and participant rosters

## Teacher access

Create `src/teachers.json` with teacher usernames and PBKDF2-SHA256 password hashes. Do not commit this file. Generate a hash with:

```
python -c 'import getpass,hashlib,secrets; password=getpass.getpass("Password: ").encode(); salt=secrets.token_bytes(16); iterations=310000; digest=hashlib.pbkdf2_hmac("sha256", password, salt, iterations); print(f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}")'
```

Use the printed value in this format:

```json
{
   "teachers": [
      {
         "username": "teacher1",
         "password_hash": "pbkdf2_sha256$310000$<salt-hex>$<hash-hex>"
      }
   ]
}
```

Start the application as described below. Visitors can view activities and participants; teachers must sign in before they can register or unregister students. Teacher sessions expire after eight hours and are stored in memory, so a server restart signs everyone out.

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Activities page: http://localhost:8000/

## Tests

Run the API tests with the project's Python environment:

```
python -m unittest discover -s tests
```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
