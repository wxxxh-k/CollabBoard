# CollabBoard

A real-time, multi-user collaborative whiteboard for a Local Area Network (LAN).
One computer runs the **Server**; any number of other computers run the **Client**
to join a room, draw together, and chat. Everything works offline over plain TCP
sockets — no internet connection or third-party service is needed.

Written in Python 3 using only the standard library (Tkinter for the GUI, `socket`
and `threading` for networking).

---

## Deliverables

| Deliverable | Where / how |
|---|---|
| **Server application** (standalone executable) | `CollabBoardServer.exe`, built from `run_server.py` (see [Building the executables](#building-the-executables)) |
| **Client application** (standalone executable) | `CollabBoardClient.exe`, built from `run_client.py` |
| **Source code** (commented) | `server/`, `client/`, `common/`, `run_server.py`, `run_client.py` |

---

## Features

- **Rooms** – create a room (generated Room ID, optional password) or join an existing one; a built-in `default` room is always available.
- **Roles** – Host, Assistant and Student, enforced by the server.
- **Drawing tools** – pen, eraser, line, rectangle, circle and text, with colour and brush-size control.
- **Real-time sync** – strokes, shapes and text appear instantly for everyone in the room; late joiners receive the full current board.
- **Live cursors** – see where every participant is pointing, labelled with their name.
- **Undo / Redo / Clear** – coordinated by the server so all clients stay consistent.
- **Save / Restore** – the board can be saved to and restored from the server's `data/` folder.
- **Chat** – room-wide group chat plus private one-to-one messages (click a participant's name).
- **Participant list** – live list with colour identity, roles and join/leave notifications.
- **Zoom & pan** – mouse-wheel zoom, fit-to-window, hand tool / Space-drag panning. Drawings use fixed board coordinates (1920 × 1080), so they look identical for everyone at any zoom or window size.
- **Reconnect** – one-click reconnect from the workspace header after a connection loss.

### Roles

| Role | Permissions |
|---|---|
| **Host** | Draw, undo/redo, save/restore, clear the board, and assign Assistant/Student roles (right-click a participant). Only one Host per room — the room's creator. |
| **Assistant** | Draw and edit (undo/redo). Cannot clear the board or manage roles. |
| **Student** | Read-only view. Drawing, undo/redo, clear and restore are rejected by the server. |

---

## Requirements

**To run the executables:** a Windows PC on the same LAN — nothing else to install.

**To run from source:**
- Python 3.10 or newer
- Tkinter (bundled with the python.org Windows installer; on Debian/Ubuntu: `sudo apt install python3-tk`)
- No `pip` packages are required (see `requirements.txt`).

---

## Quick start

### 1. Start the server (one computer on the LAN)

Using the executable: double-click **`CollabBoardServer.exe`**.
From source (run in the project root):

```bash
python run_server.py
```

The console shows `Listening on 0.0.0.0:5000`. Keep this window open while the
session is running; press `Ctrl+C` to stop it.

Find the server computer's LAN IPv4 address:
- **Windows:** `ipconfig` → *IPv4 Address* of the active Wi-Fi/Ethernet adapter
- **Linux/macOS:** `ip addr` or `ifconfig`

Allow inbound TCP port **5000** through the server's firewall:

```powershell
# Windows PowerShell (Administrator)
New-NetFirewallRule -DisplayName "CollabBoard TCP 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```
```bash
# Linux (UFW)
sudo ufw allow 5000/tcp
```

### 2. Start the client (every participant's computer)

Using the executable: double-click **`CollabBoardClient.exe`**.
From source:

```bash
python run_client.py
```

On the login screen enter:

| Field | Value |
|---|---|
| Username | Any name; must be unique within the room (case-insensitive) |
| Select Role | Host, Assistant or Student |
| Server IP Address | The server's LAN IPv4 address (`127.0.0.1` if the server is on the same PC) |
| Port Number | `5000` |
| Room ID | The room to join (leave empty when creating a room) |
| Room Password | The room's password, if it has one |

Then choose:

- **CREATE A ROOM** – creates a new room and makes you its Host (Host role only). The generated Room ID is shown in the workspace header; click **Copy ID** to share it.
- **JOIN ROOM** – joins an existing room with its Room ID (and password if set). It never creates a room.

> **Try it on one computer:** start the server, then launch two clients using
> `127.0.0.1`. Create a room in the first, and join it from the second using the Room ID.
> The `default` room can also be joined with no password.

---

## Using the whiteboard

| Action | How |
|---|---|
| Draw | Select a tool in the left toolbar, choose colour and brush size, then drag on the board |
| Change your colour | **Choose Color** in the toolbar (shown to everyone in the room) |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` or the top-bar buttons |
| Clear board | Clear button (Host only) |
| Save / Restore board | Save/Restore controls — stored on the server |
| Zoom | Mouse wheel, `+` / `-`, or the zoom buttons; click the percentage to reset to 100% |
| Fit to window | Fit button or `0` |
| Pan | Hand tool, hold `Space` and drag, middle/right-drag, or `Shift` + wheel |
| Group chat | Type in the chat box and press Enter |
| Private chat | Click a participant's name in the Participants panel; use the back arrow to return |
| Assign roles | Host: right-click a participant → Assistant / Student |
| Hide/show sidebar | Header button (auto-hides on narrow windows) |
| Reconnect | **Reconnect** button in the header after a connection loss |

---

## Building the executables

The executables are built with [PyInstaller](https://pyinstaller.org). Build on
Windows to produce `.exe` files (PyInstaller builds for the OS it runs on). From the
project root:

```bash
pip install pyinstaller

pyinstaller --onefile --name CollabBoardServer --paths . run_server.py
pyinstaller --onefile --windowed --name CollabBoardClient --paths . run_client.py
```

The finished files appear in `dist/`. Both are standalone — the target machine
does not need Python installed. When running as an executable, the `data/` folder is
created next to the `.exe` file.

---

## Project structure

```text
CollabBoard/
├── run_server.py          # Server launcher / executable entry point
├── run_client.py          # Client launcher / executable entry point
├── requirements.txt
├── README.md
├── common/                # Code shared by client and server
│   ├── config.py          #   Host, port, limits, default room
│   ├── protocol.py        #   Newline-delimited JSON message framing
│   └── user_colors.py     #   Participant colour utilities
├── server/
│   ├── server.py          #   TCP listener, accepts clients (one thread each)
│   ├── client_handler.py  #   Per-connection message handling
│   ├── session_manager.py #   Rooms, passwords, roles, members
│   ├── canvas_manager.py  #   Shared board state, undo/redo/clear
│   └── persistence.py     #   Save/load boards as JSON in data/
├── client/
│   ├── main.py            #   Application controller
│   ├── login.py           #   Login / create / join screen
│   ├── main_window.py     #   Workspace window
│   ├── whiteboard.py      #   Drawing canvas, live cursors
│   ├── viewport.py        #   Zoom / pan coordinate transforms
│   ├── toolbar.py         #   Tool, colour and size controls
│   ├── chat.py            #   Group and private chat UI
│   ├── conversations.py   #   Chat conversation history
│   ├── participants.py    #   Participant list and role menu
│   ├── network.py         #   TCP connection to the server
│   ├── sync_manager.py    #   Applies server events to local state
│   ├── state_manager.py   #   Local board state
│   ├── widgets.py, theme.py  # Shared UI widgets and styling
├── data/                  # Saved boards and the client's username history
└── documentation/         # Additional technical notes
```

---

## How it works

- **Architecture:** a central server with many clients over TCP. The server is the
  single source of truth for each room's board, so undo, redo, clear and late-join
  snapshots are consistent for everyone.
- **Protocol:** newline-delimited JSON messages (`common/protocol.py`), e.g.
  `join_room`, `draw`, `chat`, `private_message`, `cursor_move`, `undo`, `save_board`.
  The maximum message size is 1 MB.
- **Concurrency:** the server runs one thread per connected client; shared state is
  protected by locks. The client keeps networking on background threads and updates
  the Tkinter UI through a queue.
- **Security:** room passwords are stored only as salted PBKDF2-SHA256 hashes. The
  server derives each sender's identity and role from the connection, so clients
  cannot impersonate others or bypass role restrictions. Private messages are only
  ever delivered to the sender and recipient in the same room.

## Configuration

Defaults are in `common/config.py`:

| Setting | Default | Meaning |
|---|---|---|
| `HOST` | `0.0.0.0` | Listen on all network interfaces |
| `PORT` | `5000` | TCP port (use the same value in every client and firewall rule) |
| `MAX_CLIENTS` | `50` | Maximum simultaneous connections |
| `DEFAULT_ROOM` | `default` | Room created automatically at server start |

## Troubleshooting

| Problem | Fix |
|---|---|
| Client cannot connect | Check the server is running, the IP is the server's LAN IPv4 (not `127.0.0.1` from another PC), the port matches, and the firewall allows TCP 5000. Both PCs must be on the same network. |
| "Room does not exist" | Check the Room ID (case-insensitive). Rooms exist in server memory and are lost when the server restarts. |
| "Incorrect password" / "Password required" | Enter the password the Host set when creating the room. |
| "Username already in use" | Choose a different username in that room. |
| "This room already has a Host" | Join as Assistant or Student. |
| `No module named tkinter` (source only) | Install Tkinter (`sudo apt install python3-tk` on Debian/Ubuntu). |

## Notes

- Rooms live in server memory and last until the server is stopped; saved boards in `data/` persist.
- This application is intended for a **trusted LAN**. Do not expose port 5000 to the public internet.
