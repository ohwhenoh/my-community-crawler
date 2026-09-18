#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

# Fetch latest changes from github
git fetch origin main

# Check if there are updates
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")

if [ $LOCAL = $REMOTE ]; then
    echo "Up-to-date. No action needed."
else
    echo "Updates found. Pulling changes and rebuilding..."
    git pull origin main
    docker compose build
    docker compose up -d
    echo "Deployment completed."
fi
