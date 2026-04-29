FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Cloud Run Jobs execute this command
CMD ["python", "-m", "src.main"]
