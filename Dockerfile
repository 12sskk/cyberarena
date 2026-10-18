FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate all 18 standalone challenge build contexts
RUN python generate_docker_challenges.py

EXPOSE 5000

CMD ["python", "app.py"]
