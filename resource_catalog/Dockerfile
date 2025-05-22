FROM python:3.10-slim

WORKDIR /app

COPY resource_catalog_server.py catalog.json ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

EXPOSE 8080
CMD ["python", "resource_catalog_server.py"]
