import io
import time

import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import ServerNotFoundError
from requests.exceptions import ConnectionError
from oauth2client.service_account import ServiceAccountCredentials


class QueueInterface:
    def __init__(self):
        # Connect and authenticate with Google sheets API
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
                      "https://www.googleapis.com/auth/spreadsheets"]
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name('serviceaccount.json', self.scope)
        for i in range(20):
            try:  # Attempt server connection
                self.gc = gspread.authorize(self.credentials)
                break
            except ServerNotFoundError as e:
                print("Connection failed, retrying...")
                time.sleep(30)  # Wait before retrying
                if i == 19:  # Final attempt, give up and fail
                    raise e
                continue
        self.service = build('drive', 'v3', credentials=self.credentials)  # http=self.creds.authorize(httplib2.Http()))

        self.worksheet = self.gc.open_by_key("1vIEMRgZJvIHGDI5OrJHG_wswMNymNetW0pPnJoxW8qU").sheet1  # Fake queue
        # self.worksheet = gc.open_by_key("1CFe6MW3KMfDUHXCaJdiqFpT-bdrNBG8KiCAh8AhkRyI").sheet1  # Actual queue

    def get_next_print(self, printer_type):
        print_id = 0  # Actually just spreadsheet row (for now)
        # SQL: SELECT 1 FROM <table> WHERE <status> = 'Queued' AND <printer type> = {printer_type}
        cell_list = self.worksheet.findall("Queued")
        for cell in cell_list:
            if self.worksheet.cell(cell.row, 10).value == printer_type:
                print_id = cell.row
                break
        return print_id

    def download_file(self, print_id):
        # Get file from Google Drive
        file_id = self.worksheet.cell(print_id, 15).value
        filename = self.worksheet.cell(print_id, 3).value
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(filename, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()


if __name__ == "__main__":
    queue = QueueInterface()
    print("Connected to queue")
    print("Please enter number for printer type."
          "\n1: Prusa"
          "\n2: Ultimaker")
    printer_type = ""

    try:
        print_id = queue.get_next_print("Prusa")
        if print_id == 0:
            print("No print found")
            exit(0)
        queue.download_file(print_id)
        print("Print found, downloaded")
    except ConnectionError:  # Internet connection failed
        print("Connection error")
        exit(0)
