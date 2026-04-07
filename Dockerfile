FROM python:3.12-slim

WORKDIR /app

# Install git (needed for pip to install from git repositories)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Expose port 8080 for the health check endpoint
EXPOSE 8080

CMD ["python", "bot.py"]
