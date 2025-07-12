# backend/indic_quiz_generator_pipeline.py

import difflib
import re
from concurrent.futures import ThreadPoolExecutor
import json
import json_repair
from agno.agent import Agent
from agno.models.groq import Groq

class QuizParser:
    """Parses the quiz JSON out of the LLM's response."""

    def run(self, reply_text: str):
        import re

        # Extract JSON-ish content
        first_index = min(reply_text.find("{"), reply_text.find("["))
        last_index = max(reply_text.rfind("}"), reply_text.rfind("]")) + 1
        json_portion = reply_text[first_index:last_index]

        try:
            quiz = json.loads(json_portion)
        except json.JSONDecodeError:
            quiz = json_repair.loads(json_portion)

        # 🔽 NEW: Handle if `quiz` is a string after decoding (bad LLM output)
        if isinstance(quiz, str):
            try:
                quiz = json.loads(quiz)
            except json.JSONDecodeError:
                quiz = json_repair.loads(quiz)

        # 🔽 Support the new JSON format
        if "Quiz" in quiz:
            quiz = quiz["Quiz"]

        questions = quiz.get("Questions") or quiz.get("questions", [])


        for q in questions:
            raw_options = q.get("Options") or q.get("options")

            # Handle if options is a dictionary (malformed JSON case)
            if isinstance(raw_options, dict):
                raw_options = list(raw_options.values())
            elif not isinstance(raw_options, list):
                # Attempt to reconstruct options from key-value pairs
                raw_options = []
                for key, value in q.items():
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned", "chapter", "timer", ):
                        if isinstance(value, str):
                            raw_options.append(key.strip())
                            raw_options.append(value.strip())
                # Remove those fields to clean up
                for key in list(q.keys()):
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned", "chapter", "timer", ):
                        q.pop(key)

            if not isinstance(raw_options, list):
                raw_options = []

            # Normalize options
            normalized = []
            seen = set()
            for opt in raw_options:
                if not isinstance(opt, str):
                    continue
                match = re.match(r"^[a-dA-D]\.\s+(.*)", opt.strip())
                text = match.group(1).strip() if match else opt.strip()
                if text not in seen:
                    seen.add(text)
                    normalized.append(text)

            while len(normalized) < 4:
                normalized.append("(missing option)")

            normalized = normalized[:4]
            labeled = [f"{label}. {text}" for label, text in zip("abcd", normalized)]
            q["Options"] = labeled

        quiz["Questions"] = questions

        return quiz


def build_english_quiz_agent(model_id: str) -> Agent:
    agent = Agent(
        model=Groq(id=model_id),
        markdown=True
    )
    return agent


def get_example_block(question_type: str) -> str:
    if question_type.upper() == "SCQ":
        return '''\
== EXAMPLES ==
{
    "Quiz": {
        "Topic": "The story of Kṛiṣhṇa's childhood and his encounters with various Asuras",
        "Questions": [
            {
                "Question": "What was Pūtanā's task assigned by Kaṃsa?",
                "Question_type": "SCQ",
                "Options": ["a. To protect the newborn Kṛiṣhṇa", "b. To kill the newborn Kṛiṣhṇa", "c. To find the newborn Kṛiṣhṇa and bring him to Kaṃsa", "d. To alert the people of Gokula about Kaṃsa's plans"],
                "Right_Option": "c",
                "Number_Of_Points_Earned": 10,
                "Chapter": "Chapter 16",
                "Timer": 15
            }
        ]
    }
}'''
    elif question_type.upper() == "MCQ":
        return '''\
== EXAMPLES ==
{
    "Quiz": {
        "Topic": "The story of Kṛiṣhṇa's childhood and his encounters with various Asuras",
        "Questions": [
            {
                "Question": "What was the effect of Kṛiṣhṇa's kick on the cart in which Śhakaṭāsura was hiding? (Select all answers that are correct)",
                "Question_type": "MCQ",
                "Options": ["a. The cart was dislodged and flew away", "b. The cart was destroyed", "c. The metal jars containing milk and curd were crushed", "d. The cart's pole was shattered"],
                "Right_Option": "abcd",
                "Number_Of_Points_Earned": 15,
                "Chapter": "Chapter 16",
                "Timer": 20
            },
            {
                "Question": "Why was Kṛiṣhṇa tied to the mortar?",
                "Question_type": "MCQ",
                "Options": [
                    "a. He broke a butter pot",
                    "b. He stole curd again",
                    "c. He refused to eat lunch",
                    "d. He ran away from home"
                ],
                "Right_Option": "ab",
                "Number_Of_Points_Earned": 15,
                "Chapter": "Chapter 17",
                "Timer": 18
            }
        ]
    }
}'''
    else:
        raise ValueError(f"Unsupported question_type: {question_type}")


def build_prompt(chapter_text: str, count: int, question_type: str) -> str:
    type_label = "Single Choice Questions (SCQ)" if question_type == "SCQ" else "Multiple Choice Questions (MCQ)"
    variation_clause = """Vary correct option combinations. Use examples like "bc", "cd", "bd", "ac". Do not always include "a".""" \
        if question_type == "MCQ" else """Avoid repeating the same option (like "a") in all correct answers — aim for balanced and varied use of "a", "b", "c", and "d" throughout."""
    points_clause = "15" if question_type == "MCQ" else "10"
    right_option_clause = """
        - Must contain **two or more** correct answers (e.g., "ac", "bcd", "cd")
        - Must be a string of **2–4 unique lowercase letters**, **without commas, spaces, or quotes**.
        - **NEVER** use only a single letter like "a" or "b"
        """ \
        if question_type == "MCQ" else """a single lowercase letter (e.g., "a")"""
    mcq_option_clause = """\n
        - For Right_Option: 
        -- **NEVER** use only a single letter like "a" or "b" or "c" or "d".
        -- If only one fact is clearly true, combine it with another plausible, justifiable option to ensure >1 correct answer.
        -- Must match regex pattern: `^[a-d]{2,4}$`

        == COMMON MISTAKES (Do not do this) ==
        ❌ Example (invalid):
        "Right_Option": "a"   ← ❌ Only one correct answer — NOT allowed.

        ✅ Corrected version (valid):
        "Right_Option": "bc"  ← ✅ Two correct answers.
        """ \
        if question_type == "MCQ" else ""

    return f"""
        You are an expert quiz generator. Based on the following passage, generate a quiz in valid JSON format.

        == QUIZ STRUCTURE ==
        - The quiz must contain exactly {count} {type_label}.
        - Every question must test a unique concept and be based solely on the passage.
        
        == QUESTION FORMAT ==
        For each question, include:
        - "Question": the question text, starting with a word like "What", "Who", "When", "Where", "Why", or "How". Use active voice, clear grammar, and a conversational tone suitable for middle to high school students.
        - "Question_type": {question_type}
        - "Options": exactly four plausible and unique answer choices labeled as:
        - a. ...
        - b. ...
        - c. ...
        - d. ...
        - "Right_Option":   
            - {right_option_clause}
        - "Number_Of_Points_Earned": "{points_clause}"
        - "Chapter": e.g. "Chapter 1"
        - "Timer": an integer from 10 to 30, depending on difficulty

        == RULES ==
        - Output must be a valid JSON **dictionary** with the following structure:
            {{
                "Quiz": {{
                    "Topic": "...",
                    "Questions": [ ... ]
                }}
            }}
            Do not output a plain array. It must be wrapped inside the dictionary above.
        - No "all of the above" or similar options.
        - Do not include explanations, markdown, or formatting.
        - Don't default Timer for 15 or 20, all the time. Introduce some variety.        
        - Every question must be logically answerable using the passage.
        - {variation_clause}
        {mcq_option_clause}

        {get_example_block(question_type)}
        
        Here is the story:
        \"\"\"
        {chapter_text}
        \"\"\"
    """


def run_parallel_quiz(chapter_text: str, num_scq: int, num_mcq: int):
    scq_agent = build_english_quiz_agent("llama3-70b-8192")
    mcq_agent = build_english_quiz_agent("llama-3.3-70b-versatile")

    parser = QuizParser()

    with ThreadPoolExecutor() as executor:
        f_scq = executor.submit(scq_agent.run, build_prompt(chapter_text, num_scq, "SCQ"))
        r_scq = f_scq.result()

        f_mcq = executor.submit(mcq_agent.run, build_prompt(chapter_text, num_mcq, "MCQ"))
        r_mcq = f_mcq.result()

    scq_data = parser.run(r_scq.content)
    mcq_data = parser.run(r_mcq.content)

    all_questions = scq_data.get("Questions", []) + mcq_data.get("Questions", [])

    return {
        "Quiz": {
            "Topic": scq_data.get("Topic") or mcq_data.get("Topic", "Unknown Topic"),
            "Questions": all_questions
        }
    }


def is_valid_mcq_option(opt: str) -> bool:
    return bool(re.fullmatch(r"[a-d]{2,4}", opt))


def validate_mcqs(mcq_questions: list, min_valid: int) -> bool:
    valid_count = sum(1 for q in mcq_questions if len(q["Right_Option"].replace(" ", "")) > 1)
    print(f"✅ Valid MCQs: {valid_count}/{len(mcq_questions)}")
    return valid_count >= min_valid


def run_scq_only(chapter_text: str, num_scq: int):
    scq_agent = build_english_quiz_agent("llama3-70b-8192")
    parser = QuizParser()
    scq_prompt = build_prompt(chapter_text, num_scq, "SCQ")
    r_scq = scq_agent.run(scq_prompt)
    return parser.run(r_scq.content)


def run_mcq_with_retries(chapter_text: str, num_mcq: int, max_retries: int = 3):
    mcq_agent = build_english_quiz_agent("llama-3.3-70b-versatile")
    mcq_prompt = build_prompt(chapter_text, num_mcq, "MCQ")  # Over-generate

    min_valid = max(1, num_mcq // 2)  # At least half (rounded down), but at least 1

    for attempt in range(max_retries):
        print(f"Running MCQ generation (Attempt {attempt + 1}/{max_retries})...")
        r_mcq = mcq_agent.run(mcq_prompt)
        parser = QuizParser()
        mcq_data = parser.run(r_mcq.content)
        mcq_questions = mcq_data.get("Questions", [])

        if validate_mcqs(mcq_questions, min_valid):
            print("✅ Enough valid MCQs found.")
            return mcq_data
        else:
            print("❌ Not enough valid MCQs. Retrying...\n")

    print("⚠️ Max retries reached. Returning last MCQ version.")
    return mcq_data


def get_valid_mcqs(mcq_questions, num_mcq):
    return [
        q for q in mcq_questions if len(q["Right_Option"].replace(" ", "")) > 1
    ][:num_mcq]


def is_similar(q1, q2, threshold=0.85):
    seq = difflib.SequenceMatcher(None, q1, q2)
    return seq.ratio() >= threshold


def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = ' '.join(text.split())
    return text


def deduplicate_questions(scq_list, mcq_list, threshold=0.85):
    filtered_mcq = []
    for mcq_q in mcq_list:
        mcq_text = normalize_text(mcq_q['Question'])
        if not any(is_similar(mcq_text, normalize_text(scq_q['Question']), threshold) for scq_q in scq_list):
            filtered_mcq.append(mcq_q)
    return filtered_mcq


# def run_parallel_quiz_with_mcq_retry(chapter_text: str, num_scq: int, num_mcq: int):
def run_parallel_quiz_with_mcq_retry(chapter_text: str, num_questions: int):
    with ThreadPoolExecutor() as executor:
        f_scq = executor.submit(run_scq_only, chapter_text, num_questions)
        f_mcq = executor.submit(run_mcq_with_retries, chapter_text, num_questions)

        scq_data = f_scq.result()
        mcq_data = f_mcq.result()

    # Logic to split SCQ and MCQ into half
    half = num_questions // 2
    num_scq_to_pick = half + (num_questions % 2)  # SCQ gets the extra if odd
    num_mcq_to_pick = half

    scq_questions = scq_data.get("Questions", [])[:num_scq_to_pick]

    valid_mcq_questions = get_valid_mcqs(mcq_data.get("Questions", []), num_mcq_to_pick*2)  # get more MCQs first to allow filtering
    valid_mcq_questions = deduplicate_questions(scq_questions, valid_mcq_questions)
    # Then slice to desired number
    mcq_questions = valid_mcq_questions[:num_mcq_to_pick]

    all_questions = scq_questions + mcq_questions

    return {
        "Quiz": {
            "Topic": scq_data.get("Topic") or mcq_data.get("Topic", "Unknown Topic"),
            "Questions": all_questions
        }
    }
