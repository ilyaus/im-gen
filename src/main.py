import logging

from src.api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

app = create_app()
