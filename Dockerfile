FROM python:3.11-slim

WORKDIR /app/backend

# Install system dependencies for WeasyPrint + SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-0 \
    libgdk-pixbuf-xlib-2.0-dev \
    libffi-dev \
    shared-mime-info \
    wget \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose FastAPI port
EXPOSE 8010

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
