"""ARQ background worker process entrypoint."""

import asyncio


async def main() -> None:
    """Start the ARQ background worker."""
    print("Worker starting...")


if __name__ == "__main__":
    asyncio.run(main())
