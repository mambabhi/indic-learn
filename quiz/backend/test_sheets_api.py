# backend/test_pipeline.py
# -*- coding: utf-8 -*-

import gspread
import quiz.backend.utils.gsheets as gsheets

creds = gsheets.get_google_credentials()

# Authorize gspread with your credentials
client = gspread.authorize(creds)

print("Authentication successful!")

# --- Open your spreadsheet ---
# Replace 'My Colab Test Sheet' with the exact name of your Google Sheet
spreadsheet_name = 'random spreadsheet'
try:
    spreadsheet = client.open(spreadsheet_name)
    print(f"Successfully opened spreadsheet: '{spreadsheet_name}'")
except gspread.exceptions.SpreadsheetNotFound:
    print(f"Error: Spreadsheet '{spreadsheet_name}' not found. Make sure the name is exact and the service account has access.")
    exit()

# Select a worksheet (default is the first one, or by name/index)
worksheet = spreadsheet.sheet1 # or spreadsheet.worksheet('Sheet1') or spreadsheet.get_worksheet(0)
print(f"Successfully selected worksheet: '{worksheet.title}'")

# ----- Function to check and load credentials from JSON file ---
# Commented out the functionality below to have it as a reference.
# from google.oauth2.service_account import Credentials
# from quiz.backend.config import env_config

# --- Assume these are loaded from your env_config ---
# Temporarily hardcode the path for absolute certainty during this test
# Make sure this exact path is where your NEWLY downloaded JSON key is located.

# SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
# GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]

# Load credentials from the JSON file
# creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)

# --- Authentication using the uploaded credentials.json ---
# def check_and_load_credentials(json_file_path, scopes):
#     print(f"Attempting to load credentials from: {os.path.abspath(json_file_path)}") # <--- ADDED: Print absolute path

#     # 1. Check if file exists
#     if not os.path.exists(json_file_path):
#         print(f"Error: Credential file not found at {os.path.abspath(json_file_path)}") # <--- ADDED: Use absolute path in error
#         return None

#     # 2. Check JSON syntax and basic structure
#     credentials_raw_content = "" # To store raw content
#     try:
#         with open(json_file_path, 'r', encoding='utf-8') as f: # <--- ADDED: encoding='utf-8' for robustness
#             credentials_raw_content = f.read() # Read raw content
#             credentials_data = json.loads(credentials_raw_content) # Parse from raw content

#         print("JSON file is syntactically valid.")

#         # Print the parsed data (sanitized private key)
#         sanitized_data = credentials_data.copy()
#         if "private_key" in sanitized_data:
#             sanitized_data["private_key"] = sanitized_data["private_key"][:30] + "..." + sanitized_data["private_key"][-30:] # Show only start/end
#         print("Parsed JSON data (sanitized private_key):\n", json.dumps(sanitized_data, indent=2)) # <--- ADDED: Print parsed data

#         # Check for required fields for a service account key
#         required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email"]
#         for key in required_keys:
#             if key not in credentials_data:
#                 print(f"Error: Missing required key '{key}' in JSON file.")
#                 return None
        
#         if credentials_data["type"] != "service_account":
#             print(f"Error: 'type' field in JSON is '{credentials_data['type']}', expected 'service_account'.")
#             return None

#         # Detailed check for private_key format
#         private_key = credentials_data["private_key"]
#         if not (private_key.startswith("-----BEGIN PRIVATE KEY-----") and private_key.endswith("-----END PRIVATE KEY-----\n")):
#             print("WARNING: 'private_key' field might be malformed (missing headers/footers or expected newlines).")
#         else:
#             print("'private_key' field appears to have correct headers/footers and newlines.")
#             # Print a portion of the private_key to inspect
#             print(f"DEBUG: private_key content (start/end/length):")
#             print(f"  Starts with: '{private_key[:50]}'")
#             print(f"  Ends with: '{private_key[-50:]}'")
#             print(f"  Total length: {len(private_key)}")
#             # Calculate these values outside the f-string to avoid backslash issues
#             contains_newline_start = ('\n' in private_key[:100])
#             contains_newline_end = ('\n' in private_key[-100:])
#             total_newlines_count = private_key.count('\n')

#             print(f"  Contains \\n at index 0-100: {contains_newline_start}") # Check for explicit newlines
#             print(f"  Contains \\n near end (-100 to end): {contains_newline_end}") # Check for explicit newlines
#             print(f"  Check if original key has multiple newlines: {total_newlines_count}") # Count total newlines


#     except json.JSONDecodeError as e:
#         print(f"Error: JSON file syntax is invalid. Details: {e}")
#         print("Raw content read:\n", credentials_raw_content) # <--- ADDED: Print raw content if decode fails
#         return None
#     except Exception as e:
#         print(f"An unexpected error occurred while reading the JSON file: {e}")
#         return None

#     # 3. Attempt to load with google-auth library
#     try:
#         creds = Credentials.from_service_account_file(json_file_path, scopes=scopes)
        
#         cred_info = creds.get_cred_info()
#         if cred_info is None:
#             print("ERROR: Credentials.from_service_account_file succeeded without error, but creds.get_cred_info() returned None.")
#             print("This strongly suggests the content of the JSON file, while syntactically valid, is not a valid Google service account key recognized by the library.")
#             print("Please ensure the private_key is complete and correctly formatted, and that the file was downloaded directly from Google Cloud Console.")
#             return None
#         else:
#             print(f"Credentials object successfully created and contains info (email: {cred_info.get('client_email')}).")
#             return creds

#     except Exception as e:
#         print(f"Error during Credentials.from_service_account_file: {e}")
#         return None

# # --- Run the check ---
# creds_obj = check_and_load_credentials(SERVICE_ACCOUNT_FILE, GOOGLE_SCOPES)

# print("\n--- Summary ---")
# print("Google service account credentials loaded successfully:", "Yes" if creds_obj else "No")
# print("Credentials object info:", creds_obj.get_cred_info() if creds_obj else "None")

