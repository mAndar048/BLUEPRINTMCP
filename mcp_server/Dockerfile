# Use official Python 3.11 slim image for deterministic builds
FROM python:3.11-slim

# Set a clean working directory inside the container
WORKDIR /app

# Copy dependency list first to leverage Docker layer caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Expose the MCP server port
EXPOSE 8000

# Run the MCP server on all interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
