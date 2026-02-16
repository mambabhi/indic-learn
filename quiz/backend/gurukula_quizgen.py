# backend/gurukula_quizgen.py
# -*- coding: utf-8 -*-

import os
import argparse
import re
from typing import Tuple
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import Optional
from dotenv import load_dotenv; load_dotenv()
from quiz.backend.config import env_config, app_config
from quiz.backend.indic_quiz_generator_pipeline import (
    run_parallel_quiz_with_mcq_retry,
)
from quiz.backend.utils.gsheets import get_gdoc_title, get_google_credentials, clear_all_sheet_formatting_only, read_chapter_text_from_gdoc
from quiz.backend.utils.logging_utils import log_and_print


# Load environment variables and app config
SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]
INPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["input_name"]
OUTPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["output_name"]

# Get the directory of the current file (gurukula_quizgen.py)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate up one directory (from 'backend' to 'quiz') and then into 'data'
DATA_DIR = os.path.join(CURRENT_DIR, '..', 'data')

# ======== UTILITY: Extract spreadsheet ID from link ========
def extract_spreadsheet_id(spreadsheet_link: str) -> str:
    """
    Extract spreadsheet ID from a Google Sheets URL.

    Supported formats:
    - https://docs.google.com/spreadsheets/d/{ID}/edit...
    - https://docs.google.com/spreadsheets/d/{ID}
    - {ID} (raw ID)

    Args:
        spreadsheet_link: A Google Sheets URL or spreadsheet ID

    Returns:
        The spreadsheet ID

    Raises:
        ValueError: If the link format is invalid
    """
    if '/' not in spreadsheet_link:
        return spreadsheet_link.strip()

    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_link)
    if not match:
        raise ValueError(
            f"❌ Invalid Google Sheets link format.\n"
            f"   Expected: https://docs.google.com/spreadsheets/d/{{SPREADSHEET_ID}}/...\n"
            f"   Got: {spreadsheet_link}"
        )

    return match.group(1)

def validate_spreadsheet_by_id(spreadsheet_id: str, creds) -> bool:
    """
    Validate if a spreadsheet ID is accessible.
    Uses direct ID lookup instead of name search (more efficient and scalable).

    Args:
        spreadsheet_id: The Google Sheets spreadsheet ID
        creds: Google credentials

    Returns:
        True if accessible, raises ValueError if not
    """
    try:
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Output spreadsheet validated and accessible (ID: {spreadsheet_id}).")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(
            f"❌ Spreadsheet with ID '{spreadsheet_id}' not found or is NOT accessible.\n"
            f"   Reason: The spreadsheet is either:\n"
            f"   1. Not shared with the service account\n"
            f"   2. Does not exist\n"
            f"   Solution: Please ensure the spreadsheet exists and is shared with the service account."
        )
    except gspread.exceptions.APIError as e:
        raise ValueError(
            f"❌ API Error accessing spreadsheet (ID: {spreadsheet_id}):\n"
            f"   {str(e)}\n"
            f"   Please verify the spreadsheet is shared with the service account."
        )
    except Exception as e:
        raise ValueError(
            f"❌ Unexpected error validating spreadsheet (ID: {spreadsheet_id}):\n"
            f"   {str(e)}\n"
            f"   Please verify the spreadsheet is shared with the service account."
        )

# ======== STEP 1: Run Agent and Get JSON ========
def generate_quiz_json(chapter_text: str, num_questions: int = 15) -> dict:
    quiz = run_parallel_quiz_with_mcq_retry(chapter_text, num_questions)

    # Flatten to match old format: {'Questions': [...]}
    return {
        "Topic": quiz["Quiz"]["Topic"],
        "Questions": quiz["Quiz"]["Questions"]
    }

# ======== STEP 2: Convert to DataFrame ========
def clean_option(opt: str) -> str:
    return re.sub(r'^[a-d]\.\s*', '', opt.strip(), flags=re.IGNORECASE)

def quiz_json_to_dataframe(chapter_title: str, quiz_json: dict, num_questions: int) -> pd.DataFrame:
    questions = quiz_json['Questions']

    # Create full DataFrame (no shuffling yet)
    full_df = pd.DataFrame(
        {
            "Chapter": re.sub(r'chapter(\d+)', r'Chapter \1', chapter_title, flags=re.IGNORECASE),
            "Timer": q.get("Timer", 15 if q.get("Question_type", "").upper() == "SCQ" else 20),
            "Points": q.get("Number_Of_Points_Earned", 10 if q.get("Question_type", "").upper() == "SCQ" else 15),
            "Type": "SCQ" if (q["Question_type"] == "MCQ" and len(q["Right_Option"].replace(" ", "")) == 1) else q["Question_type"],
            "Question": q["Question"].strip() + "?" if not q["Question"].strip().endswith("?") else q["Question"].strip(),
            "Option A": clean_option(q["Options"][0]) if len(q["Options"]) > 0 else "",
            "Option B": clean_option(q["Options"][1]) if len(q["Options"]) > 1 else "",
            "Option C": clean_option(q["Options"][2]) if len(q["Options"]) > 2 else "",
            "Option D": clean_option(q["Options"][3]) if len(q["Options"]) > 3 else "",
            "Right Answer": q["Right_Option"].replace(" ", "").lower()
        }
        for q in questions
    )

    # Separate main and backup questions
    if len(full_df) > num_questions:
        df_main = full_df.iloc[:num_questions].sample(frac=1, random_state=42).reset_index(drop=True)
        df_backup = full_df.iloc[num_questions:].reset_index(drop=True)

        # Insert note row between main and backup
        note_row = {
            "Chapter": "The following questions are optional backups in case any of the questions above are not usable.",
            "Timer": "",
            "Points": "",
            "Type": "",
            "Question": "",
            "Option A": "",
            "Option B": "",
            "Option C": "",
            "Option D": "",
            "Right Answer": ""
        }

        df = pd.concat([df_main, pd.DataFrame([note_row]), df_backup], ignore_index=True)
    else:
        df = full_df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df
    

# ======== STEP 3: Upload to Google Sheet ========
def check_spreadsheet_exists_in_drive(spreadsheet_name: str, creds) -> bool:
    """
    Check if a spreadsheet exists in Google Drive (without requiring access).
    Uses Google Drive API to search for the spreadsheet by name.
    Returns True if found, False otherwise.
    """
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        results = drive_service.files().list(
            q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            spaces='drive',
            pageSize=1,
            fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        return len(files) > 0
    except Exception:
        # If Drive API call fails, we can't determine, so return None
        return None

def validate_output_spreadsheet(spreadsheet_name: str, creds) -> bool:
    """
    Validate if the output spreadsheet exists and is accessible.
    Provides specific error messages for different failure scenarios.
    Returns True if valid, raises ValueError if not.
    """
    try:
        client = gspread.authorize(creds)
        client.open(spreadsheet_name)
        print(f"✅ Output spreadsheet '{spreadsheet_name}' validated and accessible.")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        # Check if spreadsheet exists but is just not shared
        spreadsheet_exists = check_spreadsheet_exists_in_drive(spreadsheet_name, creds)
        
        if spreadsheet_exists:
            # Spreadsheet exists but not shared with service account
            raise ValueError(
                f"❌ Output spreadsheet '{spreadsheet_name}' exists but is NOT accessible.\n"
                f"   Reason: The spreadsheet is NOT shared with the service account.\n"
                f"   Solution: Please share the spreadsheet with the service account email address."
            )
        elif spreadsheet_exists is False:
            # Spreadsheet doesn't exist
            raise ValueError(
                f"❌ Output spreadsheet '{spreadsheet_name}' does not exist.\n"
                f"   Reason: A spreadsheet with this name could not be found in Google Drive.\n"
                f"   Solution: Please create the spreadsheet first, then try again."
            )
        else:
            # Can't determine, fall back to generic message
            raise ValueError(
                f"❌ Output spreadsheet '{spreadsheet_name}' is not accessible.\n"
                f"   Reason: The spreadsheet is either:\n"
                f"   1. Not shared with the service account\n"
                f"   2. Does not exist\n"
                f"   Please ensure the spreadsheet exists and is shared with the service account."
            )
    except gspread.exceptions.APIError as e:
        raise ValueError(
            f"❌ API Error accessing spreadsheet '{spreadsheet_name}':\n"
            f"   {str(e)}\n"
            f"   Please verify the spreadsheet is shared with the service account."
        )
    except Exception as e:
        raise ValueError(
            f"❌ Unexpected error validating spreadsheet '{spreadsheet_name}':\n"
            f"   {str(e)}\n"
            f"   Please verify the spreadsheet is shared with the service account."
        )
    
def upload_to_sheet(df: pd.DataFrame, chapter_title: str, output_spreadsheet_link: Optional[str] = None):
    """
    Upload quiz data to a Google Sheet.

    Args:
        df: DataFrame with quiz data
        chapter_title: Title of the chapter/worksheet
        output_spreadsheet_link: Google Sheets link or ID (optional)
                                If not provided, uses default from config
    """
    print("Uploading to Google Sheet...")

    creds = get_google_credentials()
    if not creds or not creds.valid:
        raise ValueError("Invalid Google service account credentials.")

    try:
        client = gspread.authorize(creds)
    except Exception as e:
        raise ValueError(f"Failed to authorize with Google Sheets API: {str(e)}")

    print("Google sheets authorized...")

    # Determine which spreadsheet to use
    if output_spreadsheet_link:
        spreadsheet_id = extract_spreadsheet_id(output_spreadsheet_link)
        print(f"📊 Using custom output spreadsheet (ID: {spreadsheet_id})")
        validate_spreadsheet_by_id(spreadsheet_id, creds)
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(f"❌ Spreadsheet with ID '{spreadsheet_id}' not found or not accessible.")
    else:
        # Legacy: use name-based lookup for backward compatibility
        spreadsheet_name = OUTPUT_SPREADSHEET_NAME
        print(f"📊 Using default output spreadsheet: '{spreadsheet_name}'")
        spreadsheet = client.open(spreadsheet_name)

    print("Spreadsheet opened for update...")

    try:
        worksheet = spreadsheet.worksheet(chapter_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=chapter_title, rows=100, cols=20)

    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

    print("✅ Google Sheet updated.")

    return spreadsheet.id, creds

# ======== STEP 4: Conditional Formatting ========
def apply_conditional_formatting(spreadsheet_id: str, chapter_title: str, df: pd.DataFrame, creds):
    sheets_api = build('sheets', 'v4', credentials=creds)

    # Get the sheet ID based on chapter_title
    sheet_metadata = sheets_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for s in sheet_metadata['sheets']:
        if s['properties']['title'] == chapter_title:
            sheet_id = s['properties']['sheetId']
            break
    if sheet_id is None:
        raise ValueError(f"Sheet ID not found for worksheet '{chapter_title}'")

    # Clear only formatting (keep contents intact)
    clear_all_sheet_formatting_only(sheets_api, spreadsheet_id, sheet_id)

    # Mapping: Option A–D -> Columns F–I (5–8)
    option_columns = {'a': 5, 'b': 6, 'c': 7, 'd': 8}
    highlight_color = {"red": 0.78, "green": 0.90, "blue": 0.79}
    requests = []

    # Iterate through each question row (skipping header)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        # SCQ: 'c', MCQ: 'bd', etc.
        correct_options = str(row[-1]).strip().lower()

        for letter, col_idx in option_columns.items():
            is_correct = letter in correct_options

            # Only apply formatting if correct; otherwise, skip to avoid clearing other formatting
            if is_correct:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": i,
                            "endRowIndex": i + 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": highlight_color
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })
    
    # Highlight the backup note row (The following...) in red background across columns A–F
    for i, row in enumerate(df.itertuples(index=False), start=1):
        if isinstance(row[0], str) and row[0].strip().startswith("The following"):
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": i,
                        "endRowIndex": i + 1,
                        "startColumnIndex": 0,  # Column A
                        "endColumnIndex": 6     # Column F (non-inclusive index)
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 1.0,
                                "green": 0.8,
                                "blue": 0.8
                            }
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

    # Send all formatting updates in one batch
    if requests:
        sheets_api.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    print("✅ Correct options highlighted in green.")

# ======== SRead Chapter Text from Spreadsheet ========
def read_chapter_text_from_sheet(chapter_title: str) -> Tuple[str, int]:
    print(f"Reading chapter text from spreadsheet: {chapter_title}")
    creds = get_google_credentials()

    client = gspread.authorize(creds)
    spreadsheet = client.open(INPUT_SPREADSHEET_NAME)

    try:
        worksheet = spreadsheet.worksheet(chapter_title)

        key_row = worksheet.col_values(1)[:2]  # A1, A2
        val_row = worksheet.col_values(2)[:2]  # B1, B2

        metadata = dict(zip(key_row, val_row))

        if "Content" not in metadata:
            raise ValueError(f"❌ Missing 'Content' key (A2) in sheet '{chapter_title}'.")

        content_val = metadata.get("Content")
        if content_val is None:
            raise ValueError(f"❌ 'Content' value is missing in sheet '{chapter_title}'.")
        
        chapter_text = str(content_val).strip()
        try:
            num_questions_val = metadata.get("NumQuestions")
            if num_questions_val is None:
                num_questions = 15
                print(f"⚠️ Warning: 'NumQuestions' was not provided in sheet '{chapter_title}', defaulting to 15.")
            else:
                num_questions = int(num_questions_val)
        except ValueError:
            print(f"⚠️ Warning: 'NumQuestions' is not a valid number in sheet '{chapter_title}', defaulting to 15.")
            num_questions = 15

        return chapter_text, num_questions

    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(f"❌ Chapter tab '{chapter_title}' not found in input spreadsheet.")


# ======== MAIN PIPELINE FUNCTION ========

# This function processes a single chapter either from a file or a spreadsheet
# It reads the chapter text, generates the quiz JSON, converts it to a DataFrame,
# uploads it to a Google Sheet, and applies conditional formatting.
# It returns the spreadsheet ID for further use if needed.

def process_chapter_to_sheet(
    chapter_path: Optional[str],
    chapter_title: str,
    num_questions: Optional[int],
    input_source: str,
    output_spreadsheet_link: Optional[str] = None,
    quiz_generator_fn=generate_quiz_json,
):
    if input_source == "spreadsheet":
        print(f"📘 Reading from spreadsheet: {chapter_title}")
        (chapter_text, num_questions) = read_chapter_text_from_sheet(chapter_title)
    elif input_source == "file":
        print(f"📘 Reading from file: {chapter_path}")
        assert chapter_path is not None, "chapter_path must not be None when input_source is 'file'"
        with open(chapter_path, "r", encoding="utf-8") as f:
            chapter_text = f.read()
    elif input_source == "gdoc":
        doc_link = app_config['documents']['link']
        print(f"📘 Reading from Google Doc: {doc_link}")
        chapter_text = read_chapter_text_from_gdoc(doc_link)
    else:
        raise ValueError("Invalid input source. Use 'spreadsheet', 'file' or 'gdoc'.")

    print(f"📘 Processing: {chapter_title} with {num_questions} questions...")
    quiz_json = quiz_generator_fn(chapter_text, num_questions)
    print(f"✅ Quiz Generated: {chapter_title}")

    df = quiz_json_to_dataframe(chapter_title, quiz_json, num_questions if num_questions is not None else 15)

    spreadsheet_id, creds = upload_to_sheet(df, chapter_title, output_spreadsheet_link)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)
    print(f"✅ Done: {chapter_title}\n")

    return spreadsheet_id  # Optional return

# ======== Processing Single Chapter ========
def run_single_quiz_pipeline(chapter_title: str, input_source: str, output_spreadsheet_link: Optional[str] = None):
    if input_source == "file":
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        if chapter_title:
            # get the chapter counts from the app_config YAML
            num_questions = app_config.get("chapter_question_counts", {}).get(chapter_title, 15)  # fallback to 15

            if not num_questions:
                raise ValueError(f"Chapter '{chapter_title}' not found in app config.")

            chapter_path = f"{DATA_DIR}/{chapter_title}.txt"
            if not os.path.exists(chapter_path):
                raise FileNotFoundError(f"No such chapter text file: {chapter_path}")
            process_chapter_to_sheet(chapter_path, chapter_title, num_questions, input_source, output_spreadsheet_link)
        else:
            # Process all .txt files in /data
            for fname in os.listdir(data_dir):
                if fname.endswith('.txt'):
                    chapter_name = os.path.splitext(fname)[0]
                    print(f"Processing chapter: {chapter_name}")
                    run_single_quiz_pipeline(chapter_name, input_source=input_source, output_spreadsheet_link=output_spreadsheet_link)
        return
    else:  # spreadsheet
        process_chapter_to_sheet(None, chapter_title, None, input_source, output_spreadsheet_link)

# ======== Processing Chapters in Batch ========
def run_batch_quiz_pipeline(input_source: str, output_spreadsheet_link: Optional[str] = None):        
    if input_source == "file":
        quiz_counts = app_config.get("chapter_question_counts", {})
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".txt"):
                chapter_path = os.path.join(DATA_DIR, filename)
                chapter_title = filename.replace(".txt", "").strip()
                num_questions = quiz_counts.get(chapter_title.lower(), 15)
                process_chapter_to_sheet(chapter_path, chapter_title, num_questions, input_source, output_spreadsheet_link)
    elif input_source == "spreadsheet":  # spreadsheet
        # ===== Get all sheet/tab names from input spreadsheet =====
        print(f"📘 Reading chapters from spreadsheet: {INPUT_SPREADSHEET_NAME}")
        creds = get_google_credentials()

        print("Authorizing Google Sheets API...")  
        if not creds or not creds.valid:
            raise ValueError("Invalid Google service account credentials.")
        
        client = gspread.authorize(creds)
        spreadsheet = client.open(INPUT_SPREADSHEET_NAME)

        print("Spreadsheet opened successfully...")
        sheet_list = spreadsheet.worksheets()
        chapter_titles = [sheet.title for sheet in sheet_list]
        
        for chapter_title in chapter_titles:
            process_chapter_to_sheet(None, chapter_title, None, input_source, output_spreadsheet_link)
    else:
        raise ValueError("Invalid input source. Use 'spreadsheet' or 'file'.")

# ======== Google Doc Processing ========
def process_chapter_to_sheet_gdoc(doc_link: str, num_questions: int, output_spreadsheet_link: Optional[str] = None, quiz_generator_fn=generate_quiz_json):
    """
    Process a chapter from a Google Doc link and number of questions.
    Uses the doc title as the chapter_title for the spreadsheet tab.
    """
    creds = get_google_credentials()
    chapter_title = get_gdoc_title(doc_link, creds)
    chapter_text = read_chapter_text_from_gdoc(doc_link)
    quiz_json = quiz_generator_fn(chapter_text, num_questions)
    df = quiz_json_to_dataframe(chapter_title, quiz_json, num_questions)
    spreadsheet_id, creds = upload_to_sheet(df, chapter_title, output_spreadsheet_link)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)
    print(f"✅ Done: {chapter_title}\n")
    return spreadsheet_id

# ======== Google Doc to Spreadsheet Workflow ========
def run_gdoc_to_spreadsheet_workflow(
    input_doc_link: str,
    output_spreadsheet_link: str,
    num_questions: int = 15,
    quiz_generator_fn=generate_quiz_json
):
    """
    Read content from a Google Doc and write quiz to a Google Spreadsheet.
    This is the default unified workflow.

    Args:
        input_doc_link: Google Doc link to read chapter text from
        output_spreadsheet_link: Google Sheets link to write quiz to
        num_questions: Number of questions to generate
        quiz_generator_fn: Function to generate quiz (default: generate_quiz_json)

    Returns:
        spreadsheet_id: The ID of the spreadsheet where quiz was written
    """
    print("=" * 60)
    print("🔄 Google Doc → Quiz → Google Spreadsheet Workflow")
    print("=" * 60)

    creds = get_google_credentials()

    print(f"📖 Reading from Google Doc: {input_doc_link}")
    chapter_title = get_gdoc_title(input_doc_link, creds)
    chapter_text = read_chapter_text_from_gdoc(input_doc_link)
    print(f"✅ Retrieved chapter: {chapter_title}")

    print(f"📘 Generating quiz with {num_questions} questions...")
    quiz_json = quiz_generator_fn(chapter_text, num_questions)
    print(f"✅ Quiz generated: {quiz_json['Topic']}")

    df = quiz_json_to_dataframe(chapter_title, quiz_json, num_questions)

    spreadsheet_id, creds = upload_to_sheet(df, chapter_title, output_spreadsheet_link)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)

    print(f"✅ Done: {chapter_title}\n")
    return spreadsheet_id

def run_batch_gdoc_to_spreadsheet_workflow(batch_config: list):
    """
    Process multiple Google Doc to Spreadsheet pairs in batch.

    Args:
        batch_config: List of dicts with input_link, output_link, and num_questions

    Returns:
        results: List of dicts with processing results (success/failed)
    """
    print("=" * 60)
    print(f"🔄 Batch Processing: {len(batch_config)} documents")
    print("=" * 60)

    results = []
    for idx, config in enumerate(batch_config, 1):
        input_link = config.get('input_link')
        output_link = config.get('output_link')
        num_questions = config.get('num_questions', 15)

        if not input_link or not output_link:
            print(f"❌ Skipping batch item {idx}: missing input_link or output_link")
            continue

        print(f"\n[{idx}/{len(batch_config)}] Processing...")
        try:
            spreadsheet_id = run_gdoc_to_spreadsheet_workflow(
                input_link,
                output_link,
                num_questions
            )
            results.append({
                'index': idx,
                'status': 'success',
                'spreadsheet_id': spreadsheet_id
            })
        except Exception as e:
            print(f"❌ Error processing batch item {idx}: {str(e)}")
            results.append({
                'index': idx,
                'status': 'failed',
                'error': str(e)
            })

    print("\n" + "=" * 60)
    print("📊 Batch Processing Summary")
    print("=" * 60)
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    print(f"✅ Successful: {successful}/{len(batch_config)}")
    print(f"❌ Failed: {failed}/{len(batch_config)}")

    return results

# ======== Main ========
def main():
    parser = argparse.ArgumentParser(
        description="Quiz generation pipeline with multiple modes"
    )

    parser.add_argument(
        '--mode',
        choices=['default_quiz_gen', 'file', 'spreadsheet'],
        default='default_quiz_gen',
        help='Quiz generation mode: default_quiz_gen (default), file, or spreadsheet'
    )
    parser.add_argument(
        '--chapter',
        type=str,
        default=None,
        help='Specific chapter to process (optional)'
    )
    parser.add_argument(
        '--output_spreadsheet',
        type=str,
        default=None,
        help='Custom output spreadsheet link or ID (optional)'
    )
    parser.add_argument(
        '--num_questions',
        type=int,
        default=None,
        help='Number of questions to generate (overrides config value)'
    )
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Use batch mode for default_quiz_gen (processes multiple doc/sheet pairs from config)'
    )

    args = parser.parse_args()

    # ===== Default Quiz Generation Mode =====
    if args.mode == 'default_quiz_gen':
        doc_config = app_config.get('source_documents', {})

        # Batch mode
        if args.batch:
            batch_config = doc_config.get('batch', [])
            if not batch_config:
                raise ValueError(
                    "❌ No batch configuration found in app_config.yaml\n"
                    "   Please add:\n"
                    "   source_documents:\n"
                    "     batch:\n"
                    "       - input_link: ...\n"
                    "         output_link: ...\n"
                    "         num_questions: 15"
                )
            run_batch_gdoc_to_spreadsheet_workflow(batch_config)
            return

        # Single pair mode
        if not doc_config.get('input_link'):
            raise ValueError(
                "❌ Missing 'source_documents.input_link' in app_config.yaml\n"
                "   Please add:\n"
                "   source_documents:\n"
                "     input_link: https://docs.google.com/document/d/{DOC_ID}/edit\n"
                "     output_link: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit\n"
                "     num_questions: 15"
            )

        if not doc_config.get('output_link'):
            raise ValueError(
                "❌ Missing 'source_documents.output_link' in app_config.yaml\n"
                "   Please add:\n"
                "   source_documents:\n"
                "     input_link: https://docs.google.com/document/d/{DOC_ID}/edit\n"
                "     output_link: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit\n"
                "     num_questions: 15"
            )

        input_doc_link = doc_config['input_link']
        output_spreadsheet_link = doc_config['output_link']
        num_questions = args.num_questions or doc_config.get('num_questions', 15)

        run_gdoc_to_spreadsheet_workflow(input_doc_link, output_spreadsheet_link, num_questions)
        return

    # ===== File/Spreadsheet Modes (Legacy) =====
    input_source = args.mode
    chapter = args.chapter
    output_spreadsheet_link = args.output_spreadsheet

    if input_source == "file":
        run_single_quiz_pipeline(chapter, input_source=input_source, output_spreadsheet_link=output_spreadsheet_link)
    else:
        run_batch_quiz_pipeline(input_source=input_source, output_spreadsheet_link=output_spreadsheet_link)

    log_and_print("Quiz generation pipeline started.")

if __name__ == "__main__":
    main()
