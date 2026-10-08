import http.server, socketserver, os

class PWAHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/companion' or self.path == '/stay4s_companion_pwa.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open('/mnt/usb4/stay4s_companion_pwa.html', 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args):
        pass

os.chdir('/mnt/usb4')
httpd = socketserver.TCPServer(('0.0.0.0', 8200), PWAHandler)
print('Stay4S Companion PWA on port 8200')
httpd.serve_forever()