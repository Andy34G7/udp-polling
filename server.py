
import asyncio
import struct
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration

HOST = "127.0.0.1"
PORT = 12345
CERT_FILE = "certs/server.crt"
KEY_FILE = "certs/server.key"
ALPN = "udp-polling"

MSG_VOTE = 1
MSG_ACK = 2
ACK_STATUS_OK = 0
ACK_STATUS_ALREADY_VOTED = 1

VOTE_PAYLOAD = struct.Struct("!BIIB")   # type, client_id, sequence, vote_value
VOTE_PACKET = struct.Struct("!BIIBB")   # payload + checksum
ACK_PACKET = struct.Struct("!BIIB")     # type, client_id, sequence, status

tallies = {1: 0, 2: 0}
total_packets = 0
unique_votes = 0
duplicate_packets = 0
invalid_packets = 0
repeat_vote_packets = 0
clients = {}  # client_id -> {seen_sequences, max_sequence, unique}


def checksum(payload_bytes):
    return sum(payload_bytes) % 256


def loss_ratio():
    expected = 0
    missing = 0
    for info in clients.values():
        expected += info["max_sequence"]
        missing += max(0, info["max_sequence"] - info["unique"])
    return 0.0 if expected == 0 else missing / float(expected)


async def handle_stream_async(reader, writer):
    global total_packets, unique_votes, duplicate_packets, invalid_packets, repeat_vote_packets

    try:
        data = await reader.readexactly(VOTE_PACKET.size)
    except Exception:
        invalid_packets += 1
        writer.close()
        return

    msg_type, client_id, sequence, vote_value, packet_checksum = VOTE_PACKET.unpack(data)
    payload = VOTE_PAYLOAD.pack(msg_type, client_id, sequence, vote_value)

    if msg_type != MSG_VOTE or checksum(payload) != packet_checksum:
        invalid_packets += 1
        print(f"[invalid] bad_type_or_checksum client={client_id} seq={sequence}")
        writer.close()
        return

    total_packets += 1
    info = clients.setdefault(
        client_id,
        {"seen_sequences": set(), "max_sequence": 0, "unique": 0, "has_voted": False},
    )
    info["max_sequence"] = max(info["max_sequence"], sequence)

    if sequence in info["seen_sequences"]:
        duplicate_packets += 1
        event = "dup"
        ack_status = ACK_STATUS_OK
    elif info["has_voted"]:
        # A new sequence from a client that already cast a vote is rejected.
        repeat_vote_packets += 1
        info["seen_sequences"].add(sequence)
        info["unique"] += 1
        event = "repeat_reject"
        ack_status = ACK_STATUS_ALREADY_VOTED
    else:
        info["seen_sequences"].add(sequence)
        info["unique"] += 1
        unique_votes += 1
        info["has_voted"] = True
        if vote_value in tallies:
            tallies[vote_value] += 1
        else:
            invalid_packets += 1
        event = "vote"
        ack_status = ACK_STATUS_OK

    writer.write(ACK_PACKET.pack(MSG_ACK, client_id, sequence, ack_status))
    await writer.drain()
    writer.close()

    print(
        f"[{event}] client={client_id} seq={sequence} vote={vote_value} "
        f"tally={tallies} unique={unique_votes} dup={duplicate_packets} "
        f"repeat_reject={repeat_vote_packets} invalid={invalid_packets} loss_est={loss_ratio():.2%}"
    )


def handle_stream(reader, writer):
    # aioquic expects a regular callback; schedule the coroutine explicitly.
    asyncio.create_task(handle_stream_async(reader, writer))


async def main():
    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=[ALPN],
    )
    configuration.load_cert_chain(CERT_FILE, KEY_FILE)

    await serve(
        HOST,
        PORT,
        configuration=configuration,
        stream_handler=handle_stream,
    )
    print(f"QUIC polling server listening on {HOST}:{PORT}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

