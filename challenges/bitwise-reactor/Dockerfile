# Auto-generated Dockerfile for CyberArena Shared Challenge: 08. Bitwise Reactor Gates
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CHALLENGE_ID=bitwise-reactor
ENV PORT=5000
EXPOSE 5000
CMD ["python", "app.py"]
