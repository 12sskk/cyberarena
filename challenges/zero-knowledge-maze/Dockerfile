# Auto-generated Dockerfile for CyberArena Shared Challenge: 18. Modular Arithmetic Graph
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CHALLENGE_ID=zero-knowledge-maze
ENV PORT=5000
EXPOSE 5000
CMD ["python", "app.py"]
