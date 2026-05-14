# Use Python 3.11-slim
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Command to run the application
# Using shell form to expand $PORT
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
