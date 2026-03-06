FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Install the project in editable mode for the CLI to work
RUN pip install -e .

# Expose ports
# 8000: FastAPI
# 8001: WhatsApp Webhook
EXPOSE 8000 8001

# The agent runs via the supervisor by default in production
# but for Docker we can just run main.py or the supervisor's run-forever
# User requested Part 10: simmi start should display specific info.
# In Docker, we can use the CLI to start it.
CMD ["simmi", "start", "--no-background"]
