# indic-learn/quiz module

The `quiz` module iside `indic-learn` is a fully automated pipeline for generating high-quality single and multiple-choice quizzes (SCQ and MCQ) from Indian story texts, designed for the **Gurukula** learning platform. It uses modern LLMs (running via [Groq](https://groq.com)) to create engaging quiz content, optimized for classroom use by the **Indic** non-profit.

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

## 🚀 Usage

There are **three main ways** to run the script:

### 1. Run One Chapter from File Mode

```bash
python backend/gurukula_quizgen.py --input_source file --chapter chapter23
```

Reads from `data/chapter23.txt` and writes the output to the quiz spreadsheet.

### 2. Run All Chapters from Files in Batch Mode

```bash
python backend/gurukula_quizgen.py --input_source file
```

Reads all `.txt` files from the `data/` folder.

### 3. Run Chapters from Spreadsheet Tabs

```bash
python backend/gurukula_quizgen.py --input_source spreadsheet
```

Reads from a Google Sheet with tabs for each chapter. Each tab must have:

```
A1: NumQuestions     B1: <number>
A2: Content          B2: <full chapter text>
```

---

## 📚 Sheet Configuration

### Input Spreadsheet: `gurukula-story-master`

* Each tab = one chapter
* Format:

  | A            | B                      |
  | ------------ | ---------------------- |
  | NumQuestions | 15                     |
  | Content      | <long chapter content> |

### Output Spreadsheet: `gurukula-quiz-master`

* Each tab = one quiz for the chapter
* Auto-formatted with colors and points

---

## 🛠 Tech Stack

* 🧠 LLaMA3 via **Groq API** (served with Markdown using **Agno agent**)
* 📊 Google Sheets API (via `gspread`, `googleapiclient`)
* 🐍 Python 3.11
* ✅ Configurable with `YAML`-based settings

---

## 🧪 Screenshots (TODO)

### ✅ Story Spreadsheet Tab (gurukula-story-master)

*Screenshot Placeholder*

### ✅ Generated Quiz Tab (gurukula-quiz-master)

*Screenshot Placeholder*

### ✅ Final Quiz in Gurukula App

*Screenshot Placeholder*

---

## 🤝 About

This project supports **Indic education** by making quiz creation for Indian stories effortless, scalable, and teacher-friendly.

Questions? Want to contribute? Reach out to `@mambabhi` on GitHub.

---

## 📂 Project Structure (simplified)

```
indic-learn/
├── backend/
│   ├── gurukula_quizgen.py      # Main script
│   ├── indic_quiz_generator_pipeline.py  # Quiz generation logic
│   └── utils/                   # Sheets formatting, logging
├── data/                        # Text chapters for file mode
├── config/                      # App config & env variables
└── README.md                    # You're here
```

---

## ✅ Coming Soon

* UI to configure and run quizzes without CLI
* Analytics on question types per chapter
* Export to CSV/HTML formats
