import re

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from lib.RocketClass import Rocket
import time


def sanitize_name(name):
    """Sanitize column names to be valid named range names."""
    return re.sub(r'\W|^(?=\d)', '_', name)


def _col_to_letter(col):
    """Convert column number to letter (1 -> A, 2 -> B, ..., 27 -> AA)."""
    letter = ''
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter


def cast_to_number(value):
    try:
        # Attempt to convert to integer first
        return int(value)
    except ValueError:
        try:
            # Fallback to float if integer conversion fails
            return float(value)
        except ValueError:
            # Handle cases where conversion fails
            print(f"Error converting value to a number: {value}")
            return None  # or handle the error as needed


class UpdateSpreadsheet:
    def __init__(self, rocket: Rocket):
        self.rocket = rocket
        self.dataframe = self.rocket.dataframe
        self.values = self.rocket.values
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file("credentials1.json", scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.service: build = build('sheets', 'v4', credentials=self.creds)
        self.spreadsheet_id = self.client.open("Goddard Flight Profile").id
        self.data_sheet_name = "Raw Data"
        self.response = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

    def update_creds(self, filename):
        self.creds = Credentials.from_service_account_file(filename, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.service: build = build('sheets', 'v4', credentials=self.creds)
        self.spreadsheet_id = self.client.open("Goddard Flight Profile").id
        self.response = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

    def update_data(self):
        sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.data_sheet_name)
        sheet.clear()

        df = self.dataframe
        # Update Google Sheet with CSV data
        cell_range = 'A1'  # Starting cell for the data
        sheet.update(cell_range, [df.columns.values.tolist()] + df.values.tolist())
        print("Updated Data")

    def get_existing_named_ranges(self):
        """Retrieve existing named ranges from the spreadsheet."""
        try:
            named_ranges = self.response.get('namedRanges', [])
            print("Existing named ranges:", named_ranges)  # Debugging output
            return {nr['name']: nr['namedRangeId'] for nr in named_ranges}
        except Exception as e:
            print("Error retrieving named ranges:", e)
            return {}

    def update_named_data(self):
        sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.data_sheet_name)
        # Get the sheet ID
        sheet_id = sheet.id

        df = self.dataframe
        existing_named_ranges = self.get_existing_named_ranges()

        # Prepare requests for deleting and adding named ranges
        delete_requests = []
        add_requests = []

        for col_idx, col_name in enumerate(df.columns):
            # Sanitize the column name for the named range
            sanitized_name = sanitize_name(col_name)
            if len(sanitized_name) == 0:
                continue  # Skip if the name is empty after sanitization

            # Define the named range for each column
            start_col = col_idx
            end_col = col_idx + 1
            num_rows = len(df) + 1  # +1 for the header row

            # Check if named range already exists and prepare delete request if needed
            if sanitized_name in existing_named_ranges:
                named_range_id = existing_named_ranges[sanitized_name]
                delete_requests.append({
                    "deleteNamedRange": {
                        "namedRangeId": named_range_id
                    }
                })
                # Remove the existing named range from the list of existing ranges
                del existing_named_ranges[sanitized_name]

            # Create a new named range request
            add_requests.append({
                "addNamedRange": {
                    "namedRange": {
                        "name": sanitized_name,
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": num_rows,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col
                        }
                    }
                }
            })

        # Send delete requests first
        if delete_requests:
            try:
                body = {"requests": delete_requests}
                response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                                   body=body).execute()
                print("Delete named data:", response)  # Debugging output
            except Exception as e:
                print("Error sending delete requests for named data:", e)

        # Send add requests
        if add_requests:
            try:
                body = {"requests": add_requests}
                print("Sending add requests:", body)  # Debugging output
                response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                                   body=body).execute()
                print("Add response:", response)  # Debugging output
            except Exception as e:
                print("Error sending add requests:", e)
        self.response = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

    def get_named_range_value(self, name):
        self.update_creds("credentials1.json")
        # Step 1: Get the named range details
        named_ranges = self.response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        if name not in named_ranges:
            print(f"Named range '{name}' not found.")
            return None

        # Step 2: Get the range details
        range_info = named_ranges[name]
        sheet_id = range_info['sheetId']

        # Find the sheet name from sheetId
        sheets = self.response.get('sheets', [])
        sheet_name = None
        for sheet in sheets:
            if sheet['properties']['sheetId'] == sheet_id:
                sheet_name = sheet['properties']['title']
                break

        if not sheet_name:
            print(f"Sheet with ID '{sheet_id}' not found.")
            return None

        # Step 3: Convert to A1 notation
        start_row = range_info['startRowIndex'] + 1
        end_row = range_info['endRowIndex']
        start_col = range_info['startColumnIndex'] + 1
        end_col = range_info['endColumnIndex']

        # Convert column indices to A1 notation
        start_col_letter = _col_to_letter(start_col)
        end_col_letter = _col_to_letter(end_col)

        # Construct A1 notation range
        a1_notation = f"{sheet_name}!{start_col_letter}{start_row}:{end_col_letter}{end_row}"

        # Step 4: Read the values
        try:
            value_response = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id,
                                                                      range=a1_notation).execute()
            value = value_response.get('values', [])[0][0]
            print("Successfully got named range value: ", name)
            return value
        except Exception as e:
            print(f"Error reading values for range '{a1_notation}':", e)
            return None

    def update_values_from_sheets(self):
        """Fetches values from named ranges corresponding to the keys in the Rocket's values dictionary."""
        named_ranges = self.get_existing_named_ranges()
        results = {}

        for key in self.rocket.values.keys():
            sanitized_name = sanitize_name(key)
            if sanitized_name in named_ranges:
                try:
                    range_name = sanitized_name
                    result = self.service.spreadsheets().values().get(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name
                    ).execute()
                    results[key] = cast_to_number(result.get('values', [])[0][0])
                except Exception as e:
                    print(f"Error fetching values for named range '{sanitized_name}':", e)
                    results[key] = None
            else:
                results[key] = None  # No named range found for this key
        print("Update values from sheets: ", results)

        self.rocket.set_vars_to_new(results)
        self.rocket.set_vals_to_vars()
        return results

    def update_sheets_from_values(self):
        """Writes the Rocket's values to the corresponding named ranges in the spreadsheet."""
        self.update_creds("credentials1.json")
        response = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        named_ranges = response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        update_requests = []

        for key, value in self.rocket.values.items():
            sanitized_name = sanitize_name(key)
            if sanitized_name in named_ranges.keys():
                named_range = named_ranges[sanitized_name]
                try:
                    # Prepare update request for the named range
                    update_requests.append({
                        "updateCells": {
                            "range": {
                                "sheetId": named_range['sheetId'],
                                "startRowIndex": named_range['startRowIndex'],
                                "endRowIndex": named_range['endRowIndex'],
                                "startColumnIndex": named_range['startColumnIndex'],
                                "endColumnIndex": named_range['endColumnIndex'],
                            },
                            "fields": "userEnteredValue",
                            "rows": [{
                                "values": [{
                                    "userEnteredValue": {
                                        "numberValue": value
                                    }
                                }]
                            }]
                        }
                    })
                except Exception as e:
                    print(f"Error preparing update request for named range '{sanitized_name}':", e)

        # Send update requests
        if update_requests:
            try:
                body = {"requests": update_requests}
                response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                                   body=body).execute()
                print("Update sheets from values:", response)  # Debugging output
            except Exception as e:
                print("Error sending update requests:", e)

    def sheet_bool(self, name):
        self.update_creds("credentials1.json")
        value = self.get_named_range_value(name)
        if value == "TRUE":
            return True
        elif value == "FALSE":
            return False
        else:
            return None

    def write_to_named_range(self, name, value):
        self.update_creds("credentials2.json")
        named_ranges = self.response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        if name not in named_ranges:
            print(f"Named range for write to named range '{name}' not found.")
            return None

        named_range = named_ranges[name]
        update_requests = [({
            "updateCells": {
                "range": {
                    "sheetId": named_range['sheetId'],
                    "startRowIndex": named_range['startRowIndex'],
                    "endRowIndex": named_range['endRowIndex'],
                    "startColumnIndex": named_range['startColumnIndex'],
                    "endColumnIndex": named_range['endColumnIndex'],
                },
                "fields": "userEnteredValue",
                "rows": [{
                    "values": [{
                        "userEnteredValue": {
                            "boolValue": value
                        }
                    }]
                }]
            }
        })]
        body = {"requests": update_requests}
        response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                           body=body).execute()
        print("Write to named range:", response)
