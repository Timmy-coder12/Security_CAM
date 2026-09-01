# OmniVision Security Camera — Real-Time Mobile SMS & Image Notification System

A full-stack, automated smart security camera system designed to monitor a live camera stream, detect target objects (people, animals, vehicles, electronics) using high-accuracy **YOLOv8**, and dispatch **real instant notifications / SMS to your mobile phone with attached photo snapshots of what was detected**.

---

## 🔍 Technical Explanation: Why Did Pen Show as Toothbrush?

Standard lightweight computer vision models (like MobileNet COCO-SSD) are trained on the **COCO 80-Class Dataset**.
* **COCO 80 Classes include:** `person`, `bicycle`, `car`, `motorcycle`, `airplane`, `bus`, `train`, `truck`, `boat`, `traffic light`, `fire hydrant`, `stop sign`, `parking meter`, `bench`, `bird`, `cat`, `dog`, `horse`, `sheep`, `cow`, `elephant`, `bear`, `zebra`, `giraffe`, `backpack`, `umbrella`, `handbag`, `tie`, `suitcase`, `frisbee`, `skis`, `snowboard`, `sports ball`, `kite`, `baseball bat`, `baseball glove`, `skateboard`, `surfboard`, `tennis racket`, `bottle`, `wine glass`, `cup`, `fork`, `knife`, `spoon`, `bowl`, `banana`, `apple`, `sandwich`, `orange`, `broccoli`, `carrot`, `hot dog`, `pizza`, `donut`, `cake`, `chair`, `couch`, `potted plant`, `bed`, `dining table`, `toilet`, `tv`, `laptop`, `mouse`, `remote`, `keyboard`, `cell phone`, `microwave`, `oven`, `toaster`, `sink`, `refrigerator`, `book`, `clock`, `vase`, `scissors`, `teddy bear`, `hair drier`, `toothbrush`.
* **Notice that `pen` or `pencil` is NOT in the dataset!**
* When an object is not in the model's vocabulary, the neural network computes probability scores across the 80 known classes. Because a pen is a long, thin, handheld cylinder, its visual feature map is closest to a `toothbrush` in the 80-class taxonomy.
* `mouse` **is** in the dataset, but because computer mice are small and dark, lightweight models need higher resolution and fine-tuned confidence thresholds.
* **This project provides YOLOv8** (which runs at full 640x640/1280x1280 resolution with deeper spatial pyramids) to reliably detect small objects like computer mice and filter out false positives.

---

## 📲 How Phone Notifications & SMS Work

### Option 1: Instant Mobile Push with Photo (NTFY — Recommended, 100% Free)
NTFY allows you to receive instant notifications with the actual photo snapshot right on your Android phone or iPhone without needing API keys or payment.
1. Download the free **ntfy** app on your phone ([Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or [Apple App Store](https://apps.apple.com/us/app/ntfy/id1625396347)).
2. In the app, tap `+` to subscribe to your topic name (e.g. `my_security_cam_12345`).
3. Set that topic in `config.json` or on the Web Dashboard.
4. When an intruder or object is detected, your phone will ring and show the alert with the full camera snapshot!

### Option 2: Cellular SMS & MMS (Twilio)
Sends standard SMS / MMS directly to your mobile phone number.
1. Create a free account on [Twilio](https://www.twilio.com).
2. Get your `Account SID`, `Auth Token`, and `Twilio Phone Number`.
3. Put them in `python_engine/config.json`:
   ```json
   {
       "twilio_enabled": true,
       "twilio_account_sid": "ACxxxxxx",
       "twilio_auth_token": "your_token",
       "twilio_from_number": "+1234567890",
       "target_phone_number": "+919876543210"
   }
   ```

### Option 3: Telegram Bot Photo Alerts
Sends real-time snapshots with bounding boxes to your Telegram app.
1. Talk to `@BotFather` on Telegram to create a bot and get your token.
2. Put `telegram_bot_token` and `telegram_chat_id` into `config.json`.

---

## 🚀 Quickstart Guide

### 1. Standalone Instant Web Launcher
* Double-click `demo.html` in your browser.
* Enter your phone number or NTFY topic.
* Draw a restricted security zone on the camera feed.
* Click **"Start Security Camera"**.
* The interactive phone simulator on the right will show live alert previews.

### 2. 24/7 Python Security Daemon (Continuous Background Surveillance)
```bash
# On Linux / macOS
./run_security_cam.sh

# On Windows
run_security_cam.bat
```
Or manually:
```bash
cd python_engine
pip install -r requirements.txt
python security_daemon.py
```

### 3. Web Management Portal
```bash
cd python_engine
python web_server.py
# Open http://localhost:5000
```

---

## ⚙️ Configuration Parameters (`config.json`)

| Parameter | Default | Description |
|---|---|---|
| `camera_source` | `0` | Camera device index (`0`, `1`) or RTSP/IP camera stream URL |
| `model_name` | `yolov8n.pt` | YOLOv8 model weights (`yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`) |
| `confidence_threshold` | `0.50` | Minimum confidence score to trigger alert |
| `alert_cooldown_seconds` | `25` | Debounce time to avoid spamming multiple SMS per minute |
| `target_phone_number` | `+1234567890` | Mobile number to receive SMS alerts |
| `ntfy_enabled` | `true` | Enable free instant mobile push alerts with photo |
| `ntfy_topic` | `my_security_cam_alert_feed` | Topic name for your phone |
| `target_classes` | `["person", "car", "dog", "cell phone"]` | Whitelisted objects that trigger alerts |
| `save_local_snapshots` | `true` | Automatically save annotated photos to `alerts/` folder |

---

## 📜 License
MIT License.
