# Auto-generated Dockerfile for CyberArena Shared Challenge: 11. YAML/JSON Config Duel
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CHALLENGE_ID=polyglot-config
ENV PORT=5000
EXPOSE 5000
CMD ["python", "app.py"]
