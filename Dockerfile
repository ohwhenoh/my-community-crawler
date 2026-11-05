# ==============================================================================
# Multi-Architecture Production Dockerfile (Debian ARM & Ubuntu x86-64 Compatible)
# ==============================================================================
FROM python:3.11-slim

# Set timezone and production-grade environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

WORKDIR /app

# Install system dependencies (including timezone configuration)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
# 플레이 라이트는 오래된 스크래퍼에서만 쓰므로, 기본 이미지에서는 빼서 가볍게 한다.
# 동적 스크래핑이 필요하면 별도 이미지에서 설치한다.


# Copy application source files
COPY *.py .

COPY targets.json .
COPY trends_cache.json .
COPY templates/ templates/

# Note: .env is not copied during build to maintain secret isolation.
# It will be mounted via docker-compose volume for absolute security.

EXPOSE 5001

# Default command can be overridden in docker-compose
CMD ["python", "-u", "scheduler_daemon.py"]
