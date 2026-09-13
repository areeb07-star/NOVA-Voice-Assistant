/* ============================================
   NOVA - Voice Module (Person 4)
   Speech Recognition + TTS + AI Brain
   ============================================ */

const CONFIG = {
  AI_URL: 'http://127.0.0.1:5000/api/process'
};

const VOICE_STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  THINKING: "thinking",
  SPEAKING: "speaking"
};

let currentVoiceState = VOICE_STATES.IDLE;
let isListening = false;
let isStartingUp = false;
let lastStopTime = 0;
let recognition = null;
let currentUtterance = null;

// ============================================================
// LANGUAGE DETECTION
// ============================================================
function detectLanguage(text) {
  const hindiWords = ['है','मैं','तुम','आप','क्या','कैसे','मेरा','तेरा','नाम','हाँ','नहीं'];
  const urduWords  = ['ہے','میں','تم','آپ','کیا','کیسے','میرا','تیرا','نام','ہاں','نہیں'];
  const tamilWords = ['என்','நீ','உங்கள்','என்ன','எப்படி','பெயர்'];
  const teluguWords= ['నా','నీ','మీరు','ఏమి','ఎలా','పేరు'];
  const malayalamWords=['എന്റെ','നിങ്ങൾ','എന്ത്','എങ്ങനെ','പേര്'];
  const kannadaWords=['ನನ್ನ','ನೀವು','ಏನು','ಹೇಗೆ','ಹೆಸರು'];
  const bengaliWords=['আমার','তোমার','আপনি','কি','কেমন','নাম'];
  const marathiWords=['माझं','तुझं','तुम्ही','काय','कसं','नाव'];
  const gujaratiWords=['મારું','તમારું','શું','કેવી','નામ'];
  const punjabiWords=['ਮੇਰਾ','ਤੇਰਾ','ਤੁਸੀਂ','ਕੀ','ਕਿਵੇਂ','ਨਾਮ'];
  const t = text.toLowerCase();
  if (hindiWords.some(w => t.includes(w))) return 'hi-IN';
  if (urduWords.some(w => t.includes(w))) return 'ur-PK';
  if (tamilWords.some(w => t.includes(w))) return 'ta-IN';
  if (teluguWords.some(w => t.includes(w))) return 'te-IN';
  if (malayalamWords.some(w => t.includes(w))) return 'ml-IN';
  if (kannadaWords.some(w => t.includes(w))) return 'kn-IN';
  if (bengaliWords.some(w => t.includes(w))) return 'bn-IN';
  if (marathiWords.some(w => t.includes(w))) return 'mr-IN';
  if (gujaratiWords.some(w => t.includes(w))) return 'gu-IN';
  if (punjabiWords.some(w => t.includes(w))) return 'pa-IN';
  return 'en-GB';
}

function getBestVoiceForLanguage(lang) {
  const voices = window.speechSynthesis.getVoices();
  const voiceMap = {
    'en-GB': ['Google UK English Female','Microsoft Libby','Microsoft Sonia','Microsoft Hazel','Kate','Serena'],
    'en-US': ['Microsoft Zira','Google US English','Samantha'],
    'hi-IN': ['Google हिन्दी','Microsoft Swara','Microsoft Kalpana'],
    'ur-PK': ['Google اردو'],
    'ta-IN': ['Google தமிழ்'],
    'te-IN': ['Google తెలుగు'],
    'ml-IN': ['Google മലയാളം'],
    'kn-IN': ['Google ಕನ್ನಡ'],
    'bn-IN': ['Google বাংলা'],
    'mr-IN': ['Google मराठी'],
    'gu-IN': ['Google ગુજરાતી'],
    'pa-IN': ['Google ਪੰਜਾਬੀ']
  };
  const preferred = voiceMap[lang] || voiceMap['en-GB'];
  for (const name of preferred) {
    const match = voices.find(v => v.name.includes(name));
    if (match) return match;
  }
  return voices.find(v => v.lang === lang) ||
         voices.find(v => v.lang.startsWith(lang.split('-')[0])) ||
         voices.find(v => v.lang === 'en-GB') ||
         voices.find(v => v.lang.startsWith('en')) ||
         voices[0];
}

// ============================================================
// SPEECH RECOGNITION
// ============================================================
function startListening() {
  if (isListening || isStartingUp) return;
  if (Date.now() - lastStopTime < 600) return;

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('[NOVA] Use Chrome browser for voice.');
    return;
  }

  try {
    recognition = new SR();
  } catch (e) {
    console.error('[NOVA] Recognition error:', e);
    return;
  }

  recognition.lang = 'en-IN';
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = function() {
    isStartingUp = false;
    isListening = true;
    updateVoiceStatus(VOICE_STATES.LISTENING);
    console.log('[NOVA] Listening started');
  };

  recognition.onresult = function(event) {
    let finalText = '';
    let interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += transcript;
      else interimText += transcript;
    }

    if (interimText) {
      const orbText = document.getElementById("orbStatusText");
      if (orbText) orbText.textContent = '🎤 ' + interimText;
    }

    if (finalText) {
      try { recognition.stop(); } catch (e) {}
      handleVoiceInput(finalText.trim());
    }
  };

  recognition.onerror = function(event) {
    if (event.error === 'no-speech' || event.error === 'aborted') return;
    console.warn('[NOVA] Error:', event.error);
    isListening = false;
    isStartingUp = false;
    updateVoiceStatus(VOICE_STATES.IDLE);
  };

  recognition.onend = function() {
    isListening = false;
    isStartingUp = false;
    lastStopTime = Date.now();
    if (currentVoiceState === VOICE_STATES.LISTENING) {
      updateVoiceStatus(VOICE_STATES.IDLE);
    }
  };

  isStartingUp = true;
  try {
    recognition.start();
  } catch (err) {
    isStartingUp = false;
    isListening = false;
    updateVoiceStatus(VOICE_STATES.IDLE);
  }
}

function stopListening() {
  if (!isListening && !isStartingUp) return;
  try { if (recognition) recognition.stop(); } catch (e) {}
  isListening = false;
  isStartingUp = false;
  lastStopTime = Date.now();
  updateVoiceStatus(VOICE_STATES.IDLE);
}

// ============================================================
// MAIN HANDLER
// ============================================================
async function handleVoiceInput(transcript) {
  if (!transcript) return;
  console.log("[NOVA] Sending:", transcript);

  const container = document.getElementById('chatContainer');
  if (container) {
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    container.appendChild(createChatMessage('user', transcript, now));
    scrollChatToBottom();
    showTypingIndicator();
  }

  updateVoiceStatus(VOICE_STATES.THINKING);

  try {
    const response = await fetch(CONFIG.AI_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: transcript, user_id: 'nova_user' })
    });

    if (!response.ok) throw new Error('HTTP ' + response.status);

    const data = await response.json();
    let reply = data.response || data.reply || 'No response';

    // Add extra details if present
    if (data.data && typeof data.data === 'object') {
      const extras = [];
      if (data.data.body) extras.push(data.data.body);
      if (data.data.task) extras.push('📌 Task: ' + data.data.task);
      if (data.data.time) extras.push('🕐 Time: ' + data.data.time);
      if (extras.length > 0) reply = reply + '\n\n' + extras.join('\n');
    }

    removeTypingIndicator();

    if (container) {
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      container.appendChild(createChatMessage('nova', reply, now));
      scrollChatToBottom();
    }

    speakResponse(reply);

  } catch (err) {
    console.error('[NOVA] AI error:', err);
    removeTypingIndicator();

    const errMsg = '❌ Could not reach the AI. Please start bridge.py.';
    if (container) {
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      container.appendChild(createChatMessage('nova', errMsg, now));
      scrollChatToBottom();
    }
    updateVoiceStatus(VOICE_STATES.IDLE);
  }
}

// ============================================================
// TEXT-TO-SPEECH
// ============================================================
function speakResponse(text) {
  if (!text) return;
  updateVoiceStatus(VOICE_STATES.SPEAKING);

  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const lang = detectLanguage(text);
  const voice = getBestVoiceForLanguage(lang);
  if (voice) { u.voice = voice; u.lang = voice.lang; } else { u.lang = lang; }
  u.rate = 0.9;
  u.pitch = 1.1;
  u.onend = function() { updateVoiceStatus(VOICE_STATES.IDLE); };
  u.onerror = function() { updateVoiceStatus(VOICE_STATES.IDLE); };
  currentUtterance = u;
  window.speechSynthesis.speak(u);
}

// ============================================================
// UI HELPERS
// ============================================================
function updateVoiceStatus(state) {
  currentVoiceState = state;
  const orbWrapper = document.querySelector(".orb-wrapper");
  const orbStatusText = document.getElementById("orbStatusText");
  const micBtn = document.getElementById("micBtn");
  const micLabel = document.getElementById("micLabel");

  if (orbWrapper) {
    orbWrapper.classList.remove("orb-state-idle","orb-state-listening","orb-state-thinking","orb-state-speaking");
    orbWrapper.classList.add("orb-state-" + state);
  }

  if (orbStatusText) {
    switch (state) {
      case VOICE_STATES.IDLE:
        orbStatusText.textContent = "Ready when you are.";
        break;
      case VOICE_STATES.LISTENING:
        orbStatusText.textContent = "🎤 I'm listening...";
        break;
      case VOICE_STATES.THINKING:
        orbStatusText.textContent = "NOVA is thinking...";
        break;
      case VOICE_STATES.SPEAKING:
        orbStatusText.textContent = "NOVA is speaking...";
        break;
    }
  }

  if (micBtn) micBtn.classList.toggle("listening", state === VOICE_STATES.LISTENING);
  if (micLabel) {
    micLabel.textContent = state === VOICE_STATES.LISTENING ? "Listening..." : "Talk to NOVA";
  }
}

function toggleMicrophone() {
  if (isListening) stopListening();
  else startListening();
}

// ============================================================
// CHAT HELPERS
// ============================================================
function createChatMessage(sender, text, time) {
  const msg = document.createElement("div");
  msg.className = "chat-message " + sender;
  const name = localStorage.getItem("nova-user-name") || "User";
  const avatarText = sender === "nova" ? "N" : (name.charAt(0) || "U").toUpperCase();
  const senderName = sender === "nova" ? "NOVA" : "YOU";
  const safeText = escapeHtml(text).split("\n").join("<br>");
  msg.innerHTML =
    '<div class="chat-avatar">' + avatarText + '</div>' +
    '<div>' +
      '<div class="chat-sender">' + senderName + '</div>' +
      '<div class="chat-bubble">' + safeText + '</div>' +
      '<div class="chat-time">' + time + '</div>' +
    '</div>';
  return msg;
}

function showTypingIndicator() {
  const container = document.getElementById("chatContainer");
  if (!container) return;
  if (document.getElementById("typingIndicator")) return;
  const typing = document.createElement("div");
  typing.className = "chat-message nova chat-typing";
  typing.id = "typingIndicator";
  typing.innerHTML =
    '<div class="chat-avatar">N</div>' +
    '<div>' +
      '<div class="chat-sender">NOVA</div>' +
      '<div class="chat-bubble"><div class="typing-dots">' +
        '<span></span><span></span><span></span>' +
      '</div></div>' +
    '</div>';
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const t = document.getElementById("typingIndicator");
  if (t) t.remove();
}

function scrollChatToBottom() {
  const c = document.getElementById("chatContainer");
  if (c) c.scrollTop = c.scrollHeight;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ============================================================
// WIRE UP DOM
// ============================================================
function wireUp() {
  const micBtn = document.getElementById("micBtn");
  if (micBtn && !micBtn.dataset.wired) {
    micBtn.dataset.wired = 'true';
    micBtn.addEventListener('click', function(e) {
      e.preventDefault();
      toggleMicrophone();
    });
    console.log('[NOVA] Mic wired');
  }

  const input = document.getElementById("assistantInput");
  const send = document.getElementById("assistantSend");

  if (send && !send.dataset.wired) {
    send.dataset.wired = 'true';
    send.addEventListener('click', function(e) {
      e.preventDefault();
      if (!input) return;
      const t = input.value.trim();
      if (!t) return;
      input.value = '';
      handleVoiceInput(t);
    });
  }

  if (input && !input.dataset.wired) {
    input.dataset.wired = 'true';
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const t = input.value.trim();
        if (!t) return;
        input.value = '';
        handleVoiceInput(t);
      }
    });
  }

  document.querySelectorAll('.quick-action').forEach(function(btn) {
    if (btn.dataset.wired) return;
    btn.dataset.wired = 'true';
    btn.addEventListener('click', function() {
      const text = btn.dataset.quick;
      if (text) handleVoiceInput(text);
    });
  });
}

// ============================================================
// INIT
// ============================================================
window.addEventListener('DOMContentLoaded', function() {
  console.log('[NOVA] Initializing...');
  wireUp();
  setTimeout(wireUp, 500);
  setTimeout(wireUp, 1500);

  if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function() {
      window.speechSynthesis.getVoices();
    };
  }

  document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && !e.target.matches('input, textarea, button, select')) {
      e.preventDefault();
      toggleMicrophone();
    }
  });

  console.log('[NOVA] Ready');
});

window.NOVA_VOICE = {
  startListening,
  stopListening,
  handleVoiceInput,
  updateVoiceStatus,
  toggleMicrophone,
  VOICE_STATES
};