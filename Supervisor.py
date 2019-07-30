import QueueInterface
import octorest
from requests.exceptions import ConnectionError


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
        except ConnectionError:
            self.state = "Offline"
            return False
        except TypeError:
            self.state = "Invalid"
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
            True if printer online, false if not
        """
        if self.state == "Invalid":
            return False
        if self.state == "Offline":
            if not force or (force and not self.start_client()):
                return False
        try:
            printer_status = self.get_full_status()
        except ConnectionError:
            self.state = "Offline"
            return False
        if printer_status['state']['text'] == "Operational" \
                and printer_status['temperature']['bed']['actual'] > 40 \
                and printer_status['temperature']['bed']['target'] == 0:
            self.state = "Cooldown"
        else:
            self.state = printer_status['state']['text']
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
        if self.state not in ("Offline", "Invalid"):
            try:
                return self.client.printer()
            except ConnectionError:
                return {'state': {'text': "Offline"}}  # Emulate the format of the octoprint output
        else:
            return {'state': {'text': self.state}}

    def get_temperatures(self):
        """Get temperature data from octoprint

        Returns
        -------
        dict
            Contains temperature data, varies by printer. Keys include 'bed'
        """
        return self.get_full_status()['temperature']


class Supervisor:
    """Interface to monitor and control a large number of printers"""
    def __init__(self):
        #Connect to queue and populate array of printers
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

    def update_printer_states(self):
        """Just update the state of all active printers"""
        for printer in self.printers:
            self.printers[printer].update_state()

    def check_printer_states(self):
        """Check all active printers, start next print job if last one complete"""
        for printer_id in self.printers:
            printer = self.printers[printer_id]
            if printer.state == "Operational":
                try:
                    # Check whether there was a print that's done - if so, mark as complete and remove from printer
                    finished_print_id = printer.client.files("iForge_Auto", True)['children'][0]['name'].split('.')[0]
                    self.queue.update_status(finished_print_id, "Complete")
                    printer.client.delete(f"local/iForge_Auto/{finished_print_id}.gcode")
                except IndexError:
                    pass
                # Get ID of next print for current printer type
                next_print_id = self.queue.get_next_print(printer.type)
                if next_print_id != 0:
                    next_print = self.queue.download_file(next_print_id, str(next_print_id)+".gcode")
                    # Upload next print and move to the operating folder
                    printer.client.upload(next_print)
                    printer.client.move(f"{str(next_print_id)}.gcode", f"iForge_Auto/{str(next_print_id)}.gcode")
                    printer.client.select(f"iForge_Auto/{str(next_print_id)}.gcode", print=True)
                    self.queue.mark_running(next_print_id)


if __name__ == "__main__":
    import time
    supervisor = Supervisor()
    print(supervisor.printers)
    while True:
        # Check printers and start new prints every 30 seconds (excluding time spent starting new prints)
        supervisor.update_printer_states()
        for printer in supervisor.printers:
            print(f"Printer: '{supervisor.printers[printer].name}'  "
                  f"Type: '{supervisor.printers[printer].type}'  "
                  f"State: '{supervisor.printers[printer].state}'")
        supervisor.check_printer_states()
        time.sleep(30)
