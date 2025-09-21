#!/usr/bin/env python3
import subprocess
import threading
import time
import os
import sys

def start_streamlit():
    """Start Streamlit in background"""
    time.sleep(5)  # Wait for FastAPI to start
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false"
        ])
    except Exception as e:
        print(f"Streamlit error: {e}")

def start_fastapi():
    """Start FastAPI"""
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Start FastAPI (this will block)
    start_fastapi()
