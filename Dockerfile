FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y gcc g++ && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN useradd -m -u 1000 appuser

COPY app/ ./app/
COPY api/ ./api/
COPY cache/ ./cache/
COPY core/ ./core/
COPY magnet/ ./magnet/
COPY models/ ./models/
COPY scraper/ ./scraper/
COPY tracker/ ./tracker/
COPY utils/ ./utils/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 7006

CMD ["python", "-m", "app.main"]
