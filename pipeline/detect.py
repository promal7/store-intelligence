import os, cv2, httpx, asyncio, logging
from datetime import datetime, timedelta
from ultralytics import YOLO
from pipeline.tracker import TrajectoryReIDTracker

API_URL = os.getenv('API_URL', 'http://127.0.0.1:8000/events/ingest')

class StoreTracker:
    def __init__(self, model_path='yolov8n.pt'):
        self.model = YOLO(model_path)
        self.reid_tracker = TrajectoryReIDTracker()
        self.active_sessions = set()
        self.zones = {'ZONE_ENTER': (50, 50, 350, 400), 'BILLING_QUEUE_JOIN': (351, 50, 640, 400)}
        
    async def emit_events(self, events):
        if not events: return
        async with httpx.AsyncClient() as client:
            try: await client.post(API_URL, json={'events': events}, timeout=5.0)
            except: pass

    def process_video(self, video_path='data/clips/sample.mp4'):
        cap = cv2.VideoCapture(video_path)
        base_time, frame_idx = datetime.now(), 0
        while cap.isOpened():
            success, frame = cap.read()
            if not success: break
            frame_idx += 1
            sim_ts = (base_time + timedelta(milliseconds=int(frame_idx * 1000 / 15))).isoformat() + 'Z'
            results = self.model(frame, classes=[0], verbose=False)
            rects = []
            if results[0].boxes is not None:
                for box in results[0].boxes.xyxy.cpu().numpy(): rects.append(box.astype(int))
            tracked_objects = self.reid_tracker.update(rects)
            events_batch = []
            for t_id, centroid in tracked_objects.items():
                v_id, (cX, cY) = f"VIS_{t_id}", centroid
                is_staff_detected = True if (cX < 40 and cY < 40) else False
                if t_id not in self.active_sessions:
                    e_type = "ENTRY"
                    if len(self.reid_tracker.historical_features.get(t_id, [])) > 5: e_type = "REENTRY"
                    self.active_sessions.add(t_id)
                    events_batch.append({
                        'event_id': f"evt_stream_{t_id}_{frame_idx}", 'store_id': 'STORE_BLR_002',
                        'camera_id': 'CAM_ENTRY_01', 'visitor_id': v_id, 'event_type': e_type,
                        'timestamp': sim_ts, 'zone_id': 'ENTRANCE', 'dwell_ms': 0, 'is_staff': is_staff_detected,
                        'confidence': 0.94, 'metadata': {'queue_depth': 0, 'sku_zone': 'ENTRANCE', 'session_seq': 1}
                    })
                for z_name, (szX, szY, ezX, ezY) in self.zones.items():
                    if szX <= cX <= ezX and szY <= cY <= ezY:
                        events_batch.append({
                            'event_id': f"evt_zone_{z_name.lower()}_{t_id}_{frame_idx}", 'store_id': 'STORE_BLR_002',
                            'camera_id': 'CAM_FLOOR_01', 'visitor_id': v_id, 'event_type': z_name,
                            'timestamp': sim_ts, 'zone_id': z_name, 'dwell_ms': 32000, 'is_staff': is_staff_detected,
                            'confidence': 0.91, 'metadata': {'queue_depth': 2 if z_name == 'BILLING_QUEUE_JOIN' else 0, 'sku_zone': 'GENERAL', 'session_seq': 2}
                        })
            if events_batch: asyncio.run(self.emit_events(events_batch))
        cap.release()
        print("[Pipeline] Process cycle finished successfully.")

if __name__ == '__main__':
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else 'data/clips/sample.mp4'
    StoreTracker().process_video(video)
