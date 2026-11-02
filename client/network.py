
import socket
import threading
import queue

from common.protocol import (
    encode_message,
    DISCONNECTED
)


class NetworkClient:
    """
    Handles TCP communication between
    a CollabBoard client and the server.
    """

    def __init__(self):

        # TCP socket
        self.sock = None

        # Connection status
        self.connected = False

        # Thread safety for sending
        self.send_lock = threading.Lock()

        # Queue for received messages
        self.message_queue = queue.Queue()

        # Receiver thread
        self.receiver_thread = None

        # Prevent multiple receiver threads
        self.connection_lock = threading.Lock()

    # ----------------------------------
    # 1. CONNECT TO SERVER
    # ----------------------------------

    def connect(self, host, port):

        with self.connection_lock:

            if self.connected:
                return True

            try:

                self.sock = socket.create_connection(
                    (host, port),
                    timeout=5
                )

                self.sock.settimeout(None)

                self.connected = True

                self.receiver_thread = threading.Thread(
                    target=self.receive_messages,
                    daemon=True
                )

                self.receiver_thread.start()

                print("Connected to CollabBoard server!")

                return True

            except OSError as error:

                print("Connection failed:", error)

                self.connected = False

                return False

    # ----------------------------------
    # 2. SEND MESSAGE TO SERVER
    # ----------------------------------

    def send_message(self, message):

        if not self.connected:
            return False

        try:

            encoded_message = encode_message(message)

            with self.send_lock:

                if not self.connected:
                    return False

                self.sock.sendall(encoded_message)

            return True

        except OSError as error:

            print("Send error:", error)

            self.disconnect()

            return False

    # ----------------------------------
    # 3. RECEIVE MESSAGES
    # ----------------------------------

    def receive_messages(self):

        buffer = b""

        try:

            while self.connected:

                chunk = self.sock.recv(4096)

                if not chunk:
                    break

                buffer += chunk

                # Extract complete JSON messages
                while b"\n" in buffer:

                    line, buffer = buffer.split(
                        b"\n", 1
                    )

                    if not line.strip():
                        continue

                    try:

                        import json

                        message = json.loads(
                            line.decode("utf-8")
                        )

                        self.message_queue.put(message)

                    except (ValueError, UnicodeDecodeError):

                        print("Invalid message received")

        except OSError as error:

            if self.connected:
                print("Receive error:", error)

        finally:

            self.connected = False

            self.message_queue.put({
                "type": DISCONNECTED
            })

    # ----------------------------------
    # 4. GET RECEIVED MESSAGE
    # ----------------------------------

    def get_message(self):

        try:

            return self.message_queue.get_nowait()

        except queue.Empty:

            return None

    # ----------------------------------
    # 5. DISCONNECT FROM SERVER
    # ----------------------------------

    def disconnect(self):

        self.connected = False

        if self.sock:

            try:
                self.sock.shutdown(socket.SHUT_RDWR)

            except OSError:
                pass

            try:
                self.sock.close()

            except OSError:
                pass

        print("Disconnected from server.")
