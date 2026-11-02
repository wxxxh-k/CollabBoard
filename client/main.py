import queue
import threading
import tkinter as tk
from tkinter import messagebox
from client.login import LoginWindow
from client.main_window import MainWindow
from client.network import NetworkClient
from client.state_manager import StateManager
from client.sync_manager import SyncManager

class CollabBoardApp:
    def __init__(self):
        self.root = tk.Tk()
        self.network = NetworkClient()
        self.state = StateManager()
        self.main_window = None
        self.pending_events = queue.Queue()
        self.ui_results = queue.Queue()
        self.connection = None
        self.sync = SyncManager(self.network, self.state, self.handle_network_event)
        self.login = LoginWindow(self.root, self.join_room)
        self.root.after(50, self.process_ui_results)
        self.root.mainloop()

    def handle_network_event(self, event):
        if self.main_window:
            self.main_window.enqueue_event(event)
        else:
            self.pending_events.put(event)

    def join_room(self, username, host, port, room, password):
        self.login.status.config(text="Connecting to server...")
        self.connection = (username, host, port, room, password)
        threading.Thread(target=self._connect_worker, args=(self.connection,), daemon=True).start()

    def _connect_worker(self, connection):
        username, host, port, room, password = connection
        connected = self.sync.join_room(host, port, room, username, password)
        self.ui_results.put(("join_result", connected, username, room))

    def reconnect(self):
        if not self.connection:
            return
        self.sync.disconnect()
        username, host, port, room, password = self.connection
        self.state.load_snapshot({"events": [], "last_sequence": 0})
        threading.Thread(target=self._reconnect_worker, args=(self.connection,), daemon=True).start()

    def _reconnect_worker(self, connection):
        username, host, port, room, password = connection
        connected = self.sync.join_room(host, port, room, username, password)
        self.ui_results.put(("reconnect_result", connected))

    def process_ui_results(self):
        try:
            while True:
                result = self.ui_results.get_nowait()
                if result[0] == "join_result":
                    _, connected, username, room = result
                    if not connected:
                        self.login.status.config(text="Connection failed. Check IP, port and firewall.")
                        messagebox.showerror("Connection failed", "Could not connect to the server.")
                        continue
                    for widget in self.root.winfo_children():
                        widget.destroy()
                    self.main_window = MainWindow(
                        self.root, username, room, self.sync,
                        on_close=self.close, on_reconnect=self.reconnect
                    )
                    while not self.pending_events.empty():
                        self.main_window.enqueue_event(self.pending_events.get_nowait())
                elif result[0] == "reconnect_result":
                    if result[1]:
                        self.main_window.whiteboard.update_status("Reconnected; synchronizing canvas...")
                    else:
                        self.main_window.whiteboard.update_status("Reconnect failed. Check server and LAN.")
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(50, self.process_ui_results)

    def close(self):
        self.sync.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    CollabBoardApp()
