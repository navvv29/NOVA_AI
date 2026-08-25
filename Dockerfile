FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY .env.example .env.example

# Set default environment variables
ENV PYTHONUNBUFFERED=1
ENV NOVA_WORKSPACE=/app/data

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

# Run the web server
CMD ["python", "-m", "src.web"]
