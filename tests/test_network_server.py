
import socket
import json

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind(("127.0.0.1", 5000))

server.listen(5)

print("Test server running on port 5000")

while True:

    conn, address = server.accept()

    print("Client connected:", address)

    buffer = b""

    while True:

        data = conn.recv(4096)

        if not data:
            break

        buffer += data

        while b"\n" in buffer:

            line, buffer = buffer.split(b"\n", 1)

            if not line.strip():
                continue

            message = json.loads(
                line.decode("utf-8")
            )

            print("Received:", message)

            response = {
                "type": "JOIN_ACK",
                "status": "success"
            }

            conn.sendall(
                (
                    json.dumps(response) + "\n"
                ).encode("utf-8")
            )

    conn.close()
