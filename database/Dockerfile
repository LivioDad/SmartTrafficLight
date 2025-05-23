FROM python:3.10-slim

WORKDIR /app

COPY database_adaptor.py database.db database_adaptor_info.json ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

EXPOSE 8081
CMD ["python", "database_adaptor.py"]
