from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import EventDB
from datetime import datetime
import csv
import os

router = APIRouter()

POS_PATH = os.getenv("POS_PATH", "data/pos_transactions.csv")

def load_pos_transactions(store_id):
    transactions = []
    if not os.path.exists(POS_PATH):
        return transactions
    with open(POS_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["store_id"] == store_id:
                try:
                    ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                    transactions.append({
                        "transaction_id": row["transaction_id"],
                        "timestamp": ts,
                        "basket_value": float(row["basket_value_inr"])
                    })
                except:
                    pass
    return transactions

@router.get("/stores/{store_id}/metrics")
async def get_metrics(store_id: str, db: AsyncSession = Depends(get_db)):

    # Get most recent event date for this store
    latest_result = await db.execute(
        select(func.max(EventDB.timestamp))
        .where(EventDB.store_id == store_id)
    )
    latest_ts = latest_result.scalar()
    if latest_ts:
        event_date = latest_ts.date()
    else:
        from datetime import date
        event_date = date.today()

    # Unique visitors — count from ENTRY or first ZONE_ENTER per visitor
    visitors_result = await db.execute(
        select(func.count(func.distinct(EventDB.visitor_id)))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type.in_(["ENTRY", "ZONE_ENTER"]))
        .where(func.date(EventDB.timestamp) == event_date)
    )
    unique_visitors = visitors_result.scalar() or 0

    # Billing visitors with timestamps for POS correlation
    billing_result = await db.execute(
        select(EventDB.visitor_id, EventDB.timestamp)
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type.in_(["BILLING_QUEUE_JOIN", "ZONE_ENTER"]))
        .where(EventDB.zone_id == "BILLING")
        .where(func.date(EventDB.timestamp) == event_date)
    )
    billing_rows = billing_result.fetchall()
    billing_visitors = len(set(r[0] for r in billing_rows))

    # POS correlation
    pos_transactions = load_pos_transactions(store_id)
    converted_visitors = set()

    for visitor_id, billing_ts in billing_rows:
        billing_ts_naive = billing_ts.replace(tzinfo=None) if hasattr(billing_ts, 'replace') else billing_ts
        for txn in pos_transactions:
            txn_ts = txn["timestamp"].replace(tzinfo=None)
            diff = (txn_ts - billing_ts_naive).total_seconds()
            if 0 <= diff <= 300:
                converted_visitors.add(visitor_id)
                break

    conversion_rate = round(len(converted_visitors) / unique_visitors, 3) if unique_visitors > 0 else 0.0

    # Avg dwell per zone
    dwell_result = await db.execute(
        select(EventDB.zone_id, func.avg(EventDB.dwell_ms))
        .where(EventDB.store_id == store_id)
        .where(EventDB.is_staff == False)
        .where(EventDB.event_type == "ZONE_DWELL")
        .where(EventDB.zone_id != None)
        .where(func.date(EventDB.timestamp) == event_date)
        .group_by(EventDB.zone_id)
    )
    avg_dwell = {row[0]: round(row[1] / 1000, 1) for row in dwell_result.fetchall()}

    # Queue depth
    queue_result = await db.execute(
        select(EventDB.metadata_)
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type == "BILLING_QUEUE_JOIN")
        .order_by(EventDB.timestamp.desc())
        .limit(1)
    )
    queue_row = queue_result.scalar()
    queue_depth = queue_row.get("queue_depth", 0) if queue_row else 0

    # Abandonment rate
    abandon_result = await db.execute(
        select(func.count())
        .where(EventDB.store_id == store_id)
        .where(EventDB.event_type == "BILLING_QUEUE_ABANDON")
        .where(func.date(EventDB.timestamp) == event_date)
    )
    abandonments = abandon_result.scalar() or 0
    abandonment_rate = round(abandonments / billing_visitors, 3) if billing_visitors > 0 else 0.0

    total_revenue = sum(t["basket_value"] for t in pos_transactions)
    avg_basket = round(total_revenue / len(pos_transactions), 2) if pos_transactions else 0.0

    return {
        "store_id"                   : store_id,
        "date"                       : str(event_date),
        "unique_visitors"            : unique_visitors,
        "conversion_rate"            : conversion_rate,
        "converted_visitors"         : len(converted_visitors),
        "avg_dwell_seconds_per_zone" : avg_dwell,
        "queue_depth"                : queue_depth,
        "abandonment_rate"           : abandonment_rate,
        "pos_transactions_today"     : len(pos_transactions),
        "total_revenue_inr"          : total_revenue,
        "avg_basket_value_inr"       : avg_basket
    }
