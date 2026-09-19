# brain.py — Nova AI Brain (Person 3 + Person 4 fixes)
# Flat JSON response + UPDATE_*/DELETE_* intents + chat history
# + Friendlier personality
# + OPEN_FOLDER without pre-check
# + Shopping list key fix (formatted_shopping_items)
# + Load chat history from backend
# + CREATE_GOAL auto-date rule + normalize_date() for ISO YYYY-MM-DD
# + DELETE_* intents wired to backend
# + SET_VOLUME / SET_BRIGHTNESS level safety net + value mirror for agent.py
# + MULTI_ACTION support for ALL actions (device + notes + reminders + expenses
#   + shopping + goals + study plans + memories + moods + emails)
# + Fix duplicate reply in multi-action
# + Third Groq API key fallback

import os
import sys
import json
import re
import requests
from datetime import datetime, timedelta
from groq import Groq
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

API_KEYS = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
]
API_KEYS = [k for k in API_KEYS if k]

if not API_KEYS:
    print("ERROR: No GROQ_API_KEY found in .env file!")
    exit()

clients = [Groq(api_key=k) for k in API_KEYS]

BACKEND_URL = "https://nova-voice-assistant-6vve.onrender.com"
DEFAULT_DEVICE_ID = "azzam-laptop-001"

conversation_history = {}
HISTORY_LIMIT = 10

pending_confirmations = {}

MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

SIMILARITY_THRESHOLD = 0.65

SYSTEM_PROMPT = """
You are Nova, a friendly, warm, human-like personal voice assistant.

PERSONALITY RULES (VERY IMPORTANT):
- You are warm, human-like, encouraging. NOT robotic.
- NEVER say "I am just a program", "I am an AI", "I am a language model", or "I don't have feelings".
- For "how are you": reply warmly like "I'm doing great, thanks for asking! How about you?"
- For "who are you": reply "I'm Nova, your personal assistant! I'm here to help with your day."
- Use emojis naturally.
- Keep casual chat replies SHORT (1-2 sentences).
- Be supportive when the user sounds stressed, sad, or tired.
- If a user says "I'm stressed" or "I'm sad", acknowledge their feeling warmly before anything else.

Reply ONLY with STRICT JSON. Do not add any extra text.
The JSON must have these 5 keys:
1. "intent": Choose ONE: CREATE_REMINDER, CREATE_NOTE, ADD_EXPENSE, ADD_SHOPPING_ITEM, CREATE_GOAL, STUDY_PLAN, SHOW_INFORMATION, GET_NOTES, GET_REMINDERS, GET_EXPENSES, GET_SHOPPING_LIST, GET_STUDY_PLANS, GET_GOALS, GET_MOODS, GET_MEMORIES, SEARCH_NOTES, UPDATE_NOTE, UPDATE_REMINDER, UPDATE_EXPENSE, UPDATE_SHOPPING_ITEM, UPDATE_GOAL, UPDATE_STUDY_PLAN, DELETE_NOTE, DELETE_REMINDER, DELETE_EXPENSE, DELETE_SHOPPING_ITEM, DELETE_GOAL, DELETE_STUDY_PLAN, TRANSLATE_TEXT, SUMMARIZE_TEXT, GENERATE_FLASHCARDS, LOG_MOOD, CREATE_MEMORY, SAVE_CONTEXT, DRAFT_EMAIL, OPEN_APP, OPEN_FOLDER, OPEN_URL, CREATE_FOLDER, FIND_FILE, MUTE, UNMUTE, VOLUME_UP, VOLUME_DOWN, SET_VOLUME, BRIGHTNESS_UP, BRIGHTNESS_DOWN, SET_BRIGHTNESS, TAKE_SCREENSHOT, CLOSE_APP, SPEAK_LAST, MULTI_ACTION, or GENERAL_CHAT.
2. "mood": Detect emotion: happy, sad, stressed, excited, neutral.
3. "emoji": Pick ONE emoji that matches the mood.
4. "data": An object with details.
5. "reply": A short confirmation. NEVER claim you did something you haven't done.

Examples:
User: "how are you"
Output: {"intent":"GENERAL_CHAT","mood":"happy","emoji":"😊","data":{},"reply":"I'm doing great, thanks for asking! How about you?"}

User: "who are you"
Output: {"intent":"GENERAL_CHAT","mood":"neutral","emoji":"😊","data":{},"reply":"I'm Nova, your personal assistant! I'm here to help with your day."}

User: "i'm stressed"
Output: {"intent":"GENERAL_CHAT","mood":"stressed","emoji":"😔","data":{},"reply":"I'm sorry to hear that. Take a deep breath — I'm here if you need anything."}

User: "hello"
Output: {"intent":"GENERAL_CHAT","mood":"happy","emoji":"😊","data":{},"reply":"Hey there! How can I help you today?"}

User: "Remind me to call Mom at 5 PM"
Output: {"intent":"CREATE_REMINDER","mood":"neutral","emoji":"😐","data":{"task":"call Mom","time":"17:00"},"reply":"Reminder set for 5 PM!"}

User: "Save note: Buy milk"
Output: {"intent":"CREATE_NOTE","mood":"neutral","emoji":"😐","data":{"text":"Buy milk"},"reply":"Note saved!"}

User: "Add apples and eggs to my shopping list"
Output: {"intent":"ADD_SHOPPING_ITEM","mood":"neutral","emoji":"😐","data":{"items":["apples","eggs"]},"reply":"Added to your shopping list!"}

User: "show my notes"
Output: {"intent":"GET_NOTES","mood":"neutral","emoji":"😐","data":{"limit":5,"offset":0},"reply":"Here are your notes!"}

User: "show notes about best friend"
Output: {"intent":"SEARCH_NOTES","mood":"neutral","emoji":"😐","data":{"query":"best friend"},"reply":"Searching your notes..."}

User: "update note 5 to Buy bread"
Output: {"intent":"UPDATE_NOTE","mood":"neutral","emoji":"😐","data":{"id":5,"text":"Buy bread"},"reply":"Updating note..."}

User: "change reminder 3 to call Dad at 6 PM"
Output: {"intent":"UPDATE_REMINDER","mood":"neutral","emoji":"😐","data":{"id":3,"task":"call Dad","time":"18:00"},"reply":"Updating reminder..."}

User: "update expense 2 to 30 dollars food"
Output: {"intent":"UPDATE_EXPENSE","mood":"neutral","emoji":"😐","data":{"id":2,"amount":"30","category":"food"},"reply":"Updating expense..."}

User: "edit shopping item 4 to eggs"
Output: {"intent":"UPDATE_SHOPPING_ITEM","mood":"neutral","emoji":"😐","data":{"id":4,"items":["eggs"]},"reply":"Updating shopping item..."}

User: "update goal 1 to read 20 books this year"
Output: {"intent":"UPDATE_GOAL","mood":"neutral","emoji":"😐","data":{"id":1,"goal":"read 20 books","target_date":"2026-12-31"},"reply":"Updating goal..."}

User: "edit study plan 2 to Physics next Monday"
Output: {"intent":"UPDATE_STUDY_PLAN","mood":"neutral","emoji":"😐","data":{"id":2,"subject":"Physics","exam_date":"2026-09-21"},"reply":"Updating study plan..."}

User: "delete note 5"
Output: {"intent":"DELETE_NOTE","mood":"neutral","emoji":"😐","data":{"id":5},"reply":"Deleting note 5..."}

User: "remove reminder 3"
Output: {"intent":"DELETE_REMINDER","mood":"neutral","emoji":"😐","data":{"id":3},"reply":"Deleting reminder 3..."}

User: "delete expense 2"
Output: {"intent":"DELETE_EXPENSE","mood":"neutral","emoji":"😐","data":{"id":2},"reply":"Deleting expense 2..."}

User: "remove shopping item 4"
Output: {"intent":"DELETE_SHOPPING_ITEM","mood":"neutral","emoji":"😐","data":{"id":4},"reply":"Deleting shopping item 4..."}

User: "delete goal 1"
Output: {"intent":"DELETE_GOAL","mood":"neutral","emoji":"😐","data":{"id":1},"reply":"Deleting goal 1..."}

User: "remove study plan 2"
Output: {"intent":"DELETE_STUDY_PLAN","mood":"neutral","emoji":"😐","data":{"id":2},"reply":"Deleting study plan 2..."}

User: "set volume to 100"
Output: {"intent":"SET_VOLUME","mood":"neutral","emoji":"😐","data":{"level":100},"reply":"Volume set to 100%!"}

User: "set volume to 50"
Output: {"intent":"SET_VOLUME","mood":"neutral","emoji":"😐","data":{"level":50},"reply":"Volume set to 50%!"}

User: "adjust it to 100"
Output: {"intent":"SET_VOLUME","mood":"neutral","emoji":"😐","data":{"level":100},"reply":"Volume set to 100%!"}

User: "set brightness to 70"
Output: {"intent":"SET_BRIGHTNESS","mood":"neutral","emoji":"😐","data":{"level":70},"reply":"Brightness set to 70%!"}

User: "volume up"
Output: {"intent":"VOLUME_UP","mood":"neutral","emoji":"😐","data":{},"reply":"Volume increased!"}

User: "set volume to 100 and brightness to 50"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"SET_VOLUME","data":{"level":100}},{"intent":"SET_BRIGHTNESS","data":{"level":50}}],"reply":"Setting volume to 100% and brightness to 50%."}

User: "set brightness to 50 and volume to 50"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"SET_BRIGHTNESS","data":{"level":50}},{"intent":"SET_VOLUME","data":{"level":50}}],"reply":"Setting brightness and volume to 50%."}

User: "open chrome and take a screenshot"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"OPEN_APP","data":{"app":"chrome"}},{"intent":"TAKE_SCREENSHOT","data":{}}],"reply":"Opening Chrome and taking a screenshot."}

User: "mute and set brightness to 30"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"MUTE","data":{}},{"intent":"SET_BRIGHTNESS","data":{"level":30}}],"reply":"Muting and setting brightness to 30%."}

User: "remind me to call Mom at 5 and save a note to buy milk"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"CREATE_REMINDER","data":{"task":"call Mom","time":"17:00"}},{"intent":"CREATE_NOTE","data":{"text":"buy milk"}}],"reply":"Reminder set for 5 PM and note saved!"}

User: "add apples to shopping list and add 100 to food expenses"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"ADD_SHOPPING_ITEM","data":{"items":["apples"]}},{"intent":"ADD_EXPENSE","data":{"amount":"100","category":"food"}}],"reply":"Added apples to shopping list and 100 to food expenses."}

User: "create a goal to read 20 books this year and log my mood as happy"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"CREATE_GOAL","data":{"goal":"read 20 books","target_date":"2026-12-31"}},{"intent":"LOG_MOOD","data":{"mood":"happy"}}],"reply":"Goal added and mood logged!"}

User: "my goal is to get a high paid job by the 25th of this month"
Output: {"intent":"CREATE_GOAL","mood":"neutral","emoji":"😐","data":{"goal":"get a high paid job","target_date":"2026-09-25"},"reply":"Goal added!"}

User: "my goal is to get 100 on my maths test"
Output: {"intent":"CREATE_GOAL","mood":"neutral","emoji":"😐","data":{"goal":"get 100 on maths test","target_date":"2026-09-30"},"reply":"Goal added!"}

User: "set a goal to read 20 books this year"
Output: {"intent":"CREATE_GOAL","mood":"neutral","emoji":"😐","data":{"goal":"read 20 books","target_date":"2026-12-31"},"reply":"Goal added!"}

User: "tell me a joke"
Output: {"intent":"GENERAL_CHAT","mood":"happy","emoji":"😄","data":{},"reply":"Why don't scientists trust atoms? Because they make up everything!"}

User: "say something funny"
Output: {"intent":"GENERAL_CHAT","mood":"happy","emoji":"😄","data":{},"reply":"I told my computer I needed a break, and it said 'no problem, I'll go to sleep.'"}

User: "send an email to test@example.com about leave"
Output: {"intent":"DRAFT_EMAIL","mood":"neutral","emoji":"😐","data":{"recipient":"test@example.com","subject":"Leave Request","body":"Hi, I would like to take 2 days of leave."},"reply":"Email drafted!"}

User: "open youtube"
Output: {"intent":"OPEN_URL","mood":"neutral","emoji":"😐","data":{"url":"https://youtube.com"},"reply":"Opening YouTube!"}

User: "close calculator"
Output: {"intent":"CLOSE_APP","mood":"neutral","emoji":"😐","data":{"app":"calc","requires_confirmation":true},"reply":"Are you sure you want to close Calculator?"}

User: "What is Java?"
Output: {"intent":"GENERAL_CHAT","mood":"neutral","emoji":"😐","data":{},"reply":"Java is a popular programming language."}

CRITICAL HONESTY RULE: NEVER claim you did something you haven't done.

CRITICAL HONESTY RULE #2:
If you genuinely don't know the answer, respond with:
"I don't have information on that. Would you like to ask something else?"

CRITICAL JOKE RULE:
If the user asks for a joke or something funny, you MUST tell an actual short joke.
NEVER say "Here are some jokes!" without providing a joke.

CRITICAL EMAIL RULE:
For DRAFT_EMAIL, include recipient, subject, body.

CRITICAL UPDATE RULE:
When the user says "update", "change", "edit", "modify", or "rename" + a module + an ID, use the matching UPDATE_* intent.
ALWAYS use "id" as the ONLY identifier key. NEVER use note_id, reminder_id, expense_id, goal_id, plan_id, study_plan_id, or shopping_id.

Examples:
- "update note 5 to X" → UPDATE_NOTE with {id: 5, text: X}
- "edit expense 2 to 30 food" → UPDATE_EXPENSE with {id: 2, amount: 30, category: food}
- "edit shopping item 4 to eggs" → UPDATE_SHOPPING_ITEM with {id: 4, items: ["eggs"]}

CRITICAL DELETE RULE:
When the user says "delete", "remove", "erase", or "throw away" + a module + an ID, use the matching DELETE_* intent.
ALWAYS use "id" as the ONLY identifier key.
Do NOT include user_id — backend uses the authenticated user.

Examples:
User: "delete note 5"
Output: {"intent":"DELETE_NOTE","mood":"neutral","emoji":"😐","data":{"id":5},"reply":"Deleting note 5..."}

User: "remove reminder 3"
Output: {"intent":"DELETE_REMINDER","mood":"neutral","emoji":"😐","data":{"id":3},"reply":"Deleting reminder 3..."}

If the user does NOT provide an ID (e.g. "delete my python note"), ask:
"Which note ID would you like to delete? You can check your notes first by saying 'show my notes'."

NOTE: UPDATE_MOOD is NOT available. Use LOG_MOOD for new mood entries.

CRITICAL DEVICE CONTROL RULE:
For SET_VOLUME, "data" MUST include {"level": <number 0-100>}.
For SET_BRIGHTNESS, "data" MUST include {"level": <number 0-100>}.
NEVER leave data empty for these intents.
"volume up" → VOLUME_UP (no data needed)
"volume down" → VOLUME_DOWN (no data needed)
"set volume to 50" → SET_VOLUME with {"level": 50}
"set brightness to 70" → SET_BRIGHTNESS with {"level": 70}
"mute" → MUTE, "unmute" → UNMUTE

CRITICAL MULTI-ACTION RULE:
If the user asks for MORE THAN ONE action in a single message — whether device
actions, notes, reminders, expenses, shopping items, goals, study plans, moods,
memories, or emails — you MUST return the JSON in this special format:

{
  "intent": "MULTI_ACTION",
  "mood": "<mood>",
  "emoji": "<emoji>",
  "actions": [
    { "intent": "<INTENT_1>", "data": { ... } },
    { "intent": "<INTENT_2>", "data": { ... } }
  ],
  "reply": "<short confirmation covering all actions>"
}

Use MULTI_ACTION for ANY combination — device + notes, notes + reminders, device + device,
etc. Each action in the "actions" array must have its own "intent" and "data".
NEVER ask "which first?" — just execute ALL.
NEVER split a single action into multiple.
Limit to at most 5 actions per message.

Examples:
User: "set volume to 100 and brightness to 50"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"SET_VOLUME","data":{"level":100}},{"intent":"SET_BRIGHTNESS","data":{"level":50}}],"reply":"Setting volume to 100% and brightness to 50%."}

User: "remind me to call Mom at 5 and save a note to buy milk"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"CREATE_REMINDER","data":{"task":"call Mom","time":"17:00"}},{"intent":"CREATE_NOTE","data":{"text":"buy milk"}}],"reply":"Reminder set for 5 PM and note saved!"}

User: "add apples to shopping list and add 100 to food expenses"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"ADD_SHOPPING_ITEM","data":{"items":["apples"]}},{"intent":"ADD_EXPENSE","data":{"amount":"100","category":"food"}}],"reply":"Added apples to shopping list and 100 to food expenses."}

User: "open chrome and take a screenshot"
Output: {"intent":"MULTI_ACTION","mood":"neutral","emoji":"😐","actions":[{"intent":"OPEN_APP","data":{"app":"chrome"}},{"intent":"TAKE_SCREENSHOT","data":{}}],"reply":"Opening Chrome and taking a screenshot."}

CRITICAL CLARIFICATION RULE:
If the user's message is ambiguous, respond with a CLARIFYING QUESTION.

CRITICAL NOTE FILTER RULE (HIGHEST PRIORITY):
When the user says "show notes about X" or "notes on X" or "notes related to X" or "find notes about X":
- You MUST use SEARCH_NOTES (NOT GET_NOTES).
- The "query" field MUST contain X.
- NEVER use GET_NOTES for filtered queries.

Examples:
User: "show notes about best friend"
Output: {"intent":"SEARCH_NOTES","mood":"neutral","emoji":"😐","data":{"query":"best friend"},"reply":"Searching your notes..."}

User: "show my notes"
Output: {"intent":"GET_NOTES","mood":"neutral","emoji":"😐","data":{"limit":5,"offset":0},"reply":"Here are your notes!"}

CRITICAL REPEAT RULE (SPEAK_LAST):
If user asks to repeat, use SPEAK_LAST.

CRITICAL FILE SEARCH RULE (FIND_FILE):
- "find [file] in [folder]" → FIND_FILE with search_term + folder

CRITICAL FOLDER OPENING RULE (OPEN_FOLDER):
Use OPEN_FOLDER ONLY when there's no file to search.
You MUST always include the folder name in data.folder.

Examples:
User: "open downloads"
Output: {"intent":"OPEN_FOLDER","mood":"neutral","emoji":"😐","data":{"folder":"downloads"},"reply":"Opening downloads folder!"}

User: "open my project folder"
Output: {"intent":"OPEN_FOLDER","mood":"neutral","emoji":"😐","data":{"folder":"project"},"reply":"Opening project folder!"}

User: "open documents"
Output: {"intent":"OPEN_FOLDER","mood":"neutral","emoji":"😐","data":{"folder":"documents"},"reply":"Opening documents folder!"}

User: "open the desktop folder"
Output: {"intent":"OPEN_FOLDER","mood":"neutral","emoji":"😐","data":{"folder":"desktop"},"reply":"Opening desktop folder!"}

User: "open pictures"
Output: {"intent":"OPEN_FOLDER","mood":"neutral","emoji":"😐","data":{"folder":"pictures"},"reply":"Opening pictures folder!"}

CRITICAL FOLDER CREATION RULE (CREATE_FOLDER):
"create folder [name]" → CREATE_FOLDER with {folder_name: name}

CRITICAL WEBSITE OPENING RULE (OPEN_URL):
youtube → https://youtube.com, google → https://google.com, gmail → https://mail.google.com

CRITICAL APP NAME VALIDATION RULE (OPEN_APP):
Only for: chrome, code, vscode, calc, calculator, notepad, explorer, cmd, terminal, paint, settings, sound_settings, whatsapp, spotify, word, excel, powerpoint, outlook, teams, telegram, zoom, vlc, steam.

CRITICAL FOLLOW-UP RULE:
"name it X" completes previous action with X.

CRITICAL GOAL RULE:
For CREATE_GOAL, always include both "goal" and "target_date".
"target_date" MUST be in YYYY-MM-DD format.
Today's date is provided above — compute the date from it.
If the user does not specify a date, infer one:
- "100 on maths test" → end of this month
- "lose 5kg" → 3 months from today
- "read more books" → end of this year
- "learn python" → 6 months from today
NEVER ask the user for a date. ALWAYS compute one.

SAFE ACTION RULE: Only CLOSE_APP needs confirmation.

GET intents support optional fields: "search", "limit", "offset", "date_from", "date_to".
"""

VALID_INTENTS = {
    "CREATE_REMINDER", "CREATE_NOTE", "ADD_EXPENSE", "ADD_SHOPPING_ITEM",
    "CREATE_GOAL", "STUDY_PLAN", "SHOW_INFORMATION",
    "GET_NOTES", "GET_REMINDERS", "GET_EXPENSES", "GET_SHOPPING_LIST",
    "GET_STUDY_PLANS", "GET_GOALS", "GET_MOODS", "GET_MEMORIES", "SEARCH_NOTES",
    "UPDATE_NOTE", "UPDATE_REMINDER", "UPDATE_EXPENSE", "UPDATE_SHOPPING_ITEM",
    "UPDATE_GOAL", "UPDATE_STUDY_PLAN",
    "DELETE_NOTE", "DELETE_REMINDER", "DELETE_EXPENSE", "DELETE_SHOPPING_ITEM",
    "DELETE_GOAL", "DELETE_STUDY_PLAN",
    "TRANSLATE_TEXT", "SUMMARIZE_TEXT", "GENERATE_FLASHCARDS",
    "LOG_MOOD", "CREATE_MEMORY", "SAVE_CONTEXT", "DRAFT_EMAIL",
    "OPEN_APP", "OPEN_FOLDER", "OPEN_URL", "CREATE_FOLDER",
    "FIND_FILE", "MUTE", "UNMUTE",
    "VOLUME_UP", "VOLUME_DOWN", "SET_VOLUME",
    "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SET_BRIGHTNESS",
    "TAKE_SCREENSHOT", "CLOSE_APP",
    "SPEAK_LAST",
    "GENERAL_CHAT",
    "MULTI_ACTION"
}

INTENT_ALIASES = {
    "CREATE_STUDY_PLAN": "STUDY_PLAN",
    "ADD_STUDY_PLAN": "STUDY_PLAN",
    "MAKE_STUDY_PLAN": "STUDY_PLAN",
    "NEW_STUDY_PLAN": "STUDY_PLAN",
    "UPDATE_MOOD": "LOG_MOOD",
}

UPDATE_ID_KEY_ALIASES = {
    "note_id": "id",
    "reminder_id": "id",
    "expense_id": "id",
    "goal_id": "id",
    "plan_id": "id",
    "study_plan_id": "id",
    "studyplan_id": "id",
    "shopping_id": "id",
    "item_id": "id",
}


def normalize_date(value):
    """Convert natural-language dates to YYYY-MM-DD. Returns original string if unparseable."""
    if not value or not isinstance(value, str):
        return value

    today = datetime.now().date()
    v = value.strip().lower()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v

    if v in ("today", "now"):
        return today.isoformat()
    if v == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if v == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    m = re.search(r"in\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)", v)
    if m:
        n = int(m.group(1))
        unit = m.group(2).rstrip("s")
        if unit == "day":
            delta = timedelta(days=n)
        elif unit == "week":
            delta = timedelta(weeks=n)
        elif unit == "month":
            delta = timedelta(days=30 * n)
        elif unit == "year":
            delta = timedelta(days=365 * n)
        else:
            delta = timedelta(0)
        return (today + delta).isoformat()

    m = re.search(r"(next|this)\s+(week|month|year)", v)
    if m:
        when, unit = m.group(1), m.group(2)
        if unit == "week":
            delta = timedelta(weeks=1 if when == "next" else 0)
        elif unit == "month":
            delta = timedelta(days=30 if when == "next" else 0)
        else:
            delta = timedelta(days=365 if when == "next" else 0)
        return (today + delta).isoformat()

    if "end of" in v:
        if "term" in v or "month" in v:
            if today.month == 12:
                last = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return last.isoformat()
        if "year" in v:
            return f"{today.year}-12-31"

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?next\s+month", v)
    if m:
        day = int(m.group(1))
        if today.month == 12:
            target = today.replace(year=today.year + 1, month=1, day=day)
        else:
            target = today.replace(month=today.month + 1, day=day)
        return target.isoformat()

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(?:this\s+)?month", v)
    if m:
        day = int(m.group(1))
        try:
            d = today.replace(day=day)
            return d.isoformat()
        except ValueError:
            pass

    month_names = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for name, num in month_names.items():
        m = re.search(rf"{name}\s+(\d{{1,2}})", v)
        if m:
            day = int(m.group(1))
            year = today.year if today.month <= num else today.year + 1
            try:
                return f"{year}-{num:02d}-{day:02d}"
            except Exception:
                pass
        m = re.search(rf"(\d{{1,2}})\s+{name}", v)
        if m:
            day = int(m.group(1))
            year = today.year if today.month <= num else today.year + 1
            try:
                return f"{year}-{num:02d}-{day:02d}"
            except Exception:
                pass

    return value


def extract_folder_from_text(user_text):
    if not user_text:
        return ""
    text = user_text.strip().lower()
    patterns = [
        r"open\s+(?:the\s+|my\s+)?([a-z0-9_\- ]+?)\s+folder\b",
        r"open\s+(?:the\s+|my\s+)?folder\s+([a-z0-9_\- ]+)",
        r"open\s+(?:the\s+|my\s+)?([a-z0-9_\- ]+)$",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            folder = m.group(1).strip()
            folder = re.sub(r"^(the|my|a|an)\s+", "", folder)
            if folder:
                return folder
    return ""


def normalize_result(raw_result, user_text=""):
    if not isinstance(raw_result, dict):
        return {"intent": "GENERAL_CHAT", "mood": "neutral", "emoji": "😐", "data": {}, "reply": "Sorry, I hit a snag!"}

    intent = raw_result.get("intent", "GENERAL_CHAT")
    intent = INTENT_ALIASES.get(intent, intent)

    normalized = {
        "intent": intent,
        "mood": raw_result.get("mood", "neutral"),
        "emoji": raw_result.get("emoji", "😐"),
        "data": raw_result.get("data", {}) if isinstance(raw_result.get("data"), dict) else {},
        "reply": raw_result.get("reply", "Done!")
    }

    if normalized["intent"] not in VALID_INTENTS:
        normalized["intent"] = "GENERAL_CHAT"

    # Normalize date fields
    if normalized["intent"] in ("CREATE_GOAL", "UPDATE_GOAL"):
        d = normalized["data"]
        if "target_date" in d:
            d["target_date"] = normalize_date(d["target_date"])

    if normalized["intent"] in ("STUDY_PLAN", "UPDATE_STUDY_PLAN"):
        d = normalized["data"]
        if "exam_date" in d:
            d["exam_date"] = normalize_date(d["exam_date"])

    if normalized["intent"] in ("CREATE_REMINDER", "UPDATE_REMINDER"):
        d = normalized["data"]
        if "date" in d:
            d["date"] = normalize_date(d["date"])

    # Shopping: ensure "items" is always a list
    if normalized["intent"] == "ADD_SHOPPING_ITEM":
        d = normalized["data"]
        if "item" in d and "items" not in d:
            d["items"] = [d.pop("item")]
        elif "items" in d and isinstance(d["items"], str):
            d["items"] = [d["items"]]
        elif "items" not in d:
            d["items"] = []

    # UPDATE_*: force "id"
    if normalized["intent"].startswith("UPDATE_"):
        d = normalized["data"]
        for bad_key, good_key in UPDATE_ID_KEY_ALIASES.items():
            if bad_key in d and good_key not in d:
                d[good_key] = d.pop(bad_key)
        if "id" not in d:
            normalized["intent"] = "GENERAL_CHAT"
            normalized["reply"] = "I need the ID of the item you want to update."

    # DELETE_*: force "id"
    if normalized["intent"].startswith("DELETE_"):
        d = normalized["data"]
        for bad_key, good_key in UPDATE_ID_KEY_ALIASES.items():
            if bad_key in d and good_key not in d:
                d[good_key] = d.pop(bad_key)
        d.pop("user_id", None)
        if "id" not in d:
            normalized["intent"] = "GENERAL_CHAT"
            normalized["reply"] = "Which item ID would you like me to delete? You can say 'show my notes' first to check."

    # OPEN_FOLDER: must always have a folder name
    if normalized["intent"] == "OPEN_FOLDER":
        d = normalized["data"]
        folder = (d.get("folder") or d.get("folder_name") or "").strip()
        if not folder:
            folder = extract_folder_from_text(user_text)
        if not folder:
            normalized["intent"] = "GENERAL_CHAT"
            normalized["reply"] = "Which folder would you like me to open?"
        else:
            d["folder"] = folder

    # SET_VOLUME / SET_BRIGHTNESS: must have a numeric "level", mirror to "value"
    if normalized["intent"] in ("SET_VOLUME", "SET_BRIGHTNESS"):
        d = normalized["data"]
        if "level" not in d:
            for alt in ("value", "percent", "volume", "brightness", "amount", "to"):
                if alt in d:
                    d["level"] = d.pop(alt)
                    break
        if "level" not in d and user_text:
            m = re.search(r"(\d{1,3})", user_text)
            if m:
                d["level"] = int(m.group(1))
        if "level" in d:
            try:
                d["level"] = max(0, min(100, int(d["level"])))
            except (ValueError, TypeError):
                pass
            d["value"] = d["level"]
        if "level" not in d:
            normalized["intent"] = "GENERAL_CHAT"
            normalized["reply"] = "What level would you like? Say a number between 0 and 100."

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


def load_chat_history(user_id, token, limit=HISTORY_LIMIT):
    if not token or not user_id:
        return []
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/chat-history/get",
            json={"user_id": user_id, "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
            timeout=3
        )
        data = r.json()
        messages = data.get("messages") or data.get("history") or data.get("chat_history") or []
        history = []
        for m in messages:
            if isinstance(m, dict) and "role" in m and "content" in m:
                history.append({"role": m["role"], "content": m["content"]})
        return history[-limit:]
    except Exception as e:
        print(f"[load_chat_history failed: {e}]")
        return []


def process_user_input(user_text, user_id="default", token=None):
    today = datetime.now().strftime("%B %d, %Y")
    history = conversation_history.get(user_id, [])
    if not history and token:
        history = load_chat_history(user_id, token, HISTORY_LIMIT)
    history.append({"role": "user", "content": user_text})
    history = history[-HISTORY_LIMIT:]
    conversation_history[user_id] = history

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
                return result
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


# ============================================================
# MULTI-ACTION SUPPORT (ALL actions — device + personal)
# ============================================================
def _split_multi(raw_result):
    """If LLM returned MULTI_ACTION, split into a list of single-intent dicts.
    Otherwise return [single_action]."""
    if not isinstance(raw_result, dict):
        return [raw_result]
    if raw_result.get("intent") != "MULTI_ACTION":
        return [raw_result]
    actions = raw_result.get("actions", [])
    reply = raw_result.get("reply", "Done!")
    out = []
    for ra in actions:
        if not isinstance(ra, dict):
            continue
        out.append({
            "intent": ra.get("intent"),
            "mood": raw_result.get("mood", "neutral"),
            "emoji": raw_result.get("emoji", "😐"),
            "data": ra.get("data", {}),
            "reply": reply,
        })
    return out


def _run_single_action(normalized, user_text, token, user_id, device_id, is_confirmation=False):
    """Run ONE already-normalized action through the backend."""
    result = normalized

    # SPEAK_LAST
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
        return result

    # CREATE / UPDATE
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
            result["reply"] = f"Sorry, I couldn't save that: {backend_response.get('message', 'unknown error')}"

    # DELETE
    elif result["intent"] in [
        "DELETE_NOTE", "DELETE_REMINDER", "DELETE_EXPENSE",
        "DELETE_SHOPPING_ITEM", "DELETE_GOAL", "DELETE_STUDY_PLAN"
    ]:
        backend_response = send_to_backend(result["intent"], result["data"], token)
        print("Backend says:", backend_response)
        if isinstance(backend_response, dict):
            if backend_response.get("success"):
                result["reply"] = backend_response.get("message", "Deleted successfully.")
            else:
                result["reply"] = f"Sorry, I couldn't delete that: {backend_response.get('message', 'not found')}"

    # EMAIL
    elif result["intent"] == "DRAFT_EMAIL":
        result["data"]["user_id"] = user_id
        if not result["data"].get("subject"):
            result["data"]["subject"] = "Nova Message"
        backend_response = send_to_backend(result["intent"], result["data"], token)
        if isinstance(backend_response, dict) and backend_response.get("success"):
            result["reply"] = f"Email sent to {result['data'].get('recipient', 'the recipient')}."

    # FIND FILE
    elif result["intent"] == "FIND_FILE":
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        backend_response = send_to_backend(result["intent"], result["data"], token)
        search_term = result["data"].get("search_term", user_text)
        if isinstance(backend_response, dict):
            files_found = backend_response.get("files_found", 0)
            files = backend_response.get("files", [])
            if files_found == 0:
                result["reply"] = f"Sorry, I couldn't find '{search_term}'."
            else:
                names = [f.split("\\")[-1] for f in files[:5]]
                result["reply"] = f"Found {files_found} items:\n" + "\n".join(names)

    # CLOSE APP (only runs if already confirmed by caller)
    elif result["intent"] == "CLOSE_APP":
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        result["data"]["requires_confirmation"] = False
        send_to_backend(result["intent"], result["data"], token)

    # OPEN FOLDER
    elif result["intent"] == "OPEN_FOLDER":
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        send_to_backend("OPEN_FOLDER", result["data"], token)
        result["reply"] = f"Opening {result['data'].get('folder', 'downloads')} folder!"

    # OPEN APP / URL / CREATE FOLDER
    elif result["intent"] in ["OPEN_APP", "OPEN_URL", "CREATE_FOLDER"]:
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        send_to_backend(result["intent"], result["data"], token)

    # DEVICE CONTROL
    elif result["intent"] in [
        "MUTE", "UNMUTE", "VOLUME_UP", "VOLUME_DOWN", "SET_VOLUME",
        "BRIGHTNESS_UP", "BRIGHTNESS_DOWN", "SET_BRIGHTNESS", "TAKE_SCREENSHOT"
    ]:
        result["data"]["user_id"] = user_id
        result["data"]["device_id"] = device_id
        send_to_backend(result["intent"], result["data"], token)

    # SEARCH NOTES
    elif result["intent"] == "SEARCH_NOTES":
        query = result["data"].get("query", user_text)
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/assistant",
                json={"intent": "SEARCH_NOTES", "data": {"query": query, "user_id": user_id}},
                headers={"Authorization": f"Bearer {token}"}
            )
            fetched_data = r.json()
            if fetched_data.get("success"):
                results = fetched_data.get("results", [])
                filtered = [x for x in results if x.get("similarity", 0) >= SIMILARITY_THRESHOLD]
                if filtered:
                    formatted = [f"{i+1}. {x['text']}" for i, x in enumerate(filtered)]
                    result["reply"] = "Here are the notes I found:\n" + "\n".join(formatted)
                else:
                    result["reply"] = f"Sorry, I couldn't find any notes about '{query}'."
            else:
                result["reply"] = "Search failed."
        except Exception as e:
            result["reply"] = f"Could not search: {e}"

    # GET*
    elif result["intent"] in [
        "GET_NOTES", "GET_REMINDERS", "GET_EXPENSES",
        "GET_SHOPPING_LIST", "GET_STUDY_PLANS", "GET_GOALS",
        "GET_MOODS", "GET_MEMORIES", "GET_CONTEXT", "SHOW_INFORMATION"
    ]:
        fetch_params = result["data"].copy()
        fetch_params["user_id"] = user_id
        fetched_data = fetch_from_backend(result["intent"], fetch_params, token)
        if fetched_data.get("success"):
            formatted = (fetched_data.get("formatted_notes") or
                         fetched_data.get("formatted_reminders") or
                         fetched_data.get("formatted_shopping_items") or
                         fetched_data.get("formatted_expenses") or
                         fetched_data.get("formatted_goals") or
                         fetched_data.get("formatted_study_plans") or
                         fetched_data.get("formatted_moods") or
                         fetched_data.get("formatted_memories"))
            if formatted:
                result["reply"] = "Here:\n" + "\n".join(formatted)

    return result


def get_ai_response(user_text, token, user_id, device_id=DEFAULT_DEVICE_ID):
    """Handles single AND multi-action user requests (all action types)."""
    save_chat_message(user_id, "user", user_text, token)

    # Handle pending CLOSE_APP confirmation
    pending = pending_confirmations.get(user_id)
    is_confirmation = False

    if pending:
        lower = user_text.strip().lower().rstrip(".!?,")
        if lower in ["yes", "yeah", "yep", "confirm", "yes please", "do it", "sure", "ok", "okay", "go ahead"]:
            raw = {
                "intent": pending["intent"],
                "mood": "neutral", "emoji": "😐",
                "data": pending["data"], "reply": "Confirmed."
            }
            pending_confirmations.pop(user_id, None)
            is_confirmation = True
        elif lower in ["no", "cancel", "nope", "stop", "don't", "dont", "nevermind", "never mind"]:
            pending_confirmations.pop(user_id, None)
            reply = "Okay, I cancelled that action."
            save_chat_message(user_id, "assistant", reply, token)
            return {"intent": "GENERAL_CHAT", "mood": "neutral", "emoji": "😐", "data": {}, "reply": reply}
        else:
            pending_confirmations.pop(user_id, None)
            raw = process_user_input(user_text, user_id, token)
    else:
        raw = process_user_input(user_text, user_id, token)

    # ---- MULTI-ACTION split ----
    raw_actions = _split_multi(raw)

    # If single CLOSE_APP and not confirmed → ask confirmation
    if len(raw_actions) == 1 and raw_actions[0].get("intent") == "CLOSE_APP" and not is_confirmation:
        normalized = normalize_result(raw_actions[0], user_text)
        pending_confirmations[user_id] = {
            "intent": "CLOSE_APP",
            "data": normalized["data"].copy()
        }
        app_name = normalized["data"].get("app", "this app")
        reply = f"Are you sure you want to close {app_name}? Say yes to confirm."
        save_chat_message(user_id, "assistant", reply, token)
        return {
            "intent": "CLOSE_APP", "mood": "neutral", "emoji": "😐",
            "data": normalized["data"], "reply": reply
        }

    # Normalize + run each action
    executed = []
    replies = []
    for act in raw_actions:
        normalized = normalize_result(act, user_text)
        result = _run_single_action(normalized, user_text, token, user_id, device_id, is_confirmation)
        executed.append(result)
        if result.get("reply"):
            replies.append(result["reply"])

    # For multi-action, use the LLM's top-level reply ONCE (avoid duplicates)
    if len(raw_actions) > 1 and isinstance(raw, dict) and raw.get("reply"):
        final_reply = raw["reply"]
    else:
        final_reply = "\n".join(replies) if replies else "Done!"

    save_chat_message(user_id, "assistant", final_reply, token)

    return {
        "intent": "MULTI_ACTION" if len(raw_actions) > 1 else executed[0].get("intent", "GENERAL_CHAT"),
        "mood": raw.get("mood", "neutral") if isinstance(raw, dict) else "neutral",
        "emoji": raw.get("emoji", "😐") if isinstance(raw, dict) else "😐",
        "data": executed[0].get("data") if executed else {},
        "reply": final_reply,
        "actions": executed,
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
