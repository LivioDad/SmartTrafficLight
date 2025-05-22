FROM python:3.10-slim

WORKDIR /app

COPY telegram_bot.py dynamic_charts.py telegram_bot_info.json ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

CMD ["python", "telegram_bot.py"]
