class SecurityAudio {
  constructor() {
    this.ctx = null;
    this.audioEnabled = true;
    this.speechEnabled = true;
    this.lastSpeech = 0;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playSiren() {
    if (!this.audioEnabled) return;
    this.init();
    if (!this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const now = this.ctx.currentTime;

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(500, now);
      osc.frequency.linearRampToValueAtTime(1000, now + 0.2);
      osc.frequency.linearRampToValueAtTime(500, now + 0.4);

      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.45);
    } catch(e) {}
  }

  speak(text) {
    if (!this.speechEnabled || !('speechSynthesis' in window)) return;
    const now = Date.now();
    if (now - this.lastSpeech < 4000) return;
    this.lastSpeech = now;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.05;
      window.speechSynthesis.speak(u);
    } catch(e) {}
  }
}
window.secAudio = new SecurityAudio();
