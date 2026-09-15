/* ============================================
   NOVA - File Summarizer (Person 4)
   FAST + CLEAR OCR version
   Deployed: BRIDGE_URL → Render bridge
   ============================================ */

(function () {
  'use strict';

  var BRIDGE_URL = 'https://nova-voice-assistant-bridge-f.onrender.com/api/summarize';
  var TESS_CDN = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
  var tesseractReady = false;
  var tesseractLoading = null;

  // Preload Tesseract as soon as page opens
  window.addEventListener('load', function () {
    console.log('[NOVA Files] Initializing...');

    preloadTesseract();

    var fileInput = document.getElementById('summarizeFileInput');
    var fileBtn = document.getElementById('summarizeFileBtn');
    var attachBtn = document.getElementById('attachFileBtn');

    if (!fileInput) {
      console.warn('[NOVA Files] No file input found');
      return;
    }

    if (fileBtn) fileBtn.addEventListener('click', function () { fileInput.click(); });
    if (attachBtn) attachBtn.addEventListener('click', function () { fileInput.click(); });

    fileInput.addEventListener('change', async function () {
      var file = fileInput.files[0];
      if (!file) return;

      showUserMessage('📄 Please summarize: ' + file.name);
      showTyping();

      var startTime = Date.now();

      try {
        console.log('[NOVA Files] File:', file.name, '| Type:', file.type, '| Size:', file.size);
        var text = await extractTextFromFile(file);
        var elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log('[NOVA Files] Extracted ' + text.length + ' chars in ' + elapsed + 's');

        if (!text || text.trim().length < 5) {
          removeTyping();
          showNovaMessage('❌ Could not extract readable text. Try a clearer image or different file.');
          fileInput.value = '';
          return;
        }

        console.log('[NOVA Files] Sending to bridge...');
        var res = await fetch(BRIDGE_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text.slice(0, 12000),
            user_id: 'nova_user'
          })
        });

        var data = await res.json();
        removeTyping();

        if (data.success) {
          showNovaMessage(data.response || 'Summary ready.');
        } else {
          showNovaMessage('❌ Error: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        console.error('[NOVA Files] Error:', err);
        removeTyping();
        showNovaMessage('❌ Failed to process file: ' + err.message);
      } finally {
        fileInput.value = '';
      }
    });
  });

  // ============================================================
  // PRELOAD TESSERACT
  // ============================================================
  function preloadTesseract() {
    if (window.Tesseract) {
      tesseractReady = true;
      console.log('[NOVA Files] Tesseract already loaded');
      return Promise.resolve();
    }
    if (tesseractLoading) return tesseractLoading;

    console.log('[NOVA Files] Preloading Tesseract in background...');
    tesseractLoading = loadScript(TESS_CDN).then(function () {
      tesseractReady = true;
      console.log('[NOVA Files] Tesseract ready');
    }).catch(function (err) {
      console.warn('[NOVA Files] Tesseract preload failed:', err);
      tesseractLoading = null;
    });
    return tesseractLoading;
  }

  async function ensureTesseract() {
    if (tesseractReady && window.Tesseract) return;
    await preloadTesseract();
    if (!window.Tesseract) throw new Error('OCR library could not load');
  }

  // ============================================================
  // ROUTE BY FILE TYPE
  // ============================================================
  async function extractTextFromFile(file) {
    var name = (file.name || '').toLowerCase();
    var type = (file.type || '').toLowerCase();

    if (type.indexOf('image/') === 0 ||
        /\.(png|jpe?g|bmp|webp|gif|tiff?)$/.test(name)) {
      console.log('[NOVA Files] → Image OCR');
      return await extractImageText(file);
    }

    if (name.indexOf('.pdf') !== -1 || type === 'application/pdf') {
      console.log('[NOVA Files] → PDF');
      return await extractPdfText(file);
    }

    if (name.indexOf('.docx') !== -1) {
      console.log('[NOVA Files] → DOCX');
      return await extractDocxText(file);
    }

    if (name.indexOf('.xlsx') !== -1 || name.indexOf('.xls') !== -1) {
      console.log('[NOVA Files] → Excel');
      return await extractExcelText(file);
    }

    console.log('[NOVA Files] → Plain text');
    return (await file.text()).trim();
  }

  // ============================================================
  // IMAGE OCR
  // ============================================================
  async function extractImageText(file) {
    await ensureTesseract();

    console.log('[NOVA Files] Preprocessing image...');
    var canvas = await preprocessImage(file);

    console.log('[NOVA Files] Running OCR...');
    var result = await window.Tesseract.recognize(canvas, 'eng', {
      tessedit_pageseg_mode: '6',
      preserve_interword_spaces: '1'
    });

    var text = cleanOcrText(result.data.text || '');
    console.log('[NOVA Files] OCR done, ' + text.length + ' chars');
    return text;
  }

  async function preprocessImage(file) {
    var img = await loadImage(file);

    var maxDim = 1400;
    var w = img.width;
    var h = img.height;
    if (w > maxDim || h > maxDim) {
      var ratio = Math.min(maxDim / w, maxDim / h);
      w = Math.round(w * ratio);
      h = Math.round(h * ratio);
      console.log('[NOVA Files] Scaled to ' + w + 'x' + h);
    }

    var canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    var ctx = canvas.getContext('2d');

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);

    var imageData = ctx.getImageData(0, 0, w, h);
    var data = imageData.data;

    var minV = 255, maxV = 0;
    for (var i = 0; i < data.length; i += 4) {
      var g = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      if (g < minV) minV = g;
      if (g > maxV) maxV = g;
    }
    var range = maxV - minV || 1;

    for (var i = 0; i < data.length; i += 4) {
      var g = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      var stretched = ((g - minV) / range) * 255;
      data[i] = data[i + 1] = data[i + 2] = stretched;
    }
    ctx.putImageData(imageData, 0, 0);

    return canvas;
  }

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      var url = URL.createObjectURL(file);
      img.onload = function () {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error('Could not load image'));
      };
      img.src = url;
    });
  }

  function cleanOcrText(raw) {
    return raw
      .replace(/\r/g, '')
      .replace(/[ \t]+/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .split('\n')
      .map(function (line) { return line.trim(); })
      .filter(function (line) { return line.length > 2; })
      .join('\n')
      .trim();
  }

  // ============================================================
  // PDF
  // ============================================================
  async function extractPdfText(file) {
    if (!window.pdfjsLib) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js');
      window.pdfjsLib.GlobalWorkerOptions.workerSrc =
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    var buf = await file.arrayBuffer();
    var pdf = await window.pdfjsLib.getDocument({ data: buf }).promise;

    var out = '';
    for (var i = 1; i <= pdf.numPages; i++) {
      var page = await pdf.getPage(i);
      var content = await page.getTextContent();
      out += content.items.map(function (item) { return item.str; }).join(' ') + '\n\n';
    }
    out = out.trim();

    if (out.length < 20) {
      console.log('[NOVA Files] Scanned PDF — running OCR (max 3 pages)');
      return await ocrPdf(file);
    }
    return out;
  }

  async function ocrPdf(file) {
    await ensureTesseract();

    var buf = await file.arrayBuffer();
    var pdf = await window.pdfjsLib.getDocument({ data: buf }).promise;

    var out = '';
    var maxPages = Math.min(pdf.numPages, 3);

    for (var i = 1; i <= maxPages; i++) {
      console.log('[NOVA Files] OCR page ' + i + '/' + maxPages);
      var page = await pdf.getPage(i);
      var vp = page.getViewport({ scale: 1.2 });
      var canvas = document.createElement('canvas');
      canvas.width = vp.width;
      canvas.height = vp.height;
      await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise;

      var result = await window.Tesseract.recognize(canvas, 'eng', {
        tessedit_pageseg_mode: '6'
      });
      out += cleanOcrText(result.data.text || '') + '\n\n';
    }
    return out.trim();
  }

  // ============================================================
  // DOCX
  // ============================================================
  async function extractDocxText(file) {
    if (!window.mammoth) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js');
    }
    var buf = await file.arrayBuffer();
    var result = await window.mammoth.extractRawText({ arrayBuffer: buf });
    return (result.value || '').trim();
  }

  // ============================================================
  // EXCEL
  // ============================================================
  async function extractExcelText(file) {
    if (!window.XLSX) {
      await loadScript('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js');
    }
    var buf = await file.arrayBuffer();
    var wb = window.XLSX.read(buf, { type: 'array' });
    var out = '';
    wb.SheetNames.forEach(function (name) {
      out += 'Sheet: ' + name + '\n' +
             window.XLSX.utils.sheet_to_csv(wb.Sheets[name]) + '\n\n';
    });
    return out.trim();
  }

  // ============================================================
  // HELPERS
  // ============================================================
  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = url;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('Failed to load ' + url)); };
      document.head.appendChild(s);
    });
  }

  function showUserMessage(text) {
    var container = document.getElementById('chatContainer');
    if (!container) return;
    var time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    var user = localStorage.getItem('nova-user-name') || 'User';
    var msg = document.createElement('div');
    msg.className = 'chat-message user';
    msg.innerHTML =
      '<div class="chat-avatar">' + (user.charAt(0) || 'U').toUpperCase() + '</div>' +
      '<div>' +
        '<div class="chat-sender">YOU</div>' +
        '<div class="chat-bubble">' + escapeHtml(text) + '</div>' +
        '<div class="chat-time">' + time + '</div>' +
      '</div>';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
  }

  function showNovaMessage(text) {
    var container = document.getElementById('chatContainer');
    if (!container) return;
    var time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    var msg = document.createElement('div');
    msg.className = 'chat-message nova';
    msg.innerHTML =
      '<div class="chat-avatar">N</div>' +
      '<div>' +
        '<div class="chat-sender">NOVA</div>' +
        '<div class="chat-bubble">' + escapeHtml(text).split('\n').join('<br>') + '</div>' +
        '<div class="chat-time">' + time + '</div>' +
      '</div>';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
  }

  function showTyping() {
    var container = document.getElementById('chatContainer');
    if (!container || document.getElementById('typingIndicator')) return;
    var t = document.createElement('div');
    t.className = 'chat-message nova';
    t.id = 'typingIndicator';
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

  function removeTyping() {
    var t = document.getElementById('typingIndicator');
    if (t) t.remove();
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
})();