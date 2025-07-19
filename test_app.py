import sys
import os
import tempfile
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import gradio as gr
from quiz.backend.gurukula_quizgen import process_chapter_to_sheet
import gspread
from google.oauth2.service_account import Credentials
import datetime
from dotenv import load_dotenv;
load_dotenv()  

# 1. Store your service account JSON securely as a multiline string or from HF secret
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")  # e.g. from Hugging Face secret

# 2. Write to a temporary file
if GOOGLE_SERVICE_ACCOUNT_JSON:
    temp_cred = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_cred.write(GOOGLE_SERVICE_ACCOUNT_JSON.encode("utf-8"))
    temp_cred.close()

    # 3. Set the env var before config loads
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_cred.name
    os.environ["GOOGLE_SCOPES"] = "https://www.googleapis.com/auth/spreadsheets"

# 4. Now import config (AFTER env vars are set)
from quiz.backend.config import load_env_vars, load_app_config
env_config = load_env_vars()
app_config = load_app_config()

# 5. Extract config values
SERVICE_ACCOUNT_FILE = env_config["SERVICE_ACCOUNT_FILE"]
GOOGLE_SCOPES = env_config["GOOGLE_SCOPES"]

# Track processed chapters per session
processed_today = []

def is_valid_gsheet_url(url: str) -> bool:
    return (
        isinstance(url, str)
        and url.startswith("https://docs.google.com/")
        and "/spreadsheets/" in url
        and len(url.strip()) > 40
    )

def extract_sheet_id(url: str) -> str:
    try:
        return url.split("/d/")[1].split("/")[0]
    except IndexError:
        return ""

def is_valid_chapter_list(chapter_list: str) -> bool:
    chapters = [c.strip() for c in chapter_list.split(",") if c.strip()]
    return all(re.fullmatch(r"[A-Za-z0-9]+", c) for c in chapters)

def get_all_chapters(spreadsheet_url):
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(spreadsheet_url)
        return [ws.title for ws in sheet.worksheets()]
    except Exception as e:
        return f"❌ Failed to read spreadsheet: {str(e)}"

def generate_quiz(input_link, output_link, specific_chapter, chapter_list, progress=gr.Progress()):
    global processed_today
    logs = []

    # --- Validation ---
    if not is_valid_gsheet_url(input_link):
        return "❌ Invalid Input Spreadsheet URL. Please provide a valid Google Sheets link.", logs
    if not is_valid_gsheet_url(output_link):
        return "❌ Invalid Output Spreadsheet URL. Please provide a valid Google Sheets link.", logs
    if extract_sheet_id(input_link) == extract_sheet_id(output_link):
        return "❌ Input and Output Spreadsheet URLs must be different.", logs

    if chapter_list and not is_valid_chapter_list(chapter_list):
        return "❌ Invalid chapter list. Use only alphanumeric names, separated by commas (e.g., chapter1, chapter2).", logs

    chapters = []
    if specific_chapter:
        chapters = [specific_chapter.strip()]
    elif chapter_list:
        chapters = [c.strip() for c in chapter_list.split(",") if c.strip()]
    else:
        result = get_all_chapters(input_link)
        if isinstance(result, str):  # error
            return result, logs
        chapters = result

    today = datetime.date.today()
    if len(processed_today) >= 6:
        return "⚠️ Daily limit of 6 chapters reached.", logs

    count_to_process = min(6 - len(processed_today), len(chapters))
    chapters = chapters[:count_to_process]

    progress(0)
    for i, chapter in enumerate(chapters):
        try:
            logs.append(f"📘 Processing {chapter}...")
            spreadsheet_id = process_chapter_to_sheet(None, chapter, None, "spreadsheet")
            logs.append(f"✅ Completed: {chapter} → Sheet ID: {spreadsheet_id}")
            processed_today.append((chapter, today))
        except Exception as e:
            logs.append(f"❌ Error processing {chapter}: {str(e)}")
        progress((i + 1) / count_to_process)

    return f"✅ {len(chapters)} chapter(s) processed successfully.", logs

# ======================
# Gradio UI
# ======================
with gr.Blocks(title="Gurukula Admin Portal") as demo:
    with gr.Tabs():
        with gr.Tab("Quiz Generator"):
            gr.Markdown("### ✍️ Generate Quiz from Indic Story Chapters")
            gr.Markdown("ℹ️ **Note:** If no specific chapters are entered, the first 6 chapters from the input spreadsheet will be processed.")

            input_link = gr.Textbox(label="Input Spreadsheet URL", placeholder="https://docs.google.com/...")
            output_link = gr.Textbox(label="Output Spreadsheet URL", placeholder="https://docs.google.com/...")
            specific_chapter = gr.Textbox(label="Process Only This Chapter (Optional)")
            chapter_list = gr.Textbox(
                label="List of Chapters (comma-separated) – optional but recommended (runs first 6 if left blank)", 
                placeholder="chapter1, chapter2"
            )

            run_button = gr.Button("Generate Quiz")
            output_text = gr.Textbox(label="Status", lines=1, interactive=False)
            output_logs = gr.Textbox(label="Logs", lines=10, interactive=False)

            run_button.click(
                fn=generate_quiz,
                inputs=[input_link, output_link, specific_chapter, chapter_list],
                outputs=[output_text, output_logs]
            )

        with gr.Tab("Storyboard Image"):
            gr.Markdown("📸 *Storyboard module coming soon...*")

        with gr.Tab("Animation"):
            gr.Markdown("🎬 *Animation module coming soon...*")

if __name__ == "__main__":
    demo.launch(share=True)
