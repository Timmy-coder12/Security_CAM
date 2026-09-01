/**
 * Mobile Push Notification Dispatcher with Real Photo Attachments
 */
class NotificationEngine {
  constructor() {
    this.phone = '+1234567890';
    this.ntfyTopic = 'my_secure_camera_alerts';
    this.cooldownSec = 10;
    this.lastAlertTime = 0;
    this.alertHistory = [];
  }

  canSend() {
    const now = Date.now() / 1000;
    return (now - this.lastAlertTime >= this.cooldownSec);
  }

  async dispatchSecurityAlert(detections, snapshotDataUrl, zoneName = null) {
    if (!this.canSend()) return false;
    this.lastAlertTime = Date.now() / 1000;

    const timeStr = new Date().toLocaleTimeString();
    const classNames = detections.map(d => `${d.class} (${Math.round(d.score * 100)}%)`).join(', ');
    const locText = zoneName ? ` in ${zoneName}` : '';
    const alertMsg = `SECURITY ALERT: Detected ${classNames}${locText} at ${timeStr}!`;

    console.log('[+] Dispatching mobile notification with snapshot:', alertMsg);

    // 1. Update UI Phone Simulator
    this.updatePhoneMockup(alertMsg, snapshotDataUrl, timeStr);

    // 2. Dispatch Real NTFY Push with Photo Snapshot Attached
    if (this.ntfyTopic) {
      await this.sendNtfyWithSnapshot(alertMsg, snapshotDataUrl);
    }

    // 3. Log event
    const alertEntry = {
      id: 'alert_' + Date.now(),
      time: timeStr,
      msg: alertMsg,
      image: snapshotDataUrl,
      targets: classNames
    };
    this.alertHistory.unshift(alertEntry);
    this.renderAlertLogs();

    return true;
  }

  async sendNtfyWithSnapshot(message, snapshotDataUrl) {
    const topic = (this.ntfyTopic || 'my_secure_camera_alerts').trim();
    if (!topic) return;

    try {
      // Clean ASCII message for HTTP headers
      const asciiMsg = message.replace(/[^\x20-\x7E]/g, '').trim();

      if (snapshotDataUrl) {
        // Convert base64 dataUrl to binary JPEG Blob
        const res = await fetch(snapshotDataUrl);
        const imageBlob = await res.blob();

        // Upload photo directly to NTFY
        const pushRes = await fetch(`https://ntfy.sh/${encodeURIComponent(topic)}`, {
          method: 'POST',
          body: imageBlob,
          headers: {
            'Title': 'Security Cam Alert: Target Detected',
            'Message': asciiMsg,
            'Filename': `snapshot_${Date.now()}.jpg`,
            'Priority': '4',
            'Tags': 'warning,camera'
          }
        });

        if (pushRes.ok) {
          console.log(`[✓] PHOTO ALERT sent to phone on topic: ${topic}`);
        } else {
          console.warn('NTFY photo push error:', await pushRes.text());
        }
      } else {
        // Fallback text-only if snapshot unavailable
        await fetch('https://ntfy.sh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: topic,
            title: 'Security Cam Alert',
            message: asciiMsg,
            priority: 4,
            tags: ['warning', 'camera']
          })
        });
      }
    } catch (e) {
      console.error('Mobile push error:', e);
    }
  }

  updatePhoneMockup(message, snapshotDataUrl, timeStr) {
    const container = document.getElementById('phone-alert-container');
    if (!container) return;

    container.innerHTML = `
      <div class="phone-notification-banner">
        <div class="banner-header">
          <span class="banner-app">🚨 SECURITY ALARM</span>
          <span class="banner-time">${timeStr}</span>
        </div>
        <div class="banner-body">${message}</div>
        ${snapshotDataUrl ? `<img src="${snapshotDataUrl}" class="banner-image-preview" alt="Alert Snapshot" />` : ''}
      </div>
    `;
  }

  renderAlertLogs() {
    const logList = document.getElementById('alert-event-feed');
    if (!logList) return;

    if (this.alertHistory.length === 0) {
      logList.innerHTML = '<div style="text-align: center; color: var(--text-dim); padding: 1.5rem; font-size: 0.78rem;">No alerts fired yet.</div>';
      return;
    }

    logList.innerHTML = this.alertHistory.slice(0, 15).map(item => `
      <div class="event-entry alert-fired">
        <div>
          <div class="event-title">${item.targets}</div>
          <div class="event-ts">${item.time}</div>
        </div>
        <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 0.68rem;" onclick="window.notifyEngine.previewAlert('${item.id}')">View</button>
      </div>
    `).join('');
  }

  previewAlert(id) {
    const item = this.alertHistory.find(x => x.id === id);
    if (item) {
      this.updatePhoneMockup(item.msg, item.image, item.time);
    }
  }
}

window.notifyEngine = new NotificationEngine();
