import QueueInterface
import octorest
from requests.exceptions import ConnectionError


class Printer:
    def __init__(self, name=None, printer_type=None, url=None, apikey=None, state=None, current_print=None):
        self.name = name
        self.type = printer_type
        self.state = state
        self.current_print = current_print
        self.client = None
        self.url = url
        self.apikey = apikey

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


if __name__ == "__main__":
    import time
    supervisor = Supervisor()
    print(supervisor.printers)
    print(supervisor.printers[1].state)
    print(supervisor.printers[1].get_full_status())
    while True:
        supervisor.printers[1].update_state()
        print(supervisor.printers[1].state)
        time.sleep(5)
