
import socket
import threading
import queue

from common.protocol import (
    encode_message,
    decode_message,
    DISCONNECTED
)


class NetworkClient:
    """
    Handles TCP communication between
    a CollabBoard client and the server.
    """

    def __init__(self):
        self.sock = None
        self.connected = False

        self.send_lock = threading.Lock()
        self.message_queue = queue.Queue()

        self.receiver_thread = None
        self.connection_lock = threading.Lock()

    # ----------------------------------
    # CONNECT TO SERVER
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
    # SEND MESSAGE
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
    # RECEIVE MESSAGES
    # ----------------------------------

    def receive_messages(self):

        buffer = b""

        try:
            while self.connected:

                chunk = self.sock.recv(4096)

                if not chunk:
                    break

                buffer += chunk

                while b"\n" in buffer:

                    line, buffer = buffer.split(b"\n", 1)

                    if not line.strip():
                        continue

                    try:
                        message = decode_message(line)

                        if isinstance(message, dict):
                            self.message_queue.put(message)
                        else:
                            print("Invalid message format received")

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
    # GET RECEIVED MESSAGE
    # ----------------------------------

    def get_message(self):

        try:
            return self.message_queue.get_nowait()

        except queue.Empty:
            return None

    # ----------------------------------
    # DISCONNECT
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
