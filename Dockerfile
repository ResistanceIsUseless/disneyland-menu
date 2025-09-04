# Use Python slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create cache directory and set permissions
RUN mkdir -p disney_responses && \
    chmod 755 disney_responses

# Set environment variables
ENV FLASK_ENV=production
ENV FLASK_APP=disneyland.py
ENV PORT=8080
ENV HOST=0.0.0.0
ENV CACHE_AUTO_CLEANUP=false

# Create volume for cache persistence (optional)
VOLUME ["/app/disney_responses"]

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "disneyland.py", "--web"]