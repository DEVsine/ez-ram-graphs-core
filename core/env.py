import os
import json
import google.auth
import io

from pathlib import Path
from dotenv import load_dotenv
from google.cloud import secretmanager

BASE_DIR = Path(__file__).resolve().parent.parent
env_file = os.path.join(BASE_DIR, ".env")


def load_env():
    # Use a local secret file, if provided
    if os.path.isfile(env_file):
        load_dotenv(env_file, override=True)
        return

    # Attempt to load the Project ID into the environment, safely failing on error.
    try:
        _, os.environ["GOOGLE_CLOUD_PROJECT"] = google.auth.default()
    except Exception:
        pass

    # Pull secrets from Google Secret Manager
    if os.environ.get("GOOGLE_CLOUD_PROJECT", None):
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        settings_name = os.environ.get("SETTINGS_NAME", "dobybot_settings")
        name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
        payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")
        load_dotenv(stream=io.StringIO(payload))
        return

    raise Exception("No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found.")


def load_google_drive_credentials():
    GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS = os.getenv(
        "GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS"
    )
    GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS = json.loads(
        GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS, strict=False
    )
    PRIVATE_KEY = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_PRIVATE_KEY", default="")
    if PRIVATE_KEY:
        PRIVATE_KEY = PRIVATE_KEY.replace(":", "\n")
        GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS["private_key"] = PRIVATE_KEY

    return GOOGLE_DRIVE_SERVICE_ACCOUNT_CREDENTIALS
