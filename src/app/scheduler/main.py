"""APScheduler cron process entrypoint."""

import asyncio


async def main() -> None:
    """Start the APScheduler cron process."""
    print("Scheduler starting...")


if __name__ == "__main__":
    asyncio.run(main())
