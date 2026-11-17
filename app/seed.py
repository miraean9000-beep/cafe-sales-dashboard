import csv
from pathlib import Path

from dotenv import load_dotenv

from .storage import store


def seed(database):
    created = 0
    with Path(__file__).with_name("sales.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            row["id"] = f'maven-{row["date"]}'
            row["value"] = float(row["value"])
            created += database.create("data", row)
    return created


if __name__ == "__main__":
    load_dotenv()
    print(f"Imported {seed(store())} records")
