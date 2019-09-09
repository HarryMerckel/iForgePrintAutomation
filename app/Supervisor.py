import logging
import os

import yaml

logging.basicConfig(filename='Supervisor.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

try:
    import QueueInterface
except ImportError:
    from app import QueueInterface

import octorest
from requests.exceptions import ConnectionError

with open('config.yml') as yaml_config:
    config = yaml.safe_load(yaml_config)
    logging.debug(config)


class Printer:
    """Acts as simplified interface for the OctoREST module for each printer"""

    def __init__(self, name=None, printer_type=None, url=None, apikey=None):
        """
        Args:
            name: String
                Vanity name for the printer
            printer_type: String
                Identifier for selecting compatible prints from the queue
            url: String
                URL or IP address pointing to the octoprint instance on the network
            apikey: String
                Octoprint API key
        """
        self.name = name
        self.type = printer_type
        self.url = url
        self.apikey = apikey

        self.state = None
        self.client = None

        self.start_client()
        self.update_state()

    def start_client(self):
        """Initialise connection to the Octoprint server

        Returns
        -------
        bool
            True if connection successful, false if not
        """
        try:
            self.client = octorest.OctoRest(url="http://" + self.url, apikey=self.apikey)
            return True
        except (ConnectionError, RuntimeError) as e:
            self.state = "Octoprint Offline"
            logging.warning(f"Server {self.url} offline: {e}")
            return False
        except TypeError:
            self.state = "Invalid"
            logging.warning(f"Server {self.url} invalidly defined")
            return False

    def update_state(self, force=False):
        """Update the current state of the Octoprint instance and printer

        Parameters
        ----------
        force: bool
            If True will force attempted reconnect to offline server, which may wait for long timeout

        Returns
        -------
        bool
            True if status retrieved from octoprint, false if not
        """
        if self.state == "Invalid":
            return False
        if self.state == "Octoprint Offline":
            if not force or (force and not self.start_client()):
                return False
        printer_status = self.get_full_status()
        logging.debug(printer_status)
        self.state = printer_status['state']['text']  # Octoprint internal state string
        return True

    def get_full_status(self):
        """Retrieve the full status output from Octoprint

        See https://docs.octoprint.org/en/master/api/printer.html#retrieve-the-current-printer-state for full details

        Returns
        -------
        dict
            See above documentation
            Concatenated recreation if printer offline or invalid configuration
        """
        if self.state not in ("Octoprint Offline", "Invalid"):
            try:
                return self.client.printer()
            except ConnectionError:
                return {'state': {'text': "Octoprint Offline"}}  # Emulate the format of the octoprint output
            except RuntimeError:
                return {'state': {'text': "Printer Offline"}}
            except AttributeError:
                return {'state': {'text': "Invalid"}}
        else:
            return {'state': {'text': self.state}}

    def get_temperatures(self):
        """Get temperature data from Octoprint

        Returns
        -------
        dict
            Contains temperature data, varies by printer. Keys include 'bed' and 'e0'
        """
        return self.get_full_status()['temperature']


class Supervisor:
    """Interface to monitor and control a large number of printers"""

    def __init__(self):
        # Connect to queue and populate array of printers
        self.queue = QueueInterface.QueueInterface()
        self.printers = {}
        self.refresh_printers()

    def refresh_printers(self):
        """Refreshes the dict of printers, updating their state if they've already been registered"""
        printer_details = self.queue.get_all_printer_details()
        for printer in printer_details:
            if printer[4] is not None:
                if printer[0] not in self.printers:
                    self.printers[printer[0]] = Printer(printer[1], printer[2], printer[3], printer[4])
                else:
                    self.printers[printer[0]].update_state(True)

    def update_printer_states(self, force=False):
        """Just update the state of all active printers"""
        for printer in self.printers:
            self.printers[printer].update_state(force)

    def check_printer_states(self):
        """Check all active printers, start next print job if last one complete"""
        for printer_id in self.printers:
            printer = self.printers[printer_id]
            if printer.state == "Operational":
                try:
                    # Check whether there was a print - if so, mark as complete or failed and remove from printer
                    folder = printer.client.files(config['printers']['working_folder'], True)
                    logging.debug(folder)
                    finished_print_id = folder['children'][0]['name'].split('.')[0]
                    if folder['children'][0]['prints']['success']:
                        print(f"Print ID#{finished_print_id} on printer {printer_id} complete")
                        self.queue.mark_complete(finished_print_id, printer_id, int(folder['children'][0]['prints']['last']['printTime']), int(3 * folder['children'][0]['gcodeAnalysis']['filament']['tool0']['length']))
                        printer.client.delete(f"local/{config['printers']['working_folder']}/{finished_print_id}.gcode")
                    else:
                        print(f"Print ID#{finished_print_id} on printer {printer_id} failed")
                        self.queue.mark_failed(finished_print_id)
                        # Send gcode containing only pause to printer, allowing print to be removed before continuing
                        with open("0.gcode", "w") as pause_gcode:
                            pause_gcode.write(f"\nM117 ID#{finished_print_id} failed\nM0\nM117 Idle\n")
                        printer.client.upload("0.gcode")
                        printer.client.select("0.gcode", print=True)
                        printer.client.delete(f"local/{config['printers']['working_folder']}/{finished_print_id}.gcode")
                        continue
                except IndexError:
                    pass
                # Get ID of next print for current printer type
                next_print_id = self.queue.get_next_print(printer.type)
                if next_print_id != 0:
                    next_print = self.queue.download_file(next_print_id, str(next_print_id) + ".gcode")
                    # Inject pause at end of print
                    with open(next_print, 'a') as print_gcode:
                        print_gcode.write("\nM0; Pause to allow user to confirm completion or failure\n")
                    # Upload next print and move to the operating folder
                    printer.client.upload(next_print)
                    printer.client.move(f"{str(next_print_id)}.gcode",
                                        f"{config['printers']['working_folder']}/{str(next_print_id)}.gcode")
                    # Select and start print
                    print(f"Starting print ID#{next_print_id} on printer {printer_id}")
                    printer.client.select(f"{config['printers']['working_folder']}/{str(next_print_id)}.gcode",
                                          print=True)
                    # Mark as running
                    self.queue.mark_running(next_print_id, printer_id)
                    os.remove(f"{str(next_print_id)}.gcode")


if __name__ == "__main__":
    import time

    supervisor = Supervisor()
    logging.debug(supervisor.printers)
    while True:
        # Check printers and start new prints every set time interval (excluding time spent starting new prints etc.)
        supervisor.update_printer_states(True)
        for printer in supervisor.printers:
            print(f"Printer: '{supervisor.printers[printer].name}'  "
                  f"Type: '{supervisor.printers[printer].type}'  "
                  f"State: '{supervisor.printers[printer].state}'")
        supervisor.check_printer_states()
        time.sleep(config['supervisor']['update_interval'])
