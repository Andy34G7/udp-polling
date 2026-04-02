"""Minimal UDP polling server with checksum validation and duplicate detection."""

import socket
import struct

HOST = "127.0.0.1"
PORT = 12345

MSG_VOTE = 1
MSG_ACK = 2

VOTE_PAYLOAD = struct.Struct("!BIIB")   # type, client_id, sequence, vote_value
VOTE_PACKET = struct.Struct("!BIIBB")   # payload + checksum
ACK_PACKET = struct.Struct("!BII")      # type, client_id, sequence

tallies = {1: 0, 2: 0}
total_packets = 0
unique_votes = 0
duplicate_packets = 0
invalid_packets = 0
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


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f"UDP polling server listening on {HOST}:{PORT}")

while True:
    data, addr = sock.recvfrom(1024)

    if len(data) != VOTE_PACKET.size:
        invalid_packets += 1
        print(f"[invalid] bad_size={len(data)} from {addr}")
        continue

    msg_type, client_id, sequence, vote_value, packet_checksum = VOTE_PACKET.unpack(data)
    payload = VOTE_PAYLOAD.pack(msg_type, client_id, sequence, vote_value)

    if msg_type != MSG_VOTE or checksum(payload) != packet_checksum:
        invalid_packets += 1
        print(f"[invalid] bad_type_or_checksum client={client_id} seq={sequence} from {addr}")
        continue

    total_packets += 1
    info = clients.setdefault(client_id, {"seen_sequences": set(), "max_sequence": 0, "unique": 0})
    info["max_sequence"] = max(info["max_sequence"], sequence)

    if sequence in info["seen_sequences"]:
        duplicate_packets += 1
        is_duplicate = True
    else:
        info["seen_sequences"].add(sequence)
        info["unique"] += 1
        unique_votes += 1
        is_duplicate = False
        if vote_value in tallies:
            tallies[vote_value] += 1
        else:
            invalid_packets += 1

    sock.sendto(ACK_PACKET.pack(MSG_ACK, client_id, sequence), addr)

    event = "dup" if is_duplicate else "vote"
    print(
        f"[{event}] client={client_id} seq={sequence} vote={vote_value} "
        f"tally={tallies} unique={unique_votes} dup={duplicate_packets} "
        f"invalid={invalid_packets} loss_est={loss_ratio():.2%}"
    )

