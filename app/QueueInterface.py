import base64
import io
import logging
from email.mime.text import MIMEText

logging.basicConfig(filename='QueueInterface.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

import mysql.connector as mariadb
import yaml
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials
from requests.exceptions import ConnectionError

with open('config.yml') as yaml_config:
    config = yaml.safe_load(yaml_config)
    logging.debug(config)


class QueueInterface:
    """Interface for the MariaDB print database"""

    def __init__(self):
        # Initialise the database and Google Drive connection
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/gmail.send']
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name('serviceaccount.json', self.scope)
        self.service = build('drive', 'v3', credentials=self.credentials)
        self.mail_service = build('gmail', 'v1', credentials=self.credentials)

        self.database = mariadb.connect(
            host=config['queue']['server']['host'],
            user=config['queue']['server']['user'],
            passwd=config['queue']['server']['password'],
            database=config['queue']['server']['database']
        )

    def __del__(self):
        # Close the database connection on close
        self.database.close()

    def create_email_message(self, to, subject, text):
        message = MIMEText(text)
        message['to'] = to
        message['from'] = config['email']['address']
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    def send_email(self, message):
        message_id = self.mail_service.users().messages().send(userId="me", body=message).execute()
        logging.debug(f"Email sent: {message_id}")

    def send_complete_email(self, print_id):
        details = self.get_details(print_id)
        subject = f"{config['email']['name']} 3D Print ID#{print_id} Complete"
        text = f"""
Your print ID#{print_id} with filename "{details[3]}" has successfully completed.

Please come and collect it from us as soon as possible!

Best regards,
{config['email']['signature']}
"""
        to = details[1]
        message = self.create_email_message(to, subject, text)
        self.send_email(message)

    def send_failed_email(self, print_id):
        details = self.get_details(print_id)
        subject = f"{config['email']['name']} 3D Print ID#{print_id} Failed"
        text = f"""
Your print ID#{print_id} with filename "{details[3]}" has failed.

Please come and talk to us so we can sort things out.

Best regards,
{config['email']['signature']}
"""
        to = details[1]
        message = self.create_email_message(to, subject, text)
        self.send_email(message)

    def get_valid_printers(self):
        """Retrieve a list of valid printer types

        Returns
        -------
        set
            Set of valid printer types from database
        """
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
        logging.debug(f"Printer types: {printer_types}")
        return printer_types

    def get_details(self, print_id):
        """Retrieve database row based on ID

        Parameters
        ----------
        print_id: int
            The ID of the desired print

        Returns
        -------
        dict
            Follows structure of database
        """
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
        logging.debug(result)
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
        logging.debug(result)
        if result is not None:
            return result[0]
        else:
            return None

    def update_status(self, print_id, new_status):
        self.database.commit()
        logging.debug(f"Updating ID {print_id} status to {new_status}")
        cursor = self.database.cursor()
        query = (
            "UPDATE `prints` "
            f"SET `print status` = '{new_status}' "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        self.database.commit()
        cursor.close()

    def mark_running(self, print_id, printer_id):
        self.database.commit()

        logging.debug(f"Updating ID {print_id} start time")
        cursor = self.database.cursor()
        query = (
            "UPDATE `prints` "
            f"SET `start time` = CURRENT_TIMESTAMP, `assigned printer` = {printer_id}, `print status` = 'Running' "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        self.database.commit()

        cursor.close()

    def mark_failed(self, print_id):
        self.database.commit()

        logging.debug(f"Updating ID {print_id} finish time")
        cursor = self.database.cursor()
        query = (
            "UPDATE `prints` "
            f"SET `finish time` = CURRENT_TIMESTAMP, `print status` = 'Failed' "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        self.database.commit()

        cursor.close()

    def mark_complete(self, print_id):
        self.database.commit()

        logging.debug(f"Updating ID {print_id} finish time")
        cursor = self.database.cursor()
        query = (
            "UPDATE `prints` "
            f"SET `finish time` = CURRENT_TIMESTAMP, `print status` = 'Complete' "
            f"WHERE `id` = {print_id}"
        )
        cursor.execute(query)
        self.database.commit()

        cursor.close()

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
        logging.debug(result)
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
        logging.debug(result)
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
            logging.debug(f"Downloading {filename}, status {status}")
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
        logging.debug(result)
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
        else:
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
    print(f"Print ID#1: {queue.get_details(1)}")
    print(f"Print ID#2: {queue.get_details(2)}")

    # Test emails TODO not working - authentication issues?
    # queue.send_complete_email(1)
    # queue.send_failed_email(1)
