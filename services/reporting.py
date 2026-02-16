"""PDF exports (weekly report).

No paid APIs.
Uses reportlab (pure python). Generates bytes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from services.risk_index import compute_daily_risk


def _date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def build_weekly_pdf(profile: dict[str, Any], logs: list[dict[str, Any]]) -> bytes:
    """Create a 7-day PDF summary from stored logs."""

    # Filter last 7 days (including today)
    today = datetime.now().date()
    start = today - timedelta(days=6)
    week_logs = [l for l in logs if l.get("date") and start <= _date(l["date"]).date() <= today]

    # Group by day
    by_day: dict[str, list[dict[str, Any]]] = {}
    for l in week_logs:
        by_day.setdefault(l["date"], []).append(l)

    def totals(day_items: list[dict[str, Any]]) -> dict[str, float]:
        return {
            "cal": sum(float(x.get("calories", 0) or 0) for x in day_items),
            "p": sum(float(x.get("protein", 0) or 0) for x in day_items),
            "c": sum(float(x.get("carbs", 0) or 0) for x in day_items),
            "f": sum(float(x.get("fat", 0) or 0) for x in day_items),
            "sugar": sum(float(x.get("sugar", 0) or 0) for x in day_items),
            "sodium": sum(float(x.get("sodium", 0) or 0) for x in day_items),
        }

    # Weekly metrics
    days_sorted = sorted(by_day.keys())
    risk_vals = [compute_daily_risk(by_day[d], profile)["score"] for d in days_sorted]
    avg_risk = round(sum(risk_vals) / max(1, len(risk_vals)), 1)
    avg_cal = round(sum(totals(by_day[d])["cal"] for d in days_sorted) / max(1, len(days_sorted)), 0)

    # Build PDF
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    y = h - 0.8 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.8 * inch, y, "NutriVision AI — Weekly Health Report")

    y -= 0.35 * inch
    c.setFont("Helvetica", 10)
    c.drawString(0.8 * inch, y, f"Period: {start.isoformat()} to {today.isoformat()}")
    y -= 0.18 * inch
    c.drawString(0.8 * inch, y, f"Profile: {profile.get('age','-')}y, {profile.get('weight','-')}kg, goals={profile.get('goals','-')}, conditions={profile.get('conditions','-')}")

    y -= 0.35 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8 * inch, y, "Weekly Summary")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    c.drawString(0.8 * inch, y, f"Average calories/day: {avg_cal} kcal")
    y -= 0.16 * inch
    c.drawString(0.8 * inch, y, f"Average Risk Exposure Index: {avg_risk}")

    y -= 0.32 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8 * inch, y, "Daily breakdown")
    y -= 0.18 * inch
    c.setFont("Helvetica", 9)

    # Table header
    c.drawString(0.8 * inch, y, "Date")
    c.drawString(2.0 * inch, y, "Calories")
    c.drawString(3.0 * inch, y, "P/C/F")
    c.drawString(4.2 * inch, y, "Sugar")
    c.drawString(4.9 * inch, y, "Sodium")
    c.drawString(5.7 * inch, y, "Risk")

    y -= 0.12 * inch
    c.line(0.8 * inch, y, 7.6 * inch, y)
    y -= 0.15 * inch

    for d in days_sorted:
        t = totals(by_day[d])
        r = compute_daily_risk(by_day[d], profile)
        c.drawString(0.8 * inch, y, d)
        c.drawString(2.0 * inch, y, str(int(round(t["cal"], 0))))
        c.drawString(3.0 * inch, y, f"{int(round(t['p']))}/{int(round(t['c']))}/{int(round(t['f']))}")
        c.drawString(4.2 * inch, y, f"{int(round(t['sugar']))}g")
        c.drawString(4.9 * inch, y, f"{int(round(t['sodium']))}mg")
        c.drawString(5.7 * inch, y, f"{r['score']} ({r['level']})")
        y -= 0.18 * inch
        if y < 1.2 * inch:
            c.showPage()
            y = h - 0.8 * inch
            c.setFont("Helvetica", 9)

    # Key notes
    if y < 2.0 * inch:
        c.showPage()
        y = h - 0.8 * inch

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.8 * inch, y, "Notes")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    c.drawString(0.8 * inch, y, "• Risk Index rises with added sugar, sodium, NOVA-4 count, additives, and disease conflicts.")
    y -= 0.16 * inch
    c.drawString(0.8 * inch, y, "• Photo scans are approximate — confirm with labels or manual edits when possible.")

    c.showPage()
    c.save()
    return buf.getvalue()
