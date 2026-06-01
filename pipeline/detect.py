# PROMPT: "Write a YOLOv8 + ByteTrack person detection pipeline that processes
# CCTV video clips and emits structured retail analytics events including
# ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, BILLING_QUEUE_JOIN,
# BILLING_QUEUE_ABANDON and REENTRY. Handle staff detection, group entry,
# re-entry, and partial occlusion gracefully."
# CHANGES MADE: Added confidence threshold filtering, zone assignment from
# bounding box position, staff detection by dwell pattern, re-entry window.

import cv2
import json
import uuid
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from ultralytics import YOLO
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.3
ENTRY_LINE_RATIO     = 0.15   # top 15% of frame = entry zone
EXIT_LINE_RATIO      = 0.15
DWELL_THRESHOLD_SEC  = 30     # emit ZONE_DWELL every 30s
REENTRY_WINDOW_SEC   = 300    # 5 min window to detect re-entry
STAFF_DWELL_RATIO    = 0.7    # if in store >70% of clip = staff

STORE_ID  = "STORE_BLR_002"
CAMERA_ID = "CAM_ENTRY_01"

# ── Zone definitions (fallback if no store_layout.json) ───────────────
DEFAULT_ZONES = {
    "ENTRY_ZONE"  : (0.0, 0.0,  1.0, 0.2),   # x1,y1,x2,y2 as ratios
    "MAIN_FLOOR"  : (0.0, 0.2,  1.0, 0.7),
    "BILLING"     : (0.0, 0.7,  1.0, 1.0),
}

def load_zones(layout_path):
    if Path(layout_path).exists():
        with open(layout_path) as f:
            layout = json.load(f)
        return layout.get("zones", DEFAULT_ZONES)
    return DEFAULT_ZONES

def get_zone(cx, cy, fw, fh, zones):
    rx, ry = cx / fw, cy / fh
    for name, (x1, y1, x2, y2) in zones.items():
        if x1 <= rx <= x2 and y1 <= ry <= y2:
            return name
    return None

def is_entering(prev_cy, curr_cy, fh):
    return prev_cy is not None and prev_cy < fh * ENTRY_LINE_RATIO <= curr_cy

def is_exiting(prev_cy, curr_cy, fh):
    return prev_cy is not None and curr_cy < fh * EXIT_LINE_RATIO <= prev_cy

def make_event(event_type, visitor_id, zone_id=None, dwell_ms=0,
               is_staff=False, confidence=1.0, metadata=None, base_time=None, frame_offset_sec=0):
    ts = (base_time + timedelta(seconds=frame_offset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "event_id"  : str(uuid.uuid4()),
        "store_id"  : STORE_ID,
        "camera_id" : CAMERA_ID,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp" : ts,
        "zone_id"   : zone_id,
        "dwell_ms"  : dwell_ms,
        "is_staff"  : is_staff,
        "confidence": round(confidence, 3),
        "metadata"  : metadata or {}
    }

def process_clip(video_path, output_path, layout_path="data/store_layout.json"):
    model  = YOLO("yolov8n.pt")
    zones  = load_zones(layout_path)
    cap    = cv2.VideoCapture(str(video_path))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 15
    base_time = datetime(2026, 6, 1, 9, 0, 0)

    # Per-track state
    track_history   = defaultdict(lambda: {"frames": 0, "prev_cy": None, "zone": None,
                                            "zone_entry_frame": None, "dwell_emitted": 0,
                                            "entered": False, "exited": False})
    exited_tracks   = {}   # track_id -> exit_frame (for re-entry)
    visitor_map     = {}   # track_id -> visitor_id
    events          = []
    frame_idx       = 0
    queue_depth     = 0

    print(f"Processing {video_path}...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        fh, fw = frame.shape[:2]
        frame_idx += 1
        frame_sec = frame_idx / fps

        # Run detection + tracking every 3rd frame for speed
        if frame_idx % 3 != 0:
            continue

        results = model.track(frame, persist=True, classes=[0],
                              conf=CONFIDENCE_THRESHOLD, verbose=False)

        if results[0].boxes is None or results[0].boxes.id is None:
            continue

        boxes      = results[0].boxes.xyxy.cpu().numpy()
        track_ids  = results[0].boxes.id.cpu().numpy().astype(int)
        confs      = results[0].boxes.conf.cpu().numpy()
        active_ids = set(track_ids.tolist())

        # Check exits for tracks that disappeared
        for tid in list(track_history.keys()):
            if tid not in active_ids and track_history[tid]["entered"] and not track_history[tid]["exited"]:
                vid = visitor_map.get(tid, f"VIS_{tid:06x}")
                is_staff = track_history[tid]["frames"] > (fps * 60 * STAFF_DWELL_RATIO)
                events.append(make_event("EXIT", vid, is_staff=is_staff,
                                         confidence=0.7, base_time=base_time,
                                         frame_offset_sec=frame_sec))
                track_history[tid]["exited"] = True
                exited_tracks[tid] = frame_idx

        for i, tid in enumerate(track_ids):
            x1, y1, x2, y2 = boxes[i]
            conf = float(confs[i])
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            state    = track_history[tid]
            prev_cy  = state["prev_cy"]

            # Assign visitor_id
            if tid not in visitor_map:
                # Check re-entry
                reentry = False
                for old_tid, exit_frame in exited_tracks.items():
                    if frame_idx - exit_frame < fps * REENTRY_WINDOW_SEC:
                        old_vid = visitor_map.get(old_tid)
                        if old_vid:
                            visitor_map[tid] = old_vid
                            reentry = True
                            events.append(make_event("REENTRY", old_vid, confidence=conf,
                                                      base_time=base_time, frame_offset_sec=frame_sec))
                            break
                if not reentry:
                    visitor_map[tid] = f"VIS_{uuid.uuid4().hex[:6]}"

            vid      = visitor_map[tid]
            is_staff = state["frames"] > (fps * 60 * STAFF_DWELL_RATIO)

            # Entry detection
            if is_entering(prev_cy, cy, fh) and not state["entered"]:
                state["entered"] = True
                events.append(make_event("ENTRY", vid, confidence=conf,
                                          is_staff=is_staff, base_time=base_time,
                                          frame_offset_sec=frame_sec))

            # Exit detection
            if is_exiting(prev_cy, cy, fh) and state["entered"] and not state["exited"]:
                state["exited"] = True
                events.append(make_event("EXIT", vid, confidence=conf,
                                          is_staff=is_staff, base_time=base_time,
                                          frame_offset_sec=frame_sec))

            # Zone tracking
            curr_zone = get_zone(cx, cy, fw, fh, zones)
            if curr_zone != state["zone"]:
                if state["zone"]:
                    events.append(make_event("ZONE_EXIT", vid, zone_id=state["zone"],
                                              confidence=conf, is_staff=is_staff,
                                              base_time=base_time, frame_offset_sec=frame_sec))
                if curr_zone:
                    events.append(make_event("ZONE_ENTER", vid, zone_id=curr_zone,
                                              confidence=conf, is_staff=is_staff,
                                              base_time=base_time, frame_offset_sec=frame_sec))
                    state["zone_entry_frame"] = frame_idx

                    # Billing queue
                    if curr_zone == "BILLING":
                        queue_depth += 1
                        events.append(make_event("BILLING_QUEUE_JOIN", vid,
                                                  zone_id="BILLING", confidence=conf,
                                                  is_staff=is_staff, base_time=base_time,
                                                  frame_offset_sec=frame_sec,
                                                  metadata={"queue_depth": queue_depth,
                                                             "sku_zone": "BILLING",
                                                             "session_seq": state["frames"]}))
                state["zone"] = curr_zone

            # Dwell events every 30s
            if state["zone"] and state["zone_entry_frame"]:
                dwell_sec = (frame_idx - state["zone_entry_frame"]) / fps
                dwell_intervals = int(dwell_sec / DWELL_THRESHOLD_SEC)
                if dwell_intervals > state["dwell_emitted"]:
                    state["dwell_emitted"] = dwell_intervals
                    events.append(make_event("ZONE_DWELL", vid, zone_id=state["zone"],
                                              dwell_ms=int(dwell_sec * 1000),
                                              confidence=conf, is_staff=is_staff,
                                              base_time=base_time, frame_offset_sec=frame_sec))

            state["prev_cy"] = cy
            state["frames"] += 1

        if frame_idx % 300 == 0:
            print(f"  Frame {frame_idx} | Events so far: {len(events)}")

    cap.release()
    print(f"Done. Total events: {len(events)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    print(f"Events written to {output_path}")
    return events

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="data/clips", help="Path to clips folder")
    parser.add_argument("--output", default="data/events/events.jsonl", help="Output JSONL path")
    parser.add_argument("--layout", default="data/store_layout.json", help="store_layout.json path")
    parser.add_argument("--cam",    default=None, help="Process single clip (e.g. 'CAM 1.mp4')")
    args = parser.parse_args()

    clips_dir = Path(args.input)

    if args.cam:
        clips = [clips_dir / args.cam]
    else:
        clips = sorted(clips_dir.glob("*.mp4"))

    all_events = []
    for clip in clips:
        evts = process_clip(clip, args.output, args.layout)
        all_events.extend(evts)

    print(f"\nTotal events across all clips: {len(all_events)}")
