from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    # Запускаем основного бота
    subprocess.run(["python", "-m", "support_bot"])
