
import sys
import os
import time

# Add project root to Python import path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, PROJECT_ROOT)

from client.network import NetworkClient


client = NetworkClient()

connected = client.connect(
    "127.0.0.1",
    5000
)

if connected:

    client.send_message({
        "type": "JOIN",
        "username": "Rahul",
        "room_id": "ROOM101"
    })

    time.sleep(1)

    response = client.get_message()

    print("Server response:", response)

    client.disconnect()
