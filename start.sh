#!/bin/bash

# Start FastAPI backend in background
echo "Starting FastAPI backend..."
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 &

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 10

# Check if backend is running
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend is running successfully!"
else
    echo "Backend failed to start, but continuing with frontend..."
fi

# Start Streamlit frontend
echo "Starting Streamlit frontend..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
