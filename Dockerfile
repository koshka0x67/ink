# E-Paper Display Web Interface Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    zlib1g-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV EPAPER_LOG_FILE=/app/logs/epaper_display.log
ENV EPAPER_CURRENT_IMAGE=/tmp/current_epaper.bmp
ENV EPAPER_CURRENT_IMAGE_BASE=/tmp/current_epaper_base.bmp
ENV EPAPER_SETTINGS_PATH=/tmp/epaper_settings.json
ENV EPAPER_DASHBOARD_PREVIEW=/tmp/dashboard_preview.bmp

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "app.py"]
