import asyncio
import json
import os
import struct
from datetime import datetime

import streamlit as st
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

HOST = "127.0.0.1"
PORT = 12345
ALPN = "udp-polling"
CA_FILE = "certs/ca.crt"
STATE_FILE = "dashboard_state.json"

MSG_VOTE = 1
MSG_ACK = 2
ACK_STATUS_OK = 0
ACK_STATUS_ALREADY_VOTED = 1

VOTE_PAYLOAD = struct.Struct("!BIIB")
VOTE_PACKET = struct.Struct("!BIIBB")
ACK_PACKET = struct.Struct("!BIIB")


def checksum(data):
    return sum(data) % 256


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def next_sequence(client_id):
    state = load_state()
    return int(state.get(str(client_id), 0)) + 1


def commit_sequence(client_id, sequence):
    state = load_state()
    state[str(client_id)] = sequence
    save_state(state)


async def send_vote(client_id, vote_value):
    sequence = next_sequence(client_id)
    payload = VOTE_PAYLOAD.pack(MSG_VOTE, client_id, sequence, vote_value)
    packet = VOTE_PACKET.pack(MSG_VOTE, client_id, sequence, vote_value, checksum(payload))

    configuration = QuicConfiguration(is_client=True, alpn_protocols=[ALPN])
    configuration.load_verify_locations(CA_FILE)

    try:
        async with connect(HOST, PORT, configuration=configuration) as connection:
            reader, writer = await connection.create_stream()
            writer.write(packet)
            await writer.drain()

            response = await reader.readexactly(ACK_PACKET.size)
            writer.close()

        msg_type, r_client_id, r_seq, status = ACK_PACKET.unpack(response)
        if msg_type != MSG_ACK:
            return {
                "outcome": "error",
                "client_id": client_id,
                "sequence": sequence,
                "message": "Invalid response type from server",
            }

        if status == ACK_STATUS_ALREADY_VOTED:
            return {
                "outcome": "already_voted",
                "client_id": r_client_id,
                "sequence": r_seq,
                "message": f"Client {r_client_id} has already voted",
            }

        if status == ACK_STATUS_OK:
            if r_client_id == client_id and r_seq == sequence:
                commit_sequence(client_id, sequence)
            return {
                "outcome": "accepted",
                "client_id": r_client_id,
                "sequence": r_seq,
                "message": f"Vote accepted for client {r_client_id} (seq={r_seq})",
            }

        return {
            "outcome": "error",
            "client_id": client_id,
            "sequence": sequence,
            "message": f"Unknown ACK status: {status}",
        }
    except Exception as exc:
        return {
            "outcome": "error",
            "client_id": client_id,
            "sequence": sequence,
            "message": f"Request failed: {exc}",
        }


st.set_page_config(page_title="Voting Dashboard", page_icon="🗳️")
st.title("Secure Voting Dashboard")

if "stats" not in st.session_state:
    st.session_state.stats = {"attempts": 0, "accepted": 0, "already_voted": 0, "errors": 0}

if "history" not in st.session_state:
    st.session_state.history = []

with st.form("vote_form"):
    client_id = int(st.number_input("Client ID", min_value=1, value=1, step=1))
    vote_value = int(st.radio("Vote Value", options=[1, 2], horizontal=True))
    submitted = st.form_submit_button("Send Vote")

if submitted:
    result = asyncio.run(send_vote(client_id, vote_value))
    st.session_state.stats["attempts"] += 1

    outcome = result["outcome"]
    if outcome == "accepted":
        st.session_state.stats["accepted"] += 1
        st.success(result["message"])
    elif outcome == "already_voted":
        st.session_state.stats["already_voted"] += 1
        st.error(result["message"])
    else:
        st.session_state.stats["errors"] += 1
        st.warning(result["message"])

    st.session_state.history.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "client": result["client_id"],
            "sequence": result["sequence"],
            "vote": vote_value,
            "result": outcome,
        },
    )
    st.session_state.history = st.session_state.history[:50]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Attempts", st.session_state.stats["attempts"])
col2.metric("Accepted", st.session_state.stats["accepted"])
col3.metric("Already Voted", st.session_state.stats["already_voted"])
col4.metric("Errors", st.session_state.stats["errors"])

st.subheader("Recent Activity")
if st.session_state.history:
    st.table(st.session_state.history)
else:
    st.info("No votes sent yet.")

st.subheader("Saved Sequences")
state = load_state()
if state:
    st.json(state)
else:
    st.caption("No saved sequence state yet.")