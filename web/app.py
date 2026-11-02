import os
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web import app, socketio


if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("STOCK_WEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("STOCK_WEB_PORT", "5000")),
        debug=False,
    )
