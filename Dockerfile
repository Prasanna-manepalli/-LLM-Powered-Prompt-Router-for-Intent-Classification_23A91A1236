# Simple Dockerfile for the LLM prompt router (Python)

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The default command runs the batch tests, which will also generate
# route_log.jsonl inside the container.
CMD ["python", "main.py", "--batch-test"]
