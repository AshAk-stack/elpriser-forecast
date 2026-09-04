
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

print("Connecting to Azure to verify data...\n")

with psycopg2.connect(conn_string) as conn:
    with conn.cursor() as cur:
        # 1. Check total row count
        cur.execute("SELECT COUNT(*) FROM electricity_prices;")
        total_rows = cur.fetchone()[0]
        print(f"Total records in database: {total_rows}")

        # 2. View the 5 most recent intervals
        print("\n--- Last 5 Intervals ---")
        cur.execute("""
            SELECT time_start, sek_per_kwh 
            FROM electricity_prices 
            ORDER BY time_start DESC 
            LIMIT 5;
        """)
        for row in cur.fetchall():
            print(f"Time: {row[0]} | Price: {row[1]} SEK")

        # 3. Find the most expensive 15-minute interval so far
        print("\n--- Highest Price Recorded ---")
        cur.execute("""
            SELECT time_start, sek_per_kwh 
            FROM electricity_prices 
            ORDER BY sek_per_kwh DESC 
            LIMIT 1;
        """)
        highest = cur.fetchone()
        print(f"Time: {highest[0]} | Price: {highest[1]} SEK")