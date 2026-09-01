document.addEventListener('DOMContentLoaded', async () => {
  const video = document.getElementById('camera-video');
  const canvas = document.getElementById('overlay-canvas');
  const zoneCanvas = document.getElementById('zone-canvas');
  const ctx = canvas.getContext('2d');
  const zoneCtx = zoneCanvas ? zoneCanvas.getContext('2d') : null;

  const btnStart = document.getElementById('btn-start');
  const btnStop = document.getElementById('btn-stop');
  const btnZone = document.getElementById('btn-zone');
  const btnClearZone = document.getElementById('btn-clear-zone');
  const btnTestSMS = document.getElementById('btn-test-sms');

  const inputPhone = document.getElementById('input-phone');
  const inputNtfyTopic = document.getElementById('input-ntfy-topic');
  const inputCooldown = document.getElementById('input-cooldown');
  const sliderConf = document.getElementById('slider-conf');
  const badgeConf = document.getElementById('badge-conf');

  const toggleNtfy = document.getElementById('toggle-ntfy');
  const toggleSms = document.getElementById('toggle-sms');
  const toggleZoneOnly = document.getElementById('toggle-zone-only');

  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');

  let stream = null;
  let isRunning = false;
  let animId = null;

  // Initialize Detector
  await window.secDetector.load();
  if (statusText) statusText.textContent = 'AI Security Engine Armed';

  // Zone drawing
  let drawing = false;
  let sx = 0, sy = 0;

  if (zoneCanvas) {
    zoneCanvas.addEventListener('mousedown', (e) => {
      if (!window.secDetector.isDrawingZone) return;
      const r = zoneCanvas.getBoundingClientRect();
      sx = (e.clientX - r.left) * (zoneCanvas.width / r.width);
      sy = (e.clientY - r.top) * (zoneCanvas.height / r.height);
      drawing = true;
    });

    zoneCanvas.addEventListener('mousemove', (e) => {
      if (!drawing || !window.secDetector.isDrawingZone) return;
      const r = zoneCanvas.getBoundingClientRect();
      const cx = (e.clientX - r.left) * (zoneCanvas.width / r.width);
      const cy = (e.clientY - r.top) * (zoneCanvas.height / r.height);

      zoneCtx.clearRect(0, 0, zoneCanvas.width, zoneCanvas.height);
      zoneCtx.strokeStyle = '#f43f5e';
      zoneCtx.lineWidth = 2;
      zoneCtx.setLineDash([4, 4]);
      zoneCtx.strokeRect(Math.min(sx, cx), Math.min(sy, cy), Math.abs(cx - sx), Math.abs(cy - sy));
    });

    zoneCanvas.addEventListener('mouseup', (e) => {
      if (!drawing || !window.secDetector.isDrawingZone) return;
      drawing = false;
      const r = zoneCanvas.getBoundingClientRect();
      const ex = (e.clientX - r.left) * (zoneCanvas.width / r.width);
      const ey = (e.clientY - r.top) * (zoneCanvas.height / r.height);

      const px = Math.min(sx, ex);
      const py = Math.min(sy, ey);
      const pw = Math.abs(ex - sx);
      const ph = Math.abs(ey - sy);

      if (pw > 20 && ph > 20) {
        window.secDetector.securityZone = {
          x: px / zoneCanvas.width,
          y: py / zoneCanvas.height,
          w: pw / zoneCanvas.width,
          h: ph / zoneCanvas.height
        };
      }
      zoneCtx.clearRect(0, 0, zoneCanvas.width, zoneCanvas.height);
      window.secDetector.isDrawingZone = false;
      btnZone.classList.remove('btn-active');
      btnZone.textContent = '📐 Draw Security Zone';
    });
  }

  // Camera start
  async function startCam() {
    if (isRunning) return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false
      });
      video.srcObject = stream;
      await video.play();

      isRunning = true;
      btnStart.disabled = true;
      btnStop.disabled = false;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      if (zoneCanvas) {
        zoneCanvas.width = video.videoWidth;
        zoneCanvas.height = video.videoHeight;
      }

      runLoop();
    } catch (e) {
      alert('Camera error: ' + e.message);
    }
  }

  function stopCam() {
    if (!isRunning) return;
    if (animId) cancelAnimationFrame(animId);
    if (stream) stream.getTracks().forEach(t => t.stop());
    video.srcObject = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    isRunning = false;
    btnStart.disabled = false;
    btnStop.disabled = true;
  }

  // Detection loop
  async function runLoop() {
    if (!isRunning) return;

    const detections = await window.secDetector.detect(video);
    const isZoneIntrusion = window.secDetector.renderHUD(ctx, detections, canvas.width, canvas.height);

    const zoneOnly = toggleZoneOnly ? toggleZoneOnly.checked : false;
    const triggerCondition = zoneOnly ? isZoneIntrusion : (detections.length > 0);

    const feedBox = document.querySelector('.camera-feed-box');

    if (triggerCondition) {
      if (feedBox) feedBox.classList.add('intruder-active');
      if (statusDot) statusDot.className = 'dot alerting';

      if (window.notifyEngine.canSend()) {
        const snap = window.secDetector.generateSnapshot(video, canvas, detections);
        window.notifyEngine.dispatchSecurityAlert(
          detections,
          snap,
          isZoneIntrusion ? 'Restricted Zone' : 'Camera Sight'
        );
        window.secAudio.playSiren();
        window.secAudio.speak('Warning: Target detected');
      }
    } else {
      if (feedBox) feedBox.classList.remove('intruder-active');
      if (statusDot) statusDot.className = 'dot';
    }

    animId = requestAnimationFrame(runLoop);
  }

  // UI Event Handlers
  btnStart.addEventListener('click', startCam);
  btnStop.addEventListener('click', stopCam);

  btnZone.addEventListener('click', () => {
    window.secDetector.isDrawingZone = !window.secDetector.isDrawingZone;
    if (window.secDetector.isDrawingZone) {
      btnZone.classList.add('btn-active');
      btnZone.textContent = '✏️ Drag Box on Camera...';
    } else {
      btnZone.classList.remove('btn-active');
      btnZone.textContent = '📐 Draw Security Zone';
    }
  });

  btnClearZone.addEventListener('click', () => {
    window.secDetector.securityZone = null;
    if (zoneCtx) zoneCtx.clearRect(0, 0, zoneCanvas.width, zoneCanvas.height);
  });

  btnTestSMS.addEventListener('click', () => {
    const testDets = [{ class: 'Person (Demo Test)', score: 0.96, bbox: [0, 0, 100, 100] }];
    const snap = window.secDetector.generateSnapshot(video, canvas, testDets);
    window.notifyEngine.dispatchSecurityAlert(testDets, snap, 'Test Area');
  });

  inputPhone.addEventListener('input', () => {
    window.notifyEngine.phone = inputPhone.value;
  });

  inputNtfyTopic.addEventListener('input', () => {
    window.notifyEngine.ntfyTopic = inputNtfyTopic.value;
  });

  inputCooldown.addEventListener('input', () => {
    window.notifyEngine.cooldownSec = parseInt(inputCooldown.value, 10) || 20;
  });

  sliderConf.addEventListener('input', () => {
    const val = parseFloat(sliderConf.value);
    window.secDetector.minConfidence = val;
    badgeConf.textContent = `${Math.round(val * 100)}%`;
  });

  toggleNtfy.addEventListener('change', () => {
    window.notifyEngine.useNtfy = toggleNtfy.checked;
  });

  toggleSms.addEventListener('change', () => {
    window.notifyEngine.useTwilio = toggleSms.checked;
  });
});
