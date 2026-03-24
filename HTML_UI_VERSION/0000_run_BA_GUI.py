import http.server
import socketserver
import webbrowser
import os
import errno

# Try to start the server on `START_PORT`, but fall back to the next available port
START_PORT = 8080
ENTRY = "0001_HTML_UI.html"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

def run_server(start_port, max_tries=100):
    socketserver.TCPServer.allow_reuse_address = True

    for port in range(start_port, start_port + max_tries):
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                url = f"http://localhost:{port}/{ENTRY}"
                print(f"Serving at {url}")
                print("Press Ctrl+C to stop.")
                webbrowser.open(url)
                httpd.serve_forever()
                return
        except OSError as e:
            if getattr(e, 'errno', None) in (errno.EADDRINUSE,):
                # Port is in use — try the next one
                continue
            raise

if __name__ == '__main__':
    run_server(START_PORT)
