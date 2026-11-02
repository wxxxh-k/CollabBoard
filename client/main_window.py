import queue
import tkinter as tk
from tkinter import messagebox
from client.whiteboard import Whiteboard
from client.chat import ChatPanel
from client.participants import ParticipantsPanel

class MainWindow:
    def __init__(self, root, username, room, sync_manager, on_close=None, on_reconnect=None):
        self.root, self.username, self.room = root, username, room
        self.sync = sync_manager
        self.on_close = on_close
        self.on_reconnect = on_reconnect
        self.events = queue.Queue()
        self.root.title(f"CollabBoard - {room}")
        self.root.geometry("1300x780")
        self.root.minsize(1000, 620)
        self.root.configure(bg="#111827")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(50, self.process_events)

    def _build(self):
        header = tk.Frame(self.root, bg="#1F2937", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🎨 CollabBoard", font=("Arial", 18, "bold"),
                 fg="white", bg="#1F2937").pack(side="left", padx=18)
        tk.Label(header, text=f"Room: {self.room}", fg="#A5B4FC",
                 bg="#1F2937").pack(side="left", padx=16)
        tk.Label(header, text=f"Signed in as {self.username}", fg="#34D399",
                 bg="#1F2937").pack(side="right", padx=12)
        tk.Button(header, text="Reconnect", command=self.reconnect,
                  bg="#374151", fg="white", relief="flat").pack(side="right", padx=8)

        workspace = tk.Frame(self.root, bg="#111827")
        workspace.pack(fill="both", expand=True, padx=8, pady=8)
        sidebar = tk.Frame(workspace, bg="#111827", width=285)
        sidebar.pack(side="right", fill="y", padx=(8, 0))
        sidebar.pack_propagate(False)
        self.participants = ParticipantsPanel(sidebar, self.username)
        self.participants.configure(height=190)
        self.participants.pack_propagate(False)
        self.participants.pack(fill="x", expand=False)
        self.chat = ChatPanel(sidebar, self.username, send_callback=self.sync.send_chat)
        self.chat.pack(fill="both", expand=True, pady=(8, 0))
        self.whiteboard = Whiteboard(
            workspace,
            on_operation=self.sync.send_drawing,
            on_clear=self.sync.clear_canvas,
            on_undo=self.sync.undo,
            on_redo=self.sync.redo,
            on_save=self.sync.save_board,
            on_load=self.sync.load_board
        )
        self.whiteboard.update_status("Connected to server")

    def enqueue_event(self, event):
        self.events.put(event)

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event.get("type")
                if kind == "snapshot_loaded":
                    self.whiteboard.load_board(event.get("board", []))
                    self.whiteboard.update_status("Canvas synchronized")
                elif kind == "remote_draw":
                    self.whiteboard.apply_operation(event["event"])
                elif kind == "chat":
                    self.chat.display_message(event.get("username", "User"),
                                               event.get("message", ""))
                elif kind == "participants":
                    self.participants.update_participants(event.get("participants", []))
                elif kind == "participant_joined":
                    self.chat.display_message("CollabBoard",
                                               f'{event.get("username", "A user")} joined the room')
                elif kind == "participant_left":
                    self.chat.display_message("CollabBoard", "A participant left the room")
                elif kind == "save_result":
                    messagebox.showinfo("Save board", "Board saved on the server." if event.get("success")
                                        else "Could not save the board.")
                elif kind == "error":
                    messagebox.showerror("CollabBoard", event.get("message", "Server error"))
                elif kind == "sync_gap":
                    self.whiteboard.update_status("Resynchronizing canvas...")
                elif kind == "sync_error":
                    self.whiteboard.update_status("Synchronization error")
                    messagebox.showerror("Synchronization", event.get("message", "Unknown error"))
                elif kind == "disconnected":
                    self.whiteboard.update_status("Disconnected from server")
                    messagebox.showwarning("Connection lost", "The connection to the server was lost. Close and reconnect.")
                elif kind == "left_room":
                    self.whiteboard.update_status("Left room")
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(50, self.process_events)

    def reconnect(self):
        if self.on_reconnect:
            self.on_reconnect()

    def close(self):
        if self.on_close:
            self.on_close()
        else:
            self.sync.disconnect()
            self.root.destroy()
