# backend/indic_quiz_generator_pipeline.py

import difflib
import re
from concurrent.futures import ThreadPoolExecutor
import json
import json_repair
from agno.agent import Agent
from agno.models.groq import Groq
from quiz.backend.utils.logging_utils import log_and_print


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

        # 🔽 Handle case where JSON loader returns a string (e.g., double-encoded JSON)
        if isinstance(quiz, str):
            try:
                quiz = json.loads(quiz)
            except json.JSONDecodeError:
                try:
                    quiz = json_repair.loads(quiz)
                except Exception:
                    log_and_print("⚠️ Could not parse quiz output, returning empty quiz.")
                    return {"Questions": []}

        # 🔽 Handle top-level "Quiz" key
        if isinstance(quiz, dict) and "Quiz" in quiz:
            quiz = quiz["Quiz"]

        # 🔽 If quiz is still not a dict, abort early
        if not isinstance(quiz, dict):
            log_and_print("⚠️ Parsed quiz is not a dict. Returning empty.")
            return {"Questions": []}

        questions = quiz.get("Questions") or quiz.get("questions", [])
        if not isinstance(questions, list):
            log_and_print("⚠️ 'Questions' is not a list. Returning empty.")
            return {"Questions": []}

        for q in questions:
            raw_options = q.get("Options") or q.get("options")

            # Handle if options is a dictionary (malformed)
            if isinstance(raw_options, dict):
                raw_options = list(raw_options.values())
            elif not isinstance(raw_options, list):
                # Try reconstructing from str fields
                raw_options = []
                for key, value in q.items():
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned",  "timer"):
                        if isinstance(value, str):
                            raw_options.append(key.strip())
                            raw_options.append(value.strip())
                for key in list(q.keys()):
                    if key.lower() not in ("question", "right_option", "options", "question_type", "number_of_points_earned",  "timer"):
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

        # Final safeguard: return normalized quiz
        return {"Questions": questions}


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
                "Timer": 25
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
        - The quiz must contain exactly {count} {type_label}. Do not generate more.
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
        - "Timer": an integer with any one of these values -- 10,15,20,25,30 -- depending on difficulty

        == RULES ==
        - Output must be a valid JSON **dictionary** with this exact structure:
            {{
                "Quiz": {{
                    "Topic": "...",
                    "Questions": [ ... ]
                }}
            }}
            Do **not** output a plain array — it must be wrapped inside the top-level "Quiz" dictionary.

        - ❌ Do NOT include options like:
            - "All of the above"
            - "None of the above"
            - "Both A and B"
            - "Only B and C", etc.

        ✅ Each answer option must be **self-contained**, **mutually exclusive**, and make logical sense independently.
        - Do NOT include contradictory or mutually exclusive correct options.
            ❌ For example, a person cannot be "confused" and "convinced" at the same time.
            ❌ Do not mark both "They agreed" and "They refused" as correct.
            ✅ All correct options must be logically compatible and able to co-exist.
        - If only one clearly correct fact is present, avoid inventing another.
        - If the passage does not provide enough information to answer a question, do not invent details.
        - Do not include explanations, markdown, or formatting. Output only plain JSON.
        - Vary the "Timer" field across questions and avoid repeating the same timer for every question.
        - Every question must be **clearly answerable from the passage**. Do not assume any outside knowledge.
        - {variation_clause}
        {mcq_option_clause}

        {get_example_block(question_type)}

        Here is the story:
        \"\"\"
        {chapter_text}
        \"\"\"
        """

def is_valid_mcq_option(opt: str) -> bool:
    return bool(re.fullmatch(r"[a-d]{2,4}", opt))


def validate_mcqs(mcq_questions: list, min_valid: int) -> bool:
    valid_count = sum(1 for q in mcq_questions if len(q["Right_Option"].replace(" ", "")) > 1)
    log_and_print(f"✅ Valid MCQs: {valid_count}/{len(mcq_questions)}")
    return valid_count >= min_valid


def run_scq_only(chapter_text: str, num_scq: int):
    scq_agent = build_english_quiz_agent("openai/gpt-oss-120b")
    parser = QuizParser()
    scq_prompt = build_prompt(chapter_text, num_scq, "SCQ")
    log_and_print(f"🔍 Running SCQ generation with prompt:\n{scq_prompt}\n")
    r_scq = scq_agent.run(scq_prompt)
    log_and_print(f"🔍 SCQ Response:\n{r_scq.content}")  # print first 1000 characters for debugging
    if r_scq.content is None:
        raise ValueError("SCQ agent returned no content.")
    return parser.run(r_scq.content)


def run_mcq_with_retries(chapter_text: str, num_mcq: int, max_retries: int = 1):
    mcq_agent = build_english_quiz_agent("openai/gpt-oss-120b")
    mcq_prompt = build_prompt(chapter_text, num_mcq, "MCQ")  # Over-generate
    log_and_print(f"🔍 Running MCQ generation with prompt:\n{mcq_prompt}\n")

    min_valid = max(1, num_mcq // 2)  # At least half (rounded down), but at least 1
    log_and_print(f"🔍 Minimum valid MCQs required: {min_valid}")

    for attempt in range(max_retries):
        print(f"Running MCQ generation (Attempt {attempt + 1}/{max_retries})...")
        r_mcq = mcq_agent.run(mcq_prompt)
        parser = QuizParser()
        if r_mcq.content is None:
            raise ValueError("MCQ agent returned no content.")
        
        mcq_data = parser.run(r_mcq.content)
        log_and_print(f"MCQ Data for attempt {attempt}: {mcq_data}")

        if not mcq_data or not isinstance(mcq_data, dict):
            log_and_print("🔎 Raw model output:")
            log_and_print(r_mcq.content[:1000])  # print first 1000 characters
            raise ValueError("MCQ parsing failed — got invalid format.")

        if not mcq_data or not (isinstance(mcq_data, dict) and "Questions" in mcq_data):
            log_and_print("❌ No questions found in MCQ response. Retrying...\n")
            continue

        mcq_questions = mcq_data.get("Questions", [])
        if validate_mcqs(mcq_questions, min_valid):
            log_and_print("✅ Enough valid MCQs found.")
            log_and_print(f"🔍 Total MCQs generated: {len(mcq_questions)}, for min_valid: {min_valid}")
            return mcq_data
        else:
            log_and_print("❌ Not enough valid MCQs. Retrying...\n")

    log_and_print("⚠️ Max retries reached. Returning last MCQ version.")
    return mcq_data


def get_valid_mcqs(mcq_questions, num_mcq):
    log_and_print(f"🔍 Filtering MCQs for MCQ Questions: {mcq_questions}.")
    log_and_print(f"🔍 Total MCQs found: {len(mcq_questions)}. Required: {num_mcq}.")

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
    
    log_and_print(f"🔍 Filtered MCQs: {filtered_mcq}")
    log_and_print(f"🔍 Deduplicated MCQs: {len(filtered_mcq)} out of {len(mcq_list)}")
    
    return filtered_mcq


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

    valid_mcq_questions = get_valid_mcqs(mcq_data.get("Questions", []), num_questions)
    log_and_print(f"🔍 Valid MCQs found: {len(valid_mcq_questions)} out of {len(mcq_data.get('Questions', []))}")

    deduplicated_questions = deduplicate_questions(scq_questions, valid_mcq_questions)
    log_and_print(f"🔍 Deduplicated Questions: {len(deduplicated_questions)} out of {len(valid_mcq_questions)}")

    mcq_questions = deduplicated_questions[:num_mcq_to_pick]
    log_and_print(f"🔍 Final MCQs selected: {len(mcq_questions)} out of {len(deduplicated_questions)}, with num to pick: {num_mcq_to_pick}")
    if len(mcq_questions) == num_mcq_to_pick:
        log_and_print("✅ Enough valid MCQs found.")

    total_collected = len(scq_questions) + len(mcq_questions)
    log_and_print(f"🔍 Total questions collected: {total_collected} (SCQ: {len(scq_questions)}, MCQ: {len(mcq_questions)})")
    remaining = num_questions - total_collected
    log_and_print(f"🔍 Remaining questions to fill: {remaining}")

    # Fill any remaining slots with extra SCQs if MCQs were insufficient
    if remaining > 0:
        log_and_print(f"⚠️ Not enough valid MCQs. Filling remaining {remaining} with more SCQs...")

        selected_q_texts = {normalize_text(q['Question']) for q in scq_questions + mcq_questions}
        extra_scqs = []
        for q in scq_data.get("Questions", []):
            norm_q = normalize_text(q['Question'])
            if norm_q not in selected_q_texts:
                extra_scqs.append(q)
                selected_q_texts.add(norm_q)
            if len(extra_scqs) >= remaining:
                break

        scq_questions += extra_scqs
        log_and_print(f"🔍 Extra SCQs added: {len(extra_scqs)}, Total SCQ Questions: {len(scq_questions)}")

    # Final full quiz
    all_questions = scq_questions + mcq_questions
    all_questions = all_questions[:num_questions]
    log_and_print(f"🔍 Final questions count: {len(all_questions)} (SCQ: {len(scq_questions)}, MCQ: {len(mcq_questions)})")

    # ✅ Add up to 5 non-duplicate SCQs as backup
    used_question_texts = {normalize_text(q['Question']) for q in all_questions}
    backup_scqs = []
    for q in scq_data.get("Questions", []):
        norm_q = normalize_text(q['Question'])
        if norm_q not in used_question_texts:
            backup_scqs.append(q)
            used_question_texts.add(norm_q)
        if len(backup_scqs) >= 5:
            break

    if backup_scqs:
        log_and_print(f"🔍 Appending {len(backup_scqs)} backup SCQs to end of quiz.")

    all_questions += backup_scqs

    return {
        "Quiz": {
            "Topic": scq_data.get("Topic") or mcq_data.get("Topic", "Unknown Topic"),
            "Questions": all_questions
        }
    }

