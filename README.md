# \# Elpriser Forecast — Swedish Electricity Price Pipeline \& Dashboard

A data engineering project that ingests Swedish electricity spot prices (zone SE3 — Gothenburg/Stockholm) from a public API, stores them in a structured Azure PostgreSQL warehouse, and visualizes pricing patterns in an interactive Power BI dashboard.

#### \## Problem

Swedish electricity prices vary significantly by time of day, day of week, and season — and have become a major topic for households trying to manage energy costs. This project builds a pipeline that automatically collects daily 15-minute interval price data and makes it easy to explore *when* electricity is cheapest and most expensive.

#### \## Architecture

```
elprisetjustnu.se API
        │
        ▼
  Python ingestion (daily\_ingest.py)
        │
        ▼
  Azure PostgreSQL — star schema
    ├── electricity\_prices  (raw landing table)
    ├── dim\_date             (date dimension: weekday, season, is\_weekend)
    ├── dim\_zone             (price zone dimension)
    └── fact\_prices          (clean fact table, joined and query-ready)
        │
        ▼
  SQL view (vw\_prices\_bi) — flattens dimensions, adds local time \& hour
        │
        ▼
  Power BI Dashboard
```

**Automation:** a Windows Task Scheduler job runs `run\_ingest.bat` daily, which activates the project's virtual environment and executes `daily\_ingest.py` to pull the latest prices and sync them into the warehouse. Output is logged to `logs/ingest\_log.txt`.

#### \## Data Model

The warehouse uses a **star schema**:

* **`fact\_prices`** — one row per 15-minute price interval, linked to `dim\_date` and `dim\_zone` by foreign key
* **`dim\_date`** — one row per calendar date, with pre-calculated `weekday`, `is\_weekend`, and `season`, avoiding repeated date logic in every query
* **`dim\_zone`** — maps zone codes (e.g. `SE3`) to a compact `zone\_id`
* **`electricity\_prices`** — the raw staging table the API data lands in first, deduplicated via a unique constraint on `(time\_start, zone)` so the ingestion script is safe to re-run without creating duplicate rows

A dedicated view, `vw\_prices\_bi`, joins all three warehouse tables into one flat table for Power BI, converting timestamps to local Swedish time and extracting `hour\_of\_day`, `month\_no`, and `month\_name` for easy filtering and correct chronological sorting.

#### \## Dashboard

!\[Dashboard](docs/dashboard.png)

The dashboard includes:

* **Price trend over time** — daily average price, showing seasonal shifts and price spikes
* **Hour × Weekday heatmap** — average price by hour of day and day of week, highlighting the most and least expensive times to use electricity
* **Summary cards** — average, minimum, and maximum price across the dataset
* **Season slicer** — filter the whole dashboard by season

The full interactive report file is available at [`powerbi/elpriser\_dashboard.pbix`](powerbi/elpriser_dashboard.pbix) — open it in Power BI Desktop to explore the data directly.

#### \## Key Findings

* Prices show a clear **daily cycle**, typically rising during morning (7–9am) and evening (5–7pm) demand peaks.
* Weekdays are consistently more expensive than weekends. Ranking average price by day of week: **Tuesday (0.932 SEK/kWh), Wednesday (0.851), Monday (0.824)**, and Thursday (0.796) are the most expensive, while Saturday (0.478) and Sunday (0.481) are roughly 45–50% cheaper — likely reflecting reduced industrial and commercial demand on weekends.
* The dataset includes a **maximum recorded price of 5.18 SEK/kWh** and a **minimum of -0.05 SEK/kWh** — negative pricing is a real, occasional feature of the Nordic electricity market, typically linked to periods of excess renewable supply.
* **December averaged noticeably lower prices (\~0.65 SEK/kWh)** than January and February (\~1.0 SEK/kWh each), despite all three being winter months. A plausible explanation is reduced industrial demand over the holiday period, though confirming this would require cross-referencing actual consumption data rather than price data alone.
* Sweden's electricity market switched from **hourly to 15-minute pricing intervals on October 1, 2025** — all data in this project reflects the newer 15-minute granularity.

#### \## How to Run This Project

**Prerequisites:** Python 3.10+, an Azure PostgreSQL instance, Power BI Desktop (for viewing the dashboard)

```bash
# Clone the repo
git clone https://github.com/AshAk-stack/elpriser-forecast.git
cd elpriser-forecast

# Set up the environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

# Add your database credentials
# Create a .env file with: DB\_HOST, DB\_NAME, DB\_USER, DB\_PASS, DB\_PORT

# Run ingestion manually
python daily\_ingest.py
```

To set up daily automation on Windows, configure Task Scheduler to run `run\_ingest.bat` at a fixed time each day (see script for details).

#### \## What's Next

This project is functional but intentionally scoped small. Possible extensions:

* A forecasting model (baseline + XGBoost) to predict next-day prices — architecture supports this via the existing `fact\_prices` table
* A price-optimization layer suggesting the cheapest windows to run appliances
* Cloud-hosted scheduling (e.g. Azure Functions or Airflow) instead of local Task Scheduler
* Docker containerization for easier reproducibility
* CI pipeline (GitHub Actions) for automated testing

#### \## Tech Stack

Python · pgAdmin · PostgreSQL (Azure) · SQL · Power BI · Git

\---

*Built as part of an active job search in data engineering / data analytics, Sweden.*

