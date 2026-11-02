import tempfile
import unittest
from pathlib import Path
import server.persistence as persistence_module

class PersistenceTests(unittest.TestCase):
    def test_save_and_load_board(self):
        original_dir = persistence_module.DATA_DIR
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence_module.DATA_DIR = Path(temp_dir)
            try:
                manager = persistence_module.PersistenceManager()
                board = [{"type": "draw", "sequence": 1, "data": {"tool": "pen"}}]
                self.assertTrue(manager.save_board("roomA", board))
                self.assertEqual(manager.load_board("roomA"), board)
                self.assertIsNone(manager.load_board("missing"))
            finally:
                persistence_module.DATA_DIR = original_dir

if __name__ == "__main__":
    unittest.main()
