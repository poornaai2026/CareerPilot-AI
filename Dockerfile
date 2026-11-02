FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Expose Web Command Center port
EXPOSE 8000

# Start CareerPilot Command Center
CMD ["python", "main.py", "dashboard", "--port", "8000"]

