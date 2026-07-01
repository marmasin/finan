# Slika za deploy Streamlit aplikacije na Google Cloud Run.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Prvo samo ovisnosti (bolji cache slojeva).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod aplikacije (baza NE ide u sliku — čuva se u GCS-u; vidi .dockerignore).
COPY . .

# Cloud Run šalje port kroz varijablu $PORT. Streamlit ga mora slušati na 0.0.0.0.
ENV PORT=8080
EXPOSE 8080

CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true
