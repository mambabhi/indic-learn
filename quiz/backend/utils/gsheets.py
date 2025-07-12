# utils/gsheets.py

def clear_all_sheet_formatting_only(sheets_api, spreadsheet_id, sheet_id):
    """
    Clears all formatting (but not data) from the specified sheet.
    """
    request_body = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": sheet_id},
                    "fields": "userEnteredFormat"  # Only formatting
                }
            }
        ]
    }

    sheets_api.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=request_body
    ).execute()

