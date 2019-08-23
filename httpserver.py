import base64
import http.server
import threading
from http.server import SimpleHTTPRequestHandler
from string import Template

global key


def exec_interval(func, secs):
    def wrapper():
        exec_interval(func, secs)
        func()
    timer = threading.Timer(secs, wrapper)
    timer.start()


def update_instances():
    ips = ["192.168.1.237:80"]
    apikeys = ["5CA2250EE4244EC98833D363A79C970F"]
    subs = {'ips': ips, 'apikeys': apikeys}

    with open("index.js.template", 'r') as template:
        source = Template(template.read())
    result = source.substitute(subs)
    with open("web/index.js", 'w') as output:
        output.write(result)


class AuthHandler(SimpleHTTPRequestHandler):
    """ Main class to present webpages and authentication. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="web", **kwargs)

    def do_HEAD(self):
        print("send header")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        print("send header")
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        global key
        ''' Present frontpage with user authentication. '''
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
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, AuthHandler)
    sa = httpd.socket.getsockname()
    print("Serving HTTP on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()


if __name__ == '__main__':
    update_instances()
    exec_interval(update_instances, 3600)
    username = "iforge"
    password = "testingpassword"
    key = base64.b64encode(f"{username}:{password}".encode())
    run()
