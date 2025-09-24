FROM python:3.11-slim

WORKDIR /app

# System dependencies (sqlite, build tools for packages like SQLAlchemy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /dbdata

# Copy project files (still overridden by volume in docker-compose)
COPY . .

EXPOSE 8010

# Run uvicorn in reload mode for dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
