# CollabBoard – Testing Report

## Test environment

Automated tests were executed in the development container using the Python interpreter available there. A graphical desktop and a second physical LAN computer were not available for this test run.

## Automated test results

Command:

```bash
python -m unittest discover -s tests -v
```

Result: **6 tests passed**.

| Test | Result | Coverage |
|---|---|---|
| Protocol newline JSON round-trip | PASS | UTF-8 JSON framing and decoding |
| Protocol rejects missing message type | PASS | Invalid outbound message validation |
| Canvas draw / undo / redo / clear | PASS | Server-side history and monotonic sequence |
| Persistence save / load | PASS | JSON board saved and restored using a temporary test directory |
| Local TCP server integration | PASS | Three clients join; chat and draw broadcast; late joiner receives board snapshot; server-coordinated undo/redo/clear snapshots; client disconnect without stopping server |
| Server validation integration | PASS | Duplicate username and unknown room are rejected with errors |

## Static checks

- Python source compilation (`compileall`): passed after integration.
- Python module imports and GUI startup on a desktop: not executed in this headless environment.
- Full GUI interaction: not executed.

## Manual tests still required

These require running the application on computers with a graphical desktop and, for LAN validation, at least two physical computers on the same network.

| Scenario | Status |
|---|---|
| Launch Tkinter login and workspace | NOT RUN |
| Drawing tools, color and brush-size visual behavior | NOT RUN |
| Simultaneous drawing from multiple physical clients | NOT RUN |
| Live chat and participant UI updates | NOT RUN |
| Save and restore through GUI | NOT RUN |
| Undo / redo through GUI | NOT RUN |
| Reconnect after restarting server or Wi-Fi | NOT RUN |
| Invalid username, room code and server address UI | NOT RUN |
| Internet-disconnected, LAN-connected operation | NOT RUN |
| Windows firewall and cross-computer routing | NOT RUN |

## Limitations identified

- The automated TCP integration test uses loopback (`127.0.0.1`), not two physical LAN computers.
- The default room is created automatically. The server protocol supports room creation, but the current login UI only exposes the default room workflow.
- The eraser paints using the white canvas background color; it is not a true object-selective eraser.
- The drawing model stores completed strokes/shapes as events; it does not transmit every mouse movement as a live streaming stroke.

Do not interpret the automated test result as proof that physical LAN or all GUI workflows have passed.
