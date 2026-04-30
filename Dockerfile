FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ЭТО САМОЕ ВАЖНОЕ — правильная команда запуска
CMD ["python", "-m", "support_bot"]