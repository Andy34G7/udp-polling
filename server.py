# A UDP polling server with a custom vote packet

import socket
import struct

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('localhost', 12345))
print("UDP polling server is running on port 12345...")

while True:
    data, addr = server_socket.recvfrom(1024)
    if len(data) == 5:
        vote_id, vote_value = struct.unpack('!IB', data)
        print(f"Received vote from {addr}: Vote ID={vote_id}, Vote Value={vote_value}")
        response = struct.pack('!I', vote_id)
        server_socket.sendto(response, addr)
    else:
        print(f"Received invalid packet from {addr}")

