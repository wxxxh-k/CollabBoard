# Integration Change Log

## Modified files

| File | Reason |
|---|---|
| `client/chat.py` | Resolved Git conflict markers; retained the ChatPanel-style GUI and connected it to the real send callback. |
| `client/client.py` | Replaced the obsolete local-mode startup path with a compatibility launcher for the integrated application. |
| `client/login.py` | Set the default room field to the server-created `default` room. |
| `client/main.py` | Added the application entry point, background connection attempts, queued GUI results and reconnect workflow. |
| `client/main_window.py` | Integrated the actual whiteboard, chat and participants panels; added GUI-thread event processing and reconnect control. |
| `client/network.py` | Standardized newline-delimited JSON TCP handling, send locking, receive queueing and socket cleanup. |
| `client/participants.py` | Resolved merge conflicts and retained the ParticipantsPanel interface used by MainWindow. |
| `client/state_manager.py` | Kept a thread-safe local mirror of the authoritative board and sequence number. |
| `client/sync_manager.py` | Connected network messages to canvas state, sequence validation, snapshots, chat, undo/redo and reconnect. |
| `client/toolbar.py` | Integrated the existing toolbar module with drawing, color, brush size and shared-board actions. |
| `client/whiteboard.py` | Connected drawing operations to SyncManager; added snapshot rendering and shared undo/redo/save/restore/clear actions. |
| `common/config.py` | Centralized LAN bind address, port, client limit and default room. |
| `common/protocol.py` | Implemented shared UTF-8 newline JSON encoding/decoding and message-size checks. |
| `server/canvas_manager.py` | Added monotonic sequence handling, server-side redo, and snapshots containing `last_sequence`. |
| `server/client_handler.py` | Standardized lowercase message types; integrated join, leave, draw, chat, participants, snapshots, undo/redo, clear, save/restore and validation. |
| `server/server.py` | Added configurable listener, default room creation, LAN binding, cleanup and controlled shutdown. |
| `server/session_manager.py` | Added optional fixed room IDs and per-room duplicate-username rejection. |
| `README.md` | Replaced the old UTF-16 placeholder README with setup, run and LAN instructions. |
| `requirements.txt` | Documented that no third-party Python packages are required. |

## Added files

- `client/__init__.py`: makes the client importable as a package.
- `client/main.py`: integrated GUI startup.
- `documentation/technical_documentation.md`: architecture, protocol, threading and synchronization.
- `documentation/user_guide.md`: user-facing setup and operation instructions.
- `documentation/testing_report.md`: executed tests and remaining manual checks.
- `documentation/integration_changes.md`: this change log.
- `tests/test_protocol.py`: protocol tests.
- `tests/test_canvas_manager.py`: server-side drawing history tests.
- `tests/test_server_integration.py`: real local TCP multi-client integration test.

## Removed obsolete ad-hoc test/demo scripts

- `client/test_chat.py`
- `client/test_login.py`
- `client/test_participants.py`
- `tests/test_network_client.py`
- `tests/test_network_server.py`
- `tests/test_state_manager.py`

These scripts contained standalone UI demos, a fake TCP test server, or outdated protocol calls. Their useful automated coverage was replaced with deterministic `unittest` tests under `tests/`.
