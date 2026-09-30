@echo off
cd /d C:\Users\ashwi\elpriser-forecast
call venv\Scripts\activate.bat
python daily_ingest.py >> logs\ingest_log.txt 2>&1