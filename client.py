# Client that sends a UDP packet to the server and waits for a response with a custom vote packet

import socket
import struct

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 12345)
vote_id = 1
vote_value = 1
vote_packet = struct.pack('!IB', vote_id, vote_value)
client_socket.sendto(vote_packet, server_address)
print(f"Sent vote: Vote ID={vote_id}, Vote Value={vote_value}")
response, _ = client_socket.recvfrom(1024)
if len(response) == 4:
    response_vote_id = struct.unpack('!I', response)[0]
    print(f"Received response: Vote ID={response_vote_id}")
else:
    print("Received invalid response")