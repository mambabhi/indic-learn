import sys
import os

# 👇 Add parent directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gradio as gr
from backend.indic_quiz_generator_pipeline import build_english_quiz_agent, build_quiz_prompt, QuizParser
from dotenv import load_dotenv; load_dotenv()

english_quiz_agent = build_english_quiz_agent()
parser = QuizParser()

quiz_data = {"questions": [], "index": 0, "answers": [], "last_selected": None}

def generate_quiz(topic, story):
    final_prompt = build_quiz_prompt(story, num_questions=15)

    try:
        english_quiz = english_quiz_agent.run(final_prompt)
    except Exception as e:
        return (
            gr.update(visible=True),  # input_form
            gr.update(visible=False),  # flashcard
            gr.update(value=f"Error: {str(e)}"),  # question_text
            gr.update(visible=False),  # radio
            gr.update(visible=False),  # checkbox
            gr.update(visible=False),  # mcq_submit_btn
            gr.update(value=""),  # feedback
            gr.update(visible=False),  # flip
            gr.update(visible=False)  # next
        )

    english_quiz_text = parser.run(english_quiz.content)
    quiz_data["questions"] = english_quiz_text["Questions"]
    quiz_data["index"] = 0
    quiz_data["answers"] = []
    quiz_data["last_selected"] = None

    return render_question(0)

def render_question(index):
    q = quiz_data["questions"][index]
    question = f"**Question {index+1} of {len(quiz_data['questions'])}:**\n" + q["Question"]
    options = q["Options"]
    qtype = q["Question_type"].upper()

    quiz_data["last_selected"] = None

    if qtype == "SCQ":
        return (
            gr.update(visible=False),  # input_form
            gr.update(visible=True),  # flashcard
            gr.update(value=question),  # question_text
            gr.update(choices=options, value=None, visible=True, interactive=True),  # radio
            gr.update(choices=[], value=None, visible=False),  # checkbox
            gr.update(visible=False),  # mcq_submit_btn
            gr.update(value=""),  # feedback
            gr.update(visible=False),  # flip
            gr.update(visible=True)  # next
        )
    else:  # MCQ
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value=question),
            gr.update(choices=[], value=None, visible=False),  # radio
            gr.update(choices=options, value=None, visible=True, interactive=True),  # checkbox
            gr.update(visible=True),  # mcq_submit_btn
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False)
        )

def submit_scq(option):
    if option is None:
        return gr.update(), "⚠️ Please select an option. Or, flip to reveal the answer.", gr.update(visible=False)

    quiz_data["last_selected"] = option
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct = current_q["Right_Option"].lower()
    selected = option[0].lower()

    if selected == correct:
        feedback = f"✅ Correct! The answer is: {option}"
    else:
        feedback = f"❌ Incorrect. You chose: {option}"

    return gr.update(interactive=False), feedback, gr.update(visible=True)

def submit_mcq(selected_options):
    if not selected_options:
        return (
            gr.update(),  # leave checkbox state unchanged
            "⚠️ Please select at least one option.",
            gr.update(visible=False),
            gr.update(visible=False)
        )

    quiz_data["last_selected"] = selected_options
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct_letters = set(current_q["Right_Option"].lower())
    selected_letters = set(opt[0].lower() for opt in selected_options)

    if selected_letters == correct_letters:
        feedback = f"✅ Correct! The answer(s): {', '.join(selected_options)}"
    else:
        feedback = f"❌ Incorrect. You chose: {', '.join(selected_options)}"

    return (
        gr.update(interactive=False),  # disable MCQ checkboxes
        feedback,
        gr.update(visible=True),  # flip button
        gr.update(visible=True)   # next question button
    )

def flip_to_show_answer():
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct_letters = set(current_q["Right_Option"].lower())
    correct_options = [
        opt for opt in current_q["Options"] if opt[0].lower() in correct_letters
    ]
    return gr.update(value=f"✅ Correct answer(s): {', '.join(correct_options)}")

def next_question():
    quiz_data["index"] += 1
    if quiz_data["index"] >= len(quiz_data["questions"]):
        return (
            gr.update(visible=True),  # input_form
            gr.update(visible=False),  # flashcard
            gr.update(value="🎉 Quiz complete! You can go back and try a new story."),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False)
        )
    return render_question(quiz_data["index"])

def go_back():
    quiz_data["questions"] = []
    quiz_data["index"] = 0
    quiz_data["answers"] = []
    quiz_data["last_selected"] = None

    return (
        gr.update(visible=True),   # input form
        gr.update(visible=False),  # flashcard
        gr.update(value=""),
        gr.update(choices=[], value=None, visible=False),
        gr.update(choices=[], value=None, visible=False),
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(visible=False),
        gr.update(visible=True)
    )

with gr.Blocks() as demo:
    with gr.Column(visible=True) as input_form:
        topic_input = gr.Textbox(label="Enter quiz topic", placeholder="e.g. The King’s Monkey Servant")
        story_input = gr.Textbox(label="Enter a story", lines=10)
        submit_btn = gr.Button("Generate Quiz")

    with gr.Column(visible=False) as flashcard:
        question_text = gr.Markdown()
        scq_options = gr.Radio(choices=[], label="Select one option", interactive=True, visible=False)
        mcq_options = gr.CheckboxGroup(choices=[], label="Select multiple options", visible=False)
        mcq_submit_btn = gr.Button("Submit MCQ", visible=False)
        feedback_text = gr.Markdown()
        flip_btn = gr.Button("Flip to show answer", visible=False)
        next_btn = gr.Button("Next Question", visible=True)
        back_btn = gr.Button("Go back to story input", visible=True)

    submit_btn.click(
        generate_quiz,
        inputs=[topic_input, story_input],
        outputs=[
            input_form, flashcard, question_text,
            scq_options, mcq_options, mcq_submit_btn,
            feedback_text, flip_btn, next_btn
        ]
    )

    scq_options.change(
        submit_scq,
        inputs=scq_options,
        outputs=[scq_options, feedback_text, flip_btn]
    )

    mcq_submit_btn.click(
        submit_mcq,
        inputs=mcq_options,
        outputs=[mcq_options, feedback_text, flip_btn, next_btn]
    )

    flip_btn.click(flip_to_show_answer, outputs=feedback_text)

    next_btn.click(
        next_question,
        outputs=[
            input_form, flashcard, question_text,
            scq_options, mcq_options, mcq_submit_btn,
            feedback_text, flip_btn, next_btn
        ]
    )

    back_btn.click(
        go_back,
        outputs=[
            input_form, flashcard, question_text,
            scq_options, mcq_options, mcq_submit_btn,
            feedback_text, flip_btn, next_btn
        ]
    )

if __name__ == "__main__":
    demo.launch()
