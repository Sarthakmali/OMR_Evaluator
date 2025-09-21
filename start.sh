#!/bin/bash

# Get the port from Heroku environment variable
PORT=${PORT:-8000}

# Start FastAPI backend in background
echo "Starting FastAPI backend on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 &

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 15

# Check if backend is running
if curl -f http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "Backend is running successfully on port $PORT!"
else
    echo "Backend failed to start, but continuing..."
fi

# Start Streamlit frontend on a different port
STREAMLIT_PORT=$((PORT + 1))
echo "Starting Streamlit frontend on port $STREAMLIT_PORT..."
streamlit run app.py --server.port $STREAMLIT_PORT --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
