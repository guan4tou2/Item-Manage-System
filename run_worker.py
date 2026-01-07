#!/usr/bin/env python3
"""Worker process for scheduled tasks"""
import os
import sys
import signal

from app import create_app
from app.utils.scheduler import init_scheduler, shutdown_scheduler


def main():
    app = create_app()

    with app.app_context():
        print("🚀 Starting scheduler worker...")
        init_scheduler()

        def signal_handler(sig, frame):
            print("🛑 Received shutdown signal...")
            shutdown_scheduler()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while True:
                pass
        except KeyboardInterrupt:
            shutdown_scheduler()
            sys.exit(0)


if __name__ == "__main__":
    main()
