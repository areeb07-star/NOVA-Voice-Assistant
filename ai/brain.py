import os
import sys
import json
import re
import requests
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

API_KEYS = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
]
API_KEYS = [k for k in API_KEYS if k]

if not API_KEYS:
    print("ERROR: No GROQ_API_KEY found in .env file!")
    exit()

clients = [Groq(api_key=k) for k in API_KEYS]

BACKEND_URL = "https://nova-voice-assistant-6vve.onrender.com"
DEFAULT_DEVICE_ID = "azzam-laptop-001"

conversation_history = {}
HISTORY_LIMIT = 6

pending_confirmations = {}

MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

SIMILARITY_THRESHOLD = 0.65

SYSTEM_PROMPT = """
You are Nova, a voice assistant for daily tasks.

Reply ONLY with STRICT JSON. Do not add any extra text.
The JSON must have these 5 keys:
1. "intent": Choose ONE: CREATE_REMINDER, CREATE_NOTE, ADD_EXPENSE, ADD_SHOPPING_ITEM, CREATE_GOAL, STUDY_PLAN, SHOW_INFORMATION, GET_NOTES, GET_REMINDERS, GET_EXPENSES, GET_SHOPPING_LIST, GET_STUDY_PLANS, GET_GOALS, GET_MOODS, GET_MEMORIES, SEARCH_NOTES, UPDATE_NOTE, UPDATE_REMINDER, UPDATE_EXPENSE, UPDATE_SHOPPING_ITEM, UPDATE_GOAL, UPDATE_STUDY_PLAN, TRANSLATE_TEXT, SUMMARIZE_TEXT, GENERATE_FLASHCARDS, LOG_MOOD, CREATE_MEMORY, SAVE_CONTEXT, DRAFT_EMAIL, OPEN_APP, OPEN_FOLDER, OPEN_URL, CREATE_FOLDER, FIND_FILE, MUTE, UNMUTE, VOLUME_UP, VOLUME_DOWN, SET_VOLUME, BRIGHTNESS_UP, BRIGHTNESS_DOWN, SET_BRIGHTNESS, TAKE_SCREENSHOT, CLOSE_APP, SPEAK_LAST, or GENERAL_CHAT.
2. "mood": Detect emotion: happy, sad, stressed, excited, neutral.
3. "emoji": Pick ONE emoji that matches the mood.
4. "data": An object with details.
5. "reply": A short confirmation. NEVER claim you did something you haven't done.

Examples:
User: "Remind me to call Mom at 5 PM"
Output: {"intent":"CREATE_REMINDER","mood":"neutral","emoji":"😐","data":{"task":"call Mom","time":"17:00"},"reply":"Reminder set for 5 PM!"}

User: "Save note: Buy milk"
Output: {"intent":"CREATE_NOTE","mood":"neutral","emoji":"😐","data":{"text":"Buy milk"},"reply":"Note saved!"}

User: "show my notes"
Output: {"intent":"GET_NOTES","mood":"neutral","emoji":"😐","data":{"limit":5,"offset":0},"reply":"Here are your notes!"}

User: "update note 5 to Buy bread"
Output: {"intent":"UPDATE_NOTE","mood":"neutral","emoji":"😐","data":{"id":5,"text":"Buy bread"},"reply":"Updating note..."}

User: "change reminder 3 to call Dad at 6 PM"
Output: {"intent":"UPDATE_REMINDER","mood":"neutral","emoji":"😐","data":{"id":3,"task":"call Dad","time":"18:00"},"reply":"Updating reminder..."}

User: "update expense 2 to 30 dollars food"
Output: {"intent":"UPDATE_EXPENSE","mood":"neutral","emoji":"😐","data":{"id":2,"amount":"30","category":"food"},"reply":"Updating expense..."}

User: "edit shopping item 4 to eggs"
Output: {"intent":"UPDATE_SHOPPING_ITEM","mood":"neutral","emoji":"😐","data":{"id":4,"item":"eggs"},"reply":"Updating shopping item..."}

User: "update goal 1 to read 20 books this year"
Output: {"intent":"UPDATE_GOAL","mood":"neutral","emoji":"😐","data":{"id":1,"goal":"read 20 books","target_date":"This year"},"reply":"Updating goal..."}

User: "edit study plan 2 to Physics next Monday"
Output: {"intent":"UPDATE_STUDY_PLAN","mood":"neutral","emoji":"😐","data":{"id":2,"subject":"Physics","exam_date":"Next Monday"},"reply":"Updating study plan..."}

User: "show notes about best friend"
Output: {"intent":"SEARCH_NOTES","mood":"neutral","emoji":"😐","data":{"query":"best friend"},"reply":"Searching your notes..."}

User: "send an email to firdousfathima275@gmail.com about leave"
Output: {"intent":"DRAFT_EMAIL","mood":"neutral","emoji":"😐","data":{"recipient":"firdousfathima275@gmail.com","subject":"Leave Request","body":"Hi Firdous, I would like to take 2 days of leave."},"reply":"Email drafted!"}

User: "open youtube"
Output: {"intent":"OPEN_URL","mood":"neutral","emoji":"😐","data":{"url":"https://youtube.com"},"reply":"Opening YouTube!"}

User: "What is Java?"
Output: {"intent":"GENERAL_CHAT","mood":"neutral","emoji":"😐","data":{},"reply":"Java is a popular programming language."}

CRITICAL HONESTY RULE: NEVER claim you did something you haven't done.

CRITICAL HONESTY RULE #2:
If you genuinely don't know the answer, respond with:
"I don't have information on that. Would you like to ask something else?"

CRITICAL EMAIL RULE:
For DRAFT_EMAIL, include recipient, subject, body.

CRITICAL UPDATE RULE:
When the user says "update", "change", "edit", "modify", or "rename" + a module + an ID,
use the matching UPDATE_* intent with the ID and the new values.

IMPORTANT: Always use "id" as the identifier key — NOT note_id, reminder_id, expense_id, item_id, plan_id, or goal_id.

Examples:
- "update note 5 to X" → UPDATE_NOTE with {id: 5, text: X}
- "change reminder 3 to X at Y" → UPDATE_REMINDER with {id: 3, task: X, time: Y}
- "edit expense 2 to 30 food" → UPDATE_EXPENSE with {id: 2, amount: 30, category: food}
- "edit shopping item 4 to eggs" → UPDATE_SHOPPING_ITEM with {id: 4, item: eggs}
- "update goal 1 to X" → UPDATE_GOAL with {id: 1, goal: X, target_date: ...}
- "edit study plan 2 to X" → UPDATE_STUDY_PLAN with {id: 2, subject: X, exam_date: ...}

NOTE: UPDATE_MOOD is NOT available. If the user wants to update a mood, use LOG_MOOD to create a new entry.

CRITICAL CLARIFICATION RULE:
If the user's message is ambiguous, respond with a CLARIFYING QUESTION.

CRITICAL SMALL TALK RULE:
Nova is a TASK assistant, NOT a joke bot.

CRITICAL REPEAT RULE (SPEAK_LAST):
If user asks to repeat, use SPEAK_LAST.

CRITICAL NOTE FILTER RULE:
- "show my notes" → GET_NOTES
- "show notes about X" → SEARCH_NOTES with query "X"

CRITICAL FILE SEARCH RULE (FIND_FILE):
- "find [file] in [folder]" → FIND_FILE with search_term + folder

CRITICAL FOLDER OPENING RULE (OPEN_FOLDER):
Use OPEN_FOLDER ONLY when there's no file to search.

CRITICAL FOLDER CREATION RULE (CREATE_FOLDER):
"create folder [name]" → CREATE_FOLDER with {folder_name: name}

CRITICAL WEBSITE OPENING RULE (OPEN_URL):
youtube → https://youtube.com, google → https://google.com, gmail → https://mail.google.com

CRITICAL APP NAME VALIDATION RULE (OPEN_APP):
Only for: chrome, code, vscode, calc, calculator, notepad, explorer, cmd, terminal, paint, settings, sound_settings, whatsapp, spotify, word, excel, powerpoint, outlook, teams, telegram, zoom, vlc, steam.

CRITICAL FOLLOW-UP RULE:
"name it X" completes previous action with X.

SAFE ACTION RULE: Only CLOSE_APP needs confirmation.
"""

VALID_INTENTS = {
    "CREATE_REMINDER", "CREATE_NOTE", "ADD_EXPENSE", "ADD_SHOPPING_ITEM",
    "CREATE_GOAL", "STUDY_PLAN", "SHOW_INFORMATION",
    "GET_NOTES", "GET_REMINDERS", "GET_EXPENSES", "GET_SHOPPING_LIST",
    "GET_STUDY_PLANS", "GET_GOALS", "GET_MOODS", "GET_MEMORIES", "SEARCH_NOTES",
    "UPDATE_NOTE", "UPDATE_REMINDER", "UPDATE_EXPENSE", "UPDATE_SHOPPING_ITEM",
    "UPDATE_GOAL", "UPDATE_STUDY_PLAN",
    "TRANSLATE_TEXT", "SUMMARIZE_TEXT", "GENERATE_FLASHCARDS",
    "LOG_MOOD", "CREATE_MEMORY", "SAVE_CONTEXT", "DRAFT_EMAIL",
    "OPEN_APP", "OPEN_FOLDER", "OPEN_URL", "CREATE_FOLDER",
    "FIND_FILE", "MUTE", "UNMUTE",
    "VOLUME_UP", "VOLUME_DOWN", "SET_VOLUME",
    "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SET_BRIGHTNESS",
    "TAKE_SCREENSHOT", "CLOSE_APP",
    "SPEAK_LAST",
    "GENERAL_CHAT"
}


def normalize_result(raw_result):
    if not isinstance(raw_result, dict):
        return {"intent": "GENERAL_CHAT", "mood": "neutral", "emoji": "😐", "data": {}, "reply": "Sorry, I hit a snag!"}

    normalized = {
        "intent": raw_result.get("intent", "GENERAL_CHAT"),
        "mood": raw_result.get("mood", "neutral"),
        "emoji": raw_result.get("emoji", "😐"),
        "data": raw_result.get("data", {}) if isinstance(raw_result.get("data"), dict) else {},
        "reply": raw_result.get("reply", "Done!")
    }

    if normalized["intent"] not in VALID_INTENTS:
        normalized["intent"] = "GENERAL_CHAT"

    if not isinstance(normalized["reply"], str):
        normalized["reply"] = "Done!"

    return normalized


def extract_json_object(raw_text):
    if not raw_text:
        return "{}"

    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def save_chat_message(user_id, role, content, token):
    if not token or not user_id:
        return
    try:
        requests.post(
            f"{BACKEND_URL}/api/chat-history/save",
            json={"user_id": user_id, "role": role, "content": content},
            headers={"Authorization": f"Bearer {token}"},
            timeout=3
        )
    except Exception:
        pass


def process_user_input(user_text, user_id="default"):
    today = datetime.now().strftime("%B %d, %Y")

    history = conversation_history.get(user_id, [])
    history.append({"role": "user", "content": user_text})
    history = history[-HISTORY_LIMIT:]

    last_error = None
    for client in clients:
        for model in MODELS:
            try:
                print(f"[Trying model: {model}]")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": f"Today's date is {today}.\n\n{SYSTEM_PROMPT}"},
                        *history
                    ],
                    temperature=0.3
                )
                ai_reply = response.choices[0].message.content
                ai_reply = extract_json_object(ai_reply)

                history.append({"role": "assistant", "content": ai_reply})
                conversation_history[user_id] = history[-HISTORY_LIMIT:]

                result = json.loads(ai_reply)
                return normalize_result(result)
            except Exception as e:
                err_str = str(e)
                print(f"[Model {model} failed: {err_str[:100]}]")
                last_error = e
                continue

    print(f"All models failed. Last error: {last_error}")
    return {"intent": "GENERAL_CHAT", "mood": "neutral", "emoji": "😐", "data": {}, "reply": "Sorry, I hit a snag!"}


def get_access_token(email, password):
    url = f"{BACKEND_URL}/api/login"
    try:
        response = requests.post(url, json={"email": email, "password": password})
        if response.status_code == 200:
            data = response.json()
            print("Login successful! Access token obtained.")
            return data.get("access_token"), data.get("user_id")
        else:
            print(f"Login failed: {response.text}")
            return None, None
    except Exception as e:
        print(f"Error logging in: {e}")
        return None, None


def send_to_backend(intent, data, token):
    url = f"{BACKEND_URL}/api/assistant"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"intent": intent, "data": data}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": f"Could not connect to backend: {e}"}


def fetch_from_backend(intent, data, token):
    url = f"{BACKEND_URL}/api/assistant"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"intent": intent, "data": data}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": f"Could not fetch data: {e}"}


def get_ai_response(user_text, token, user_id, device_id=DEFAULT_DEVICE_ID):
    save_chat_message(user_id, "user", user_text, token)

    pending = pending_confirmations.get(user_id)
    is_confirmation = False

    if pending:
        lower = user_text.strip().lower()
        if lower in ["yes", "yeah", "confirm", "yes please", "do it", "sure", "ok", "okay"]:
            result = {
                "intent": pending["intent"],
                "mood": "neutral",
                "emoji": "😐",
                "data": pending["data"],
                "reply": "Confirmed. Executing..."
            }
            pending_confirmations.pop(user_id, None)
            is_confirmation = True
        elif lower in ["no", "cancel", "nope", "stop", "don't", "dont"]:
            pending_confirmations.pop(user_id, None)
            reply = "Okay, I cancelled that action."
            save_chat_message(user_id, "assistant", reply, token)
            return {
                "intent": "GENERAL_CHAT",
                "mood": "neutral",
                "emoji": "😐",
                "data": {},
                "reply": reply
            }
        else:
            pending_confirmations.pop(user_id, None)
            result = process_user_input(user_text, user_id)
    else:
        result = process_user_input(user_text, user_id)

    if result["intent"] == "SPEAK_LAST":
        history = conversation_history.get(user_id, [])
        last_reply = None
        for msg in reversed(history[:-1]):
            if msg.get("role") == "assistant":
                try:
                    prev = json.loads(msg.get("content", "{}"))
                    if prev.get("intent") != "SPEAK_LAST" and prev.get("reply"):
                        last_reply = prev.get("reply")
                        break
                except Exception:
                    continue
        result["reply"] = last_reply if last_reply else "I don't have anything to repeat yet."
        save_chat_message(user_id, "assistant", result["reply"], token)
        return {
            "intent": result.get("intent"),
            "mood": result.get("mood"),
            "emoji": result.get("emoji"),
            "data": result.get("data"),
            "reply": result.get("reply")
        }

    # --- CREATE + UPDATE ---
    if result["intent"] in [
        "CREATE_NOTE", "CREATE_REMINDER", "ADD_EXPENSE", "ADD_SHOPPING_ITEM",
        "STUDY_PLAN", "CREATE_GOAL", "LOG_MOOD", "CREATE_MEMORY", "SAVE_CONTEXT",
        "UPDATE_NOTE", "UPDATE_REMINDER", "UPDATE_EXPENSE", "UPDATE_SHOPPING_ITEM",
        "UPDATE_GOAL", "UPDATE_STUDY_PLAN"
    ]:
        result["data"]["user_id"] = user_id
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

        if isinstance(backend_response, dict) and not backend_response.get("success"):
            error_msg = backend_response.get("message", "unknown error")
            result["reply"] = f"Sorry, I couldn't save that: {error_msg}"

    # --- DRAFT_EMAIL ---
    elif result["intent"] == "DRAFT_EMAIL":
        result["data"]["user_id"] = user_id
        if not result["data"].get("subject"):
            result["data"]["subject"] = "Nova Message"
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

        if isinstance(backend_response, dict) and backend_response.get("success"):
            recipient = result["data"].get("recipient", "the recipient")
            result["reply"] = f"Email sent to {recipient}."
        else:
            error_msg = backend_response.get("message", "unknown error") if isinstance(backend_response, dict) else "unknown"
            result["reply"] = f"Sorry, I couldn't send the email: {error_msg}"

    # --- FIND_FILE ---
    elif result["intent"] == "FIND_FILE":
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

        search_term = result["data"].get("search_term", user_text)
        folder = result["data"].get("folder", "")

        if isinstance(backend_response, dict):
            files_found = backend_response.get("files_found", 0)
            files = backend_response.get("files", [])

            if not backend_response.get("success"):
                result["reply"] = f"Sorry, I couldn't search for '{search_term}' right now."
            elif files_found == 0:
                if folder:
                    result["reply"] = f"Sorry, I couldn't find '{search_term}' in your {folder} folder."
                else:
                    result["reply"] = f"Sorry, I couldn't find any file or folder matching '{search_term}'."
            else:
                file_names = [f.split("\\")[-1] for f in files[:5]]
                if len(file_names) == 1:
                    result["reply"] = f"Found 1 item: {file_names[0]}"
                else:
                    result["reply"] = f"Found {files_found} items:\n" + "\n".join(file_names)
        else:
            result["reply"] = f"Sorry, I couldn't find '{search_term}'."

    # --- CLOSE_APP ---
    elif result["intent"] == "CLOSE_APP":
        if not is_confirmation:
            pending_confirmations[user_id] = {
                "intent": "CLOSE_APP",
                "data": result["data"].copy()
            }
            app_name = result["data"].get("app", "this app")
            result["reply"] = f"Are you sure you want to close {app_name}? Say yes to confirm."
            result["data"]["requires_confirmation"] = True
            save_chat_message(user_id, "assistant", result["reply"], token)
            return {
                "intent": result.get("intent"),
                "mood": result.get("mood"),
                "emoji": result.get("emoji"),
                "data": result.get("data"),
                "reply": result.get("reply")
            }

        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        result["data"]["requires_confirmation"] = False
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

    # --- OPEN_FOLDER ---
    elif result["intent"] == "OPEN_FOLDER":
        folder = result["data"].get("folder", "")

        check_payload = {
            "search_term": folder,
            "user_id": user_id,
            "device_id": device_id
        }
        check_response = send_to_backend("FIND_FILE", check_payload, token)
        print("Pre-check says:", check_response)

        files_found = check_response.get("files_found", 0) if isinstance(check_response, dict) else 0

        if files_found == 0:
            result["reply"] = f"Sorry, I couldn't find a folder named '{folder}' on your laptop. Want me to open a different folder?"
        else:
            result["data"]["user_id"] = user_id
            result["data"]["device_id"] = device_id
            backend_response = send_to_backend("OPEN_FOLDER", result["data"], token)
            print("Backend says:", backend_response)

            if isinstance(backend_response, dict) and backend_response.get("success"):
                result["reply"] = f"Opening {folder} folder!"
            else:
                result["reply"] = f"Sorry, I couldn't open {folder}."

    # --- OPEN_APP / OPEN_URL / CREATE_FOLDER ---
    elif result["intent"] in ["OPEN_APP", "OPEN_URL", "CREATE_FOLDER"]:
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

        if isinstance(backend_response, dict) and backend_response.get("success"):
            if result["intent"] == "OPEN_APP":
                app = result["data"].get("app", "the app")
                result["reply"] = f"Opening {app} on your laptop..."
            elif result["intent"] == "OPEN_URL":
                result["reply"] = "Opening that website in your browser..."
            elif result["intent"] == "CREATE_FOLDER":
                folder = result["data"].get("folder_name", "the folder")
                result["reply"] = f"Creating folder {folder} on your Desktop..."
        else:
            result["reply"] = "Sorry, I couldn't complete that action right now."

    # --- OTHER DEVICE ACTIONS ---
    elif result["intent"] in ["MUTE", "UNMUTE",
                              "VOLUME_UP", "VOLUME_DOWN", "SET_VOLUME",
                              "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SET_BRIGHTNESS",
                              "TAKE_SCREENSHOT"]:
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)

    # --- SEMANTIC SEARCH ---
    elif result["intent"] == "SEARCH_NOTES":
        query = result["data"].get("query", user_text)
        search_payload = {"query": query, "user_id": user_id}
        url = f"{BACKEND_URL}/api/assistant"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = requests.post(url, json={"intent": "SEARCH_NOTES", "data": search_payload}, headers=headers)
            fetched_data = r.json()
            print("Semantic search result:", fetched_data)

            if fetched_data.get("success"):
                results = fetched_data.get("results", [])
                filtered = [item for item in results if item.get("similarity", 0) >= SIMILARITY_THRESHOLD]

                if filtered:
                    formatted = [f"{i+1}. {item['text']} (similarity: {round(item['similarity'], 2)})"
                                 for i, item in enumerate(filtered)]
                    result["reply"] = "Here are the notes I found:\n" + "\n".join(formatted)
                else:
                    result["reply"] = f"Sorry, I couldn't find any notes about '{query}'."
            else:
                result["reply"] = f"Search failed: {fetched_data.get('message', 'unknown error')}"
        except Exception as e:
            result["reply"] = f"Could not search: {e}"

    # --- FETCHING DATA ---
    elif result["intent"] in ["GET_NOTES", "GET_REMINDERS", "GET_EXPENSES",
                              "GET_SHOPPING_LIST", "GET_STUDY_PLANS", "GET_GOALS",
                              "GET_MOODS", "GET_MEMORIES", "GET_CONTEXT", "SHOW_INFORMATION"]:
        fetch_params = result["data"].copy()
        fetch_params["user_id"] = user_id
        fetched_data = fetch_from_backend(result["intent"], fetch_params, token)
        print("Fetched from database:", fetched_data)

        if fetched_data.get("success"):
            formatted = (fetched_data.get("formatted_notes") or
                         fetched_data.get("formatted_reminders") or
                         fetched_data.get("formatted_items") or
                         fetched_data.get("formatted_expenses") or
                         fetched_data.get("formatted_goals") or
                         fetched_data.get("formatted_study_plans") or
                         fetched_data.get("formatted_moods") or
                         fetched_data.get("formatted_memories"))

            if formatted:
                if result["intent"] == "GET_NOTES":
                    result["reply"] = "Here are your notes:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_REMINDERS":
                    result["reply"] = "Here are your reminders:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_EXPENSES":
                    result["reply"] = "Here are your expenses:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_SHOPPING_LIST":
                    result["reply"] = "Here is your shopping list:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_GOALS":
                    result["reply"] = "Here are your goals:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_STUDY_PLANS":
                    result["reply"] = "Here are your study plans:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_MOODS":
                    result["reply"] = "Here are your moods:\n" + "\n".join(formatted)
                elif result["intent"] == "GET_MEMORIES":
                    result["reply"] = "Here is what I remember:\n" + "\n".join(formatted)

    # --- INSTANT MODULES ---
    elif result["intent"] in ["TRANSLATE_TEXT", "SUMMARIZE_TEXT", "GENERATE_FLASHCARDS", "GENERAL_CHAT"]:
        print("INSTANT MODULE: No backend needed. Just showing AI's answer!")

    save_chat_message(user_id, "assistant", result["reply"], token)

    return {
        "intent": result.get("intent"),
        "mood": result.get("mood"),
        "emoji": result.get("emoji"),
        "data": result.get("data"),
        "reply": result.get("reply")
    }


if __name__ == "__main__":
    print(">> Nova Brain is ready! Type 'exit' to quit.")

    test_email = "test@test.com"
    test_password = "TestPassword123"
    access_token, test_user_id = get_access_token(test_email, test_password)

    if not access_token:
        print("Exiting: Could not get access token.")
        exit()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            break

        result = get_ai_response(user_input, access_token, test_user_id)
        print("\n>> AI Output (JSON):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\n>> Nova says: {result['reply']}")