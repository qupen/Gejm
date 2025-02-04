#!/bin/sh

echo "Waiting for database to be ready..."
sleep 5

echo "Running database migrations..."
flask db upgrade

echo "Starting Flask application..."
exec python app.py 
