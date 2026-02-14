FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Install runtime dependencies:
# - TigerVNC (Xvnc): virtual display + VNC in one process for Playwright
# - noVNC (+ websockify): browser-accessible VNC session on a dedicated port
RUN apt-get update && apt-get install -y --no-install-recommends \
    tigervnc-standalone-server \
    tigervnc-tools \
    websockify \
    novnc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers - BOTH chromium AND chrome
RUN playwright install chromium chrome

# Copy application/runtime code
COPY app.py chatgpt_client.py start.sh ./
RUN chmod +x /app/start.sh

# Expose API/noVNC ports
EXPOSE 8000
EXPOSE 6080

# Force Python to output logs immediately (critical for Docker)
ENV PYTHONUNBUFFERED=1

# Environment defaults for Docker/Coolify
# NOTE: Do NOT set CHATGPT_BROWSER_CHANNEL - let it use default chromium
ENV UNLIMITEDGPT_HEADLESS=false
ENV CHATGPT_USE_STEALTH=true
ENV CHATGPT_REAL_BROWSER=false
ENV CHATGPT_IGNORE_AUTOMATION=true
ENV ENABLE_VNC=true
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV APP_PORT=8000

# Run with the startup script
CMD ["/bin/bash", "/app/start.sh"]
