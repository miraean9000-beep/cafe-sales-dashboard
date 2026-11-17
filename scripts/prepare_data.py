import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "sales.csv"


def prepare(source):
    totals = defaultdict(Decimal)
    products = defaultdict(Counter)
    with open(source, encoding="utf-8-sig", newline="") as source_file:
        for record in csv.DictReader(source_file):
            if record["store_location"] != "Lower Manhattan":
                continue
            day = datetime.strptime(record["transaction_date"], "%m/%d/%Y").date().isoformat()
            quantity = int(record["transaction_qty"])
            totals[day] += quantity * Decimal(record["unit_price"])
            products[day][record["product_detail"]] += quantity
    if len(totals) < 100:
        raise ValueError("Expected at least 100 distinct days for Lower Manhattan")
    with TARGET.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["date", "value", "memo"])
        for day, total in sorted(totals.items()):
            counts = products[day]
            writer.writerow([day, f"{total:.2f}", f"판매 {counts.total()}개 · 최다 판매 {counts.most_common(1)[0][0]}"])
    print(f"Prepared {len(totals)} days")


if __name__ == "__main__":
    prepare(sys.argv[1])
