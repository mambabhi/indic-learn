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
from quiz.backend.utils.gsheets import clear_all_sheet_formatting_only
from quiz.backend.utils.logging_utils import log_and_print


# Load environment variables and app config
SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]
INPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["input_name"]
OUTPUT_SPREADSHEET_NAME = app_config["spreadsheets"]["output_name"]

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
def upload_to_sheet(df: pd.DataFrame, chapter_title: str):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open(OUTPUT_SPREADSHEET_NAME)

    # Check if sheet with chapter_title exists, else create it
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
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
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
    else:
        raise ValueError("Invalid input source. Use 'spreadsheet' or 'file'.")

    print(f"📘 Processing: {chapter_title} with {num_questions} questions...")
    quiz_json = quiz_generator_fn(chapter_text, num_questions)
    print(f"✅ Quiz Generated: {chapter_title}")

    df = quiz_json_to_dataframe(chapter_title, quiz_json, num_questions if num_questions is not None else 15)

    spreadsheet_id, creds = upload_to_sheet(df, chapter_title)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)
    print(f"✅ Done: {chapter_title}\n")

    return spreadsheet_id  # Optional return

# ======== Processing Single Chapter ========
def run_single_quiz_pipeline(chapter_title: str, input_source: str):
    data_folder = "data"

    if input_source == "file":
        # get the chapter counts from the app_config YAML
        num_questions = app_config.get("chapter_question_counts", {}).get(chapter_title, 15)  # fallback to 15

        if not num_questions:
            raise ValueError(f"Chapter '{chapter_title}' not found in app config.")

        chapter_path = f"{data_folder}/{chapter_title}.txt"
        if not os.path.exists(chapter_path):
            raise FileNotFoundError(f"No such chapter text file: {chapter_path}")
        process_chapter_to_sheet(chapter_path, chapter_title, num_questions, input_source)
    else:  # spreadsheet
        process_chapter_to_sheet(None, chapter_title, None, input_source)

# ======== Processing Chapters in Batch ========
def run_batch_quiz_pipeline(input_source: str):        
    if input_source == "file":
        data_folder = "data"
        quiz_counts = app_config.get("chapter_question_counts", {})
        for filename in os.listdir(data_folder):
            if filename.endswith(".txt"):
                chapter_path = os.path.join(data_folder, filename)
                chapter_title = filename.replace(".txt", "").strip()
                num_questions = quiz_counts.get(chapter_title.lower(), 15)
                process_chapter_to_sheet(chapter_path, chapter_title, num_questions, input_source)
    elif input_source == "spreadsheet":  # spreadsheet
        # ===== Get all sheet/tab names from input spreadsheet =====
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open(INPUT_SPREADSHEET_NAME)

        sheet_list = spreadsheet.worksheets()
        chapter_titles = [sheet.title for sheet in sheet_list]

        for chapter_title in chapter_titles:
            process_chapter_to_sheet(None, chapter_title, None, input_source)
    else:
        raise ValueError("Invalid input source. Use 'spreadsheet' or 'file'.")

# ======== Main ========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run quiz pipeline for Gurukula content.")
    parser.add_argument(
        "--input_source",
        type=str,
        choices=["spreadsheet", "file"],
        required=True,
        help="Where to read the chapter text from: 'spreadsheet' or 'file'"
    )
    parser.add_argument(
        "--chapter",
        type=str,
        help="Run quiz generation for a specific chapter (e.g. 'chapter16')"
    )

    args = parser.parse_args()

    if args.chapter:
        run_single_quiz_pipeline(args.chapter, input_source=args.input_source)
    else:
        run_batch_quiz_pipeline(input_source=args.input_source)

    log_and_print("Quiz generation pipeline started.")
