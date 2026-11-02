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

if __name__ == "__main__":
    unittest.main()
