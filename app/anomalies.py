def calculate_active_anomalies(events, store_id):
    anomalies = []
    store_events = [e for e in events if e.store_id == store_id]
    queue_events = [e for e in store_events if e.event_type == 'BILLING_QUEUE_JOIN']
    if len(queue_events) > 15:
        anomalies.append({
            "severity": "CRITICAL",
            "type": "QUEUE_SPIKE",
            "suggested_action": "Deploy backup register terminals immediately."
        })
    if not anomalies:
        anomalies.append({
            "severity": "INFO",
            "type": "NORMAL_OPERATIONS",
            "suggested_action": "No active bottlenecks detected."
        })
    return anomalies
