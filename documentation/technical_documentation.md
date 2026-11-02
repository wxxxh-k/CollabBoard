# CollabBoard – Technical Documentation

## 1. Architecture

CollabBoard uses a client/server architecture. Every desktop client runs a Tkinter GUI and opens a TCP connection to one central server. The server owns room membership, drawing event ordering, and the persistent canvas history.

```text
Tkinter GUI
  ├── LoginWindow
  ├── Whiteboard / ChatPanel / ParticipantsPanel
  └── MainWindow event queue
          |
          v
      SyncManager <----> StateManager
          |
          v
   NetworkClient (TCP socket)
          |
          v
     CollabBoardServer
       ├── ClientHandler (one thread per TCP client)
       ├── SessionManager (rooms and participants)
       ├── CanvasManager (ordered canvas events / undo / redo)
       └── PersistenceManager (JSON board files)
```

## 2. TCP/IP communication

The server creates an IPv4 TCP socket and binds to `0.0.0.0:5000` by default. Binding to `0.0.0.0` makes the service reachable through the server computer's LAN interfaces, subject to firewall rules. TCP provides a reliable ordered byte stream, but it does not preserve application message boundaries.

## 3. Message framing and JSON protocol

Each application message is a JSON object encoded as UTF-8 and terminated by a newline (`\\n`). The sender uses `sendall`. Both endpoints buffer received bytes until a complete newline-terminated message is available. This handles partial reads and multiple messages arriving in one TCP read.

Common message shapes:

| Type | Direction | Important fields |
|---|---|---|
| `join_room` | Client → server | `username`, `room_id`, optional `password` |
| `joined_room` | Server → client | `client_id`, `username`, `room_id` |
| `draw` | Both directions | `data`; server event also has `sequence`, `user_id` |
| `chat` | Both directions | `message`; server adds `username`, `client_id` |
| `participants` | Server → clients | `participants` array |
| `participant_joined` | Server → clients | `client_id`, `username` |
| `participant_left` | Server → clients | `client_id` |
| `board_snapshot` | Server → client(s) | `board`, `last_sequence` |
| `clear`, `undo`, `redo` | Client → server | no extra fields |
| `save_board`, `load_board` | Client → server | no extra fields |
| `save_result` | Server → client | `success` |
| `error` | Server → client | `message` |
| `ping`, `pong` | Both directions | optional keepalive |

The canonical names are lowercase. `common/protocol.py` provides shared encoding, decoding and message-size validation.

## 4. Threading and Tkinter safety

- The server accept loop accepts TCP connections.
- Each accepted connection is handled by a daemon `ClientHandler` thread.
- A per-handler send lock prevents concurrent writes from interleaving JSON messages.
- `SessionManager` and `CanvasManager` use locks to protect shared room and board state.
- The client receiver thread reads and decodes socket messages into a thread-safe queue.
- `SyncManager` consumes that queue and converts protocol events into application events.
- `MainWindow` polls its GUI event queue using Tkinter `after()`. Tkinter widgets are only changed from the GUI thread.

## 5. Canvas synchronization

The server assigns a monotonically increasing sequence number to every accepted drawing event. A newly joined client receives a snapshot containing the current board and `last_sequence`. Later drawing events must arrive in sequence. Duplicate or stale events are ignored; a sequence gap requests a fresh snapshot.

Undo removes the latest retained drawing operation belonging to the requesting user. Redo restores that user's most recently undone operation as a new server event. Clear and restore also advance the room sequence and broadcast a complete snapshot. Snapshot replacement avoids trying to replay stale events after destructive operations.

## 6. Save and restore

The server-side `PersistenceManager` writes each room's board to JSON under `data/`. Saving uses a temporary file followed by an atomic replace. Loading replaces the room's in-memory board and broadcasts a new snapshot.

## 7. LAN operation

The server binds to all IPv4 interfaces, but clients should connect using the server computer's private LAN IPv4 address. All participants must be able to reach the server on the configured TCP port. No cloud service, DNS service, or internet connection is used by the application.\n\n### Participant color assignment\n\nThe login screen does not ask for a color. Each participant chooses a preferred color from the whiteboard toolbar. Preferences may be identical; the server assigns a unique actual drawing color per room. The participant list displays the actual assigned color. Changing a preference sends `set_user_color`; the server reallocates a free color and broadcasts `user_color_changed` plus an updated participant list. Drawing messages are colored by the server-assigned color, not by a client-supplied color.\n