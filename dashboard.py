import streamlit as st
import socket
import struct
import time
from collections import defaultdict

HOST = "0.0.0.0"
PORT = 6001

ACK_PACKET = struct.Struct("!BII")

if "sock" not in st.session_state:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(0.5)
    st.session_state.sock = sock
else:
    sock = st.session_state.sock

st.set_page_config(page_title="Live Voting Dashboard", layout="wide")
st.title("Live Voting Dashboard")

if "total_received" not in st.session_state:
    st.session_state.total_received = 0
    st.session_state.last_seq = {}
    st.session_state.tallies = defaultdict(int)
    st.session_state.duplicates = 0
    st.session_state.clients = {}

try:
    while True:
        data, addr = sock.recvfrom(1024)

        if len(data) == ACK_PACKET.size:
            msg_type, client_id, seq = ACK_PACKET.unpack(data)

            st.session_state.total_received += 1

            if client_id not in st.session_state.last_seq:
                st.session_state.last_seq[client_id] = seq
                st.session_state.clients[client_id] = set()
            else:
                st.session_state.last_seq[client_id] = max(
                    st.session_state.last_seq[client_id], seq
                )

            if seq in st.session_state.clients[client_id]:
                st.session_state.duplicates += 1
            else:
                st.session_state.clients[client_id].add(seq)

except socket.timeout:
    pass

total_expected = sum(st.session_state.last_seq.values())
packet_loss = total_expected - st.session_state.total_received
loss_percent = (packet_loss / total_expected * 100) if total_expected > 0 else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Expected", total_expected)
col2.metric("Total Received", st.session_state.total_received)
col3.metric("Packet Loss", packet_loss)
col4.metric("Loss %", f"{loss_percent:.2f}%")

st.markdown("---")

st.subheader("Client Activity")

client_data = {
    "Client ID": [],
    "Max Sequence": [],
    "Packets Received": []
}

for cid in st.session_state.last_seq:
    client_data["Client ID"].append(cid)
    client_data["Max Sequence"].append(st.session_state.last_seq[cid])
    client_data["Packets Received"].append(len(st.session_state.clients[cid]))

st.table(client_data)

st.subheader("Duplicate Packets")
st.write("Total Duplicates:", st.session_state.duplicates)

st.subheader("Packet Flow")

chart_data = {
    "Received": st.session_state.total_received,
    "Lost": packet_loss
}

st.bar_chart(chart_data)

time.sleep(1)
st.rerun()
