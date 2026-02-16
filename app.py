import sys
import os
import re
from typing import Union
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import gradio as gr
from quiz.backend.gurukula_quizgen import (
    run_gdoc_to_spreadsheet_workflow,
)
import gspread
from quiz.backend.utils.gsheets import get_google_credentials
import datetime

def is_valid_gsheet_url(url: str) -> bool:
    """Validate Google Sheets URL format"""
    return (
        isinstance(url, str)
        and url.startswith("https://docs.google.com/")
        and "/spreadsheets/" in url
        and len(url.strip()) > 40
    )

def is_valid_gdoc_url(url: str) -> bool:
    """Validate Google Doc URL format"""
    return (
        isinstance(url, str)
        and url.startswith("https://docs.google.com/")
        and "/document/" in url
        and len(url.strip()) > 40
    )

def is_valid_num_questions(num_str: str) -> tuple[bool, Union[int, None]]:
    """
    Validate and parse number of questions.
    Returns (is_valid, num_questions)
    """
    if not num_str or not num_str.strip():
        return True, 15  # Default to 15 if empty
    
    try:
        n = int(num_str.strip())
        if n < 1 or n > 30:
            return False, None
        return True, n
    except ValueError:
        return False, None

def generate_quiz(
    gdoc_link_1,
    num_questions_1,
    gdoc_link_2,
    num_questions_2,
    gdoc_link_3,
    num_questions_3,
    output_spreadsheet,
    progress=gr.Progress()
):
    """
    Generate quiz from Google Docs and write to spreadsheet.
    
    Args:
        gdoc_link_1, gdoc_link_2, gdoc_link_3: Google Doc URLs
        num_questions_1, num_questions_2, num_questions_3: Number of questions for each doc
        output_spreadsheet: Output Google Sheets URL
        progress: Gradio progress tracker
    """
    logs = []

    # Validate output spreadsheet
    if not output_spreadsheet or not output_spreadsheet.strip():
        return "❌ Output Spreadsheet URL is required.", logs
    
    if not is_valid_gsheet_url(output_spreadsheet):
        return "❌ Invalid Output Spreadsheet URL format. Please provide a valid Google Sheets link (e.g., https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit).", logs
    
    # Collect valid doc pairs
    valid_pairs = []
    doc_inputs = [
        (gdoc_link_1, num_questions_1),
        (gdoc_link_2, num_questions_2),
        (gdoc_link_3, num_questions_3)
    ]
    
    for idx, (link, num_str) in enumerate(doc_inputs, 1):
        link = link.strip() if link else ""
        num_str = num_str.strip() if num_str else ""
        
        # Skip empty rows
        if not link and not num_str:
            continue
        
        # Validate that both link and num_questions are provided together
        if link and not num_str:
            return f"❌ Chapter Link {idx} is provided but 'Num Questions' is missing.", logs
        
        if not link and num_str:
            return f"❌ 'Num Questions' is provided for Chapter Link {idx} but no link was provided.", logs
        
        # Validate Google Doc URL format
        if not is_valid_gdoc_url(link):
            return f"❌ Invalid Google Doc link format for Chapter Link {idx}. Please provide a valid Google Docs link (e.g., https://docs.google.com/document/d/YOUR_DOC_ID/edit).", logs
        
        # Validate number of questions
        is_valid, n = is_valid_num_questions(num_str)
        if not is_valid:
            return f"❌ 'Num Questions' for Chapter Link {idx} must be a number between 1 and 30.", logs
        
        valid_pairs.append((link, n))
    
    # Check that at least one doc is provided
    if not valid_pairs:
        return "❌ Please provide at least one Google Doc link with a valid number of questions (1-30).", logs
    
    # Process all valid pairs
    count_to_process = len(valid_pairs)
    progress(0)
    for i, (link, n) in enumerate(valid_pairs):
        try:
            logs.append(f"📘 Processing GDoc: {link[:60]}... with {n} questions...")
            spreadsheet_id = run_gdoc_to_spreadsheet_workflow(
                input_doc_link=link,
                output_spreadsheet_link=output_spreadsheet,
                num_questions=n
            )
            logs.append(f"✅ Completed: Sheet ID: {spreadsheet_id}")
        except Exception as e:
            logs.append(f"❌ Error processing document: {str(e)}")
        progress((i + 1) / count_to_process)
    
    return f"✅ {len(valid_pairs)} Google Doc(s) processed successfully.", logs

# ======================
# Gradio UI
# ======================
with gr.Blocks(title="Gurukula Admin Portal") as demo:
    with gr.Tabs():
        with gr.Tab("Quiz Generator"):
            gr.Markdown("### ✍️ Generate Quiz from Google Docs")

            with gr.Column():
                gr.Markdown("""
                Add up to 3 Google Doc links with their question counts, and specify a single output spreadsheet.
                
                **Requirements:**
                - Each Google Doc link must start with `https://docs.google.com/document/`
                - Number of questions must be between 1 and 30 (leave blank for default 15)
                - Output Spreadsheet must start with `https://docs.google.com/spreadsheets/`
                """)
                
                with gr.Row():
                    gdoc_link_1 = gr.Textbox(label="Chapter Link 1", placeholder="https://docs.google.com/document/d/{DOC_ID}/edit")
                    num_questions_1 = gr.Textbox(label="Num Questions", placeholder="15 (or leave blank)")

                with gr.Row():
                    gdoc_link_2 = gr.Textbox(label="Chapter Link 2", placeholder="https://docs.google.com/document/d/{DOC_ID}/edit")
                    num_questions_2 = gr.Textbox(label="Num Questions", placeholder="15 (or leave blank)")

                with gr.Row():
                    gdoc_link_3 = gr.Textbox(label="Chapter Link 3", placeholder="https://docs.google.com/document/d/{DOC_ID}/edit")
                    num_questions_3 = gr.Textbox(label="Num Questions", placeholder="15 (or leave blank)")

                output_spreadsheet = gr.Textbox(
                    label="Output Spreadsheet URL (required)",
                    placeholder="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
                )

            run_button = gr.Button("Generate Quiz", variant="primary")
            output_text = gr.Textbox(label="Status", lines=1, interactive=False)
            output_logs = gr.Textbox(label="Logs", lines=10, interactive=False)

            run_button.click(
                fn=generate_quiz,
                inputs=[
                    gdoc_link_1, num_questions_1,
                    gdoc_link_2, num_questions_2,
                    gdoc_link_3, num_questions_3,
                    output_spreadsheet
                ],
                outputs=[output_text, output_logs]
            )

        with gr.Tab("Storyboard Image"):
            gr.Markdown("📸 *Storyboard module coming soon...*")

        with gr.Tab("Animation"):
            gr.Markdown("🎬 *Animation module coming soon...*")

if __name__ == "__main__":
    demo.launch()