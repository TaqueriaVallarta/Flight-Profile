import re
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from lib.RocketClass import Rocket
import time
import os

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

    def get_existing_named_ranges(self):
        """Retrieve existing named ranges from the spreadsheet."""
        print("Getting existing named ranges:", time.process_time())
        try:
            named_ranges = self.response.get('namedRanges', [])
            print("Got named ranges:", time.process_time())
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
            except Exception as e:
                print("Error sending delete requests for named data:", e)

        # Send add requests
        if add_requests:
            try:
                body = {"requests": add_requests}
                self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id,
                                                                   body=body).execute()
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
            return value
        except Exception as e:
            print(f"Error reading values for range '{a1_notation}':", e)
            return None

    def update_values_from_sheets(self):
        """Fetches values from named ranges corresponding to the keys in the Rocket's values dictionary."""
        print("Getting named ranges for updating values:", time.process_time())
        named_ranges = self.get_existing_named_ranges()
        results = {}
        print("Finished getting named ranges for updating values:", time.process_time())

        # Prepare the list of named range names to fetch in a single batch request
        range_names = [
            sanitize_name(key) for key in self.rocket.values.keys() if sanitize_name(key) in named_ranges
        ]

        if not range_names:
            print("No valid named ranges found for fetching.")
            return results

        try:
            # Use batchGet to fetch all values in a single API call
            response = self.service.spreadsheets().values().batchGet(
                spreadsheetId=self.spreadsheet_id,
                ranges=range_names
            ).execute()

            # Extract values from the batchGet response
            value_ranges = response.get('valueRanges', [])
            for value_range in value_ranges:
                range_name = value_range.get('range').split('!')[0]  # Extract range name from response
                if range_name in named_ranges:
                    try:
                        value = value_range.get('values', [])[0][0]
                        results[range_name] = cast_to_number(value)
                    except (IndexError, KeyError) as e:
                        print(f"Error processing values for named range '{range_name}':", e)
                        results[range_name] = None
                else:
                    results[range_name] = None  # No named range found for this key
        except Exception as e:
            print(f"Error in batch fetching values: {e}")

        # Update the Rocket instance with the fetched values
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
            except Exception as e:
                print("Error sending update requests:", e)

    def sheet_bool(self, name):
        value = self.get_named_range_value(name)
        if value == "TRUE":
            return True
        elif value == "FALSE":
            return False
        else:
            return None

    def write_to_named_range(self, name, value):
        """Writes a single value to the specified named range in the spreadsheet."""
        named_ranges = self.response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        if name not in named_ranges:
            print(f"Named range for '{name}' not found.")
            return None

        named_range = named_ranges[name]

        # Extract sheet details and construct the A1 notation range
        sheet_id = named_range['sheetId']
        start_row = named_range['startRowIndex'] + 1  # Convert to 1-based indexing
        end_row = named_range['endRowIndex']
        start_col = named_range['startColumnIndex'] + 1
        end_col = named_range['endColumnIndex']

        # Convert column indices to A1 notation
        start_col_letter = _col_to_letter(start_col)
        end_col_letter = _col_to_letter(end_col)

        # Construct A1 notation for the named range
        a1_notation = f"{self.client.open_by_key(self.spreadsheet_id).get_worksheet_by_id(sheet_id).title}!{start_col_letter}{start_row}:{end_col_letter}{end_row}"

        # Prepare the update request body
        update_body = {
            "range": a1_notation,
            "values": [[value]],  # Single value to write
            "majorDimension": "ROWS"
        }

        try:
            # Use the values.update method to update the cell content
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=a1_notation,
                valueInputOption="USER_ENTERED",
                body=update_body
            ).execute()
        except Exception as e:
            print(f"Error updating named range '{name}':", e)

    def process_spreadsheet_update(self):
        """Processes updates to the spreadsheet based on the presence of credentials and input flags."""
        # Check for the existence of the credentials files
        print("Initialized:", time.process_time())
        if os.path.exists("credentials1.json") and os.path.exists("credentials2.json"):
            print("Detected Credentials:", time.process_time())

            # Check if sheet inputs should be used
            sheet_input = self.sheet_bool('use_sheet_inputs')
            print("Detected sheet_input var:", time.process_time())
            if sheet_input:
                self.update_values_from_sheets()
            print("Update inputs:", time.process_time())

            # Simulate the rocket to ground
            self.rocket.simulate_to_ground()
            print("Simulate to ground:", time.process_time())

            # Update the spreadsheet with new data
            self.update_data()
            print("Sending data to sheet:", time.process_time())

            # Update named ranges in the spreadsheet
            self.update_named_data()
            print("Updating named data:", time.process_time())
        else:
            # If credentials files are missing, perform local simulation and export data
            print("Credentials missing. Running simulation locally.")
            rocket = self.rocket
            rocket.simulate_to_ground()
            rocket.dataframe.to_csv("Simulation_data.csv", index=False)
            rocket.dataframe.to_clipboard(index=False)
