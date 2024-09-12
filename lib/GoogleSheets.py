from re import sub
from gspread import authorize
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from lib.RocketClass import Rocket
import logging
import os

logging.basicConfig(level=logging.INFO)


class UpdateSpreadsheet:
    def __init__(self, rocket: Rocket):
        self.rocket = rocket
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = self.initialize_creds("credentials1.json")
        self.client = authorize(self.creds)
        self.service = build('sheets', 'v4', credentials=self.creds, cache_discovery=False)
        self.spreadsheet_id = self.client.open("Goddard Flight Profile").id
        self.data_sheet_name = "Raw Data"
        self.response = self.fetch_spreadsheet_metadata()

    @staticmethod
    def sanitize_name(name):
        """Sanitize column names to be valid named range names."""
        return sub(r'\W|^(?=\d)', '_', name)

    @staticmethod
    def _col_to_letter(col):
        """Convert column number to letter (1 -> A, 2 -> B, ..., 27 -> AA)."""
        letter = ''
        while col > 0:
            col, remainder = divmod(col - 1, 26)
            letter = chr(65 + remainder) + letter
        return letter

    def update_creds(self, filename):
        """Update credentials and reinitialize services."""
        self.creds = self.initialize_creds(filename)
        self.client = authorize(self.creds)
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.spreadsheet_id = self.client.open("Goddard Flight Profile").id
        self.response = self.fetch_spreadsheet_metadata()

    def handle_requests(self, requests):
        """Send batch requests to the Google Sheets API."""
        if not requests:
            return
        try:
            body = {"requests": requests}
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()
        except Exception as e:
            logging.error(f"Error sending batch requests: {e}")

    def update_data(self):
        """Clear and update data in the designated Google Sheet."""
        sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.data_sheet_name)
        sheet.clear()
        df = self.rocket.dataframe
        cell_range = 'A1'
        sheet.update(cell_range, [df.columns.values.tolist()] + df.values.tolist())

    def fetch_spreadsheet_metadata(self):
        """Fetch metadata of the spreadsheet."""
        return self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()

    def initialize_creds(self, filename):
        """Initialize credentials from a service account file."""
        return Credentials.from_service_account_file(filename, scopes=self.scope)

    def get_existing_named_ranges(self):
        """Retrieve existing named ranges from the spreadsheet."""
        try:
            named_ranges = self.response.get('namedRanges', [])
            return {nr['name']: nr['namedRangeId'] for nr in named_ranges}
        except Exception as e:
            logging.error(f"Error retrieving named ranges: {e}")
            return {}

    def update_named_data(self):
        """Update named ranges in the Google Sheet."""
        sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.data_sheet_name)
        sheet_id = sheet.id
        df = self.rocket.dataframe
        existing_named_ranges = self.get_existing_named_ranges()

        delete_requests, add_requests = [], []

        for col_idx, col_name in enumerate(df.columns):
            sanitized_name = self.sanitize_name(col_name)
            if not sanitized_name:
                continue

            start_col = col_idx
            end_col = col_idx + 1
            num_rows = len(df) + 1

            if sanitized_name in existing_named_ranges:
                delete_requests.append({"deleteNamedRange": {"namedRangeId": existing_named_ranges[sanitized_name]}})
                del existing_named_ranges[sanitized_name]

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

        self.handle_requests(delete_requests)
        self.handle_requests(add_requests)
        self.response = self.fetch_spreadsheet_metadata()

    def get_named_range_value(self, name):
        """Fetch value from a named range in the Google Sheet."""
        named_ranges = self.response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        if name not in named_ranges:
            logging.info(f"Named range '{name}' not found.")
            return None

        range_info = named_ranges[name]
        sheet_id = range_info['sheetId']
        sheets = self.response.get('sheets', [])
        sheet_name = next((s['properties']['title'] for s in sheets if s['properties']['sheetId'] == sheet_id), None)

        if not sheet_name:
            logging.error(f"Sheet with ID '{sheet_id}' not found.")
            return None

        start_row = range_info['startRowIndex'] + 1
        end_row = range_info['endRowIndex']
        start_col_letter = self._col_to_letter(range_info['startColumnIndex'] + 1)
        end_col_letter = self._col_to_letter(range_info['endColumnIndex'])

        a1_notation = f"{sheet_name}!{start_col_letter}{start_row}:{end_col_letter}{end_row}"

        try:
            value_response = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id,
                                                                      range=a1_notation).execute()
            return value_response.get('values', [])[0][0]
        except Exception as e:
            logging.error(f"Error reading values for range '{a1_notation}': {e}")
            return None

    def update_values_from_sheets(self):
        """Fetch values from named ranges and update Rocket variables."""
        named_ranges = self.get_existing_named_ranges()
        range_names = [self.sanitize_name(key) for key in self.rocket.values.keys() if
                       self.sanitize_name(key) in named_ranges]

        if not range_names:
            logging.info("No valid named ranges found for fetching.")
            return {}

        try:
            response = self.service.spreadsheets().values().batchGet(
                spreadsheetId=self.spreadsheet_id, ranges=range_names
            ).execute()

            results = {}
            for value_range in response.get('valueRanges', []):
                if value_range.get('values'):
                    value = value_range.get('values', [[]])[0][0]
                    try:
                        # Attempt to cast to a float
                        results[value_range['range'].split('!')[0]] = float(value)
                    except ValueError:
                        # Log error if unable to cast to float
                        logging.error(f"Error converting value to a float: {value}")

            return results

        except Exception as e:
            logging.error(f"Error fetching batch values: {e}")
            return {}

    def update_sheets_from_values(self):
        """Writes the Rocket's values to the corresponding named ranges in the spreadsheet."""
        response = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        named_ranges = response.get('namedRanges', [])
        named_ranges = {nr['name']: nr['range'] for nr in named_ranges}

        update_requests = []

        for key, value in self.rocket.values.items():
            sanitized_name = self.sanitize_name(key)
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

    def process_spreadsheet_update(self):
        if os.path.exists("credentials1.json"):
            logging.info("Updating spreadsheet...")
            try:
                if self.sheet_bool("use_sheet_inputs"):
                    updated_values = self.update_values_from_sheets()
                    for key, value in updated_values.items():
                        self.rocket.values[key] = value
                    logging.info("Spreadsheet updated successfully.")
                else:
                    logging.info("No input update necessary")
            except Exception as e:
                logging.error(f"Error during spreadsheet processing: {e}")

            """Main method to handle spreadsheet updates."""
            self.update_data()
            self.update_named_data()
        else:
            # If credentials files are missing, perform local simulation and export data
            print("Credentials missing. Running simulation locally.")
            rocket = self.rocket
            rocket.simulate_to_ground()
            rocket.dataframe.to_csv("Simulation_data.csv", index=False)
            rocket.dataframe.to_clipboard(index=False)
