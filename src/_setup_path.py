"""
Setup path cho imports - Phải import file này TRƯỚC các module khác
"""
import os
import sys

# Bảo đảm thêm src vào sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)
