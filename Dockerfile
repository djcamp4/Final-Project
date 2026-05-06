FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer — only rebuilds when requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .
COPY app/ app/
COPY .agents/ .agents/

# Cloud Run injects PORT automatically (default 8080)
ENV PORT=8080

CMD ["python3", "server.py"]
