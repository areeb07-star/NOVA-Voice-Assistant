# bridge.py — Connects frontend to brain.py
# Multi-user + CORS-ready + Render-ready

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from brain import get_ai_response, get_access_token
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================
# CORS — allows local + any Vercel URL
# ============================================================
CORS(
    app,
    origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ],
    origin_regex=r"^https://.*\.vercel\.app$",
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


# ============================================================
# FALLBACK ACCOUNT (used only if browser doesn't send a token)
# ============================================================
FALLBACK_EMAIL = "test@test.com"
FALLBACK_PASSWORD = "TestPassword123"

print("Logging in to backend (fallback account)...")
FALLBACK_TOKEN, FALLBACK_USER_ID = get_access_token(FALLBACK_EMAIL, FALLBACK_PASSWORD)

if not FALLBACK_TOKEN:
    print("WARNING: Could not get fallback token — bridge will still start.")
    FALLBACK_TOKEN = ""
    FALLBACK_USER_ID = ""
else:
    print(f"Fallback logged in! User ID: {FALLBACK_USER_ID}")


# ============================================================
# GROQ CLIENT for /api/summarize
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY missing in .env — summarize will fail")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ============================================================
# /api/process
# ============================================================
@app.route('/api/process', methods=['POST', 'OPTIONS'])
def process_command():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(force=True) or {}
        user_text = (data.get('text') or data.get('user_text') or '').strip()
        device_id = data.get('device_id')

        browser_token = data.get('access_token') or data.get('token')
        browser_user_id = data.get('user_id')

        if browser_token and browser_user_id and browser_user_id != 'nova_user':
            TOKEN = browser_token
            USER_ID = browser_user_id
            print(f">> Using BROWSER user_id: {USER_ID}")
        else:
            TOKEN = FALLBACK_TOKEN
            USER_ID = FALLBACK_USER_ID
            print(f">> Using FALLBACK user_id: {USER_ID}")

        if not user_text:
            return jsonify({'success': False, 'error': 'No text'}), 400

        if not device_id:
            device_id = "NO_DEVICE"
            print("⚠️ WARNING: Frontend did not send device_id!")

        print(f"Received [{device_id}]: {user_text}")

        result = get_ai_response(user_text, TOKEN, USER_ID, device_id)

        print(f"AI Response: {result.get('reply')}")

        return jsonify({
            'success': True,
            'response': result.get('reply', 'No response'),
            'reply': result.get('reply', 'No response'),
            'intent': result.get('intent'),
            'emoji': result.get('emoji'),
            'mood': result.get('mood'),
            'data': result.get('data', {})
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# /api/health
# ============================================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'Nova bridge running!',
        'fallback_user': FALLBACK_USER_ID or None,
    })


# ============================================================
# /api/summarize
# ============================================================
@app.route('/api/summarize', methods=['POST', 'OPTIONS'])
def summarize_file():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        if not groq_client:
            return jsonify({'success': False, 'error': 'GROQ_API_KEY missing in .env'}), 500

        data = request.get_json(force=True) or {}
        text = (data.get('text') or '').strip()

        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        print(f"=== SUMMARIZE: {len(text)} chars ===")

        summary_prompt = (
            "You are a helpful assistant. Summarize the following text in 3-5 sentences. "
            "Be clear and concise. Output ONLY the summary, no extra commentary.\n\n"
            f"TEXT:\n{text}"
        )

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.3
        )

        summary = response.choices[0].message.content.strip()
        print(f"=== SUMMARY: {summary[:200]}... ===")

        return jsonify({'success': True, 'response': summary, 'summary': summary})

    except Exception as e:
        print(f"Summarize error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# START — works locally AND on Render
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Nova Bridge Starting on port {port}...")
    print("Endpoints: /api/process, /api/health, /api/summarize")
    app.run(host='0.0.0.0', port=port, debug=False)