@echo off
echo =================================================
echo   Starting OmniVision 24/7 Security Cam Daemon
echo =================================================
cd python_engine
if not exist config.json (
    copy ..\config.json.example config.json
    echo [+] Created default config.json from template.
)
pip install -r requirements.txt
python security_daemon.py
pause
