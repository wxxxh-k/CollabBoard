import queue
import socket
import threading
from common.protocol import encode_message, decode_message, DISCONNECTED, MAX_MESSAGE_SIZE

class NetworkClient:
    """Thread-safe newline-delimited JSON TCP client."""
    def __init__(self):
        self.sock = None
        self.connected = False
        self.send_lock = threading.Lock()
        self.message_queue = queue.Queue()
        self.receiver_thread = None
        self.connection_lock = threading.Lock()

    def connect(self, host, port):
        with self.connection_lock:
            if self.connected:
                return True
            try:
                sock = socket.create_connection((host, int(port)), timeout=5)
                sock.settimeout(None)
                self.sock = sock
                self.connected = True
                self.receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.receiver_thread.start()
                return True
            except (OSError, ValueError) as error:
                self.connected = False
                print("Connection failed:", error)
                return False

    def send_message(self, message):
        if not self.connected or not self.sock:
            return False
        try:
            payload = encode_message(message)
            with self.send_lock:
                if not self.connected:
                    return False
                self.sock.sendall(payload)
            return True
        except (OSError, ValueError, TypeError) as error:
            print("Send error:", error)
            self.disconnect()
            return False

    def receive_messages(self):
        buffer = bytearray()
        sock = self.sock
        try:
            while self.connected and sock:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                if len(buffer) > MAX_MESSAGE_SIZE and b"\n" not in buffer:
                    raise ValueError("Incoming message exceeds maximum size.")
                while b"\n" in buffer:
                    line, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    if not line.strip():
                        continue
                    try:
                        self.message_queue.put(decode_message(line))
                    except (ValueError, UnicodeDecodeError):
                        self.message_queue.put({"type": "error", "message": "Received invalid server message."})
        except (OSError, ValueError) as error:
            if self.connected:
                print("Receive error:", error)
        finally:
            self.connected = False
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
            if self.sock is sock:
                self.sock = None
            self.message_queue.put({"type": DISCONNECTED})

    def get_message(self):
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None

    def disconnect(self):
        self.connected = False
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
