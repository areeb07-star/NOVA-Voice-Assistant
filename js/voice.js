/* ============================================
   NOVA - Voice Module (Person 4) — Final
   Mic button: 1st click stops Nova, 2nd click starts listening
   Bug 5 fix: reliable TTS stop (pause + cancel + ttsId guard)
   Multi-user: sends user_id + access_token to bridge.py
   Deployed: AI_URL + SUMMARIZE_URL → Render bridge
   ============================================ */

const CONFIG = {
  AI_URL: 'https://nova-voice-assistant-bridge-f.onrender.com/api/process',
  SUMMARIZE_URL: 'https://nova-voice-assistant-bridge-f.onrender.com/api/summarize',
  LOCAL_AGENT_URL: 'http://127.0.0.1:5050'
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

// TTS guards
let ttsId = 0;
let isSpeaking = false;
let isPaused = false;

// ============================================================
// AUTO-DETECT DEVICE ID
// ============================================================
async function autoDetectDeviceId() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(CONFIG.LOCAL_AGENT_URL + '/device_id', {
      signal: controller.signal,
      cache: 'no-store'
    });
    clearTimeout(timeout);

    if (res.ok) {
      const data = await res.json();
      if (data.device_id) {
        localStorage.setItem('nova-device-id', data.device_id);
        console.log('[NOVA] ✅ Device from agent:', data.device_id);
        return data.device_id;
      }
    }
  } catch (e) {
    console.log('[NOVA] ⚠️ Local agent not reachable:', e.message);
  }

  const stored = localStorage.getItem('nova-device-id');
  if (stored) {
    console.log('[NOVA] Using cached device:', stored);
    return stored;
  }

  console.log('[NOVA] ❌ No device ID — running in browser-only mode');
  return null;
}

function getDeviceId() {
  return localStorage.getItem('nova-device-id') || null;
}

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
    console.warn('[NOVA] Use Chrome browser.');
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
// STOP SPEAKING
// ============================================================
function stopSpeaking() {
  if (!window.speechSynthesis) return;

  ttsId++;

  try { window.speechSynthesis.pause(); } catch (e) {}
  try { window.speechSynthesis.cancel(); } catch (e) {}

  setTimeout(function() {
    try { window.speechSynthesis.cancel(); } catch (e) {}
  }, 50);

  isSpeaking = false;
  isPaused = false;
  currentUtterance = null;
  updateVoiceStatus(VOICE_STATES.IDLE);
  console.log('[NOVA] 🛑 Speech stopped.');
}

function pauseSpeaking() {
  if (!window.speechSynthesis) return;
  try { window.speechSynthesis.pause(); isPaused = true; } catch (e) {}
}

function resumeSpeaking() {
  if (!window.speechSynthesis) return;
  try { window.speechSynthesis.resume(); isPaused = false; } catch (e) {}
}

// ============================================================
// SMART MIC HANDLER
// ============================================================
function handleMicClick() {
  const speaking = window.speechSynthesis &&
                   (window.speechSynthesis.speaking || window.speechSynthesis.pending);

  if (speaking || isSpeaking || currentVoiceState === VOICE_STATES.SPEAKING) {
    console.log('[NOVA] 🎤 Mic pressed while speaking → stop only');
    stopSpeaking();
    return;
  }

  if (isListening || isStartingUp) {
    stopListening();
    return;
  }

  startListening();
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
    const deviceId = await autoDetectDeviceId();
    console.log('[NOVA] Using device_id:', deviceId || '(none)');

    const loggedInUserId =
      localStorage.getItem('nova-user-id') ||
      localStorage.getItem('user_id') ||
      localStorage.getItem('nova_user_id') ||
      'nova_user';

    const accessToken =
      localStorage.getItem('nova-access-token') ||
      localStorage.getItem('access_token') ||
      '';

    const payload = {
      text: transcript,
      user_id: loggedInUserId,
      access_token: accessToken
    };
    if (deviceId) payload.device_id = deviceId;

    const response = await fetch(CONFIG.AI_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) throw new Error('HTTP ' + response.status);

    const data = await response.json();
    console.log('[NOVA] AI Response:', data);

    let reply = data.response || data.reply || 'No response';

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

    const errMsg = '❌ Could not reach the AI. Please try again.';
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

  ttsId++;
  const myId = ttsId;

  try { window.speechSynthesis.cancel(); } catch (e) {}

  updateVoiceStatus(VOICE_STATES.SPEAKING);
  isSpeaking = true;

  const u = new SpeechSynthesisUtterance(text);
  const lang = detectLanguage(text);
  const voice = getBestVoiceForLanguage(lang);
  if (voice) { u.voice = voice; u.lang = voice.lang; } else { u.lang = lang; }
  u.rate = 0.9;
  u.pitch = 1.1;

  u.onend = function() {
    if (myId === ttsId) {
      isSpeaking = false;
      updateVoiceStatus(VOICE_STATES.IDLE);
    }
  };
  u.onerror = function() {
    if (myId === ttsId) {
      isSpeaking = false;
      updateVoiceStatus(VOICE_STATES.IDLE);
    }
  };

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
      case VOICE_STATES.IDLE: orbStatusText.textContent = "Ready when you are."; break;
      case VOICE_STATES.LISTENING: orbStatusText.textContent = "🎤 I'm listening..."; break;
      case VOICE_STATES.THINKING: orbStatusText.textContent = "NOVA is thinking..."; break;
      case VOICE_STATES.SPEAKING: orbStatusText.textContent = "NOVA is speaking..."; break;
    }
  }

  if (micBtn) {
    micBtn.classList.toggle("listening", state === VOICE_STATES.LISTENING);
    micBtn.classList.toggle("speaking", state === VOICE_STATES.SPEAKING);
  }

  if (micLabel) {
    if (state === VOICE_STATES.LISTENING) {
      micLabel.textContent = "Listening...";
    } else if (state === VOICE_STATES.SPEAKING) {
      micLabel.textContent = "Tap to interrupt";
    } else if (state === VOICE_STATES.THINKING) {
      micLabel.textContent = "Thinking...";
    } else {
      micLabel.textContent = "Talk to NOVA";
    }
  }
}

function toggleMicrophone() {
  handleMicClick();
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
  if (!container || document.getElementById("typingIndicator")) return;
  const t = document.createElement("div");
  t.className = "chat-message nova";
  t.id = "typingIndicator";
  t.innerHTML =
    '<div class="chat-avatar">N</div>' +
    '<div>' +
      '<div class="chat-sender">NOVA</div>' +
      '<div class="chat-bubble"><div class="typing-dots">' +
        '<span></span><span></span><span></span>' +
      '</div></div>' +
    '</div>';
  container.appendChild(t);
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
      handleMicClick();
    });
  }

  const stopBtn = document.getElementById("stopBtn");
  if (stopBtn && !stopBtn.dataset.wired) {
    stopBtn.dataset.wired = 'true';
    stopBtn.addEventListener('click', function(e) {
      e.preventDefault();
      stopSpeaking();
      stopListening();
    });
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
    if (btn.id === 'summarizeFileBtn') return;
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

  autoDetectDeviceId().then(id => {
    if (id) console.log('[NOVA] ✅ Device ready:', id);
  });

  if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function() {
      window.speechSynthesis.getVoices();
    };
  }

  document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && !e.target.matches('input, textarea, button, select')) {
      e.preventDefault();
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        stopSpeaking();
      } else {
        handleMicClick();
      }
    }
  });

  console.log('[NOVA] Ready');
});

window.NOVA_VOICE = {
  startListening,
  stopListening,
  handleMicClick,
  handleVoiceInput,
  updateVoiceStatus,
  toggleMicrophone,
  stopSpeaking,
  pauseSpeaking,
  resumeSpeaking,
  getDeviceId,
  autoDetectDeviceId,
  VOICE_STATES
};