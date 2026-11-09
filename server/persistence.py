import json
import os
import sys

from pathlib import Path


# When packaged as an .exe, keep the data folder next to the executable
# (the bundled source files live in a temporary folder that is deleted on exit).
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"


class PersistenceManager:

    def __init__(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save_board(self, room_id, board):

        file_path = DATA_DIR / f"{room_id}.json"

        temporary_path = DATA_DIR / f"{room_id}.tmp"

        try:

            with open(temporary_path, "w", encoding="utf-8") as file:

                json.dump(
                    {
                        "room_id": room_id,
                        "board": board
                    },
                    file,
                    indent=4
                )

                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, file_path)

            return True

        except (OSError, TypeError, ValueError) as error:

            print("Save error:", error)

            return False

    def load_board(self, room_id):

        file_path = DATA_DIR / f"{room_id}.json"

        try:

            with open(file_path, "r", encoding="utf-8") as file:

                saved_data = json.load(file)

            board = saved_data.get("board")

            if not isinstance(board, list):
                return None

            return board

        except FileNotFoundError:

            return None

        except (OSError, json.JSONDecodeError) as error:

            print("Load error:", error)

            return None