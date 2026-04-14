from __future__ import annotations

"""Temporal worker stub for Phase 0. Will be implemented in Phase 3."""

import asyncio
import signal


async def main() -> None:
    """Start the Temporal worker (stub — blocks until stopped)."""
    print("Publishing worker stub — will start Temporal activities in Phase 3")
    print("Worker is running. Send SIGTERM or SIGINT to stop.")

    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, _handle_signal)
    loop.add_signal_handler(signal.SIGINT, _handle_signal)

    await stop_event.wait()
    print("Publishing worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
