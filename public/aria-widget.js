/**
 * ARIA — 121.500 AI Radio Widget
 * EcoFlight AI | Universal AI Co-Pilot Frequency
 *
 * HOW TO ADD TO ANY DASHBOARD (3 steps):
 * ─────────────────────────────────────────
 * Step 1: Add this script tag to your HTML <head> or before </body>:
 *
 *   <script src="aria-widget.js"></script>
 *
 * Step 2: Add a button anywhere to open ARIA:
 *
 *   <button onclick="ARIA.open()">🎙 ARIA — 121.500 AI</button>
 *
 * Step 3: (Optional) Set flight data so ARIA knows your route:
 *
 *   ARIA.setContext({
 *     aircraft: 'B737',
 *     origin: 'KJFK',
 *     destination: 'KLAX',
 *     fuel_remaining_kg: 8000,
 *     fuel_saved_kg: 380,
 *     co2_saved_kg: 1200,
 *     cost_saved_usd: 304
 *   });
 *
 * That's it. ARIA handles the rest — voice input, AI response, ElevenLabs speech.
 *
 * CONFIG (optional — change these at the top of this file):
 *   ARIA_BACKEND   — URL of the EcoFlight backend (default: http://localhost:8000)
 *   ARIA_XI_KEY    — Your ElevenLabs API key
 *   ARIA_VOICE_ID  — ElevenLabs voice ID (default: Roger)
 */

(function () {
  // ══════════════════════════════════════════════════════════════════════
  //  CONFIG — edit these
  // ══════════════════════════════════════════════════════════════════════
  const ARIA_BACKEND  = 'http://localhost:8000';
  const ARIA_XI_KEY   = 'sk_1456c213d59ac750a4226882e49d203da059398edb66d970';
  const ARIA_VOICE_ID = 'CwhRBWXzGAHq8TQ4Fs17'; // Roger (clear pilot voice)

  // ══════════════════════════════════════════════════════════════════════
  //  STATE
  // ══════════════════════════════════════════════════════════════════════
  let _open        = false;
  let _recording   = false;
  let _recognition = null;
  let _flightCtx   = null;
  let _typingCount = 0;

  // ══════════════════════════════════════════════════════════════════════
  //  INJECT CSS
  // ══════════════════════════════════════════════════════════════════════
  const style = document.createElement('style');
  style.textContent = `
    #__ariaPanel {
      position: fixed; bottom: 20px; right: 20px;
      width: 380px; max-height: 560px;
      background: linear-gradient(160deg, #070f1c, #0b1825);
      border: 1px solid #00ff9d44;
      border-radius: 12px;
      box-shadow: 0 0 40px rgba(0,255,157,0.12), 0 8px 32px rgba(0,0,0,0.6);
      display: none; flex-direction: column;
      font-family: 'Share Tech Mono', 'Courier New', monospace;
      z-index: 99999; overflow: hidden;
    }
    #__ariaPanel * { box-sizing: border-box; }
    #__ariaPTTBtn {
      width: 72px; height: 72px; border-radius: 50%;
      background: radial-gradient(circle, #002a15, #001a0a);
      border: 2px solid #00ff9d; color: #00ff9d;
      font-size: 1.6rem; cursor: pointer;
      box-shadow: 0 0 16px rgba(0,255,157,0.3);
      transition: all 0.15s; outline: none;
    }
    #__ariaPTTBtn.aria-recording {
      background: radial-gradient(circle, #1a0000, #0a0000) !important;
      border-color: #ff4444 !important; color: #ff4444 !important;
      box-shadow: 0 0 30px rgba(255,68,68,0.5) !important;
      transform: scale(1.08);
    }
    #__ariaTranscript::-webkit-scrollbar { width: 4px; }
    #__ariaTranscript::-webkit-scrollbar-thumb { background: #1c3248; border-radius: 2px; }
    @keyframes __ariaBlink { 0%,100%{opacity:1} 50%{opacity:0} }
    .__ariaInput {
      flex: 1; background: #0a1520; border: 1px solid #1c3248;
      color: #c8d6e2; font-family: 'Share Tech Mono','Courier New',monospace;
      font-size: 0.65rem; padding: 7px 10px; border-radius: 5px; outline: none;
    }
    .__ariaInput::placeholder { color: #2e5070; }
    .__ariaSendBtn {
      background: #001a0a; border: 1px solid #00ff9d; color: #00ff9d;
      font-family: 'Share Tech Mono','Courier New',monospace;
      font-size: 0.6rem; padding: 7px 10px; border-radius: 5px;
      cursor: pointer; letter-spacing: 1px;
    }
    .__ariaSendBtn:hover { background: #002a14; }
  `;
  document.head.appendChild(style);

  // ══════════════════════════════════════════════════════════════════════
  //  INJECT HTML PANEL
  // ══════════════════════════════════════════════════════════════════════
  function buildPanel() {
    const div = document.createElement('div');
    div.id = '__ariaPanel';
    div.innerHTML = `
      <!-- Header -->
      <div style="background:linear-gradient(90deg,#001a10,#050f1a);border-bottom:1px solid #00ff9d33;
          padding:10px 14px;display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div id="__ariaStatusDot" style="width:8px;height:8px;border-radius:50%;background:#555;
              box-shadow:0 0 6px #555;transition:all 0.3s;"></div>
          <span style="color:#00ff9d;font-size:0.7rem;letter-spacing:2px;font-weight:bold;">ARIA — 121.500 AI</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="color:#00ff9d;font-size:1rem;letter-spacing:1px;">121.500</span>
          <button onclick="ARIA.close()" style="background:none;border:none;color:#4a6070;
              font-size:1rem;cursor:pointer;padding:2px 6px;" title="Close">✕</button>
        </div>
      </div>
      <!-- Status bar -->
      <div id="__ariaStatusBar" style="padding:5px 14px;font-size:0.6rem;color:#4a6070;
          border-bottom:1px solid #0e2030;letter-spacing:1px;">Connecting to ARIA...</div>
      <!-- Transcript -->
      <div id="__ariaTranscript" style="flex:1;overflow-y:auto;padding:12px 14px;
          min-height:200px;max-height:300px;display:flex;flex-direction:column;gap:10px;
          scrollbar-width:thin;scrollbar-color:#1c3248 transparent;"></div>
      <!-- PTT + Text input -->
      <div style="padding:12px 14px;border-top:1px solid #0e2030;">
        <div style="text-align:center;margin-bottom:10px;">
          <button id="__ariaPTTBtn"
            onmousedown="ARIA._startRec()" onmouseup="ARIA._stopRec()"
            ontouchstart="ARIA._startRec()" ontouchend="ARIA._stopRec()"
            title="Hold to Talk">🎙</button>
          <div id="__ariaPTTLabel" style="margin-top:6px;font-size:0.55rem;color:#4a6070;
              letter-spacing:2px;">HOLD TO TALK</div>
        </div>
        <div style="display:flex;gap:6px;">
          <input id="__ariaInput" class="__ariaInput" type="text"
            placeholder="Or type your question..."
            onkeydown="if(event.key==='Enter') ARIA._sendText()" />
          <button class="__ariaSendBtn" onclick="ARIA._sendText()">SEND</button>
        </div>
      </div>
    `;
    document.body.appendChild(div);
  }

  // ══════════════════════════════════════════════════════════════════════
  //  PUBLIC API  (window.ARIA)
  // ══════════════════════════════════════════════════════════════════════
  window.ARIA = {

    /** Open/close the panel */
    open() {
      _open = true;
      document.getElementById('__ariaPanel').style.display = 'flex';
      _checkStatus();
      const t = document.getElementById('__ariaTranscript');
      if (!t.children.length) {
        _sysMsg('ARIA online. 121.500 AI active. Hold PTT and speak, or type a question.');
        if (_flightCtx && _flightCtx.origin) {
          _sysMsg(`Route loaded: ${_flightCtx.origin} → ${_flightCtx.destination || '?'} | EcoFlight saved ${Math.round(_flightCtx.fuel_saved_kg || 0)} kg fuel`);
        }
      }
    },

    close() {
      _open = false;
      document.getElementById('__ariaPanel').style.display = 'none';
    },

    toggle() { _open ? this.close() : this.open(); },

    /**
     * Pass flight data so ARIA can give route-specific answers.
     * Call this after your route is computed.
     *
     * @param {Object} ctx - flight context object
     */
    setContext(ctx) {
      _flightCtx = ctx;
      try { localStorage.setItem('ecoflight_aria_context', JSON.stringify(ctx)); } catch(e) {}
    },

    // ── Internal (called from inline HTML handlers) ───────────────────
    _startRec: () => _startRecording(),
    _stopRec:  () => _stopRecording(),
    _sendText: () => _sendText(),
  };

  // ══════════════════════════════════════════════════════════════════════
  //  STATUS CHECK
  // ══════════════════════════════════════════════════════════════════════
  async function _checkStatus() {
    try {
      const r = await fetch(`${ARIA_BACKEND}/radio/status`);
      const d = await r.json();
      const dot = document.getElementById('__ariaStatusDot');
      const bar = document.getElementById('__ariaStatusBar');
      dot.style.background = '#00ff9d';
      dot.style.boxShadow = '0 0 8px #00ff9d';
      bar.style.color = '#00ff9d';
      bar.textContent = 'ARIA ONLINE — ElevenLabs voice | Physics AI engine';
    } catch {
      const dot = document.getElementById('__ariaStatusDot');
      dot.style.background = '#c44040';
      dot.style.boxShadow = '0 0 8px #c44040';
      document.getElementById('__ariaStatusBar').textContent =
        'Backend offline — start EcoFlight backend on port 8000';
    }
  }

  // ══════════════════════════════════════════════════════════════════════
  //  FLIGHT CONTEXT
  // ══════════════════════════════════════════════════════════════════════
  function _buildCtx() {
    if (_flightCtx) return _flightCtx;
    try {
      const raw = localStorage.getItem('ecoflight_aria_context');
      if (raw) return JSON.parse(raw);
    } catch(e) {}
    return {
      aircraft: 'B737', flight_phase: 'cruise',
      current_altitude_ft: 35000, optimal_altitude_ft: 37000,
      fuel_remaining_kg: 8000, total_fuel_kg: 15000,
      fuel_burn_rate_kg_per_hr: 2200, distance_remaining_nm: 800,
      groundspeed_kt: 460, wind_component_kt: 15,
      contrail_risk: 'medium', efficiency_pct: 94.0
    };
  }

  // ══════════════════════════════════════════════════════════════════════
  //  PUSH-TO-TALK
  // ══════════════════════════════════════════════════════════════════════
  function _startRecording() {
    if (_recording) return;
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      _sysMsg('Speech recognition requires Chrome. Type your question below.');
      return;
    }
    _recording = true;
    const btn = document.getElementById('__ariaPTTBtn');
    btn.classList.add('aria-recording');
    btn.textContent = '🔴';
    document.getElementById('__ariaPTTLabel').textContent = 'TRANSMITTING...';

    _recognition = new SpeechRec();
    _recognition.lang = 'en-US';
    _recognition.continuous = false;
    _recognition.interimResults = false;
    _recognition.onresult = (e) => {
      document.getElementById('__ariaInput').value = e.results[0][0].transcript;
    };
    _recognition.onerror = () => _resetPTT();
    _recognition.onend = () => {
      if (_recording) {
        const q = document.getElementById('__ariaInput').value.trim();
        if (q) _query(q);
        _resetPTT();
      }
    };
    _recognition.start();
  }

  function _stopRecording() {
    if (!_recording) return;
    _recording = false;
    if (_recognition) _recognition.stop();
    _resetPTT();
  }

  function _resetPTT() {
    _recording = false;
    const btn = document.getElementById('__ariaPTTBtn');
    if (!btn) return;
    btn.classList.remove('aria-recording');
    btn.textContent = '🎙';
    document.getElementById('__ariaPTTLabel').textContent = 'HOLD TO TALK';
  }

  function _sendText() {
    const inp = document.getElementById('__ariaInput');
    const q = inp.value.trim();
    if (!q) return;
    inp.value = '';
    _query(q);
  }

  // ══════════════════════════════════════════════════════════════════════
  //  QUERY ARIA BACKEND
  // ══════════════════════════════════════════════════════════════════════
  async function _query(text) {
    _pilotMsg(text);
    const tid = _typingMsg();
    try {
      const res = await fetch(`${ARIA_BACKEND}/radio/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          flight_context: _buildCtx(),
          include_audio: false
        })
      });
      const data = await res.json();
      _removeTyping(tid);
      const reply = data.aria_response || data.response_text || '';
      _ariaMsg(reply, data.urgency);
      if (reply) _speak(reply);
    } catch {
      _removeTyping(tid);
      _sysMsg('Cannot reach backend. Make sure EcoFlight backend is running on port 8000.');
    }
  }

  // ══════════════════════════════════════════════════════════════════════
  //  ELEVENLABS TTS (browser-direct) + browser fallback
  // ══════════════════════════════════════════════════════════════════════
  async function _speak(text) {
    if (!ARIA_XI_KEY) { _speakBrowser(text); return; }
    try {
      const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${ARIA_VOICE_ID}`, {
        method: 'POST',
        headers: {
          'xi-api-key': ARIA_XI_KEY,
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg'
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_flash_v2_5',
          voice_settings: { stability: 0.55, similarity_boost: 0.75, style: 0.05, use_speaker_boost: true }
        })
      });
      if (!res.ok) { _speakBrowser(text); return; }
      const blob = await res.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.play().catch(() => _speakBrowser(text));
    } catch { _speakBrowser(text); }
  }

  function _speakBrowser(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.95; utt.pitch = 0.9; utt.volume = 1;
    const v = window.speechSynthesis.getVoices();
    const pref = v.find(x => x.name.includes('Daniel') || x.name.includes('Alex') || (x.lang === 'en-GB' && x.localService));
    if (pref) utt.voice = pref;
    window.speechSynthesis.speak(utt);
  }

  // ══════════════════════════════════════════════════════════════════════
  //  TRANSCRIPT HELPERS
  // ══════════════════════════════════════════════════════════════════════
  function _pilotMsg(text) {
    const t = document.getElementById('__ariaTranscript');
    const el = document.createElement('div');
    el.style.cssText = 'display:flex;flex-direction:column;align-items:flex-end;';
    el.innerHTML = `
      <div style="font-size:0.5rem;color:#4a6070;letter-spacing:1px;margin-bottom:3px;">PILOT</div>
      <div style="background:#0a1520;border:1px solid #1c3248;border-radius:8px 8px 2px 8px;
          padding:8px 12px;max-width:85%;font-size:0.65rem;color:#c8d6e2;line-height:1.5;">${_esc(text)}</div>`;
    t.appendChild(el); t.scrollTop = t.scrollHeight;
  }

  function _ariaMsg(text, urgency) {
    const colors = { urgent: '#ff4444', advisory: '#d49820', routine: '#00ff9d' };
    const c = colors[urgency] || '#00ff9d';
    const t = document.getElementById('__ariaTranscript');
    const el = document.createElement('div');
    el.style.cssText = 'display:flex;flex-direction:column;align-items:flex-start;';
    el.innerHTML = `
      <div style="font-size:0.5rem;letter-spacing:1px;margin-bottom:3px;color:${c};">ARIA</div>
      <div style="background:#001a10;border:1px solid ${c}44;border-left:3px solid ${c};
          border-radius:2px 8px 8px 8px;padding:8px 12px;max-width:95%;
          font-size:0.65rem;color:#c8d6e2;line-height:1.6;">${_esc(text)}</div>`;
    t.appendChild(el); t.scrollTop = t.scrollHeight;
  }

  function _sysMsg(text) {
    const t = document.getElementById('__ariaTranscript');
    const el = document.createElement('div');
    el.style.cssText = 'text-align:center;font-size:0.55rem;color:#2e5070;padding:4px 0;letter-spacing:0.5px;';
    el.textContent = text;
    t.appendChild(el); t.scrollTop = t.scrollHeight;
  }

  function _typingMsg() {
    const id = '__ariaTyping' + (++_typingCount);
    const t = document.getElementById('__ariaTranscript');
    const el = document.createElement('div');
    el.id = id;
    el.style.cssText = 'display:flex;align-items:flex-start;gap:6px;';
    el.innerHTML = `<div style="font-size:0.5rem;color:#00ff9d;letter-spacing:1px;margin-top:2px;">ARIA</div>
      <div style="color:#00ff9d;font-size:0.9rem;animation:__ariaBlink 1s infinite;">▌</div>`;
    t.appendChild(el); t.scrollTop = t.scrollHeight;
    return id;
  }

  function _removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function _esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ══════════════════════════════════════════════════════════════════════
  //  INIT
  // ══════════════════════════════════════════════════════════════════════
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildPanel);
  } else {
    buildPanel();
  }

})();
