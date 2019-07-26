import io

import mysql.connector as mariadb
import yaml
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
from requests.exceptions import ConnectionError

with open('QueueInterface.conf') as yaml_config:
    config = yaml.safe_load(yaml_config)


class QueueInterface:
    def __init__(self):
        # Connect and authenticate with Google drive API
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name('serviceaccount.json', self.scope)
        self.service = build('drive', 'v3', credentials=self.credentials)

        self.database = mariadb.connect(
            host=config['server']['host'],
            user=config['server']['user'],
            passwd=config['server']['password'],
            database=config['server']['database']
        )

    def __del__(self):
        self.database.close()

    def get_valid_printers(self):
        self.database.commit()
        printer_types = set()
        cursor = self.database.cursor()
        query = (
            "SELECT `type` "
            "FROM `printers`"
        )
        cursor.execute(query)
        for printer_type in cursor:
            printer_types.add(printer_type[0])
        cursor.close()
        return printer_types

    def get_details(self, print_id):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "SELECT * "
            "FROM `prints` "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        return result

    def get_status(self, print_id):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "SELECT `print status` "
            "FROM `prints` "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        if result is not None:
            return result[0]
        else:
            return None

    def update_status(self, print_id, new_status):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "UPDATE `prints` "
            f"SET `print status` = '{new_status}' "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        self.database.commit()
        cursor.close()

    def mark_running(self, print_id):
        self.update_status(print_id, "Running")

    def get_next_print(self, printer_type):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "SELECT `id` "
            "FROM `prints` "
            "WHERE `print status` = 'Queued' "
            f"AND `printer type` = '{printer_type}' "
            "ORDER BY `added` ASC "
            "LIMIT 1"
        )
        cursor.execute(query)
        result = cursor.fetchone()
        if result is not None:
            print_id = result[0]
            cursor.close()
            return print_id
        else:
            cursor.close()
            return 0
        # TODO - This method does not account for anything but which print was added first

    def download_file(self, print_id, filename_override=None):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "SELECT `drive file id`, `gcode filename` "
            "FROM `prints` "
            f"WHERE `id` = '{print_id}'"
        )
        cursor.execute(query)
        result = cursor.fetchone()
        if result is not None:
            file_id = result[0]
            if filename_override is not None:
                filename = filename_override
            else:
                filename = result[1]
        else:
            return
        # Get file from Google Drive
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(filename, mode='wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return filename

    def get_all_printer_details(self):
        self.database.commit()
        cursor = self.database.cursor()
        query = (
            "SELECT `id`, `name`, `type`, `ip address`, `api key` "
            "FROM printers"
        )
        cursor.execute(query)
        result = cursor.fetchall()
        return result


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
        print("Please enter number for printer type.")
        printers = sorted(list(queue.get_valid_printers()))
        for i in range(len(printers)):
            print(f"{i+1}: {printers[i]}")
        try:
            # Get user choice of printer type
            printer_type = printers[int(input(">> ")) - 1]
        except KeyError:
            print("Invalid input, please choose a number from those shown.")
            continue

    try:
        # Retrieve and download gcode file, if available
        print(f"Searching for next queued {printer_type} print...")
        print_id = queue.get_next_print(printer_type)
        if print_id == 0:
            print("No print found")
            exit(0)
        print(f"{printer_type} print found, downloading...")
        print_filename = queue.download_file(print_id)  # Download file to local directory
        try:
            root.filename = filedialog.asksaveasfilename(title="Save as...", initialfile=print_filename, initialdir="/",
                                                         filetypes=(("gcode files", "*.gcode"), ("all files", "*.*")))
            shutil.move(print_filename, root.filename)  # Move file from local directory to user's chosen directory
            print(f"Downloaded to {root.filename}")
        except FileNotFoundError:
            print("Cancelling...")
            # TODO: Remove downloaded file
    except ConnectionError:  # Internet connection failed
        print("Connection error")
        exit(0)

    # Print lookup test
    print(f"Print ID 1: {queue.get_details(1)}")
    print(f"Print ID 2: {queue.get_details(2)}")
