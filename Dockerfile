# Use an official Python runtime as a parent image
FROM python:3.9

# Set environment variables
ENV SECRET_KEY='your_secret_key'

# Set the working directory in the container
WORKDIR /usr/src/app

# Install zbar shared library
RUN apt-get update && apt-get install -y \
    zbar-tools \
    libzbar0

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
