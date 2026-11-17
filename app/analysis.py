from datetime import date
from itertools import groupby


def summarize(rows):
    if not rows:
        return {"count": 0, "currency": "USD", "trend": "기록 없음", "series": []}

    rows = sorted(rows, key=lambda row: row["date"])
    daily = {
        date.fromisoformat(day): round(sum(row["value"] for row in records), 2)
        for day, records in groupby(rows, key=lambda row: row["date"])
    }
    end = max(daily)
    start = min(daily)

    def window(offset):
        last = end.toordinal() - offset
        first = last - 6
        values = [value for day, value in daily.items() if first <= day.toordinal() <= last]
        return {"start": date.fromordinal(first).isoformat() if first > 0 else None,
                "end": date.fromordinal(last).isoformat() if last > 0 else None,
                "days": len(values), "total": round(sum(values), 2)}

    recent, previous = window(0), window(7)
    complete = recent["days"] == previous["days"] == 7
    change = round(recent["total"] - previous["total"], 2) if complete else None
    percent = round(100 * change / previous["total"], 2) if complete and previous["total"] else None
    trend = "기록 부족" if change is None else "증가" if change > 0 else "감소" if change < 0 else "유지"
    peak = max(daily, key=daily.get)
    total = round(sum(daily.values()), 2)
    return {
        "count": len(daily), "records": len(rows), "currency": "USD",
        "start": start.isoformat(), "end": end.isoformat(), "total": total,
        "average": round(total / len(daily), 2), "minimum": min(daily.values()),
        "maximum": daily[peak], "peak_date": peak.isoformat(),
        "peak_memos": [row["memo"] for row in rows if row["date"] == peak.isoformat() and row["memo"]][:5],
        "recent": recent, "previous": previous, "change": change, "change_percent": percent, "trend": trend,
        "series": [{"date": day.isoformat(), "value": value} for day, value in daily.items()],
    }
