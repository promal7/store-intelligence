import os
import sys

sys.path.append(os.getcwd())

print("\n--- SYSTEM DIAGNOSIS START ---")

db_path = "store_intelligence.db"
print(f"1. Database Exist Check: {os.path.exists(db_path)}")

clips_dir = "data/clips"
if os.path.exists(clips_dir):
    print("2. Videos in clips folder:", os.listdir(clips_dir))
else:
    print("2. ❌ data/clips folder missing!")

try:
    from app import funnel
    print("\n✅ SUCCESS: funnel.py completely load ho gaya hai bina kisi error ke!")
    print("Available API Endpoints/Functions:", [f for f in dir(funnel) if not f.startswith('_')])
except Exception as e:
    print(f"\n❌ Import Error: {e}")
