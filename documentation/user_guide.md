# CollabBoard – User Guide

## Start a collaboration session

1. Start the server on one computer with `python -m server.server`.
2. Find that computer's private IPv4 address using `ipconfig` (Windows) or `ip addr` (Linux).
3. Ensure inbound TCP port 5000 is allowed by the server computer's firewall.
4. Start the client on each participating computer with `python -m client.main`.
5. Enter a unique username, the server's LAN IPv4 address, port `5000`, and room code `default`.
6. Leave the room password blank and select **JOIN WHITEBOARD**.

## Drawing

- Select Pen, Eraser, Line, Rectangle, Circle or Text.
- Choose a color and brush size.
- Draw on the white canvas. Completed strokes and shapes are sent to the server and broadcast to other room members.
- Eraser draws in the canvas background color.

## Chat and participants

- Type a message in Group Chat and press Enter or Send.
- The Participants panel shows the current room membership.
- Join and leave notifications appear in chat.

## Canvas actions

- **Undo** removes your latest retained drawing operation.
- **Redo** restores your latest undone operation.
- **Clear Canvas** clears the shared room canvas for everyone.
- **Save** stores the current board on the server.
- **Restore** loads the most recently saved board and synchronizes it to everyone.

## Connection loss

Use **Reconnect** in the workspace header after the server or network becomes available again. If reconnect fails, check the server terminal, IP address, port, firewall and room code.

## Exit

Close the workspace window to disconnect. The server remains running for other clients.\n\n### Participant color assignment\n\nThe login screen does not ask for a color. Each participant chooses a preferred color from the whiteboard toolbar. Preferences may be identical; the server assigns a unique actual drawing color per room. The participant list displays the actual assigned color. Changing a preference sends `set_user_color`; the server reallocates a free color and broadcasts `user_color_changed` plus an updated participant list. Drawing messages are colored by the server-assigned color, not by a client-supplied color.\n