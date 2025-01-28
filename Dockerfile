FROM python:3.11-slim

# StreamK3s environment variables
ENV MY_POD_IP=${MY_POD_IP}
ENV API_PORT=${API_PORT}
ENV PUBLISH_PATH=${PUBLISH_PATH}
ENV MY_POD_NAME=${MY_POD_NAME}
ENV MY_POD_NAMESPACE=${MY_POD_NAMESPACE}
ENV APP_ENV=${APP_ENV}

# Vector logging config
ENV VECTOR_SINK_ADDR=${VECTOR_SINK_ADDR}

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Copy application code and dataset
COPY . .

# Set up non-root user
RUN adduser -u 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app
USER appuser

# Run generator
CMD ["python", "./main.py"]