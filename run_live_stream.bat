@echo off
echo =================================================
echo   Starting OmniVision Live Mobile Streamer
echo =================================================
cd python_engine
pip install -r requirements.txt
python live_mobile_stream.py
pause
