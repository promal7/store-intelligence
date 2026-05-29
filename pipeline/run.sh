#!/bin/bash
# Apex Video Intelligence Pipeline Execution Entry
echo "[System Boot] Initializing AI Tracking Layer pipeline run..."
python3 pipeline/detect.py "$@"
