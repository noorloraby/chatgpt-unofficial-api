FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Install Xvfb for virtual display (bypasses headless detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY app.py chatgpt_client.py ./

# Expose the API port
EXPOSE 8000

# Force Python to output logs immediately (critical for Docker)
ENV PYTHONUNBUFFERED=1

# Environment defaults (can be overridden in Coolify)
ENV UNLIMITEDGPT_HEADLESS=false
ENV CHATGPT_USE_STEALTH=true
ENV CHATGPT_REAL_BROWSER=false
ENV CHATGPT_IGNORE_AUTOMATION=true

# Create startup script for better logging
RUN echo '#!/bin/bash\n\
    echo "Starting Xvfb..."\n\
    Xvfb :99 -screen 0 1920x1080x24 &\n\
    sleep 2\n\
    export DISPLAY=:99\n\
    echo "Xvfb started on display :99"\n\
    echo "Starting uvicorn..."\n\
    exec python -m uvicorn app:app --host 0.0.0.0 --port 8000\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Run with the startup script
CMD ["/bin/bash", "/app/start.sh"]
