# Private chat, group chat, responsive UI and whiteboard navigation

## Files changed
| File | Change |
|---|---|
| `common/protocol.py` | Registered `private_message`, `private_message_failed`; `MAX_CHAT_LENGTH`. Framing unchanged. |
| `server/client_handler.py` | `handle_private_message` (validation, same-room lookup by client id, delivery + sender echo, failure event); group `chat` now carries `scope` and `ts`; `participant_left` carries `username`. |
| `server/session_manager.py` | `get_client(room_id, client_id)` – lookup restricted to one room. |
| `client/network.py` | Writer thread + outbox queue: sends never block the Tk thread; pending messages (e.g. `leave_room`) are flushed on disconnect. |
| `client/sync_manager.py` | `send_private_message`. |
| `client/chat.py` | Only hooks: header text swap, back button, thin private accent, new-message banner, disable-able composer, per-conversation drafts. Message bubbles, colors, fonts, spacing, scrolling untouched. |
| `client/participants.py` | Rewritten: clickable names, Group Chat row, unread badges, active highlight, hover, collapse, bounded + scrollable list. |
| `client/main_window.py` | Resizable window (`resizable(True, True)` – the login screen had disabled it), responsive sidebar (auto-hide, width clamp), conversation controller, toolbar-independent layout. Participant list now shows only people who are online (former drawing authors still take part in the color map). |
| `client/whiteboard.py`, `client/toolbar.py` | Rewritten: modern top bar / tool rail / status bar, world-coordinate drawing, zoom, pan, fit. Public API used by `main_window` is unchanged. |
| New: `client/conversations.py`, `client/viewport.py`, `client/theme.py`, `client/widgets.py` | Conversation state, zoom/pan math, palette, vector icon buttons + tooltips. |
| New tests | `tests/test_private_chat.py`, `test_client_network.py`, `test_conversations.py`, `test_viewport.py` (+ protocol test). |

## Behavior notes
- Clear Canvas now asks for confirmation (it clears the board for everyone).
- A click without dragging with Line/Rectangle/Circle no longer publishes an empty shape.
- Shapes send only start/end points; pen strokes send all points (rounded to 0.1).
- Private chats are keyed by client id. If someone reconnects they get a new id, so it is a new conversation; the old one stays readable while it has unread messages or is open.
- Message history lives for the active session only (not persisted).
