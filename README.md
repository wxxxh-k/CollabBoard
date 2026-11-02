# CollabBoard

LAN-based, real-time collaborative whiteboard built with Python, Tkinter and TCP sockets.

## Features

- Multiple TCP clients collaborate in a shared room.
- Pen, eraser, line, rectangle, circle and text tools.
- Color selection and brush-size control.
- Real-time drawing and chat broadcasting.
- Live participant list and join/leave notifications.
- Shared canvas snapshots for newly joined clients.
- Server-coordinated undo, redo and clear.
- Save and restore a room's canvas on the server.
- Newline-delimited JSON over TCP; no internet service is required.

## Requirements

- Python 3.10 or newer recommended.
- Tkinter (normally included with the Windows python.org installer; on Debian/Ubuntu install `python3-tk` if missing).
- All application dependencies are from the Python standard library.

## Project layout

```text
CollabBoard/
├── client/
│   ├── main.py
│   ├── main_window.py
│   ├── login.py
│   ├── network.py
│   ├── whiteboard.py
│   ├── toolbar.py
│   ├── chat.py
│   ├── participants.py
│   ├── sync_manager.py
│   └── state_manager.py
├── server/
│   ├── server.py
│   ├── session_manager.py
│   ├── client_handler.py
│   ├── canvas_manager.py
│   └── persistence.py
├── common/
│   ├── protocol.py
│   └── config.py
├── documentation/
├── tests/
├── requirements.txt
└── README.md
```

## Run on one computer (smoke test)

Open two terminals in the project root.

Terminal 1:

```bash
python -m server.server
```

Terminal 2:

```bash
python -m client.main
```

Open a second client in another terminal/window and use `127.0.0.1` as the server address. Both clients should use room code `default`.

## Run over a LAN (no internet required)

All computers must be connected to the same local network (same Wi-Fi router or Ethernet LAN). Internet access is not needed.

### On the server computer

1. Extract the project folder.
2. Open a terminal in the `CollabBoard` project root.
3. Start the server:

   ```bash
   python -m server.server
   ```

4. Find the server computer's LAN IPv4 address:
   - Windows: run `ipconfig` and find the IPv4 address under the active Wi-Fi or Ethernet adapter.
   - Linux: run `ip addr` and find the IPv4 address of the active LAN interface.
5. Allow inbound TCP port `5000` through the computer's firewall.

Windows PowerShell (run as Administrator):

```powershell
New-NetFirewallRule -DisplayName "CollabBoard TCP 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

Linux with UFW:

```bash
sudo ufw allow 5000/tcp
```

### On every client computer

1. Copy/extract the same project folder.
2. Open a terminal in its project root.
3. Start the client:

   ```bash
   python -m client.main
   ```

4. Enter:
   - Username: a unique name within the room.
   - Server IP: the server computer's LAN IPv4 address (not `127.0.0.1`).
   - Port: `5000`.
   - Room code: `default`.
   - Room password: leave blank for the default room.
5. Select **JOIN WHITEBOARD**.

The server terminal should show each connection. Drawing and chat should appear on all clients in the same room.

## Configuration

Default settings are in `common/config.py`:

- `HOST = "0.0.0.0"`: listen on all IPv4 interfaces.
- `PORT = 5000`: TCP listening port.
- `MAX_CLIENTS = 50`: maximum simultaneous TCP connections.
- `DEFAULT_ROOM = "default"`: room available when the server starts.

Change the port in `common/config.py` if necessary, then use the same port in each client's login screen and firewall rule.

## Run automated tests

From the project root:

```bash
python -m unittest discover -s tests -v
```

The tests exercise protocol framing, canvas history and a real local TCP server/client exchange. They do not replace a multi-computer LAN test.

## Data and privacy

Saved room boards are written under the server's `data/` directory. The server does not need an internet connection. Do not expose port 5000 to the public internet; this project is intended for a trusted LAN.

## Notes

- The built-in default room is created each time the server starts. Saved board files are stored separately by room code.
- Usernames must be unique within a room while connected.
- Reconnect is available from the workspace header after a connection loss.
- `python -m client.main` and `python -m server.server` are the supported launch commands. Run them from the project root so package imports resolve correctly.
