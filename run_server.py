"""Launcher for the CollabBoard server (also the entry point for the .exe build).

Run from source:   python run_server.py
Build the .exe:    pyinstaller --onefile --name CollabBoardServer --paths . run_server.py
"""
from server.server import CollabBoardServer

if __name__ == "__main__":
    server = CollabBoardServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
