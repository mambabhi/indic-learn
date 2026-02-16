# Quiz Generation Pipeline - Developer Guide

This guide helps Claude (and developers) understand the quiz generation pipeline architecture, testing procedures, and recent implementations.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quiz Generation Modes](#quiz-generation-modes)
3. [Configuration Guide](#configuration-guide)
4. [Testing Procedures](#testing-procedures)
5. [Common Workflows](#common-workflows)
6. [Troubleshooting](#troubleshooting)

---

## 🏗 Architecture Overview

### Core Pipeline Components

```
Input Source → Quiz Generation → DataFrame Conversion → Google Sheets Upload → Formatting
```

**Key Files:**
- `gurukula_quizgen.py` - Main entry point, workflow orchestration, Google Sheets integration
- `indic_quiz_generator_pipeline.py` - LLM-based quiz generation logic
- `utils/gsheets.py` - Google Sheets/Docs API utilities
- `config/app_config.yaml` - Configuration for all modes

### Quiz Generation Process

1. **Read Content**: From file, spreadsheet, or Google Doc
2. **Generate Quiz**: Parallel SCQ/MCQ generation using ChatGPT OSS via Groq
3. **Convert to DataFrame**: Structure questions with metadata (points, timer, etc.)
4. **Upload to Sheet**: Write to Google Spreadsheet with chapter as tab name
5. **Apply Formatting**: Highlight correct answers in green

---

## 🎯 Quiz Generation Modes

### 1. Default Mode (NEW - **Recommended**)

**Purpose**: Simplified, config-driven workflow using spreadsheet IDs for O(1) lookup

**Key Features**:
- No command-line arguments needed
- Uses spreadsheet **IDs** instead of names (scalable to millions of files)
- Reads input/output links from `app_config.yaml`
- Supports single-run and batch modes

**Usage**:

```bash
# Single run (uses source_documents.input_link and source_documents.output_link)
python -m quiz.backend.gurukula_quizgen

# With custom question count
python -m quiz.backend.gurukula_quizgen --num_questions 20

# Batch mode (processes source_documents.batch array)
python -m quiz.backend.gurukula_quizgen --batch
```

**Configuration** (`app_config.yaml`):

```yaml
source_documents:
  # Single run configuration
  input_link: https://docs.google.com/document/d/DOC_ID/edit
  output_link: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
  num_questions: 15

  # Batch run configuration
  batch:
    - input_link: https://docs.google.com/document/d/DOC_ID_1/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_1/edit
      num_questions: 15
    - input_link: https://docs.google.com/document/d/DOC_ID_2/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_2/edit
      num_questions: 20
```

**Implementation Details**:
- Uses `extract_spreadsheet_id()` to parse URLs or raw IDs
- Uses `validate_spreadsheet_by_id()` for O(1) validation
- Uses `run_gdoc_to_spreadsheet_workflow()` for single processing
- Uses `run_batch_gdoc_to_spreadsheet_workflow()` for batch processing

### 2. File Mode (Legacy)

**Purpose**: Process chapters from local text files in `quiz/data/`

**Usage**:

```bash
# Single chapter
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23

# All chapters in /data
python -m quiz.backend.gurukula_quizgen --mode file
```

**Configuration**:
- Text files in `quiz/data/` directory
- Question counts in `app_config.yaml` under `chapter_question_counts`

### 3. Spreadsheet Mode (Legacy)

**Purpose**: Process chapters from Google Spreadsheet tabs

**Usage**:

```bash
# Single chapter
python -m quiz.backend.gurukula_quizgen --mode spreadsheet --chapter chapter23

# All chapters (all tabs)
python -m quiz.backend.gurukula_quizgen --mode spreadsheet
```

**Configuration**:
- Input spreadsheet name: `app_config.yaml` → `spreadsheets.input_name`
- Output spreadsheet name: `app_config.yaml` → `spreadsheets.output_name`
- Each tab should have: `NumQuestions` in A1, `Content` in A2

---

## ⚙️ Configuration Guide

### Environment Variables (`.env`)

```env
SERVICE_ACCOUNT_FILE=path/to/service-account.json
GOOGLE_SCOPES=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents
GOOGLE_SERVICE_ACCOUNT_KEY_BASE64=<base64_encoded_key>
```

### App Configuration (`app_config.yaml`)

```yaml
# Legacy modes (backward compatibility)
spreadsheets:
  input_name: gurukula-story-master
  output_name: gurukula-quiz-master

documents:
  link: https://docs.google.com/document/d/DOC_ID/edit

# NEW: Default mode configuration
source_documents:
  input_link: https://docs.google.com/document/d/DOC_ID/edit
  output_link: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
  num_questions: 15

  batch:
    - input_link: https://docs.google.com/document/d/DOC_ID_1/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_1/edit
      num_questions: 15

# Question counts for file mode
chapter_question_counts:
  chapter23: 15
  chapter24: 20
```

### Google Service Account Setup

1. Create a service account in Google Cloud Console
2. Enable Google Sheets API and Google Drive API
3. Download service account JSON key
4. Share spreadsheets/docs with service account email
5. Set environment variables

---

## 🧪 Testing Procedures

### Prerequisites

1. **Valid Google Credentials**: Ensure `.env` is configured with service account
2. **Shared Documents**: All spreadsheets/docs must be shared with service account email
3. **Valid Configuration**: `app_config.yaml` has correct document/spreadsheet IDs

### Test Suite

#### Test 1: Default Mode - Single Run

**Purpose**: Test basic default mode with single doc/sheet pair

**Setup**:
1. Edit `app_config.yaml` → `source_documents.input_link` (valid Google Doc)
2. Edit `app_config.yaml` → `source_documents.output_link` (valid spreadsheet ID)
3. Ensure both are shared with service account

**Run**:
```bash
cd /Users/shri/Projects/indic-learn
python -m quiz.backend.gurukula_quizgen
```

**Expected Output**:
```
============================================================
🔄 Google Doc → Quiz → Google Spreadsheet Workflow
============================================================
📖 Reading from Google Doc: https://docs.google.com/...
✅ Retrieved chapter: Chapter Title
📘 Generating quiz with 15 questions...
✅ Quiz generated: Topic Name
Uploading to Google Sheet...
📊 Using custom output spreadsheet (ID: SPREADSHEET_ID)
✅ Output spreadsheet validated and accessible (ID: SPREADSHEET_ID).
Google sheets authorized...
Spreadsheet opened for update...
✅ Google Sheet updated.
✅ Correct options highlighted in green.
✅ Done: Chapter Title
```

**Verification**:
- Open output spreadsheet
- Check for new tab with chapter title
- Verify 15 questions generated
- Verify correct answers highlighted in green

#### Test 2: Default Mode - Custom Question Count

**Purpose**: Test `--num_questions` override

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen --num_questions 20
```

**Expected**: 20 questions generated instead of config default (15)

#### Test 3: Default Mode - Batch Processing

**Purpose**: Test batch mode with multiple doc/sheet pairs

**Setup**:
1. Edit `app_config.yaml` → `source_documents.batch` with multiple entries
2. Ensure all docs/sheets are shared with service account

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen --batch
```

**Expected Output**:
```
============================================================
🔄 Batch Processing: 2 documents
============================================================

[1/2] Processing...
============================================================
🔄 Google Doc → Quiz → Google Spreadsheet Workflow
============================================================
...
✅ Done: Chapter 1

[2/2] Processing...
============================================================
🔄 Google Doc → Quiz → Google Spreadsheet Workflow
============================================================
...
✅ Done: Chapter 2

============================================================
📊 Batch Processing Summary
============================================================
✅ Successful: 2/2
❌ Failed: 0/2
```

#### Test 4: Legacy File Mode

**Purpose**: Ensure backward compatibility with file mode

**Setup**:
1. Ensure `quiz/data/chapter23.txt` exists
2. Set `chapter_question_counts.chapter23` in config

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23
```

**Expected**: Reads from file, generates quiz, writes to default output spreadsheet

#### Test 5: Legacy Spreadsheet Mode

**Purpose**: Ensure backward compatibility with spreadsheet mode

**Setup**:
1. Configure `spreadsheets.input_name` in `app_config.yaml`
2. Ensure input spreadsheet exists and has chapter tabs

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen --mode spreadsheet
```

**Expected**: Reads all tabs from input spreadsheet, generates quizzes

#### Test 6: Error Handling - Invalid Spreadsheet ID

**Purpose**: Test error messages for invalid/inaccessible spreadsheets

**Setup**:
1. Temporarily set `output_link` to invalid ID: `INVALID_ID`

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen
```

**Expected Output**:
```
❌ Spreadsheet with ID 'INVALID_ID' not found or is NOT accessible.
   Reason: The spreadsheet is either:
   1. Not shared with the service account
   2. Does not exist
   Solution: Please ensure the spreadsheet exists and is shared with the service account.
```

#### Test 7: Error Handling - Missing Configuration

**Purpose**: Test error messages for missing config

**Setup**:
1. Temporarily remove `source_documents` section from `app_config.yaml`

**Run**:
```bash
python -m quiz.backend.gurukula_quizgen
```

**Expected Output**:
```
❌ Missing 'source_documents.input_link' in app_config.yaml
   Please add:
   source_documents:
     input_link: https://docs.google.com/document/d/{DOC_ID}/edit
     output_link: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
     num_questions: 15
```

### Using test_pipeline.py

The `test_pipeline.py` file can be used for unit testing individual components:

```bash
python -m quiz.backend.test_pipeline
```

---

## 🔄 Common Workflows

### Workflow 1: Generate Quiz for New Chapter

1. Create Google Doc with chapter content
2. Create/identify output Google Sheet
3. Share both with service account email
4. Add to `app_config.yaml`:
   ```yaml
   source_documents:
     input_link: <doc_link>
     output_link: <sheet_link>
     num_questions: 15
   ```
5. Run: `python -m quiz.backend.gurukula_quizgen`

### Workflow 2: Batch Process Multiple Chapters

1. Prepare multiple Google Docs
2. Create/identify output Google Sheets
3. Share all with service account
4. Add all pairs to `app_config.yaml` under `source_documents.batch`
5. Run: `python -m quiz.backend.gurukula_quizgen --batch`

### Workflow 3: Regenerate Quiz with Different Question Count

1. Keep same config
2. Run: `python -m quiz.backend.gurukula_quizgen --num_questions 25`

### Workflow 4: Debug Quiz Generation Issues

1. Check logs for error messages
2. Verify service account has access to docs/sheets
3. Test with `test_pipeline.py` to isolate issues
4. Check LLM API connectivity (Groq)

---

## 🐛 Troubleshooting

### Issue: "Spreadsheet not found or not accessible"

**Causes**:
1. Spreadsheet ID is incorrect
2. Spreadsheet not shared with service account
3. Service account credentials invalid

**Solutions**:
1. Verify spreadsheet ID in URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
2. Share spreadsheet with service account email (found in JSON key file)
3. Check `.env` file has correct credentials
4. Regenerate service account key if needed

### Issue: "Invalid Google Sheets link format"

**Cause**: URL format not recognized by `extract_spreadsheet_id()`

**Solution**: Use one of these formats:
- Full URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
- Raw ID: `SPREADSHEET_ID`

### Issue: "Missing source_documents in config"

**Cause**: `app_config.yaml` doesn't have `source_documents` section

**Solution**: Add to `app_config.yaml`:
```yaml
source_documents:
  input_link: https://docs.google.com/document/d/DOC_ID/edit
  output_link: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
  num_questions: 15
```

### Issue: Quiz generation times out or fails

**Causes**:
1. LLM API (Groq) is down or rate-limited
2. Content is too long
3. Network issues

**Solutions**:
1. Check Groq API status
2. Reduce `num_questions` or split content
3. Check internet connectivity
4. Retry after delay

### Issue: Correct answers not highlighted

**Cause**: Conditional formatting failed (usually permissions)

**Solution**:
1. Check service account has "Editor" access (not just "Viewer")
2. Verify Google Sheets API is enabled in Google Cloud Console

---

## 🔑 Key Functions Reference

### Utility Functions

- **`extract_spreadsheet_id(link)`**: Extracts ID from URL or returns raw ID
- **`validate_spreadsheet_by_id(id, creds)`**: Validates spreadsheet access using direct lookup

### Workflow Functions

- **`run_gdoc_to_spreadsheet_workflow(input_link, output_link, num_questions)`**: Single doc → sheet processing
- **`run_batch_gdoc_to_spreadsheet_workflow(batch_config)`**: Batch processing with error handling

### Legacy Functions (Backward Compatibility)

- **`process_chapter_to_sheet()`**: Generic chapter processing for file/spreadsheet modes
- **`run_single_quiz_pipeline()`**: Single chapter from file
- **`run_batch_quiz_pipeline()`**: Batch from files or spreadsheet tabs
- **`upload_to_sheet()`**: Upload DataFrame to Google Sheets (supports both ID and name lookup)

---

## 📊 Performance Characteristics

### Default Mode (ID-based lookup)
- **Lookup Time**: O(1) - Direct ID access
- **Scalability**: Millions of spreadsheets
- **Recommended For**: Production, large-scale deployments

### Legacy Mode (Name-based lookup)
- **Lookup Time**: O(n) - Search by name across Drive
- **Scalability**: Slows down with thousands of files
- **Recommended For**: Small deployments, backward compatibility

---

## 🎯 Best Practices

1. **Always use Default Mode** for new implementations
2. **Share documents with service account** before running pipeline
3. **Use batch mode** for processing multiple chapters efficiently
4. **Test with single run** before attempting batch operations
5. **Monitor logs** for error messages and debugging info
6. **Keep backups** of configuration files
7. **Use descriptive chapter titles** in Google Docs (becomes tab name)

---

## 📚 Additional Resources

- **Main README**: `/Users/shri/Projects/indic-learn/README.md`
- **Pipeline Implementation**: `indic_quiz_generator_pipeline.py`
- **Google Sheets Utils**: `utils/gsheets.py`
- **Test Script**: `test_pipeline.py`

---

## 🔄 Recent Changes (2026-02-07)

### Added: Default Quiz Generation Mode

**Why**: To address scalability issues with name-based spreadsheet lookup and simplify the workflow.

**Changes**:
1. Added `source_documents` configuration section
2. Added `extract_spreadsheet_id()` and `validate_spreadsheet_by_id()` utilities
3. Updated `upload_to_sheet()` to support both ID and name-based lookup
4. Added `run_gdoc_to_spreadsheet_workflow()` for single processing
5. Added `run_batch_gdoc_to_spreadsheet_workflow()` for batch processing
6. Updated `main()` to support `--mode` argument with `default_quiz_gen` as default
7. Added `--batch` and `--num_questions` arguments
8. Maintained backward compatibility with file/spreadsheet modes

**Benefits**:
- O(1) spreadsheet lookup (scalable to millions of files)
- Simplified workflow (no arguments needed)
- Config-driven approach
- Better error messages
- Single and batch modes

---

**Last Updated**: 2026-02-07
**Maintained By**: Gurukula Team
**Contact**: @mambabhi on GitHub
