import os
import json
import random
import statistics
from datetime import datetime, timedelta

# ==============================================
# Simulated Weather Data Collection & Analysis System
# ==============================================

DATA_DIR = "data"
CACHE_FILE = os.path.join(DATA_DIR, "weather_cache.json")

# ---------- Utility Functions ----------
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def generate_fake_data(days=7):
    """Generate random temperature data for N days"""
    records = []
    base_date = datetime.now() - timedelta(days=days)
    for i in range(days):
        date = base_date + timedelta(days=i)
        record = {
            "date": date.strftime("%Y-%m-%d"),
            "high": random.randint(15, 35),
            "low": random.randint(5, 20),
            "rain": random.choice([True, False])
        }
        records.append(record)
    return records

def save_to_cache(data):
    ensure_data_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_from_cache():
    if not os.path.exists(CACHE_FILE):
        return []
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- Data Processing ----------
def analyze_temperature(data):
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]
    result = {
        "avg_high": statistics.mean(highs) if highs else None,
        "avg_low": statistics.mean(lows) if lows else None,
        "max_high": max(highs) if highs else None,
        "min_low": min(lows) if lows else None,
    }
    return result

def rain_statistics(data):
    total = len(data)
    rain_days = sum(1 for d in data if d["rain"])
    rain_rate = rain_days / total if total else 0
    return {
        "rain_days": rain_days,
        "rain_rate": round(rain_rate * 100, 2)
    }

# ---------- Summary Computation ----------
def compute_summary(data):
    """Aggregate all computed statistics"""
    t_stats = analyze_temperature(data)
    r_stats = rain_statistics(data)
    return {
        "temperature": t_stats,
        "rainfall": r_stats,
        "total_days": len(data)
    }

# ---------- Output Module ----------
def pretty_print_summary(summary):
    print("=== Weather Summary ===")
    print(f"Days: {summary['total_days']}")
    print(f"Avg High: {summary['temperature']['avg_high']:.2f} °C")
    print(f"Avg Low : {summary['temperature']['avg_low']:.2f} °C")
    print(f"Max High: {summary['temperature']['max_high']} °C")
    print(f"Min Low : {summary['temperature']['min_low']} °C")
    print(f"Rain Days: {summary['rainfall']['rain_days']}")
    print(f"Rain Rate: {summary['rainfall']['rain_rate']} %")
    print("========================")

# ---------- Main Workflow ----------
def main(days=7):
    print("[INFO] Starting weather data analyzer...")
    cache = load_from_cache()
    if not cache:
        print("[INFO] No cache found, generating new data...")
        cache = generate_fake_data(days)
        save_to_cache(cache)
    else:
        print("[INFO] Loaded cached weather data.")

    summary = compute_summary(cache)
    pretty_print_summary(summary)

    # Basic weather trend message
    if summary["temperature"]["avg_high"] > 30:
        print("  High average temperature detected. Stay hydrated!")
    elif summary["temperature"]["avg_low"] < 10:
        print("  Low temperatures expected. Keep warm!")
    else:
        print("  Weather conditions are moderate and pleasant.")

    # Dynamic closure test: nested local function
    def day_by_day_report():
        for d in cache:
            print(f"{d['date']}: {d['high']} / {d['low']} °C, {'Rain' if d['rain'] else 'Clear'}")

    day_by_day_report()

if __name__ == "__main__":
    main(10)



