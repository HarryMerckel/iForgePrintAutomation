import base64
import http.server
import threading
from http.server import SimpleHTTPRequestHandler
from string import Template

import yaml

try:
    import QueueInterface
except ImportError:
    from app import QueueInterface

global key

with open('config.yml') as yaml_config:
    config = yaml.safe_load(yaml_config)


def exec_interval(func, secs):
    """ Execute function repeatedly at given interval. Note: Not accurate! """
    def wrapper():
        exec_interval(func, secs)
        func()
    timer = threading.Timer(secs, wrapper)
    timer.start()


def update_instances():
    ips = []
    apikeys = []

    # Get printer details from database
    queue = QueueInterface.QueueInterface()
    printer_details = queue.get_all_printer_details()
    for printer in printer_details:
        if printer[4] is not None:
            ips.append(printer[3]+":80")
            apikeys.append(printer[4])

    subs = {'ips': ips, 'apikeys': apikeys}

    # Substitute placeholders for values and write hosted file
    with open("index.js.template", 'r') as template:
        source = Template(template.read())
    result = source.substitute(subs)
    with open("web/index.js", 'w') as output:
        output.write(result)


class AuthHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="web", **kwargs)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        global key
        if self.headers.get('Authorization') is None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received'.encode())
            pass
        elif self.headers.get('Authorization') == f"Basic {key.decode('utf-8')}":
            SimpleHTTPRequestHandler.do_GET(self)
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.get('Authorization').encode())
            self.wfile.write('not authenticated'.encode())
            pass


def run(port=8000):
    # Host web server
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, AuthHandler)
    sa = httpd.socket.getsockname()
    print("Serving HTTP on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()


if __name__ == '__main__':
    # Initial js file creation
    update_instances()
    # 1 hour between major js file updates - still requires user to refresh page on client side
    exec_interval(update_instances, config["web"]["update_interval"])
    # Set up authentication and start server
    username = config["web"]["username"]
    password = config["web"]["password"]
    key = base64.b64encode(f"{username}:{password}".encode())
    run(config["web"]["port"])
