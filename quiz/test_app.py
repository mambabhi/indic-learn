import gradio as gr
from backend.indic_quiz_generator_pipeline import build_english_quiz_agent, build_quiz_prompt, QuizParser
from dotenv import load_dotenv; load_dotenv()

english_quiz_agent = build_english_quiz_agent()
parser = QuizParser()

quiz_data = {"questions": [], "index": 0, "answers": [], "last_selected": None}

def generate_quiz(topic, story, mode):
    final_prompt = build_quiz_prompt(story, num_questions=15)

    try: 
        english_quiz = english_quiz_agent.run(final_prompt)
    except Exception as e:
        return (
            gr.update(visible=True),  # input_form
            gr.update(visible=False),  # flashcard
            gr.update(visible=False),  # csv_output_form
            gr.update(value=f"Error: {str(e)}"),  # question_text
            gr.update(choices=[], value=None, visible=False),  # scq
            gr.update(choices=[], value=None, visible=False),  # mcq
            gr.update(visible=False),  # shared_submit
            gr.update(value=""),  # feedback
            gr.update(visible=False),  # flip
            gr.update(visible=True),  # next
            gr.update(value="")  # csv_text_output
        )

    english_quiz_text = parser.run(english_quiz.content)
    quiz_data["questions"] = english_quiz_text["Questions"]
    quiz_data["index"] = 0
    quiz_data["answers"] = []
    quiz_data["last_selected"] = None

    if mode == "interactive":
        return render_question(0)
    else:
        # Convert questions to CSV text format
        csv_lines = ["Question,Options,Right_Option"]
        for q in quiz_data["questions"]:
            question = q["Question"].replace(",", ";")
            options = " | ".join(q["Options"]).replace(",", ";")
            right = q["Right_Option"]
            csv_lines.append(f"{question},{options},{right}")
        csv_content = "\n".join(csv_lines)
        return (
            gr.update(visible=False),  # input_form
            gr.update(visible=False),  # flashcard
            gr.update(visible=True),   # csv_output_form
            gr.update(value=""), gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(), gr.update(value=csv_content)
        )

def render_question(index):
    q = quiz_data["questions"][index]
    question = f"**Question {index+1} of {len(quiz_data['questions'])}:**\n" + q["Question"]
    options = q["Options"]
    qtype = q["Question_type"].upper()

    quiz_data["last_selected"] = None

    if qtype == "SCQ":
        return (
            gr.update(visible=False),  # input_form
            gr.update(visible=True),   # flashcard
            gr.update(visible=False),  # csv_output_form
            gr.update(value=question),  # question_text
            gr.update(choices=options, value=None, visible=True, interactive=True),  # radio
            gr.update(choices=[], value=None, visible=False),  # checkbox
            gr.update(visible=True),  # submit button shared
            gr.update(value=""),  # feedback
            gr.update(visible=False),  # flip
            gr.update(visible=True),  # next
            gr.update(value="")  # csv output
        )
    else:  # MCQ
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value=question),
            gr.update(choices=[], value=None, visible=False),
            gr.update(choices=options, value=None, visible=True, interactive=True),
            gr.update(visible=True),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="")
        )

def submit_answer(scq_selected, mcq_selected):
    current_q = quiz_data["questions"][quiz_data["index"]]
    correct_letters = set(current_q["Right_Option"].lower())

    if current_q["Question_type"].upper() == "SCQ":
        if scq_selected is None:
            return (
                gr.update(interactive=True),
                gr.update(value="⚠️ Please select an option. Or, flip to reveal the answer."),
                gr.update(visible=False),
                gr.update(visible=True)
            )
        quiz_data["last_selected"] = scq_selected
        selected = scq_selected[0].lower()
        feedback = (
            f"✅ Correct! The answer is: {scq_selected}"
            if selected in correct_letters else
            f"❌ Incorrect. You chose: {scq_selected}"
        )
        return (
            gr.update(interactive=False),
            gr.update(value=feedback),
            gr.update(visible=True),
            gr.update(visible=True)
        )
    else:
        if not mcq_selected:
            return (
                gr.update(interactive=True),
                gr.update(value="⚠️ Please select at least one option."),
                gr.update(visible=False),
                gr.update(visible=False)
            )
        quiz_data["last_selected"] = mcq_selected
        selected_letters = set(opt[0].lower() for opt in mcq_selected)
        feedback = (
            f"✅ Correct! The answer(s): {', '.join(mcq_selected)}"
            if selected_letters == correct_letters else
            f"❌ Incorrect. You chose: {', '.join(mcq_selected)}"
        )
        return (
            gr.update(interactive=False),
            gr.update(value=feedback),
            gr.update(visible=True),
            gr.update(visible=True)
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
            gr.update(visible=False),  # csv
            gr.update(value="🎉 Quiz complete! You can go back and try a new story."),
            gr.update(choices=[], value=None, visible=False),
            gr.update(choices=[], value=None, visible=False),
            gr.update(visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value="")
        )
    return render_question(quiz_data["index"])

def go_back():
    quiz_data.update({"questions": [], "index": 0, "answers": [], "last_selected": None})
    return (
        gr.update(visible=True),   # input form
        gr.update(visible=False),  # flashcard
        gr.update(visible=False),  # csv_output_form
        gr.update(value=""),
        gr.update(choices=[], value=None, visible=False),
        gr.update(choices=[], value=None, visible=False),
        gr.update(visible=False),
        gr.update(value=""),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(value="")
    )

with gr.Blocks() as demo:
    with gr.Column(visible=True) as input_form:
        quiz_mode = gr.Radio(["interactive", "csv"], value="interactive", label="Mode")
        topic_input = gr.Textbox(label="Enter quiz topic", placeholder="e.g. The King’s Monkey Servant")
        story_input = gr.Textbox(label="Enter a story", lines=10)
        submit_btn = gr.Button("Generate Quiz")

    with gr.Column(visible=False) as flashcard:
        question_text = gr.Markdown()
        scq_options = gr.Radio(choices=[], label="Select one option", interactive=True, visible=False)
        mcq_options = gr.CheckboxGroup(choices=[], label="Select multiple options", visible=False)
        submit_btn_shared = gr.Button("Submit Answer", visible=False)
        feedback_text = gr.Markdown()
        flip_btn = gr.Button("Flip to show answer", visible=False)
        next_btn = gr.Button("Next Question", visible=True)
        back_btn = gr.Button("Go back to story input", visible=True)

    with gr.Column(visible=False) as csv_output_form:
        csv_text_output = gr.Textbox(lines=15, label="Quiz CSV", interactive=False)
        csv_copy_btn = gr.Button("Copy to Clipboard")
        csv_download_btn = gr.Button("Download CSV")
        csv_back_btn = gr.Button("Go back to story input")

    submit_btn.click(
        generate_quiz,
        inputs=[topic_input, story_input, quiz_mode],
        outputs=[
            input_form, flashcard, csv_output_form,
            question_text, scq_options, mcq_options, submit_btn_shared,
            feedback_text, flip_btn, next_btn, csv_text_output
        ]
    )

    submit_btn_shared.click(
        submit_answer,
        inputs=[scq_options, mcq_options],
        outputs=[scq_options, feedback_text, flip_btn, next_btn]
    )

    flip_btn.click(flip_to_show_answer, outputs=feedback_text)

    next_btn.click(
        next_question,
        outputs=[
            input_form, flashcard, csv_output_form,
            question_text, scq_options, mcq_options, submit_btn_shared,
            feedback_text, flip_btn, next_btn, csv_text_output
        ]
    )

    back_btn.click(
        go_back,
        outputs=[
            input_form, flashcard, csv_output_form,
            question_text, scq_options, mcq_options, submit_btn_shared,
            feedback_text, flip_btn, next_btn, csv_text_output
        ]
    )

    csv_back_btn.click(
        go_back,
        outputs=[
            input_form, flashcard, csv_output_form,
            question_text, scq_options, mcq_options, submit_btn_shared,
            feedback_text, flip_btn, next_btn, csv_text_output
        ]
    )

if __name__ == "__main__":
    demo.launch(share=True)
