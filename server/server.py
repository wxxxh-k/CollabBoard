import socket
import threading
from common.config import HOST, PORT, MAX_CLIENTS, DEFAULT_ROOM
from server.session_manager import SessionManager
from server.canvas_manager import CanvasManager
from server.persistence import PersistenceManager
from server.client_handler import ClientHandler

class CollabBoardServer:
    def __init__(self, host=HOST, port=PORT):
        self.host, self.port = host, int(port)
        self.server_socket = None
        self.running = False
        self.clients = set()
        self.clients_lock = threading.Lock()
        self.session_manager = SessionManager()
        self.canvas_manager = CanvasManager(self.session_manager)
        self.persistence_manager = PersistenceManager()
        self.session_manager.create_room("Default Room", room_id=DEFAULT_ROOM)

    def start(self):
        if self.running:
            return
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CLIENTS)
            self.server_socket.settimeout(1.0)
            self.running = True
            print("=" * 42)
            print("COLLABBOARD SERVER")
            print(f"Listening on {self.host}:{self.port}")
            print(f"Default room code: {DEFAULT_ROOM}")
            print("Press Ctrl+C to stop.")
            print("=" * 42)
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                except socket.timeout:
                    self.cleanup_clients()
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
                with self.clients_lock:
                    active = {h for h in self.clients if h.is_alive()}
                    self.clients = active
                    if len(self.clients) >= MAX_CLIENTS:
                        client_socket.close()
                        print("[REJECTED] Maximum clients reached")
                        continue
                    handler = ClientHandler(client_socket, address, self.session_manager,
                                            self.canvas_manager, self.persistence_manager)
                    self.clients.add(handler)
                handler.start()
        except OSError as error:
            if self.running or self.server_socket:
                print("[SERVER ERROR]", error)
            raise
        finally:
            self.stop()

    def cleanup_clients(self):
        with self.clients_lock:
            self.clients = {handler for handler in self.clients if handler.is_alive()}

    def stop(self):
        self.running = False
        sock, self.server_socket = self.server_socket, None
        if sock:
            try:
                sock.close()
            except OSError:
                pass
        with self.clients_lock:
            handlers = list(self.clients)
            self.clients.clear()
        for handler in handlers:
            handler.running = False
            try:
                handler.client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                handler.client_socket.close()
            except OSError:
                pass
        print("CollabBoard server stopped.")

if __name__ == "__main__":
    server = CollabBoardServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
