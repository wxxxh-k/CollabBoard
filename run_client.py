"""Launcher for the CollabBoard client (also the entry point for the .exe build).

Run from source:   python run_client.py
Build the .exe:    pyinstaller --onefile --windowed --name CollabBoardClient --paths . run_client.py
"""
from client.main import CollabBoardApp

if __name__ == "__main__":
    CollabBoardApp()
