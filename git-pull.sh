#!/bin/bash
set -e

# 1. Fetch latest changes
echo "Fetching latest changes..."
git fetch origin

# 2. Reset core/lang JSON files to remote version
echo "Overwriting /backend/core/lang/*.json with remote..."
git checkout origin/main -- backend/core/lang/*.json

# 3. Keep local data JSON files (force local version)
echo "Restoring local /backend/data/*.json..."
git checkout HEAD -- backend/data/*.json

# 4. Pull remaining changes
echo "Pulling other changes..."
git pull --rebase

echo "Git update completed."