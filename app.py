import sys
import os
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import gradio as gr
from quiz.backend.gurukula_quizgen import process_chapter_to_sheet
import gspread
from quiz.backend.utils.gsheets import get_google_credentials
import datetime

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
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        sheet = client.open_by_url(spreadsheet_url)
        return [ws.title for ws in sheet.worksheets()]
    except Exception as e:
        return f"❌ Failed to read spreadsheet: {str(e)}"

def is_valid_gdoc_url(url: str) -> bool:
    return (
        isinstance(url, str)
        and url.startswith("https://docs.google.com/")
        and "/document/" in url
        and len(url.strip()) > 40
    )

def generate_quiz(
    input_mode,
    gdoc_links,
    gdoc_num_questions,
    input_link,
    output_link,
    specific_chapter,
    chapter_list,
    progress=gr.Progress()
):
    global processed_today
    logs = []

    if input_mode == "Google Docs":
        valid_pairs = []
        for link, num in zip(gdoc_links, gdoc_num_questions):
            link = link.strip()
            num = num.strip()
            if link:
                if not is_valid_gdoc_url(link):
                    return f"❌ Invalid Google Doc link: {link}", logs
                if num:
                    if not num.isdigit():
                        return f"❌ Number of questions must be numeric for link: {link}", logs
                    n = int(num)
                    if n < 2 or n > 20:
                        return f"❌ Number of questions must be between 2 and 20 for link: {link}", logs
                else:
                    n = 15
                valid_pairs.append((link, n))
            elif num:
                return "❌ Number of questions provided without a Google Doc link.", logs
        if not valid_pairs:
            return "❌ Please provide at least one Google Doc link.", logs
        today = datetime.date.today()
        if len(processed_today) >= 6:
            return "⚠️ Daily limit of 6 docs reached.", logs
        count_to_process = min(6 - len(processed_today), len(valid_pairs))
        valid_pairs = valid_pairs[:count_to_process]
        progress(0)
        for i, (link, n) in enumerate(valid_pairs):
            try:
                logs.append(f"📘 Processing GDoc: {link} with {n} questions...")
                from quiz.backend.gurukula_quizgen import process_chapter_to_sheet_gdoc
                spreadsheet_id = process_chapter_to_sheet_gdoc(link, n)
                logs.append(f"✅ Completed: {link} → Sheet ID: {spreadsheet_id}")
                processed_today.append((link, today))
            except Exception as e:
                logs.append(f"❌ Error processing {link}: {str(e)}")
            progress((i + 1) / count_to_process)
        return f"✅ {len(valid_pairs)} Google Doc(s) processed successfully.", logs

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

def gdoc_input_filter(input_mode, *args):
    gdoc_links = args[:3]
    gdoc_num_questions = args[3:6]
    rest = args[6:]
    if input_mode == "Google Docs":
        filtered = [(l, n) for l, n in zip(gdoc_links, gdoc_num_questions) if l.strip()]
        if filtered:
            links, nums = zip(*filtered)
            return [input_mode, list(links), list(nums)] + list(rest)
        else:
            return [input_mode, [], []] + list(rest)
    else:
        return [input_mode, [], []] + list(rest)

# ======================
# Gradio UI
# ======================
with gr.Blocks(title="Gurukula Admin Portal") as demo:
    with gr.Tabs():
        with gr.Tab("Quiz Generator"):
            gr.Markdown("### ✍️ Generate Quiz from Indic Story Chapters")

            input_mode = gr.Radio([
                "Google Docs", "Spreadsheets"
            ], value="Google Docs", label="Input Source")

            with gr.Column(visible=True) as gdoc_ui:
                gdoc_links = []
                gdoc_num_questions = []
                for i in range(3):
                    with gr.Row():
                        gdoc_link = gr.Textbox(label=f"Chapter Link {i+1}", placeholder="https://docs.google.com/document/...")
                        num_questions = gr.Textbox(label="Num Questions", placeholder="15")
                        gdoc_links.append(gdoc_link)
                        gdoc_num_questions.append(num_questions)

            with gr.Column(visible=False) as spreadsheet_ui:
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

            def toggle_ui(mode):
                return (
                    gr.update(visible=(mode == "Google Docs")),
                    gr.update(visible=(mode == "Spreadsheets"))
                )
            input_mode.change(
                toggle_ui,
                inputs=[input_mode],
                outputs=[gdoc_ui, spreadsheet_ui]
            )

            run_button.click(
                fn=lambda *args: generate_quiz(*gdoc_input_filter(*args)),
                inputs=[input_mode, *gdoc_links, *gdoc_num_questions, input_link, output_link, specific_chapter, chapter_list],
                outputs=[output_text, output_logs]
            )

        with gr.Tab("Storyboard Image"):
            gr.Markdown("📸 *Storyboard module coming soon...*")

        with gr.Tab("Animation"):
            gr.Markdown("🎬 *Animation module coming soon...*")

if __name__ == "__main__":
    demo.launch()
