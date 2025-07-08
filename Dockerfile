FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Prevent output buffering (helps logging in Docker)
ENV PYTHONUNBUFFERED=1

# Run the bot when the container starts
CMD ["python", "main.py"]
