from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg
import os
import smtplib
import uuid
import hashlib
import secrets
import google.genai as genai

from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)
CORS(app)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# ============================================================
# EMAIL
# ============================================================

def send_email(recipient, subject, body):

    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)



# ============================================================
# SMART RETRIEVAL HELPERS
# ============================================================

def get_retrieval_params(details):
    limit = details.get("limit", 5)
    offset = details.get("offset", 0)
    search = details.get("search")
    date_from = details.get("date_from")
    date_to = details.get("date_to")

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5

    if limit < 1:
        limit = 5

    if limit > 100:
        limit = 100

    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0

    if offset < 0:
        offset = 0

    if search is not None:
        search = str(search).strip()
        if search == "":
            search = None

    if date_from is not None:
        date_from = str(date_from).strip()
        if date_from == "":
            date_from = None

    if date_to is not None:
        date_to = str(date_to).strip()
        if date_to == "":
            date_to = None

    return limit, offset, search, date_from, date_to


def build_retrieval_filter(
    user_id,
    search=None,
    date_from=None,
    date_to=None,
    search_columns=None
):
    conditions = ["user_id = %s"]
    params = [user_id]

    if search and search_columns:
        search_conditions = []

        for column in search_columns:
            search_conditions.append(f"{column} ILIKE %s")
            params.append(f"%{search}%")

        conditions.append(
            "(" + " OR ".join(search_conditions) + ")"
        )

    if date_from:
        conditions.append("created_at >= %s::timestamptz")
        params.append(date_from)

    if date_to:
        conditions.append(
            "created_at < (%s::date + INTERVAL '1 day')"
        )
        params.append(date_to)

    return " AND ".join(conditions), params


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def create_user_id():
    return str(uuid.uuid4())


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id):

    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=7)
    )

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            INSERT INTO auth_sessions
            (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (
                user_id,
                token_hash,
                expires_at
            )
        )

        conn.commit()

    finally:

        cur.close()
        conn.close()

    return token
#=========================================================
#get_user_from _token
#==========================================================
def get_user_from_token(token):
    if not token:
        return None

    token_hash = hash_token(token)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT user_id
        FROM auth_sessions
        WHERE token_hash = %s
        AND expires_at > NOW()
        """,
        (token_hash,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row[0]

    return None

# ============================================================
# HOME / HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Nova Voice Assistant API is running"
    })


# ============================================================
# REGISTER
# ============================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json() or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if not name or not email or not password:

        return jsonify({
            "success": False,
            "message": "Name, email and password are required"
        }), 400

    if len(password) < 8:

        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters"
        }), 400

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT user_id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        existing_user = cur.fetchone()

        if existing_user:

            return jsonify({
                "success": False,
                "message": "Email is already registered"
            }), 409

        user_id = create_user_id()

        password_hash = generate_password_hash(
            password
        )

        cur.execute(
            """
            INSERT INTO users
            (user_id, name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                name,
                email,
                password_hash
            )
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Registration successful",
            "user_id": user_id,
            "name": name,
            "email": email
        }), 201

    except Exception as e:

        conn.rollback()

        print("REGISTER ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Registration failed"
        }), 500

    finally:

        cur.close()
        conn.close()


# ============================================================
# LOGIN
# ============================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json() or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required"
        }), 400

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT user_id, name, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cur.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        user_id, name, email, password_hash = user

        if not check_password_hash(
            password_hash,
            password
        ):

            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        token = create_session(user_id)

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user_id": user_id,
            "name": name,
            "email": email,
            "access_token": token
        })

    except Exception as e:

        print("LOGIN ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Login failed"
        }), 500

    finally:

        cur.close()
        conn.close()


# ============================================================
# LOGOUT
# ============================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    data = request.get_json() or {}

    token = str(
        data.get("access_token", "")
    ).strip()

    if not token:

        return jsonify({
            "success": False,
            "message": "Access token is required"
        }), 400

    token_hash = hash_token(token)

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            DELETE FROM auth_sessions
            WHERE token_hash = %s
            """,
            (token_hash,)
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Logout successful"
        })

    except Exception as e:

        conn.rollback()

        print("LOGOUT ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Logout failed"
        }), 500

    finally:

        cur.close()
        conn.close()


# ============================================================
# MAIN ASSISTANT API
# ============================================================

@app.route("/api/assistant", methods=["POST"])
def assistant():

    data = request.get_json() or {}
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return jsonify({
            "success": False,
            "message": "Authorization token is required"
        }), 401

    token = auth_header.split(" ", 1)[1]
    authenticated_user_id = get_user_from_token(token)

    if not authenticated_user_id:
        return jsonify({
            "success": False,
            "message": "Invalid or expired authorization token"
        }), 401
    intent = data.get("intent")
    details = data.get("data", {})

    if not isinstance(details, dict):

        return jsonify({
            "success": False,
            "message": "Data must be an object"
        }), 400


    # ========================================================
    # SMART FILE FINDER
    # ========================================================

    if intent == "FIND_FILE":

        search_term = str(
            details.get("search_term", "")
        ).strip().lower()

        files = details.get("files", [])

        if not search_term:

            return jsonify({
                "success": False,
                "message": "Search term is required"
            }), 400

        if not isinstance(files, list):

            return jsonify({
                "success": False,
                "message": "Files must be provided as a list"
            }), 400

        matches = []

        for file in files:

            if not isinstance(file, dict):
                continue

            file_name = str(
                file.get("name", "")
            )

            if search_term in file_name.lower():

                matches.append({
                    "name": file_name,
                    "path": file.get("path", ""),
                    "type": file.get("type", ""),
                    "size": file.get("size", "")
                })

        return jsonify({
            "success": True,
            "search_term": search_term,
            "files_found": len(matches),
            "files": matches
        })


    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    conn = get_connection()
    cur = conn.cursor()

    try:

        user_id = authenticated_user_id


        # ====================================================
        # CREATE NOTE
        # ====================================================

        if intent == "CREATE_NOTE":

            text = str(
                details.get("text", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not text:

                return jsonify({
                    "success": False,
                    "message": "Note text is required"
                }), 400

            cur.execute(
                """
                INSERT INTO notes
                (user_id, text)
                VALUES (%s, %s)
                """,
                (
                    user_id,
                    text
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Note saved successfully",
                "user_id": user_id
            })


        # ====================================================
        # CREATE REMINDER
        # ====================================================

        elif intent == "CREATE_REMINDER":

            task = str(
                details.get("task", "")
            ).strip()

            reminder_time = details.get("time")

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not task or not reminder_time:

                return jsonify({
                    "success": False,
                    "message": "Task and time are required"
                }), 400

            cur.execute(
                """
                INSERT INTO reminders
                (user_id, task, time)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    task,
                    reminder_time
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Reminder saved successfully",
                "user_id": user_id,
                "task": task,
                "time": reminder_time
            })


        # ====================================================
        # ADD EXPENSE
        # ====================================================

        elif intent == "ADD_EXPENSE":

            amount = details.get("amount")

            category = str(
                details.get("category", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if amount is None or not category:

                return jsonify({
                    "success": False,
                    "message": "Amount and category are required"
                }), 400

            cur.execute(
                """
                INSERT INTO expenses
                (user_id, amount, category)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    amount,
                    category
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Expense saved successfully",
                "user_id": user_id,
                "amount": float(amount),
                "category": category
            })


        # ====================================================
        # ADD SHOPPING ITEM
        # ====================================================

        elif intent == "ADD_SHOPPING_ITEM":

            items = details.get(
                "items",
                []
            )

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if isinstance(items, str):

                items = [items]

            if not isinstance(items, list) or not items:

                return jsonify({
                    "success": False,
                    "message": "Shopping items are required"
                }), 400

            clean_items = []

            for item in items:

                item = str(item).strip()

                if item:

                    cur.execute(
                        """
                        INSERT INTO shopping_items
                        (user_id, item)
                        VALUES (%s, %s)
                        """,
                        (
                            user_id,
                            item
                        )
                    )

                    clean_items.append(item)

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Shopping items added successfully",
                "user_id": user_id,
                "items": clean_items
            })


        # ====================================================
        # STUDY PLAN
        # ====================================================

        elif intent == "STUDY_PLAN":

            subject = str(
                details.get("subject", "")
            ).strip()

            exam_date = details.get(
                "exam_date"
            )

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not subject or not exam_date:

                return jsonify({
                    "success": False,
                    "message": "Subject and exam date are required"
                }), 400

            cur.execute(
                """
                INSERT INTO study_plans
                (user_id, subject, exam_date)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    subject,
                    exam_date
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Study plan saved successfully",
                "user_id": user_id,
                "subject": subject,
                "exam_date": str(exam_date)
            })


        # ====================================================
        # CREATE GOAL
        # ====================================================

        elif intent == "CREATE_GOAL":

            goal = str(
                details.get("goal", "")
            ).strip()

            target_date = details.get(
                "target_date"
            )

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not goal or not target_date:

                return jsonify({
                    "success": False,
                    "message": "Goal and target date are required"
                }), 400

            cur.execute(
                """
                INSERT INTO goals
                (user_id, goal, target_date)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    goal,
                    target_date
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Goal saved successfully",
                "user_id": user_id,
                "goal": goal,
                "target_date": str(target_date)
            })


        # ====================================================
        # LOG MOOD
        # ====================================================

        elif intent == "LOG_MOOD":

            mood = str(
                details.get("mood", "")
            ).strip()

            emoji = str(
                details.get("emoji", "")
            ).strip()

            text = str(
                details.get("text", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not mood:

                return jsonify({
                    "success": False,
                    "message": "Mood is required"
                }), 400

            cur.execute(
                """
                INSERT INTO moods
                (user_id, mood, emoji, text)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    mood,
                    emoji,
                    text
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Mood logged successfully",
                "user_id": user_id,
                "mood": mood,
                "emoji": emoji,
                "text": text
            })


        # ====================================================
        # SEND EMAIL
        # ====================================================

        elif intent == "DRAFT_EMAIL":

            recipient = str(
                details.get("recipient", "")
            ).strip()

            subject = str(
                details.get("subject", "")
            ).strip()

            body = str(
                details.get("body", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not recipient or not subject or not body:

                return jsonify({
                    "success": False,
                    "message": "Recipient, subject and body are required"
                }), 400

            cur.execute(
                """
                INSERT INTO emails
                (user_id, recipient, subject, body)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    recipient,
                    subject,
                    body
                )
            )

            send_email(
                recipient,
                subject,
                body
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Email sent successfully",
                "user_id": user_id,
                "recipient": recipient,
                "subject": subject
            })


        # ====================================================
        # DAILY BRIEFING
        # ====================================================

        elif intent == "SHOW_INFORMATION":

            info_type = details.get(
                "type",
                "summary"
            )

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if info_type != "summary":

                return jsonify({
                    "success": False,
                    "message": "Unsupported information type"
                }), 400


            # Recent reminders

            cur.execute(
                """
                SELECT id, task, time, created_at
                FROM reminders
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,)
            )

            reminder_rows = cur.fetchall()

            reminders = [
                {
                    "id": row[0],
                    "task": row[1],
                    "time": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in reminder_rows
            ]


            # Study plans

            cur.execute(
                """
                SELECT id, subject, exam_date, created_at
                FROM study_plans
                WHERE user_id = %s
                ORDER BY exam_date ASC
                LIMIT 5
                """,
                (user_id,)
            )

            study_rows = cur.fetchall()

            study_plans = [
                {
                    "id": row[0],
                    "subject": row[1],
                    "exam_date": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in study_rows
            ]


            # Goals

            cur.execute(
                """
                SELECT id, goal, target_date, created_at
                FROM goals
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,)
            )

            goal_rows = cur.fetchall()

            goals = [
                {
                    "id": row[0],
                    "goal": row[1],
                    "target_date": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in goal_rows
            ]


            # Moods

            cur.execute(
                """
                SELECT id, mood, emoji, text, created_at
                FROM moods
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,)
            )

            mood_rows = cur.fetchall()

            moods = [
                {
                    "id": row[0],
                    "mood": row[1],
                    "emoji": row[2],
                    "text": row[3],
                    "created_at": str(row[4])
                }
                for row in mood_rows
            ]


            # Shopping

            cur.execute(
                """
                SELECT id, item, created_at
                FROM shopping_items
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,)
            )

            shopping_rows = cur.fetchall()

            shopping_items = [
                {
                    "id": row[0],
                    "item": row[1],
                    "created_at": str(row[2])
                }
                for row in shopping_rows
            ]


            # Expenses

            cur.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE user_id = %s
                """,
                (user_id,)
            )

            total_expenses = cur.fetchone()[0]


            return jsonify({
                "success": True,
                "user_id": user_id,
                "type": "summary",
                "briefing": {
                    "reminders": reminders,
                    "study_plans": study_plans,
                    "goals": goals,
                    "moods": moods,
                    "shopping_items": shopping_items,
                    "total_expenses": float(total_expenses)
                }
            })

        # ====================================================
        # CREATE MEMORY
        # ====================================================

        elif intent == "CREATE_MEMORY":

            memory = str(
                details.get("memory", "")
            ).strip()

            category = str(
                details.get("category", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not memory:

                return jsonify({
                    "success": False,
                    "message": "Memory is required"
                }), 400

            cur.execute(
                """
                INSERT INTO memories
                (user_id, memory, category)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    memory,
                    category
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Memory saved successfully",
                "user_id": user_id,
                "memory": memory,
                "category": category
            })


        # ====================================================
        # SAVE CONTEXT
        # ====================================================

        elif intent == "SAVE_CONTEXT":

            context = str(
                details.get("context", "")
            ).strip()

            current_task = str(
                details.get("current_task", "")
            ).strip()

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not context:

                return jsonify({
                    "success": False,
                    "message": "Context is required"
                }), 400

            cur.execute(
                """
                INSERT INTO user_context
                (user_id, context, current_task)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    context,
                    current_task
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Context saved successfully",
                "user_id": user_id,
                "context": context,
                "current_task": current_task
            })


        # ====================================================
        # MULTI ACTION
        # ====================================================

        elif intent == "MULTI_ACTION":

            command = str(
                details.get("command", "")
            ).strip()

            actions = details.get(
                "actions",
                []
            )

            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not isinstance(actions, list) or not actions:

                return jsonify({
                    "success": False,
                    "message": "At least one action is required"
                }), 400

            results = []

            try:

                for action in actions:

                    if not isinstance(action, dict):

                        results.append({
                            "success": False,
                            "message": "Invalid action format"
                        })

                        continue

                    action_intent = action.get(
                        "intent"
                    )

                    action_data = action.get(
                        "data",
                        {}
                    )

                    if not isinstance(action_data, dict):

                        results.append({
                            "intent": action_intent,
                            "success": False,
                            "message": "Action data must be an object"
                        })

                        continue


                    # CREATE REMINDER

                    if action_intent == "CREATE_REMINDER":

                        task = str(
                            action_data.get(
                                "task",
                                ""
                            )
                        ).strip()

                        reminder_time = action_data.get(
                            "time"
                        )

                        if not task or not reminder_time:

                            results.append({
                                "intent": action_intent,
                                "success": False,
                                "message": "Task and time are required"
                            })

                            continue

                        cur.execute(
                            """
                            INSERT INTO reminders
                            (user_id, task, time)
                            VALUES (%s, %s, %s)
                            """,
                            (
                                user_id,
                                task,
                                reminder_time
                            )
                        )

                        results.append({
                            "intent": action_intent,
                            "success": True,
                            "message": "Reminder created successfully"
                        })


                    # STUDY PLAN

                    elif action_intent == "STUDY_PLAN":

                        subject = str(
                            action_data.get(
                                "subject",
                                ""
                            )
                        ).strip()

                        exam_date = action_data.get(
                            "exam_date"
                        )

                        if not subject or not exam_date:

                            results.append({
                                "intent": action_intent,
                                "success": False,
                                "message": "Subject and exam date are required"
                            })

                            continue

                        cur.execute(
                            """
                            INSERT INTO study_plans
                            (user_id, subject, exam_date)
                            VALUES (%s, %s, %s)
                            """,
                            (
                                user_id,
                                subject,
                                exam_date
                            )
                        )

                        results.append({
                            "intent": action_intent,
                            "success": True,
                            "message": "Study plan created successfully"
                        })


                    # CREATE GOAL

                    elif action_intent == "CREATE_GOAL":

                        goal = str(
                            action_data.get(
                                "goal",
                                ""
                            )
                        ).strip()

                        target_date = action_data.get(
                            "target_date"
                        )

                        if not goal or not target_date:

                            results.append({
                                "intent": action_intent,
                                "success": False,
                                "message": "Goal and target date are required"
                            })

                            continue

                        cur.execute(
                            """
                            INSERT INTO goals
                            (user_id, goal, target_date)
                            VALUES (%s, %s, %s)
                            """,
                            (
                                user_id,
                                goal,
                                target_date
                            )
                        )

                        results.append({
                            "intent": action_intent,
                            "success": True,
                            "message": "Goal created successfully"
                        })


                    else:

                        results.append({
                            "intent": action_intent,
                            "success": False,
                            "message": "Unsupported action"
                        })


                successful_actions = sum(
                    1
                    for result in results
                    if result.get("success") is True
                )

                failed_actions = (
                    len(results)
                    - successful_actions
                )

                if successful_actions == 0:

                    conn.rollback()
                    status = "failed"

                else:

                    status = (
                        "completed"
                        if failed_actions == 0
                        else "partial"
                    )


                cur.execute(
                    """
                    INSERT INTO automation_logs
                    (user_id, command, actions, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        command,
                        psycopg.types.json.Json(actions),
                        status
                    )
                )

                conn.commit()

                return jsonify({
                    "success": successful_actions > 0,
                    "message": "Multi-action request processed",
                    "user_id": user_id,
                    "status": status,
                    "successful_actions": successful_actions,
                    "failed_actions": failed_actions,
                    "results": results
                })


            except Exception:

                conn.rollback()
                raise


        # ====================================================
        # DOCUMENT ASSISTANT
        # ====================================================

        elif intent == "DOCUMENT_ASSIST":

            file_name = str(
                details.get("file_name", "")
            ).strip()

            action = str(
                details.get("action", "")
            ).strip().upper()

            document_text = str(
                details.get("text", "")
            ).strip()

            question = str(
                details.get("question", "")
            ).strip()


            allowed_actions = {
                "SUMMARIZE",
                "QUESTIONS",
                "IMPORTANT_QUESTIONS",
                "KEY_POINTS",
                "REVISION_NOTES"
            }


            if not user_id:

                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            if not document_text:

                return jsonify({
                    "success": False,
                    "message": "Document text is required"
                }), 400

            if action not in allowed_actions:

                return jsonify({
                    "success": False,
                    "message": "Unsupported document action"
                }), 400


            if action == "SUMMARIZE":

                prompt = f"""
Summarize the following document clearly and concisely.

Include the main ideas and important facts.

Do not add information that is not present.

DOCUMENT:

{document_text}
"""


            elif action == "QUESTIONS":

                if not question:

                    return jsonify({
                        "success": False,
                        "message": "Question is required for QUESTIONS action"
                    }), 400

                prompt = f"""
Answer the following question using only the information
contained in the document.

If the answer cannot be found in the document,
clearly say that it is not available.

Question:

{question}

DOCUMENT:

{document_text}
"""


            elif action == "IMPORTANT_QUESTIONS":

                prompt = f"""
Create 10 important study questions based only on
the following document.

Focus on:
- Concepts
- Definitions
- Important facts
- Topics useful for revision

Do not invent information.

DOCUMENT:

{document_text}
"""


            elif action == "KEY_POINTS":

                prompt = f"""
Extract the most important key points from the following document.

Present them as clear bullet points.

Do not add information that is not present.

DOCUMENT:

{document_text}
"""


            else:

                prompt = f"""
Create concise revision notes from the following document.

Organize the notes using headings and bullet points.

Include:
- Important concepts
- Definitions
- Facts
- Relationships

Do not add information that is not present.

DOCUMENT:

{document_text}
"""


            response = gemini_client.models.generate_content(
                model="gemini-3.7-flash",
                contents=prompt
            )

            result = (
                response.text or ""
            ).strip()


            if not result:

                return jsonify({
                    "success": False,
                    "message": "No result was generated"
                }), 500


            cur.execute(
                """
                INSERT INTO document_assists
                (user_id, file_name, action, result)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    file_name,
                    action,
                    result
                )
            )

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Document assistance completed successfully",
                "user_id": user_id,
                "file_name": file_name,
                "action": action,
                "result": result
            })


        
        # =========================================
        # GET NOTES
        # =========================================

        elif intent == "GET_NOTES":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["text"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM notes
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, text, created_at
                FROM notes
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            notes = [
                {
                    "id": row[0],
                    "text": row[1],
                    "created_at": str(row[2])
                }
                for row in rows
            ]

            formatted_notes = [
                f"{index}. {note['text']}"
                for index, note in enumerate(
                    notes,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(notes),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(notes) < total,
                "has_previous": offset > 0,
                "notes": notes,
                "formatted_notes": formatted_notes
            })

        # ============================================================
        # GET REMINDERS
        # ============================================================

        elif intent == "GET_REMINDERS":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["task"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM reminders
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, task, time, created_at
                FROM reminders
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            reminders = [
                {
                    "id": row[0],
                    "task": row[1],
                    "time": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_reminders = [
                f"{index}. {reminder['task']} "
                f"(Time: {reminder['time']}, "
                f"Created: {reminder['created_at']})"
                for index, reminder in enumerate(
                    reminders,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(reminders),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(reminders) < total,
                "has_previous": offset > 0,
                "reminders": reminders,
                "formatted_reminders": formatted_reminders
            })

        # ============================================================
        # GET EXPENSES
        # ============================================================

        elif intent == "GET_EXPENSES":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["category"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM expenses
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, amount, category, created_at
                FROM expenses
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            expenses = [
                {
                    "id": row[0],
                    "amount": float(row[1]),
                    "category": row[2],
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_expenses = [
                f"{index}. ₹{expense['amount']} - "
                f"{expense['category']}"
                for index, expense in enumerate(
                    expenses,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(expenses),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(expenses) < total,
                "has_previous": offset > 0,
                "expenses": expenses,
                "formatted_expenses": formatted_expenses
            })

        # ============================================================
        # GET SHOPPING LIST
        # ============================================================

        elif intent == "GET_SHOPPING_LIST":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["item"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM shopping_items
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, item, created_at
                FROM shopping_items
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            shopping_items = [
                {
                    "id": row[0],
                    "item": row[1],
                    "created_at": str(row[2])
                }
                for row in rows
            ]

            formatted_shopping_items = [
                f"{index}. {item['item']}"
                for index, item in enumerate(
                    shopping_items,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(shopping_items),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(shopping_items) < total,
                "has_previous": offset > 0,
                "shopping_items": shopping_items,
                "formatted_shopping_items": formatted_shopping_items
            })

        # ============================================================
        # GET STUDY PLANS
        # ============================================================

        elif intent == "GET_STUDY_PLANS":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["subject"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM study_plans
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, subject, exam_date, created_at
                FROM study_plans
                WHERE {where_clause}
                ORDER BY exam_date ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            study_plans = [
                {
                    "id": row[0],
                    "subject": row[1],
                    "exam_date": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_study_plans = [
                f"{index}. {plan['subject']} - "
                f"Exam date: {plan['exam_date']}"
                for index, plan in enumerate(
                    study_plans,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(study_plans),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(study_plans) < total,
                "has_previous": offset > 0,
                "study_plans": study_plans,
                "formatted_study_plans": formatted_study_plans
            })

        # ============================================================
        # GET GOALS
        # ============================================================

        elif intent == "GET_GOALS":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["goal"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM goals
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, goal, target_date, created_at
                FROM goals
                WHERE {where_clause}
                ORDER BY target_date ASC, id ASC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            goals = [
                {
                    "id": row[0],
                    "goal": row[1],
                    "target_date": str(row[2]),
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_goals = [
                f"{index}. {goal['goal']} - "
                f"Target date: {goal['target_date']}"
                for index, goal in enumerate(
                    goals,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(goals),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(goals) < total,
                "has_previous": offset > 0,
                "goals": goals,
                "formatted_goals": formatted_goals
            })

        # ============================================================
        # GET MOODS
        # ============================================================

        elif intent == "GET_MOODS":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=["mood", "text"]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM moods
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, mood, emoji, text, created_at
                FROM moods
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            moods = [
                {
                    "id": row[0],
                    "mood": row[1],
                    "emoji": row[2],
                    "text": row[3],
                    "created_at": str(row[4])
                }
                for row in rows
            ]

            formatted_moods = []

            for index, mood in enumerate(
                moods,
                start=offset + 1
            ):
                mood_text = mood["text"] or ""

                formatted_moods.append(
                    f"{index}. {mood['emoji']} "
                    f"{mood['mood']} - {mood_text}"
                )

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(moods),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(moods) < total,
                "has_previous": offset > 0,
                "moods": moods,
                "formatted_moods": formatted_moods
            })

        # ============================================================
        # GET EMAILS
        # ============================================================

        elif intent == "GET_EMAILS":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=[
                    "recipient",
                    "subject",
                    "body"
                ]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM emails
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, recipient, subject, body, created_at
                FROM emails
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            emails = [
                {
                    "id": row[0],
                    "recipient": row[1],
                    "subject": row[2],
                    "body": row[3],
                    "created_at": str(row[4])
                }
                for row in rows
            ]

            formatted_emails = [
                f"{index}. To: {email['recipient']} | "
                f"Subject: {email['subject']} | "
                f"Body: {email['body']}"
                for index, email in enumerate(
                    emails,
                    start=offset + 1
                )
            ]

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(emails),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(emails) < total,
                "has_previous": offset > 0,
                "emails": emails,
                "formatted_emails": formatted_emails
            })

        # ============================================================
        # GET MEMORIES
        # ============================================================

        elif intent == "GET_MEMORIES":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=[
                    "memory",
                    "category"
                ]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM memories
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, memory, category, created_at
                FROM memories
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            memories = [
                {
                    "id": row[0],
                    "memory": row[1],
                    "category": row[2],
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_memories = []

            for index, memory in enumerate(
                memories,
                start=offset + 1
            ):
                if memory["category"]:
                    formatted_memories.append(
                        f"{index}. {memory['memory']} "
                        f"(Category: {memory['category']})"
                    )
                else:
                    formatted_memories.append(
                        f"{index}. {memory['memory']}"
                    )

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(memories),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(memories) < total,
                "has_previous": offset > 0,
                "memories": memories,
                "formatted_memories": formatted_memories
            })

        # ============================================================
        # GET CONTEXT
        # ============================================================

        elif intent == "GET_CONTEXT":

            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "User ID is required"
                }), 400

            limit, offset, search, date_from, date_to = (
                get_retrieval_params(details)
            )

            where_clause, params = build_retrieval_filter(
                user_id=user_id,
                search=search,
                date_from=date_from,
                date_to=date_to,
                search_columns=[
                    "context",
                    "current_task"
                ]
            )

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM user_context
                WHERE {where_clause}
                """,
                tuple(params)
            )

            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, context, current_task, created_at
                FROM user_context
                WHERE {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [limit, offset])
            )

            rows = cur.fetchall()

            contexts = [
                {
                    "id": row[0],
                    "context": row[1],
                    "current_task": row[2],
                    "created_at": str(row[3])
                }
                for row in rows
            ]

            formatted_contexts = []

            for index, context in enumerate(
                contexts,
                start=offset + 1
            ):
                if context["current_task"]:
                    formatted_contexts.append(
                        f"{index}. {context['context']} "
                        f"(Current task: "
                        f"{context['current_task']})"
                    )
                else:
                    formatted_contexts.append(
                        f"{index}. {context['context']}"
                    )

            return jsonify({
                "success": True,
                "user_id": user_id,
                "count": len(contexts),
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
                "has_next": offset + len(contexts) < total,
                "has_previous": offset > 0,
                "contexts": contexts,
                "formatted_contexts": formatted_contexts
            })

# ====================================================
        # UNKNOWN INTENT
        # ====================================================

        else:

            return jsonify({
                "success": False,
                "message": "Unknown intent"
            }), 400


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        conn.rollback()

        print("ASSISTANT ERROR:", e)

        return jsonify({
            "success": False,
            "message": "An internal server error occurred"
        }), 500


    finally:

        cur.close()
        conn.close()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=8000
    )