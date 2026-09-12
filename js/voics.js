/* ============================================
   NOVA - Voice Module
   Placeholder functions for future voice integration.
   Person 4 will connect real Speech Recognition & TTS.
   ============================================ */

const VOICE_STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  THINKING: "thinking",
  SPEAKING: "speaking"
};

let currentVoiceState = VOICE_STATES.IDLE;
let isListening = false;

function getVoiceState() {
  return currentVoiceState;
}

function startListening() {
  if (isListening) return;
  isListening = true;
  currentVoiceState = VOICE_STATES.LISTENING;
  updateVoiceStatus(VOICE_STATES.LISTENING);
  console.log("[NOVA Voice] Listening started...");
  // Person 4: Connect SpeechRecognition API here
}

function stopListening() {
  if (!isListening) return;
  isListening = false;
  currentVoiceState = VOICE_STATES.IDLE;
  updateVoiceStatus(VOICE_STATES.IDLE);
  console.log("[NOVA Voice] Listening stopped.");
}

function handleVoiceInput(transcript) {
  if (!transcript) return;
  console.log("[NOVA Voice] Input received:", transcript);
  currentVoiceState = VOICE_STATES.THINKING;
  updateVoiceStatus(VOICE_STATES.THINKING);

  setTimeout(() => {
    speakResponse("I heard you say: " + transcript);
  }, 1500);
}

function speakResponse(text) {
  currentVoiceState = VOICE_STATES.SPEAKING;
  updateVoiceStatus(VOICE_STATES.SPEAKING);
  console.log("[NOVA Voice] Speaking:", text);
  // Person 4: Connect SpeechSynthesis API here

  setTimeout(() => {
    currentVoiceState = VOICE_STATES.IDLE;
    updateVoiceStatus(VOICE_STATES.IDLE);
  }, 2000);
}

function updateVoiceStatus(state) {
  const orbWrapper = document.querySelector(".orb-wrapper");
  const orbStatusText = document.querySelector(".orb-status-text");
  const micBtn = document.querySelector(".mic-btn");

  if (!orbWrapper) return;

  orbWrapper.classList.remove(
    "orb-state-idle",
    "orb-state-listening",
    "orb-state-thinking",
    "orb-state-speaking"
  );
  orbWrapper.classList.add("orb-state-" + state);

  if (orbStatusText) {
    orbStatusText.classList.remove("listening", "thinking", "speaking");
    switch (state) {
      case VOICE_STATES.IDLE:
        orbStatusText.textContent = "Ready when you are.";
        break;
      case VOICE_STATES.LISTENING:
        orbStatusText.textContent = "🎤 I'm listening...";
        orbStatusText.classList.add("listening");
        break;
      case VOICE_STATES.THINKING:
        orbStatusText.textContent = "NOVA is thinking...";
        orbStatusText.classList.add("thinking");
        break;
      case VOICE_STATES.SPEAKING:
        orbStatusText.textContent = "NOVA is speaking...";
        orbStatusText.classList.add("speaking");
        break;
    }
  }

  if (micBtn) {
    micBtn.classList.toggle("listening", state === VOICE_STATES.LISTENING);
  }
}

function toggleMicrophone() {
  if (isListening) {
    stopListening();
  } else {
    startListening();
  }
}

window.NOVA_VOICE = {
  startListening,
  stopListening,
  handleVoiceInput,
  updateVoiceStatus,
  toggleMicrophone,
  getVoiceState,
  VOICE_STATES
};