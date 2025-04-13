#!/bin/bash
# Rebuilds the MLB model from scratch

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing packages..."
pip install -r requirements.txt

echo "Running model pipeline..."
python MyModelFromScratch.py
python odds_scraper_with_fallback.py
python merge_boxscores_with_odds.py
python make_predictions.py
