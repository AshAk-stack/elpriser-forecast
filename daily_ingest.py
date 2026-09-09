import os
from datetime import date, timedelta
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import requests

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

conn_string = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS} port={DB_PORT} sslmode=require"

def fetch_and_load_day(target_date: date, cur):
    year = target_date.strftime("%Y")
    month_day = target_date.strftime("%m-%d")
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_SE3.json"

    response = requests.get(url, timeout=10)
    if response.status_code == 404:
        print(f"[{target_date}] Data not available yet (404).")
        return 0
    response.raise_for_status()

    records = [
        (
            item["time_start"],
            item["time_end"],
            item["SEK_per_kWh"],
            item["EUR_per_kWh"],
            "SE3",
        )
        for item in response.json()
    ]

    insert_query = """
        INSERT INTO electricity_prices (time_start, time_end, sek_per_kwh, eur_per_kwh, zone)
        VALUES %s
        ON CONFLICT ON CONSTRAINT unique_interval_zone DO NOTHING;
    """
    execute_values(cur, insert_query, records)
    return len(records)

def fetch_and_load_day(target_date: date, cur):
    """Pull one day's 15-min prices from the API and land them in the raw table."""
    year = target_date.strftime("%Y")
    month_day = target_date.strftime("%m-%d")
    url = f"https://www.elprisetjustnu.se/api/v1/prices/{year}/{month_day}_SE3.json"
 
    response = requests.get(url, timeout=10)
    if response.status_code == 404:
        print(f"[{target_date}] Data not available yet (404).")
        return 0
    response.raise_for_status()
 
    records = [
        (
            item["time_start"],
            item["time_end"],
            item["SEK_per_kWh"],
            item["EUR_per_kWh"],
            "SE3",
        )
        for item in response.json()
    ]
 
    insert_query = """
        INSERT INTO electricity_prices (time_start, time_end, sek_per_kwh, eur_per_kwh, zone)
        VALUES %s
        ON CONFLICT ON CONSTRAINT unique_interval_zone DO NOTHING;
    """
    execute_values(cur, insert_query, records)
    return len(records)
 
 
def upsert_dim_date(target_date: date, cur):
    """Make sure dim_date has a row for this date. Safe to run every time (no-op if it exists)."""
    cur.execute(
        """
        INSERT INTO dim_date (date_id, year, month, day, weekday, is_weekend, season)
        SELECT
            %(d)s::date,
            EXTRACT(YEAR FROM %(d)s::date)::INT,
            EXTRACT(MONTH FROM %(d)s::date)::INT,
            EXTRACT(DAY FROM %(d)s::date)::INT,
            TO_CHAR(%(d)s::date, 'Day'),
            EXTRACT(ISODOW FROM %(d)s::date) IN (6,7),
            CASE
                WHEN EXTRACT(MONTH FROM %(d)s::date) IN (12,1,2) THEN 'Winter'
                WHEN EXTRACT(MONTH FROM %(d)s::date) IN (3,4,5) THEN 'Spring'
                WHEN EXTRACT(MONTH FROM %(d)s::date) IN (6,7,8) THEN 'Summer'
                ELSE 'Autumn'
            END
        ON CONFLICT (date_id) DO NOTHING;
        """,
        {"d": target_date},
    )


def upsert_fact_prices(cur):
    """
    Push any rows from the raw table into fact_prices that aren't there yet.
    Joins to dim_zone to translate the zone code (e.g. 'SE3') into its zone_id.
    """
    cur.execute(
        """
        INSERT INTO fact_prices (date_id, zone_id, time_start, time_end, sek_per_kwh, eur_per_kwh)
        SELECT
            (ep.time_start AT TIME ZONE 'Europe/Stockholm')::date,
            dz.zone_id,
            ep.time_start,
            ep.time_end,
            ep.sek_per_kwh,
            ep.eur_per_kwh
        FROM electricity_prices ep
        JOIN dim_zone dz ON dz.zone_code = ep.zone
        ON CONFLICT (zone_id, time_start) DO NOTHING;
        """
    )    

def run():
    today = date.today()
    tomorrow = today + timedelta(days=1)
 
    print("Connecting to Azure PostgreSQL...")
    with psycopg2.connect(conn_string) as conn:
        with conn.cursor() as cur:
 
            for day in (today, tomorrow):
                inserted = fetch_and_load_day(day, cur)
                upsert_dim_date(day, cur)
                conn.commit()
                print(f"[{day}] Raw: {inserted} intervals ingested. dim_date row ensured.")
 
            upsert_fact_prices(cur)
            conn.commit()
            print("fact_prices synced with electricity_prices.")
 
    print("\nDaily ingestion + modeling complete.")

if __name__ == "__main__":
    run()