# Client that sends a UDP packet to the server and waits for a response with a custom vote packet

import asyncio
import json
import os
import struct
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

HOST = "127.0.0.1"
PORT = 12345
ALPN = "udp-polling"
CA_FILE = "certs/ca.crt"
STATE_FILE = "client_state.json"

MSG_VOTE = 1
MSG_ACK = 2
ACK_STATUS_OK = 0
ACK_STATUS_ALREADY_VOTED = 1
ACK_PACKET = struct.Struct("!BIIB")

def checksum(data):
    return sum(data) % 256


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def next_sequence(client_id):
    state = load_state()
    key = str(client_id)
    return int(state.get(key, 0)) + 1


def commit_sequence(client_id, sequence):
    state = load_state()
    state[str(client_id)] = sequence
    save_state(state)

async def main():
    client_id = int(input("Enter client ID: "))
    sequence = next_sequence(client_id)
    vote_value = int(input("Enter vote (1 or 2): "))

    payload = struct.pack("!BIIB", MSG_VOTE, client_id, sequence, vote_value)
    packet = struct.pack("!BIIBB", MSG_VOTE, client_id, sequence, vote_value, checksum(payload))

    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=[ALPN],
    )
    configuration.load_verify_locations(CA_FILE)

    async with connect(
        HOST,
        PORT,
        configuration=configuration,
    ) as connection:
        reader, writer = await connection.create_stream()
        writer.write(packet)
        await writer.drain()

        print(f"Sent vote: client={client_id}, seq={sequence}, vote={vote_value}")

        response = await reader.readexactly(ACK_PACKET.size)
        msg_type, r_client_id, r_seq, status = ACK_PACKET.unpack(response)
        if msg_type != MSG_ACK:
            print("Error: invalid response type from server")
        elif status == ACK_STATUS_ALREADY_VOTED:
            print(f"Error: client {r_client_id} has already voted")
        else:
            print(f"Vote acknowledged: client={r_client_id}, seq={r_seq}")

        if (
            msg_type == MSG_ACK
            and status == ACK_STATUS_OK
            and r_client_id == client_id
            and r_seq == sequence
        ):
            commit_sequence(client_id, sequence)

        writer.close()


if __name__ == "__main__":
    asyncio.run(main())
