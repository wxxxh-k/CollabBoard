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


## Participant identity colors

Each participant is assigned a distinct color by the server when joining a room. The participant list displays the username, color swatch, and hex value. Normal drawing tools and chat sender labels use that assigned color; eraser strokes remain white so erasing continues to work. Colors are allocated consistently for all clients in the room while users are connected. The palette expands automatically for larger rooms so active participants continue to receive distinct colors.

## Personal user colors

Each participant chooses a personal color on the login screen before joining a room.
The selected color is shared by the server and shown consistently to everyone in that
room. Participants can change their color at any time using **Choose Color** in the
whiteboard toolbar; the participant list, chat identity color, and future drawings
update for all connected clients. Existing drawings keep the color they had when made.\n\n### Participant color assignment\n\nThe login screen does not ask for a color. Each participant chooses a preferred color from the whiteboard toolbar. Preferences may be identical; the server assigns a unique actual drawing color per room. The participant list displays the actual assigned color. Changing a preference sends `set_user_color`; the server reallocates a free color and broadcasts `user_color_changed` plus an updated participant list. Drawing messages are colored by the server-assigned color, not by a client-supplied color.\n

## Viewer-relative participant colors

Participants can choose the same preferred color. Each client reserves that
color for its own user and assigns alternate display colors to other users whose
preferences collide. These display assignments are local to each viewer; the
server preserves everyone's original preferred color. The participant list, chat,
live drawings, and restored board use the same viewer-relative mapping.

Run tests with `python -m unittest discover -s tests -v`.

## Responsive desktop layout

The client window now opens at a size that fits the available display and can be resized or maximized. The board/sidebar divider is draggable. The participant list has its own scrollbar, so additional users do not push the chat composer off-screen. The participant area is height-bounded while chat receives the remaining sidebar space. The drawing toolbar is vertically scrollable on shorter displays.


## Messaging: group chat and private chat

Every room has a **Group Chat** (the default conversation when you join). Everyone in
the room sends to it and receives from it (`chat` event, room broadcast).

To talk privately, **click a participant's name** in the Participants panel. The chat
header switches to that person ("Private · only you and Name", with a blue accent line
and a back arrow). Use the back arrow, or the **Group Chat** row at the top of the
participants list, to return. Each conversation keeps its own history and unsent draft
for the session. A new private message shows an unread badge on that person's row, a
banner in the chat (click it to open), and "Show chat · N new" if the sidebar is hidden.

Protocol (newline-delimited JSON, framing unchanged):

| Event | Direction | Fields |
|---|---|---|
| `chat` | client → server | `message` |
| `chat` | server → whole room | `scope:"group"`, `client_id`, `username`, `message`, `ts`, colors |
| `private_message` | client → server | `to_client_id`, `message` |
| `private_message` | server → recipient **and** sender only | `message_id`, `from_client_id`, `from_username`, `to_client_id`, `to_username`, `message`, `ts` |
| `private_message_failed` | server → sender only | `to_client_id`, `text`, `reason` |
| `participant_left` | server → room | `client_id`, `username` (username is new) |

The server takes the sender from the authenticated connection (it cannot be spoofed),
looks the recipient up by **client id inside the sender's own room only** (other rooms,
unknown ids, yourself, empty or oversized text and departed users are rejected with
`private_message_failed`), and never broadcasts private messages.

## Whiteboard navigation

- **Zoom:** mouse wheel (at the cursor), `+` / `-`, or the zoom buttons; click the percentage to reset to 100%.
- **Fit to window:** the fit button or `0`. The board refits automatically on window resize until you zoom or pan.
- **Pan:** Hand tool, hold **Space** and drag, middle/right mouse drag, or Shift + wheel.
- **Undo / Redo:** `Ctrl+Z` / `Ctrl+Y` (when the board has focus) or the top-bar buttons.
- Drawings are stored in *world* coordinates on a 1920 × 1080 page, so they are identical for every participant at any zoom, pan or window size.

## Window resizing

The workspace window is freely resizable (minimum 760 × 500). The whiteboard takes all
spare space. Below 900 px wide the sidebar hides automatically (toggle it with the header
button); the tool rail and participant list scroll when space is short.
