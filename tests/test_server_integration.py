import json
import socket
import threading
import time
import unittest
from server.server import CollabBoardServer

def send(sock, message):
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))

def receive(sock):
    data = bytearray()
    deadline = time.time() + 3
    while time.time() < deadline:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("server closed connection")
        if chunk == b"\n":
            return json.loads(data.decode("utf-8"))
        data.extend(chunk)
    raise TimeoutError("No server response")

class ServerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.server = CollabBoardServer(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        while (self.server.server_socket is None or self.server.server_socket.getsockname()[1] == 0) and time.time() < deadline:
            time.sleep(0.01)
        self.port = self.server.server_socket.getsockname()[1]

    def connect_and_join(self, username):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        sock.settimeout(3)
        send(sock, {"type": "join_room", "room_id": "default", "username": username})
        messages = [receive(sock) for _ in range(4)]
        self.assertEqual(messages[0]["type"], "joined_room")
        self.assertEqual(messages[1]["type"], "board_snapshot")
        return sock, messages

    def test_join_chat_draw_and_disconnect(self):
        first, _ = self.connect_and_join("Alice")
        second, _ = self.connect_and_join("Bob")
        # Drain the participant-joined and refreshed participant-list events.
        receive(first)
        receive(first)
        send(first, {"type": "chat", "message": "hello LAN"})
        chat_first = receive(first)
        chat_second = receive(second)
        self.assertEqual(chat_first["type"], "chat")
        self.assertEqual(chat_second["message"], "hello LAN")

        send(first, {"type": "draw", "data": {"tool": "pen", "points": [[2, 3], [5, 8]]}})
        draw_first = receive(first)
        draw_second = receive(second)
        self.assertEqual(draw_first["type"], "draw")
        self.assertEqual(draw_second["sequence"], 1)

        # A late joiner receives the authoritative current board and sequence.
        third, join_messages = self.connect_and_join("Charlie")
        self.assertEqual(len(join_messages[1]["board"]), 1)
        self.assertEqual(join_messages[1]["last_sequence"], 1)
        receive(first)
        receive(first)
        receive(second)
        receive(second)

        # Undo and redo are coordinated by the server and broadcast as snapshots.
        send(first, {"type": "undo"})
        undo_first, undo_second, undo_third = receive(first), receive(second), receive(third)
        self.assertEqual(undo_first["type"], "board_snapshot")
        self.assertEqual(undo_first["board"], [])
        self.assertEqual(undo_first["last_sequence"], 2)

        send(first, {"type": "redo"})
        redo_first, redo_second, redo_third = receive(first), receive(second), receive(third)
        self.assertEqual(len(redo_first["board"]), 1)
        self.assertEqual(redo_first["last_sequence"], 3)

        send(first, {"type": "clear"})
        clear_first, clear_second, clear_third = receive(first), receive(second), receive(third)
        self.assertEqual(clear_first["type"], "board_snapshot")
        self.assertEqual(clear_first["board"], [])
        self.assertEqual(clear_first["last_sequence"], 4)

        first.close()
        time.sleep(0.1)
        self.assertTrue(self.server.running)
        second.close()
        third.close()

    def test_reject_duplicate_username_and_unknown_room(self):
        first, _ = self.connect_and_join("SameName")
        duplicate = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        duplicate.settimeout(3)
        send(duplicate, {"type": "join_room", "room_id": "default", "username": "samename"})
        error = receive(duplicate)
        self.assertEqual(error["type"], "error")
        self.assertIn("already in use", error["message"])

        unknown = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        unknown.settimeout(3)
        send(unknown, {"type": "join_room", "room_id": "not-a-room", "username": "Other"})
        error = receive(unknown)
        self.assertEqual(error["type"], "error")
        self.assertIn("does not exist", error["message"])
        first.close()
        duplicate.close()
        unknown.close()

    def tearDown(self):
        self.server.stop()
        if self.thread.is_alive():
            self.thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()
