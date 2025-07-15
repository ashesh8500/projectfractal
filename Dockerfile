# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements_production.txt .
RUN pip install --no-cache-dir -r requirements_production.txt

# Copy the rest of the application code
COPY . .

# The port the gRPC server listens on, provided by Cloud Run
# EXPOSE $PORT is not needed for Cloud Run when using shell form of CMD
# EXPOSE 50051

# Command to run the application
CMD ["python", "server.py"]
