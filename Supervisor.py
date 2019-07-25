import QueueInterface
import octorest
from requests.exceptions import ConnectionError


class Printer:
    def __init__(self, name=None, printer_type=None, url=None, apikey=None):
        self.name = name
        self.type = printer_type
        self.url = url
        self.apikey = apikey

        self.state = None
        self.client = None

        self.start_client()
        self.update_state()

    def start_client(self):
        try:
            self.client = octorest.OctoRest(url="http://" + self.url, apikey=self.apikey)
            return 1
        except ConnectionError:
            self.state = "Offline"
            return 0
        except TypeError:
            self.state = "Invalid"
            return 0

    def update_state(self, force=False):
        if self.state == "Invalid":
            return 0
        if self.state == "Offline":
            if not force or (force and not self.start_client()):
                return 0
        self.state = self.get_full_status()['state']['text']

    def get_full_status(self):
        if self.state not in ("Offline", "Invalid"):
            return self.client.printer()
        else:
            return


class Supervisor:
    def __init__(self):
        self.queue = QueueInterface.QueueInterface()
        self.printers = {}
        self.refresh_printers()

    def refresh_printers(self):
        printer_details = self.queue.get_all_printer_details()
        for printer in printer_details:
            if printer[4] is not None:
                if printer[0] not in self.printers:
                    self.printers[printer[0]] = Printer(printer[1], printer[2], printer[3], printer[4])
                else:
                    self.printers[printer[0]].update_state(True)

    def update_printer_states(self):
        for printer in self.printers:
            self.printers[printer].update_state()

    def check_printer_states(self):
        for printer_id in self.printers:
            printer = self.printers[printer_id]
            if printer.state == "Operational":
                try:
                    finished_print_id = printer.client.files("iForge_Auto", True)['children'][0]['name'].split('.')[0]
                    self.queue.update_status(finished_print_id, "Complete")
                    printer.client.delete(f"local/iForge_Auto/{finished_print_id}.gcode")
                except IndexError:
                    pass
                next_print_id = self.queue.get_next_print(printer.type)
                if next_print_id != 0:
                    next_print = self.queue.download_file(next_print_id, str(next_print_id)+".gcode")
                    printer.client.upload(next_print, path="iForge_Auto", select=True, print=True)
                    print(f"Now printing {next_print}")


if __name__ == "__main__":
    import time
    supervisor = Supervisor()
    print(supervisor.printers)
    while True:
        supervisor.update_printer_states()
        for printer in supervisor.printers:
            print(f"Printer: '{supervisor.printers[printer].name}'  "
                  f"Type: '{supervisor.printers[printer].type}'  "
                  f"State: '{supervisor.printers[printer].state}'")
        supervisor.check_printer_states()
        time.sleep(30)
