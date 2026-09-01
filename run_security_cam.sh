#!/bin/bash
echo "================================================="
echo "  Starting OmniVision 24/7 Security Cam Daemon"
echo "================================================="
cd python_engine
if [ ! -f config.json ]; then
    cp ../config.json.example config.json
    echo "[+] Created default config.json from template."
fi
pip install -r requirements.txt
python3 security_daemon.py
