import json
import requests
import argparse
import time
from pathlib import Path

API_URL = "http://localhost:8000"
BATCH_SIZE = 100

def emit_events(events_path, api_url=API_URL):
    path = Path(events_path)
    if not path.exists():
        print(f"Events file not found: {events_path}")
        return

    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    print(f"Loaded {len(events)} events from {events_path}")

    accepted = 0
    rejected = 0
    duplicate = 0

    for i in range(0, len(events), BATCH_SIZE):
        batch = events[i:i + BATCH_SIZE]
        try:
            response = requests.post(
                f"{api_url}/events/ingest",
                json={"events": batch},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                accepted  += data.get("accepted", 0)
                rejected  += data.get("rejected", 0)
                duplicate += data.get("duplicate", 0)
                print(f"Batch {i//BATCH_SIZE + 1}: accepted={data.get('accepted')} rejected={data.get('rejected')} duplicate={data.get('duplicate')}")
            else:
                print(f"Batch {i//BATCH_SIZE + 1} failed: {response.status_code}")
        except Exception as e:
            print(f"Batch {i//BATCH_SIZE + 1} error: {e}")
        time.sleep(0.1)

    print(f"\nDone. Total accepted={accepted} rejected={rejected} duplicate={duplicate}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="data/events/events.jsonl")
    parser.add_argument("--api",    default=API_URL)
    args = parser.parse_args()
    emit_events(args.events, args.api)
