# Quick Start: Testing Default Quiz Generation Mode

This guide walks you through testing the new default quiz generation mode step by step.

## Prerequisites Checklist

- [ ] Google Service Account credentials configured in `.env`
- [ ] Service account has access to Google Sheets API and Google Drive API
- [ ] A test Google Doc with chapter content
- [ ] A test Google Spreadsheet for output
- [ ] Both documents shared with service account email

## Step 1: Prepare Test Documents

### 1.1 Create Test Google Doc

1. Create a new Google Doc: https://docs.google.com
2. Add chapter content (story text)
3. Give it a clear title (e.g., "Chapter 25 - The Forest Adventure")
4. Copy the document URL

**Example URL**:
```
https://docs.google.com/document/d/1YyDyBCD-Wy4G6Kr_8PTBCxeMeJI6xjaUHGSca2xWVhQ/edit?tab=t.0
```

### 1.2 Create Test Google Spreadsheet

1. Create a new Google Sheet: https://sheets.google.com
2. Give it a name (e.g., "Quiz Output Test")
3. Copy the spreadsheet URL

**Example URL**:
```
https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1/edit
```

### 1.3 Share with Service Account

1. Find your service account email in the JSON credentials file:
   ```bash
   cat quiz/backend/credentials/service-account.json | grep client_email
   ```

2. Open both documents and click "Share"

3. Add the service account email (e.g., `quiz-gen@project.iam.gserviceaccount.com`)

4. Give "Editor" permissions

## Step 2: Configure app_config.yaml

Edit `/Users/shri/Projects/indic-learn/quiz/backend/config/app_config.yaml`:

```yaml
source_documents:
  # Replace with your actual document URLs
  input_link: https://docs.google.com/document/d/1YyDyBCD-Wy4G6Kr_8PTBCxeMeJI6xjaUHGSca2xWVhQ/edit?tab=t.0
  output_link: https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1/edit
  num_questions: 15
```

**Note**: You can use full URLs or just the IDs:
```yaml
source_documents:
  input_link: 1YyDyBCD-Wy4G6Kr_8PTBCxeMeJI6xjaUHGSca2xWVhQ
  output_link: 1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1
  num_questions: 15
```

## Step 3: Run Basic Test (Single Mode)

Navigate to project root and run:

```bash
cd /Users/shri/Projects/indic-learn
python -m quiz.backend.gurukula_quizgen
```

### Expected Output (Success)

```
============================================================
🔄 Google Doc → Quiz → Google Spreadsheet Workflow
============================================================
📖 Reading from Google Doc: https://docs.google.com/document/d/...
✅ Retrieved chapter: Chapter 25 - The Forest Adventure
📘 Generating quiz with 15 questions...
✅ Quiz generated: The Forest Adventure
Uploading to Google Sheet...
📊 Using custom output spreadsheet (ID: 1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1)
✅ Output spreadsheet validated and accessible (ID: 1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1).
Google sheets authorized...
Spreadsheet opened for update...
✅ Google Sheet updated.
✅ Correct options highlighted in green.
✅ Done: Chapter 25 - The Forest Adventure
```

### Verify Results

1. Open your output spreadsheet
2. You should see a new tab named after your chapter (e.g., "Chapter 25 - The Forest Adventure")
3. The tab should contain:
   - Column headers: Chapter, Timer, Points, Type, Question, Option A, Option B, Option C, Option D, Right Answer
   - 15 questions (or more if backup questions generated)
   - Correct answers highlighted in green
   - A separator row (highlighted in red) if backup questions exist

## Step 4: Run Test with Custom Question Count

Test the `--num_questions` override:

```bash
python -m quiz.backend.gurukula_quizgen --num_questions 20
```

**Expected**: 20 questions generated (overrides config value of 15)

## Step 5: Test Batch Mode

### 5.1 Configure Batch

Edit `app_config.yaml` to add multiple document pairs:

```yaml
source_documents:
  input_link: https://docs.google.com/document/d/DOC_ID_1/edit
  output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_1/edit
  num_questions: 15

  batch:
    - input_link: https://docs.google.com/document/d/DOC_ID_1/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_1/edit
      num_questions: 15
    - input_link: https://docs.google.com/document/d/DOC_ID_2/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET_ID_2/edit
      num_questions: 20
```

### 5.2 Run Batch

```bash
python -m quiz.backend.gurukula_quizgen --batch
```

### Expected Output (Success)

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

## Step 6: Test Error Handling

### 6.1 Test Invalid Spreadsheet ID

Temporarily set an invalid ID in config:

```yaml
source_documents:
  input_link: https://docs.google.com/document/d/VALID_DOC_ID/edit
  output_link: https://docs.google.com/spreadsheets/d/INVALID_ID/edit
  num_questions: 15
```

Run:
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

### 6.2 Test Missing Configuration

Temporarily remove `source_documents` section from config.

Run:
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

### 6.3 Test Unshared Document

1. Remove service account sharing from one of your test documents
2. Run the pipeline

**Expected**: Clear error message about permissions

## Step 7: Verify Backward Compatibility

### 7.1 Test Legacy File Mode

```bash
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23
```

**Expected**: Works as before (reads from `quiz/data/chapter23.txt`)

### 7.2 Test Legacy Spreadsheet Mode

```bash
python -m quiz.backend.gurukula_quizgen --mode spreadsheet
```

**Expected**: Works as before (reads from configured input spreadsheet)

## Common Issues and Solutions

### Issue: "Invalid Google service account credentials"

**Solution**:
1. Check `.env` file exists and has correct path
2. Verify service account JSON file exists at the path
3. Check JSON file is valid (not corrupted)

### Issue: "Spreadsheet not found or not accessible"

**Solution**:
1. Verify spreadsheet ID is correct (check URL)
2. Share spreadsheet with service account email
3. Give "Editor" permissions (not just "Viewer")

### Issue: "Failed to read Google Doc"

**Solution**:
1. Verify document ID is correct
2. Share document with service account
3. Ensure document has content

### Issue: Quiz generation hangs or times out

**Solution**:
1. Check internet connectivity
2. Verify Groq API is accessible
3. Check if content is too long (reduce num_questions)
4. Look for rate limiting errors in logs

### Issue: Correct answers not highlighted

**Solution**:
1. Ensure service account has "Editor" access (not "Viewer")
2. Verify Google Sheets API is enabled in Google Cloud Console
3. Check for API quota limits

## Success Criteria Checklist

After running all tests, verify:

- [ ] Default single mode runs without arguments
- [ ] Custom question count works with `--num_questions`
- [ ] Batch mode processes multiple documents
- [ ] Error messages are clear and actionable
- [ ] Output spreadsheet has correct tabs and formatting
- [ ] Correct answers are highlighted in green
- [ ] Legacy file mode still works
- [ ] Legacy spreadsheet mode still works
- [ ] Invalid IDs produce helpful error messages
- [ ] Missing config produces helpful error messages

## Performance Notes

- **Single run**: ~30-60 seconds per chapter (depending on question count and LLM response time)
- **Batch mode**: Processes sequentially, ~30-60 seconds per document
- **Scalability**: ID-based lookup is O(1), works efficiently with millions of spreadsheets

## Next Steps

Once testing is complete:

1. Update production `app_config.yaml` with real document pairs
2. Set up batch configuration for all chapters
3. Run production quiz generation
4. Monitor logs for any issues
5. Verify all output spreadsheets are correctly formatted

## Useful Commands

```bash
# Run default mode
python -m quiz.backend.gurukula_quizgen

# Run with custom questions
python -m quiz.backend.gurukula_quizgen --num_questions 25

# Run batch mode
python -m quiz.backend.gurukula_quizgen --batch

# Run legacy file mode
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23

# Run legacy spreadsheet mode
python -m quiz.backend.gurukula_quizgen --mode spreadsheet

# Check service account email
cat quiz/backend/credentials/service-account.json | grep client_email

# View logs (if logging to file)
tail -f quiz/backend/logs/quiz_generation.log
```

---

**Last Updated**: 2026-02-07
**Author**: Gurukula Team
**For Questions**: See `CLAUDE.md` or contact @mambabhi on GitHub
