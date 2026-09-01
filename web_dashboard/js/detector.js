/**
 * Security Detector Engine with Zone Monitoring & Snapshot Composer
 */
class ClientDetector {
  constructor() {
    this.model = null;
    this.isLoaded = false;
    this.minConfidence = 0.45;
    this.targetWhitelist = new Set(['person', 'cell phone', 'mouse', 'backpack', 'bottle', 'car', 'dog', 'cat', 'laptop']);
    this.securityZone = null; // {x, y, w, h} normalized
    this.isDrawingZone = false;
  }

  async load() {
    if (this.model) return true;
    try {
      if (typeof cocoSsd === 'undefined') throw new Error('cocoSsd script missing');
      this.model = await cocoSsd.load({ base: 'mobilenet_v2' });
      this.isLoaded = true;
      return true;
    } catch(e) {
      console.error('Model load failed:', e);
      return false;
    }
  }

  async detect(videoEl) {
    if (!this.model || !videoEl || videoEl.readyState < 2) return [];
    try {
      const raw = await this.model.detect(videoEl, 15);
      return raw.filter(d => {
        if (d.score < this.minConfidence) return false;
        if (this.targetWhitelist.size > 0 && !this.targetWhitelist.has(d.class.toLowerCase())) {
          return false;
        }
        return true;
      });
    } catch(e) {
      return [];
    }
  }

  checkZone(det, w, h) {
    if (!this.securityZone) return false;
    const [bx, by, bw, bh] = det.bbox;
    const cx = bx + bw / 2;
    const cy = by + bh / 2;
    const zx = this.securityZone.x * w;
    const zy = this.securityZone.y * h;
    const zw = this.securityZone.w * w;
    const zh = this.securityZone.h * h;
    return (cx >= zx && cx <= zx + zw && cy >= zy && cy <= zy + zh);
  }

  renderHUD(ctx, detections, w, h) {
    ctx.clearRect(0, 0, w, h);

    // Draw Zone
    if (this.securityZone) {
      const zx = this.securityZone.x * w;
      const zy = this.securityZone.y * h;
      const zw = this.securityZone.w * w;
      const zh = this.securityZone.h * h;
      ctx.save();
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 6]);
      ctx.strokeRect(zx, zy, zw, zh);
      ctx.fillStyle = 'rgba(244, 63, 94, 0.15)';
      ctx.fillRect(zx, zy, zw, zh);
      ctx.fillStyle = '#f43f5e';
      ctx.font = 'bold 11px monospace';
      ctx.fillText('RESTRICTED SECURITY ZONE', zx + 8, zy + 18);
      ctx.restore();
    }

    let intrusion = false;

    detections.forEach(det => {
      const [x, y, bw, bh] = det.bbox;
      const conf = Math.round(det.score * 100);
      const isIntruder = this.checkZone(det, w, h);
      if (isIntruder) intrusion = true;

      const color = isIntruder ? '#f43f5e' : '#00f2fe';

      // Draw box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(x, y, bw, bh);

      // Corner brackets
      const cLen = Math.min(16, Math.min(bw, bh) / 3);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(x, y, cLen, 3);
      ctx.fillRect(x, y, 3, cLen);
      ctx.fillRect(x + bw - cLen, y, cLen, 3);
      ctx.fillRect(x + bw - 3, y, 3, cLen);

      // Tag badge
      const tag = `${det.class.toUpperCase()} ${conf}%`;
      ctx.font = 'bold 11px monospace';
      const tw = ctx.measureText(tag).width;
      ctx.fillStyle = isIntruder ? '#f43f5e' : 'rgba(10, 14, 23, 0.85)';
      ctx.fillRect(x, Math.max(0, y - 20), tw + 10, 20);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(tag, x + 5, Math.max(14, y - 6));
    });

    return intrusion;
  }

  generateSnapshot(videoEl, canvasEl, detections) {
    if (!videoEl || videoEl.videoWidth === 0) return null;
    const w = videoEl.videoWidth;
    const h = videoEl.videoHeight;
    const off = document.createElement('canvas');
    off.width = w;
    off.height = h;
    const offCtx = off.getContext('2d');

    offCtx.drawImage(videoEl, 0, 0, w, h);
    if (canvasEl) offCtx.drawImage(canvasEl, 0, 0, w, h);

    // Banner Watermark
    offCtx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    offCtx.fillRect(0, h - 30, w, 30);
    offCtx.fillStyle = '#f43f5e';
    offCtx.font = 'bold 12px monospace';
    const ts = new Date().toISOString().replace('T', ' ').substring(0, 19);
    offCtx.fillText(`SECURITY ALERT PHOTO | ${ts} | TARGETS: ${detections.length}`, 12, h - 10);

    return off.toDataURL('image/jpeg', 0.85);
  }
}
window.secDetector = new ClientDetector();
