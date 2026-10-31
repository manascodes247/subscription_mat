"""Brightloop application package."""

from pathlib import Path

from dotenv import load_dotenv


# Local development reads an untracked .env file. Production deployments
# should inject the same variables through their secret manager.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
