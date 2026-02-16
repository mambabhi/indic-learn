# Quiz Generation Task Guide

This file helps Claude understand common quiz generation tasks and workflows.

## Common Tasks

### Task: Generate Quiz for a New Chapter

**User might say**: "Generate a quiz for chapter 25" or "Create quiz from this Google Doc"

**Steps**:
1. Ask user for the Google Doc link (if not provided)
2. Ask user for output spreadsheet link (or use default from config)
3. Verify both are shared with service account
4. Update `app_config.yaml` if needed
5. Run: `python -m quiz.backend.gurukula_quizgen`
6. Verify output in spreadsheet

**Key Questions to Ask**:
- What is the Google Doc link?
- Where should the quiz be written? (spreadsheet link)
- How many questions? (default: 15)
- Is this for testing or production?

---

### Task: Batch Process Multiple Chapters

**User might say**: "Generate quizzes for all these chapters" or "Process chapters 20-25"

**Steps**:
1. Gather all Google Doc links
2. Gather all output spreadsheet links (or use same spreadsheet for all)
3. Add to `app_config.yaml` under `source_documents.batch`
4. Run: `python -m quiz.backend.gurukula_quizgen --batch`
5. Review batch summary for any failures
6. Retry failed items individually if needed

**Config Example**:
```yaml
source_documents:
  batch:
    - input_link: https://docs.google.com/document/d/DOC1/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET1/edit
      num_questions: 15
    - input_link: https://docs.google.com/document/d/DOC2/edit
      output_link: https://docs.google.com/spreadsheets/d/SHEET2/edit
      num_questions: 20
```

---

### Task: Regenerate Quiz with Different Question Count

**User might say**: "Make it 20 questions instead" or "Generate more questions"

**Steps**:
1. Keep same config (don't modify `app_config.yaml`)
2. Run with override: `python -m quiz.backend.gurukula_quizgen --num_questions 20`
3. This will replace the existing quiz tab in the spreadsheet

**Note**: The `--num_questions` flag overrides the config value temporarily without changing the file.

---

### Task: Debug Quiz Generation Failure

**User might say**: "The quiz generation failed" or "I'm getting an error"

**Steps**:
1. Check the error message carefully
2. Common issues:
   - **"Spreadsheet not found"**: Check sharing with service account
   - **"Invalid credentials"**: Check `.env` file
   - **"API Error"**: Check Google APIs are enabled
   - **"Timeout"**: Content too long or network issue
3. Verify prerequisites:
   - Service account credentials in `.env`
   - Documents shared with service account email
   - Google Sheets/Drive APIs enabled
   - Correct document IDs in config
4. Test with a simple document first
5. Check `test_pipeline.py` for unit testing

**Helpful Commands**:
```bash
# Check service account email
cat quiz/backend/credentials/service-account.json | grep client_email

# Test with existing chapter
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23

# Run backend tests
python -m quiz.backend.test_pipeline
```

---

### Task: Migrate from Legacy Mode to Default Mode

**User might say**: "Update to the new mode" or "Use the new ID-based lookup"

**Steps**:
1. Identify current mode (file/spreadsheet)
2. If using spreadsheet mode:
   - Get spreadsheet ID from URL
   - Update `app_config.yaml` with `source_documents` section
   - Add `input_link` (Google Doc) and `output_link` (spreadsheet ID)
3. Test with single run first
4. Gradually migrate batch operations
5. Update documentation/scripts that reference old modes

**Migration Example**:
```yaml
# OLD (spreadsheet mode)
spreadsheets:
  input_name: gurukula-story-master
  output_name: gurukula-quiz-master

# NEW (default mode)
source_documents:
  input_link: https://docs.google.com/document/d/DOC_ID/edit
  output_link: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
  num_questions: 15
```

---

### Task: Set Up Service Account Access

**User might say**: "How do I set up permissions?" or "Getting permission denied"

**Steps**:
1. Find service account email:
   ```bash
   cat quiz/backend/credentials/service-account.json | grep client_email
   ```
2. For each Google Doc/Sheet:
   - Click "Share" button
   - Add service account email
   - Grant "Editor" permissions (not just Viewer)
3. Verify access by running a test
4. If still failing, check Google Cloud Console:
   - Ensure Google Sheets API is enabled
   - Ensure Google Drive API is enabled
   - Check service account key is valid

---

### Task: Understand Quiz Output Format

**User might say**: "What does the output look like?" or "Explain the spreadsheet format"

**Output Structure**:
- Each chapter becomes a tab in the output spreadsheet
- Tab name matches chapter title from Google Doc
- Columns:
  - **Chapter**: Chapter number/title
  - **Timer**: Time limit in seconds (15 for SCQ, 20 for MCQ)
  - **Points**: Points earned (10 for SCQ, 15 for MCQ)
  - **Type**: SCQ or MCQ
  - **Question**: The question text
  - **Option A/B/C/D**: Answer options
  - **Right Answer**: Correct answer(s) as letters (e.g., "a" or "bd")

**Formatting**:
- Correct answer options are highlighted in green
- Backup questions (if generated) are separated by a red-highlighted note row
- Questions are randomized within the main set

---

## File Locations

**Key Files**:
- Main script: `quiz/backend/gurukula_quizgen.py`
- Configuration: `quiz/backend/config/app_config.yaml`
- Environment: `.env` (in project root)
- Testing guide: `quiz/backend/TESTING_DEFAULT_MODE.md`
- Developer guide: `quiz/backend/CLAUDE.md`
- Credentials: `quiz/backend/credentials/service-account.json`

**Test Files**:
- Backend tests: `quiz/backend/test_pipeline.py`
- Chapter data: `quiz/data/*.txt`

---

## Quick Command Reference

```bash
# Default mode (single run)
python -m quiz.backend.gurukula_quizgen

# Custom question count
python -m quiz.backend.gurukula_quizgen --num_questions 25

# Batch mode
python -m quiz.backend.gurukula_quizgen --batch

# Legacy file mode
python -m quiz.backend.gurukula_quizgen --mode file --chapter chapter23

# Legacy spreadsheet mode
python -m quiz.backend.gurukula_quizgen --mode spreadsheet

# Get service account email
cat quiz/backend/credentials/service-account.json | grep client_email

# Run tests
python -m quiz.backend.test_pipeline
```

---

## Decision Tree for Mode Selection

**Use Default Mode when**:
- Starting new project
- Need scalability (many spreadsheets)
- Want simple config-driven workflow
- Processing Google Docs → Google Sheets

**Use File Mode when**:
- Have local text files
- Testing with sample data
- Don't need Google integration

**Use Spreadsheet Mode when**:
- Need backward compatibility
- Already have input spreadsheet with tabs
- Small number of spreadsheets (<100)

---

## Error Message Guide

### "Spreadsheet with ID 'X' not found or is NOT accessible"
**Cause**: Spreadsheet not shared or doesn't exist
**Fix**: Share with service account, verify ID

### "Missing 'source_documents.input_link' in app_config.yaml"
**Cause**: Config not set up for default mode
**Fix**: Add `source_documents` section to config

### "Invalid Google Sheets link format"
**Cause**: URL format not recognized
**Fix**: Use format `https://docs.google.com/spreadsheets/d/ID/edit` or just `ID`

### "Invalid Google service account credentials"
**Cause**: `.env` file missing or credentials invalid
**Fix**: Check `.env` exists, verify service account JSON is valid

### "API Error accessing spreadsheet"
**Cause**: API quota exceeded or API not enabled
**Fix**: Check Google Cloud Console, enable APIs, check quotas

---

## Best Practices for Claude

1. **Always verify prerequisites** before running commands
2. **Ask clarifying questions** about which mode to use
3. **Test with single run** before attempting batch
4. **Check error messages carefully** - they're designed to be actionable
5. **Verify document sharing** if permission errors occur
6. **Use full testing guide** for comprehensive verification
7. **Reference CLAUDE.md** for architectural details
8. **Keep backups** before regenerating quizzes

---

**Last Updated**: 2026-02-07
**For detailed documentation**: See `quiz/backend/CLAUDE.md`
