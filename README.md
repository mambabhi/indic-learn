---
title: Indic-Learn App  # Give your Space a nice title
emoji: 📚 # You can pick any emoji that fits
colorFrom: purple # Adjust colors as you like
colorTo: indigo # Adjust colors as you like
sdk: gradio # IMPORTANT: Change this if you're using Streamlit, Docker, or another SDK
app_file: app.py # IMPORTANT: Change this to the name of your main application file (e.g., main.py, gradio_app.py)
pinned: false
---

<p align="left">
  <img width="52" height="51" alt="Image" src="https://github.com/user-attachments/assets/e4bde3a6-765d-48a9-a025-7425c959de43" alt="Gurukula Logo" />
</p>

**`indic-learn`** is a modular AI-powered toolkit designed to support culturally grounded educational content for the Gurukula learning platform. Its first major module, `quiz`, is a fully automated pipeline for generating high-quality single and multiple-choice quizzes (SCQ and MCQ) from Indian story texts. Built for scale and precision, it leverages concurrent LLM agents (via Groq and Agno) to produce rich, classroom-ready assessments with minimal manual intervention.

Future modules coming soon include:

* **`storyboard`** — frame-by-frame visual generation from story chapters for use in illustrated books and slide decks.
* **`animation`** — culturally customized animated storytelling with rich textures and Indic design sensibilities.

---

📘 **Features of the `quiz` module**

* Parallel SCQ and MCQ generation using dedicated Groq-hosted LLaMA3 agents via Agno.
* Intelligent fallback strategy: if MCQ generation produces too few valid questions, SCQs are added to maintain the desired count.
* Optional extra questions included for manual curation by Gurukula admins.
* Automatic filtering of invalid or low-quality questions using format checks and semantic similarity deduplication.
* Points and timers vary based on question difficulty and type.
* All content written to a Google Sheet with per-chapter tabs for easy review and classroom use.
* Correct answers are highlighted automatically via the Google Sheets API.

---

🛠 **Setup**

You’ll need a `.env` and `config.yaml` file with the following (simplified for this README):

```yaml
# config.yaml
spreadsheet:
  name: gurukula-quiz-master
input_spreadsheet:
  name: gurukula-story-master
chapter_question_counts:
  chapter23: 20
  chapter24: 15
```

```env
SERVICE_ACCOUNT_FILE=path/to/google-service-key.json
GOOGLE_SCOPES=https://www.googleapis.com/auth/spreadsheets
```

---

🚀 **How to Generate Quizzes**

**Using the Hugging Face Spaces Web UI**

- Launch the URL: https://huggingface.co/spaces/mambabhi/indic-learn (for local testing use the `app.py` file).
- Upload or specify your input spreadsheet (with chapters).
- Specify the output spreadsheet where generated quizzes will be written automatically.
- Monitor progress and logs directly in the UI.

**Using the main script on command line**

For all invocations use: `backend/gurukula_quizgen.py`

1. **Run a single chapter from file:**

```bash
python -m quiz.backend.gurukula_quizgen.py --input_source file --chapter chapter23
```

2. **Run all chapters in batch from file:**

```bash
python -m quiz.backend.gurukula_quizgen.py --input_source file
```

3. **Run a single chapter from Google Sheets:**

```bash
python -m quiz.backend.gurukula_quizgen.py --input_source spreadsheet --chapter chapter23
```

4. **Run from Google Sheets (single or multiple tabs):**

```bash
python -m quiz.backend.gurukula_quizgen.py --input_source spreadsheet
```

---

🧾 **Input Sheet Format (`gurukula-story-master`)**

Each chapter should be a separate tab. The layout within a tab should look like:

| A            | B                                                               |
| ------------ | --------------------------------------------------------------- |
| NumQuestions | 15                                                              |
| Content      | Once upon a time in a village... (full story content goes here) |

📌 *Chapters without valid content or missing tabs are skipped automatically.*

---

📤 **Output Sheet Format (`gurukula-quiz-master`)**

* Each chapter gets a tab with the generated questions.
* SCQs and MCQs are mixed and randomized.
* Correct options are highlighted in green.

---

## 🧪 Screenshots

### ✅ Story Spreadsheet Tab (gurukula-story-master)

<img width="526" height="352" alt="Image" src="https://github.com/user-attachments/assets/85daa294-ce14-4c38-8445-5c0f412ad668" alt="Story Master Screenshot"/>
<br/>
<i>Figure 1: Input spreadsheet with story content and number of questions.</i>

### ✅ Generated Quiz Tab (gurukula-quiz-master)

<img width="1347" height="554" alt="Image" src="https://github.com/user-attachments/assets/b689a935-13d5-4eb3-b2c1-d8641973f91d" alt="Quiz Master Output"/>
<br/>
<i>Figure 2: Generated quiz questions with highlights in output sheet.</i>

### ✅ Hugging Face Spaces UI for Quiz Generation

<img width="489" height="802" alt="Image" src="https://github.com/user-attachments/assets/f60cfdf8-bc5c-4811-a933-1f30059f45b3" />
<br/>
<i>Figure 3: Hugging Face Spaces UI—upload your input spreadsheet and specify the output spreadsheet. The UI triggers quiz generation and updates the output sheet automatically.</i>

### ✅ Final Quiz in Gurukula App

![Image](https://github.com/user-attachments/assets/373d4ec6-e549-472b-978a-4450e6cd9a50)

<br/>
<i>Figure 3: Gurukula app displaying quiz in interactive mode.</i>

---

## 📋 Features

### ⚡ Parallel Quiz Generation

* Uses **two LLaMA 3** models in **concurrent threads**:

  * One model generates SCQs (Single Correct Questions)
  * Another generates MCQs (Multiple Correct Questions)
* Reduces generation time and avoids rate limits

### ✅ Intelligent Question Filtering

* Validates MCQs to ensure they contain **multiple correct options**
* De-duplicates questions using **text similarity** checks
* Adds **extra SCQs** for optionality if MCQ count is low

### 🧠 Quiz Metadata & UX

* Supports difficulty-based **Points** and **Timer** settings
* Highlights correct options in green using Google Sheets formatting
* Allows flexible quiz size per chapter (configurable)

### 📤 Google Sheets Integration

* Reads chapters directly from Google Sheets tabs
* Writes quizzes to a separate output Google Sheet
* Enables easy use by **Gurukula admins** via spreadsheets

---

## 🛠 Tech Stack

* 🧠 LLaMA3 via **Groq API** (served with Markdown using **Agno agent**)
* 📊 Google Sheets API (via `gspread`, `googleapiclient`)
* 🐍 Python 3.11
* ✅ Configurable with `YAML`-based settings

---

## 🧩 Key Functionality

### 1. Quiz Generation Pipeline
- **Parallel Generation:** Two LLaMA 3 models (via Groq API and Agno agent) run in parallel threads—one for SCQs (single correct answer), one for MCQs (multiple correct answers).
- **Prompt Engineering:** Carefully crafted prompts instruct LLMs to generate questions in strict JSON format, with clear rules for options, correct answers, and structure.
- **Validation & Filtering:** MCQs are validated to ensure multiple correct options. Questions are deduplicated using text similarity checks.
- **Fallback Logic:** If not enough valid MCQs are generated, extra SCQs are added to maintain the desired quiz size.

### 2. Google Sheets Integration
- **Input:** Reads story chapters from a Google Sheet (each chapter is a tab with `NumQuestions` and `Content` fields).
- **Output:** Writes generated quizzes to a separate output Google Sheet, with each chapter as a tab. Correct answers are highlighted using conditional formatting.
- **Configurable:** Sheet names, question counts, and other settings are loaded from YAML and `.env` files.

### 3. Quiz Structure
- **SCQ:** Single correct answer, labeled as a single letter (e.g., `"a"`).
- **MCQ:** Multiple correct answers, labeled as a string of letters (e.g., `"ac"`), with validation to ensure at least two correct options.
- **Question Format:** Each question includes the text, options (labeled "a."–"d."), correct answer(s), points, and timer.

### 4. User Interfaces
- **CLI:** Main script can be run for a single chapter or batch mode, from file or spreadsheet.
- **Gradio UI:** Web interface for admins to trigger quiz generation, select chapters, and view logs.

### 5. Extensibility
- **Pluggable Pipeline:** Modular quiz generation logic allows for future expansion (e.g., storyboard, animation modules).
- **Logging:** All steps are logged for debugging and traceability.

---

## 📝 Key Definitions

- **SCQ (Single Choice Question):** Only one correct answer.
- **MCQ (Multiple Choice Question):** Two or more correct answers, must be a string of unique letters (e.g., `"bd"`).
- **QuizParser:** Parses and normalizes the LLM output into the expected JSON structure.
- **Conditional Formatting:** Correct options are highlighted in green in the output Google Sheet.

---

## 📁 Project Structure

```
indic-learn/
├── backend/
│   ├── gurukula_quizgen.py      # Main script
│   ├── indic_quiz_generator_pipeline.py  # Quiz generation logic, prompt building, validation, parsing
│   └── utils/                   # Google Sheets utilities, logging, etc.
├── data/                        # Text chapters for file-based mode
├── config/                      # App config & env variables
└── README.md                    # You're here
```

---

## 🤝 About

This project supports **Indic education** by making quiz creation for Indian stories effortless, scalable, and teacher-friendly.

Questions? Want to contribute? Reach out to `@mambabhi` on GitHub.

```

---

## ✅ Coming Soon
### Quiz module 

* UI to configure and run quizzes without CLI
* Analytics on question types per chapter
* Export to CSV/HTML formats

### Storyboard module 
* Stay tuned...
### Animation module 
* Stay tuned...

✨ Built with ❤️ for Indic education.

---

© 2025 [Gurukula](https://gurukula.com). All rights reserved.  
This project is maintained in partnership with the Gurukula learning platform.
