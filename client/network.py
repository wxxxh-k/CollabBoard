import queue
import socket
import threading
from common.protocol import encode_message, decode_message, DISCONNECTED, MAX_MESSAGE_SIZE

class NetworkClient:
    """Thread-safe newline-delimited JSON TCP client.

    Receiving happens on a reader thread and sending on a writer thread, so the
    Tkinter main thread never blocks on socket I/O. send_message() only encodes
    the message and queues it.
    """
    def __init__(self):
        self.sock = None
        self.connected = False
        self.send_lock = threading.Lock()
        self.message_queue = queue.Queue()
        self.receiver_thread = None
        self.sender_thread = None
        self.outbox = None
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
                self.outbox = queue.Queue()
                self.sender_thread = threading.Thread(
                    target=self._send_loop, args=(sock, self.outbox), daemon=True)
                self.sender_thread.start()
                self.receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.receiver_thread.start()
                return True
            except (OSError, ValueError) as error:
                self.connected = False
                print("Connection failed:", error)
                return False

    def send_message(self, message):
        """Queue a message for the writer thread. Never blocks on the network."""
        if not self.connected or not self.sock or self.outbox is None:
            return False
        try:
            payload = encode_message(message)
        except (ValueError, TypeError) as error:
            print("Send error:", error)
            return False
        with self.send_lock:
            if not self.connected or self.outbox is None:
                return False
            self.outbox.put(payload)
        return True

    def _send_loop(self, sock, outbox):
        """Writer thread: drains the outbox in order until a None sentinel."""
        while True:
            payload = outbox.get()
            if payload is None:
                return
            try:
                sock.sendall(payload)
            except OSError as error:
                if self.connected and self.sock is sock:
                    print("Send error:", error)
                    self.disconnect()
                return

    def receive_messages(self):
        buffer = bytearray()
        sock = self.sock
        outbox = self.outbox
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
            if outbox is not None:
                outbox.put(None)  # stop the writer thread of this connection
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
        with self.send_lock:
            self.connected = False
            sock, self.sock = self.sock, None
            outbox, self.outbox = self.outbox, None
        sender = self.sender_thread
        if outbox is not None:
            outbox.put(None)  # flush anything already queued (e.g. leave_room), then stop
        if sender and sender is not threading.current_thread():
            sender.join(timeout=1.0)
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
