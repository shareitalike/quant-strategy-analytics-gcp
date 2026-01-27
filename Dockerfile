FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run expects port 8080
EXPOSE 8080

# Configurable data path (mounted or GCS-fuse)
ENV DATA_PATH="/app/data"

CMD ["streamlit", "run", "app.py",
     "--server.port=8080",
     "--server.address=0.0.0.0"]
