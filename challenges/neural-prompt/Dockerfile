# Auto-generated Dockerfile for CyberArena Shared Challenge: 03. Sentinel Core Directives
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CHALLENGE_ID=neural-prompt
ENV PORT=5000
EXPOSE 5000
CMD ["python", "app.py"]
