import time
from datetime import date, timedelta
from psycopg2.extras import execute_values
import requests
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = "5432"

conn_string = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS} port={DB_PORT} sslmode=require"

# 2. Date range: Oct 1, 2025 to today
start_date = date(2025, 10, 1)
end_date = date.today()

def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

print("Connecting to Azure PostgreSQL...")
with psycopg2.connect(conn_string) as conn:
    with conn.cursor() as cur:
        # Create table with unique constraint on (time_start, zone)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS electricity_prices (
                id SERIAL PRIMARY KEY,
                time_start TIMESTAMPTZ NOT NULL,
                time_end TIMESTAMPTZ NOT NULL,
                sek_per_kwh NUMERIC(10, 5) NOT NULL,
                eur_per_kwh NUMERIC(10, 5) NOT NULL,
                zone VARCHAR(10) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_interval_zone UNIQUE (time_start, zone)
            );
        """)
        conn.commit()
        print("Table verified/created.")

        total_days = (end_date - start_date).days + 1
        print(f"Starting ingestion of {total_days} days of 15-min intervals...\n")

        for single_date in daterange(start_date, end_date):
            year = single_date.strftime("%Y")
            month_day = single_date.strftime("%m-%d")
            url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_SE3.json"

            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 404:
                    print(f"[{single_date}] No data published yet (404). Skipping.")
                    continue
                resp.raise_for_status()
                day_data = resp.json()
            except Exception as e:
                print(f"[{single_date}] Network error: {e}. Skipping.")
                continue

            # Transform into records tuple
            records = [
                (
                    item["time_start"],
                    item["time_end"],
                    item["SEK_per_kWh"],
                    item["EUR_per_kWh"],
                    "SE3"
                )
                for item in day_data
            ]

            # Bulk insert with ON CONFLICT DO NOTHING
            insert_query = """
                INSERT INTO electricity_prices (time_start, time_end, sek_per_kwh, eur_per_kwh, zone)
                VALUES %s
                ON CONFLICT ON CONSTRAINT unique_interval_zone DO NOTHING;
            """

            execute_values(cur, insert_query, records)
            conn.commit()
            print(f"[{single_date}] Inserted {len(records)} intervals.")

            # Gentle sleep to avoid hammering the free API
            time.sleep(0.1)

print("\nBackfill complete. All data loaded successfully.")