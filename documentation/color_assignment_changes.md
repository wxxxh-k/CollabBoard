# Viewer-relative color assignment

## Behavior

Each participant stores only their preferred color. The server does not globally
replace duplicate preferences. Every client builds its own display-color map:

- The current viewer's preferred color is always reserved for that viewer.
- Other participants keep their preferred colors when those colors are available
  in that viewer's display.
- If another participant's preference collides, that participant is shown in
  the next available palette color.
- The mapping is recalculated when participants join, leave, or change preferences.

For example, if Alice and Bob both choose blue, Alice sees Alice as blue and Bob
as red; Bob sees Bob as blue and Alice as red. A third participant choosing green
remains green in both views.

## Implementation

- `common/user_colors.py`: `build_viewer_color_map` implements deterministic
  viewer-relative allocation and supports palette exhaustion.
- `server/session_manager.py`: stores each participant's requested/preferred color
  without enforcing a room-wide unique color.
- `server/client_handler.py`: publishes preferred colors and author IDs with
  drawing/chat/participant events.
- `client/main_window.py`: builds a local display map and applies it to the
  participant list, chat, live drawing events, and board snapshots.
- `client/whiteboard.py`: supports a display-color override when rendering a
  drawing authored by another participant.

The server-side preferred color remains unchanged when a viewer assigns a local
display fallback to another participant. The mapping is presentation-only.
