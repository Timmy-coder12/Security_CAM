"""
Multi-Channel Alert & SMS Dispatcher
Supports:
1. Twilio SMS & MMS (Real cellular SMS/MMS to any phone number)
2. NTFY Push Notification (Free instant mobile push with embedded photo to Android & iOS)
3. Telegram Bot (Instant photo with bounding box + caption to Telegram app)
4. Generic Webhook / Fast2SMS API
"""
import os
import time
import json
import base64
import requests
from threading import Thread

class AlertDispatcher:
    def __init__(self, config=None):
        self.config = config or {}
        self.last_alert_time = 0
        self.cooldown_sec = self.config.get("alert_cooldown_seconds", 30)

    def can_alert(self):
        now = time.time()
        if now - self.last_alert_time >= self.cooldown_sec:
            return True
        return False

    def send_alert_async(self, detected_objects, image_path=None, zone_name=None):
        """Dispatches alerts in a background thread so camera stream never stutters."""
        if not self.can_alert():
            print(f"[*] Alert triggered but ignored due to cooldown ({self.cooldown_sec}s).")
            return False

        self.last_alert_time = time.time()
        t = Thread(target=self._send_all_channels, args=(detected_objects, image_path, zone_name))
        t.daemon = True
        t.start()
        return True

    def _send_all_channels(self, detected_objects, image_path, zone_name):
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        objects_summary = ", ".join([f"{d['class']} ({int(d['conf']*100)}%)" for d in detected_objects])
        
        location_info = f" in {zone_name}" if zone_name else ""
        msg_text = (
            f"🚨 SECURITY ALERT: Detected {objects_summary}{location_info} at {timestamp_str}!"
        )
        print(f"\n[+] DISPATCHING ALERT: {msg_text}")

        # 1. Dispatch NTFY Push (Free, instant with photo on iOS/Android)
        if self.config.get("ntfy_enabled", True):
            ntfy_topic = self.config.get("ntfy_topic", "my_secure_cam_alert_feed")
            self._send_ntfy_push(ntfy_topic, msg_text, image_path)

        # 2. Dispatch Twilio SMS / MMS
        if self.config.get("twilio_enabled", False):
            self._send_twilio_sms(msg_text, image_path)

        # 3. Dispatch Telegram Bot Photo
        if self.config.get("telegram_enabled", False):
            self._send_telegram(msg_text, image_path)

        # 4. Dispatch Webhook / Custom SMS Gateway
        if self.config.get("custom_webhook_enabled", False):
            self._send_webhook(msg_text, image_path)

    def _send_ntfy_push(self, topic, message, image_path):
        """Sends instant push notification to Android/iOS with image preview."""
        url = f"https://ntfy.sh/{topic}"
        headers = {
            "Title": "🚨 Camera Motion Alert!",
            "Priority": "urgent",
            "Tags": "warning,camera"
        }
        try:
            if image_path and os.path.exists(image_path):
                # Upload with image attachment
                with open(image_path, "rb") as img_file:
                    headers["Filename"] = os.path.basename(image_path)
                    headers["Message"] = message
                    res = requests.post(url, data=img_file, headers=headers, timeout=10)
            else:
                res = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)

            if res.status_code in [200, 201]:
                print(f"[✓] NTFY Push alert sent to topic '{topic}' successfully!")
            else:
                print(f"[!] NTFY returned status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[!] NTFY push failed: {e}")

    def _send_twilio_sms(self, message, image_path):
        """Sends real cellular SMS / MMS via Twilio REST API."""
        account_sid = self.config.get("twilio_account_sid")
        auth_token = self.config.get("twilio_auth_token")
        from_number = self.config.get("twilio_from_number")
        to_number = self.config.get("target_phone_number")

        if not all([account_sid, auth_token, from_number, to_number]):
            print("[!] Twilio credentials not fully set in config.json.")
            return

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data = {
            "From": from_number,
            "To": to_number,
            "Body": message
        }

        # Optional public image URL for MMS if configured
        public_image_url = self.config.get("public_snapshot_base_url")
        if public_image_url and image_path:
            img_name = os.path.basename(image_path)
            data["MediaUrl"] = f"{public_image_url.rstrip('/')}/{img_name}"

        try:
            res = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=10)
            if res.status_code in [200, 201]:
                print(f"[✓] Twilio SMS sent to {to_number} successfully! SID: {res.json().get('sid')}")
            else:
                print(f"[!] Twilio SMS failed ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"[!] Twilio request error: {e}")

    def _send_telegram(self, message, image_path):
        """Sends annotated detection photo + message to Telegram."""
        bot_token = self.config.get("telegram_bot_token")
        chat_id = self.config.get("telegram_chat_id")

        if not bot_token or not chat_id:
            print("[!] Telegram bot token or chat ID missing.")
            return

        try:
            if image_path and os.path.exists(image_path):
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                with open(image_path, "rb") as f:
                    res = requests.post(url, data={"chat_id": chat_id, "caption": message}, files={"photo": f}, timeout=15)
            else:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                res = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)

            if res.status_code == 200:
                print("[✓] Telegram alert dispatched successfully!")
            else:
                print(f"[!] Telegram alert error: {res.text}")
        except Exception as e:
            print(f"[!] Telegram request error: {e}")

    def _send_webhook(self, message, image_path):
        webhook_url = self.config.get("custom_webhook_url")
        if not webhook_url:
            return
        payload = {
            "alert": message,
            "timestamp": time.time(),
            "has_image": bool(image_path and os.path.exists(image_path))
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
            print("[✓] Custom webhook fired!")
        except Exception as e:
            print(f"[!] Webhook error: {e}")
