import socket
import threading

from common.config import HOST, PORT, MAX_CLIENTS

from server.session_manager import SessionManager
from server.canvas_manager import CanvasManager
from server.persistence import PersistenceManager
from server.client_handler import ClientHandler


class CollabBoardServer:

    def __init__(self):

        self.host = HOST
        self.port = PORT

        self.server_socket = None

        self.running = False

        self.clients = set()

        self.clients_lock = threading.Lock()

        # Initialize managers

        self.session_manager = SessionManager()

        self.canvas_manager = CanvasManager(
            self.session_manager
        )

        self.persistence_manager = PersistenceManager()

    # ---------------- START SERVER ----------------

    def start(self):

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.server_socket.bind(
            (self.host, self.port)
        )

        self.server_socket.listen(MAX_CLIENTS)

        self.running = True

        print("----------------------------------")
        print("       COLLABBOARD SERVER")
        print("----------------------------------")
        print(f"Server running on {self.host}:{self.port}")
        print("Waiting for clients...")
        print("----------------------------------")

        try:

            while self.running:

                client_socket, address = (
                    self.server_socket.accept()
                )

                with self.clients_lock:

                    if len(self.clients) >= MAX_CLIENTS:

                        client_socket.close()

                        print("[REJECTED] Maximum clients reached")

                        continue

                    handler = ClientHandler(
                        client_socket,
                        address,
                        self.session_manager,
                        self.canvas_manager,
                        self.persistence_manager
                    )

                    self.clients.add(handler)

                handler.start()

                print(
                    f"[CLIENT COUNT] {len(self.clients)}"
                )

                threading.Thread(
                    target=self.cleanup_clients,
                    daemon=True
                ).start()

        except OSError as error:

            if self.running:
                print("[SERVER ERROR]", error)

        finally:

            self.stop()

    # ---------------- CLEANUP ----------------

    def cleanup_clients(self):

        with self.clients_lock:

            self.clients = {
                handler
                for handler in self.clients
                if handler.is_alive()
            }

    # ---------------- STOP SERVER ----------------

    def stop(self):

        if not self.running and self.server_socket is None:
            return

        print("\nStopping CollabBoard server...")

        self.running = False

        if self.server_socket:

            try:
                self.server_socket.close()
            except OSError:
                pass

            self.server_socket = None

        with self.clients_lock:

            handlers = list(self.clients)

            self.clients.clear()

        for handler in handlers:

            handler.running = False

            try:
                handler.client_socket.shutdown(
                    socket.SHUT_RDWR
                )
            except OSError:
                pass

            try:
                handler.client_socket.close()
            except OSError:
                pass

        print("Server stopped.")


if __name__ == "__main__":

    server = CollabBoardServer()

    try:

        server.start()

    except KeyboardInterrupt:

        server.stop()