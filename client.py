# Client that sends a UDP packet to the server and waits for a response with a custom vote packet

import socket
import struct

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('127.0.0.1', 12345)

MSG_VOTE = 1
client_id = int(input("Enter client ID: "))
sequence = int(input("Enter sequence number: "))
vote_value = int(input("Enter vote (1 or 2): "))

def checksum(data):
    return sum(data) % 256

payload = struct.pack("!BIIB", MSG_VOTE, client_id, sequence, vote_value)
packet = struct.pack("!BIIBB", MSG_VOTE, client_id, sequence, vote_value, checksum(payload))

client_socket.sendto(packet, server_address)
print(f"Sent vote: client={client_id}, seq={sequence}, vote={vote_value}")

response, _ = client_socket.recvfrom(1024)
msg_type, r_client_id, r_seq = struct.unpack("!BII", response)

print(f"ACK received: client={r_client_id}, seq={r_seq}")
