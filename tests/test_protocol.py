import unittest
from common.protocol import encode_message, decode_message

class ProtocolTests(unittest.TestCase):
    def test_newline_json_round_trip(self):
        message = {"type": "chat", "message": "hello"}
        encoded = encode_message(message)
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(decode_message(encoded[:-1]), message)

    def test_rejects_invalid_message(self):
        with self.assertRaises(ValueError):
            encode_message({"message": "missing type"})

    def test_private_message_types_are_registered_and_framed(self):
        from common.protocol import MESSAGE_TYPES
        self.assertIn("private_message", MESSAGE_TYPES)
        self.assertIn("private_message_failed", MESSAGE_TYPES)
        message = {"type": "private_message", "to_client_id": "abc", "message": "héllo \u2714"}
        encoded = encode_message(message)
        self.assertEqual(encoded.count(b"\n"), 1)  # one frame, newline-terminated
        self.assertEqual(decode_message(encoded[:-1]), message)

if __name__ == "__main__":
    unittest.main()
