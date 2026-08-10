"""
Config module.

Cố ý KHÔNG re-export database/driver ở đây: `driver.py` import `settings.py`, mà import
`src.config.settings` lại chạy file này trước -> vòng lặp import. Import thẳng module con.
"""
from . import version

__all__ = ["version"]
