"""pytest 設定 — 確保 src 路徑正確"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
