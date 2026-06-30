#!/usr/bin/env python3
"""
ARKA - Main entry point
Initializes the Discord bot, Lavalink node, VRChat manager,
and the FastAPI dashboard, then runs them concurrently.
"""
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Import local modules
from arka.bot import ARKABot
from arka.dashboard import create_app
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('arka.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('arka')

async def main() -> None:
    """Start bot and dashboard together."""
    try:
        bot = ARKABot()
        # Create FastAPI app, passing the bot instance for shared state
        app = create_app(bot)

        # Uvicorn server config
        host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
        port = int(os.getenv("DASHBOARD_PORT", "8080"))
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        # Run bot and server concurrently
        await asyncio.gather(
            bot.start(os.getenv("DISCORD_TOKEN")),
            server.serve()
        )
    except Exception as exc:
        logger.error(f"Fatal error in main: {exc}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as exc:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        sys.exit(1)