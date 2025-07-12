# backend/gurukula_quizgen.py
# -*- coding: utf-8 -*-

import os
import argparse
import re
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import load_app_config

from dotenv import load_dotenv; load_dotenv()
from config import env_config, app_config
from indic_quiz_generator_pipeline import (
    run_parallel_quiz_with_mcq_retry,
)
from utils.gsheets import clear_all_sheet_formatting_only

SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]
SPREADSHEET_NAME = app_config["spreadsheet"]["name"]

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

def quiz_json_to_dataframe(quiz_json: dict) -> pd.DataFrame:
    questions = quiz_json['Questions']
    return pd.DataFrame(
        {
            "Chapter": q["Chapter"],
            "Timer": q["Timer"],
            "Points": q["Number_Of_Points_Earned"],
            "Type": "SCQ" if (q["Question_type"] == "MCQ" and len(q["Right_Option"].replace(" ", "")) == 1) else q["Question_type"],
            "Question": q["Question"].strip() + "?" if not q["Question"].strip().endswith("?") else q["Question"].strip(),
            "Option A": clean_option(q["Options"][0]) if len(q["Options"]) > 0 else "",
            "Option B": clean_option(q["Options"][1]) if len(q["Options"]) > 1 else "",
            "Option C": clean_option(q["Options"][2]) if len(q["Options"]) > 2 else "",
            "Option D": clean_option(q["Options"][3]) if len(q["Options"]) > 3 else "",
            "Right Answer": q["Right_Option"].replace(" ", "").lower()
        }
        for q in questions
    ).sample(frac=1, random_state=42).reset_index(drop=True)

# ======== STEP 3: Upload to Google Sheet ========
def upload_to_sheet(df: pd.DataFrame, chapter_title: str):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open(SPREADSHEET_NAME)

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

    # Send all formatting updates in one batch
    if requests:
        sheets_api.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    print("✅ Correct options highlighted in green.")

# ======== MAIN PIPELINE FUNCTION ========

def process_chapter_to_sheet(
    chapter_path: str,
    chapter_title: str,
    num_questions: int,
    quiz_generator_fn=generate_quiz_json
):
    print(f"📘 Reading File: {chapter_path} ...")
    with open(chapter_path, "r", encoding="utf-8") as f:
        chapter_text = f.read()

    print(f"📘 Processing: {chapter_title} with {num_questions} questions...")
    quiz_json = quiz_generator_fn(chapter_text, num_questions)
    print(f"✅ Quiz Generated: {chapter_title}")

    df = quiz_json_to_dataframe(quiz_json)

    spreadsheet_id, creds = upload_to_sheet(df, chapter_title)
    apply_conditional_formatting(spreadsheet_id, chapter_title, df, creds)
    print(f"✅ Done: {chapter_title}\n")

    return spreadsheet_id  # Optional return

# ======== Processing Single Chapter ========
def run_single_quiz_pipeline(chapter_title: str, ):
    # get the chapter counts from the app_config YAML
    num_questions = app_config.get("chapter_question_counts", {}).get(chapter_title, 15)  # fallback to 15

    if not num_questions:
        raise ValueError(f"Chapter '{chapter_title}' not found in app config.")

    chapter_path = f"data/{chapter_title}.txt"
    if not os.path.exists(chapter_path):
        raise FileNotFoundError(f"No such chapter text file: {chapter_path}")

    process_chapter_to_sheet(chapter_path, chapter_title, num_questions)

# ======== Processing Chapters in Batch ========
def run_batch_quiz_pipeline():
    app_config = load_app_config()
    data_folder = "data"
    quiz_counts = app_config.get("chapter_question_counts", {})

    for filename in os.listdir(data_folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_folder, filename)
            chapter_title = filename.replace(".txt", "").replace("data/", "").strip()

            num_questions = quiz_counts.get(chapter_title.lower(), 15)  # default to 15 if not found

            process_chapter_to_sheet(filepath, chapter_title, num_questions)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run quiz pipeline for Gurukula content.")
    parser.add_argument("--chapter", type=str, help="Run quiz generation for a specific chapter (e.g. 'chapter16')")

    args = parser.parse_args()

    if args.chapter:
        run_single_quiz_pipeline(args.chapter)
    else:
        run_batch_quiz_pipeline()
