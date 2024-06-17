#waits on certain port and automatically executes training process after HMPL mutual learning phase
#more about Human-Machine Peer Learning (HMPL) in Frontiers in Education article by Hromada & Kim (2023)
#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import subprocess,ssl,re

path_regex=re.compile("^/[a-z]+::[a-z]+-[a-z]+$")

ssl_dir="/etc/letsencrypt/live/pesel.lesen.digital/"

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def disconnect(self):
        #self.finish()
        self.connection.close()

    def _handle(self):
        try:
            self.log_message("command: %s", self.path)
            if path_regex.match(self.path):
                matches=self.path.split('::')
                subprocess.run("./train.sh "+matches[1]+" "+matches[0][1:],shell=True)
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write('{"ok": true}\r\n'.encode())
                self.disconnect()


        finally:
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write('{"wtf":"mess with the best, end like the rest"}\r\n'.encode())
            self.disconnect()

if __name__ == "__main__":
    #httpd=HTTPServer(("pesel.lesen.digital",8080), CORSRequestHandler)
    httpd=HTTPServer(("pesel.lesen.digital",8080), Handler)
    httpd.socket = ssl.wrap_socket (httpd.socket, keyfile=ssl_dir+"privkey.pem", certfile=ssl_dir+'fullchain.pem', server_side=True)
    httpd.serve_forever()
