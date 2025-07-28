# utils/gsheets.py

import os
import json
import base64
import binascii
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from quiz.backend.config import env_config
from quiz.backend.utils.logging_utils import log_and_print

# Load environment variables and app config
SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]

def get_google_credentials():
    """
    Load Google service account credentials. Prioritizes Base64 encoded string from environment
    for deployment, falls back to local file path for development.
    Returns a Credentials object.
    """
    print("Loading Google service account credentials...")
    service_account_info = None
    log_message = "" 

    # 1. Try to load from Base64 encoded environment variable (Hugging Face / Deployment)
    google_key_base64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_BASE64")
    if google_key_base64 and not google_key_base64.startswith("placeholder_for_base64_encoded_key"):
        log_and_print("Attempting to load credentials from GOOGLE_SERVICE_ACCOUNT_KEY_BASE64 env var.")
        try:
            decoded_json_bytes = base64.b64decode(google_key_base64)
            service_account_info = json.loads(decoded_json_bytes.decode('utf-8'))
        except (binascii.Error, json.JSONDecodeError) as e:
            log_and_print(f"ERROR: Failed to decode or parse GOOGLE_SERVICE_ACCOUNT_KEY_BASE64: {e}", to_console=True)
            raise ValueError("Invalid Base64 encoded service account key.") from e

        log_and_print("Base64 decoded successfully, loading JSON...")
    else:
        # 2. Fallback to local file path (VS Code / Local Development)
        absolute_service_account_path = os.path.abspath(SERVICE_ACCOUNT_FILE)
        log_and_print(f"DEBUG: Attempting to load credentials from absolute path: {absolute_service_account_path}")

        if not os.path.exists(absolute_service_account_path):
            log_and_print(f"ERROR: Credentials file DOES NOT EXIST at: {absolute_service_account_path}")
            raise FileNotFoundError(f"Credentials file not found at: {absolute_service_account_path}")
        
        log_and_print(f"Attempting to load credentials from local file: {absolute_service_account_path}")

        if not os.path.exists(absolute_service_account_path):
            log_and_print(f"ERROR: Local credentials file DOES NOT EXIST at: {absolute_service_account_path}", to_console=True)
            raise FileNotFoundError(f"Credentials file not found at: {absolute_service_account_path}")

        try:
            with open(absolute_service_account_path, 'r') as f:
                service_account_info = json.load(f)
            log_and_print("Local service account JSON file loaded successfully.")
        except json.JSONDecodeError as e:
            log_and_print(f"ERROR: Failed to parse JSON from local credentials file '{absolute_service_account_path}': {e}", to_console=True)
            raise ValueError("Malformed local service account JSON file.") from e

# Now that service_account_info is populated (or an error was raised), create Credentials object
    if service_account_info:
        log_and_print(log_message, to_console=True) # Log which method was used
        creds = Credentials.from_service_account_info(service_account_info, scopes=GOOGLE_SCOPES)
        log_and_print("Service Account Credentials Loaded Successfully (Initial object created)", to_console=True)

        # Force a refresh to get the token, as before
        if not creds.token or creds.expired:
            log_and_print("DEBUG: Token is None or expired, attempting to refresh credentials...", to_console=True)
            try:
                creds.refresh(Request())
                log_and_print("DEBUG: Credentials refreshed successfully.", to_console=True)
            except Exception as refresh_error:
                log_and_print(f"ERROR: Failed to refresh credentials: {refresh_error}", to_console=True)
                import traceback
                traceback.print_exc() # Print full traceback for deeper insights
                raise ValueError(f"Failed to refresh Google service account credentials: {refresh_error}") from refresh_error

        # Final validity check
        if not creds or not creds.valid: # This check should now pass if everything is correct
            log_and_print("ERROR: Credentials object is invalid or not properly initialized AFTER REFRESH.", to_console=True)
            raise ValueError("Invalid Google service account credentials.")

        # Final debug prints
        log_and_print(f"DEBUG: Final creds object type: {type(creds)}", to_console=True)
        log_and_print(f"DEBUG: Final creds.valid: {creds.valid}", to_console=True)
        log_and_print(f"DEBUG: Final creds.expired: {creds.expired}", to_console=True)
        if creds.token:
            log_and_print(f"DEBUG: Final creds.token: {creds.token[:10]}... (first 10 chars)", to_console=True)
        else:
            log_and_print("DEBUG: Final creds.token: None (This should ideally not happen after refresh)", to_console=True)

        return creds
    else:
        # This branch should ideally not be reached if previous checks are robust
        log_and_print("ERROR: Service account information could not be determined.", to_console=True)
        raise ValueError("Service account information missing.")


def clear_all_sheet_formatting_only(sheets_api, spreadsheet_id, sheet_id):
    """
    Clears all formatting (but not data) from the specified sheet.
    """
    request_body = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": sheet_id},
                    "fields": "userEnteredFormat"  # Only formatting
                }
            }
        ]
    }

    sheets_api.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=request_body
    ).execute()

