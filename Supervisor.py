import QueueInterface
import octorest


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

    def start_client(self):
        try:
            self.client = octorest.OctoRest(url="http://" + self.url, apikey=self.apikey)
            self.update_state()
            return 1
        except ConnectionError:
            self.state = "Offline"
            return 0
        except TypeError:
            self.state = "Invalid"
            return 0

    def update_state(self):
        printer_flags = self.client.printer()['state']['flags']
        print(printer_flags)

    def get_status(self):
        return self.client.printer()


class Supervisor:
    def __init__(self):
        self.queue = QueueInterface.QueueInterface()
        self.printers = {}
        self.refresh_printers()

    def refresh_printers(self):
        printer_details = self.queue.get_all_printer_details()
        for printer in printer_details:
            if printer[4] is not None:
                self.printers[printer[0]] = Printer(printer[1], printer[2], printer[3], printer[4])


if __name__ == "__main__":
    supervisor = Supervisor()
    print(supervisor.printers)
    print(supervisor.printers[1].state)
    print(supervisor.printers[1].client.printer())
