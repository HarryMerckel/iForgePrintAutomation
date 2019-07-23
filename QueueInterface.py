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
                    raise
                continue
        self.service = build('drive', 'v3', credentials=self.credentials)

        self.worksheet = self.gc.open_by_key("1vIEMRgZJvIHGDI5OrJHG_wswMNymNetW0pPnJoxW8qU").sheet1  # Fake queue
        # self.worksheet = gc.open_by_key("1CFe6MW3KMfDUHXCaJdiqFpT-bdrNBG8KiCAh8AhkRyI").sheet1  # Actual queue

    def get_status(self, print_id):
        return self.worksheet.cell(print_id, 9).value

    def update_status(self, print_id, new_status):
        self.worksheet.update_cell(print_id, 5, new_status)

    def get_next_print(self, printer_type):
        print_id = 0  # Actually just spreadsheet row (for now)
        # SQL:
        # SELECT TOP 1
        # FROM Queue
        # WHERE Status = 'Queued'
        # AND PrinterType = {printer_type}
        # ORDER BY TimestampAdded ASC
        # Find all queued prints
        queued_cells = self.worksheet.findall("Queued")
        queued_set = set()
        for cell in queued_cells:
            queued_set.add(cell.row)
        # Find all prints that are for the given printer type
        printer_cells = self.worksheet.findall(printer_type)
        printer_set = set()
        for cell in printer_cells:
            printer_set.add(cell.row)
        # Find intersection, set of valid queued prints for correct printer
        valid_set = queued_set & printer_set
        return sorted(list(valid_set))[0]  # Lowest value is first in queue
        # TODO - This method does not account for anything but which print was added first

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
        return filename


if __name__ == "__main__":
    import shutil
    from tkinter import filedialog
    from tkinter import *
    root = Tk()

    queue = QueueInterface()
    print("Connected to queue")

    # Next queued print search test
    printer_type = ""
    while printer_type == "":
        print("Please enter number for printer type."
              "\n1: Prusa"
              "\n2: Ultimaker")
        printers = {"1": "Prusa",
                    "2": "Ultimaker"}
        try:
            printer_type = printers[input(">> ")]
        except KeyError:
            print("Invalid input, please choose a number from those shown.")
            continue

    try:
        print(f"Searching for next queued {printer_type} print...")
        print_id = queue.get_next_print(printer_type)
        if print_id == 0:
            print("No print found")
            exit(0)
        print(f"{printer_type} print found, downloading...")
        print_filename = queue.download_file(print_id)  # Download file to local directory
        root.filename = filedialog.asksaveasfilename(title="Save as...", initialfile=print_filename, initialdir="/",
                                                     filetypes=(("gcode files", "*.gcode"), ("all files", "*.*")))
        shutil.move(print_filename, root.filename)  # Move file from local directory to user's chosen directory

        print(f"Downloaded to {root.filename}")
    except ConnectionError:  # Internet connection failed
        print("Connection error")
        exit(0)

    # Print lookup test
    print(f"Print ID 4 status: {queue.get_status(4)}")
    print(f"Print ID 5 status: {queue.get_status(5)}")
