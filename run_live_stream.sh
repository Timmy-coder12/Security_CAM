#!/bin/bash
echo "================================================="
echo "  Starting OmniVision Live Mobile Streamer"
echo "================================================="
cd python_engine
pip install -r requirements.txt
python3 live_mobile_stream.py
