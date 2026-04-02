import streamlit as st
import socket
import struct
import time

HOST = "127.0.0.1"
PORT = 12345

ACK_PACKET = struct.Struct("!BII")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 6000))

st.title(" Live Voting Dashboard")

total_received = 0
last_seq = {}

placeholder = st.empty()

while True:
    data, addr = sock.recvfrom(1024)

    if len(data) == ACK_PACKET.size:
        msg_type, client_id, seq = ACK_PACKET.unpack(data)

        total_received += 1

        if client_id not in last_seq:
            last_seq[client_id] = seq
        else:
            last_seq[client_id] = max(last_seq[client_id], seq)

        total_expected = sum(last_seq.values())
        packet_loss = total_expected - total_received
        loss_percent = (packet_loss / total_expected * 100) if total_expected > 0 else 0

        with placeholder.container():
            st.subheader("📡 Packet Statistics")
            st.write("Total Expected:", total_expected)
            st.write("Total Received:", total_received)
            st.write("Packet Loss:", packet_loss)
            st.write("Loss %:", round(loss_percent, 2))

    time.sleep(0.5)