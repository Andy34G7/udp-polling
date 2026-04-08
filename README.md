# udp-polling

UDP polling demo secured with QUIC (TLS 1.3 over UDP).

## Prerequisites

1. Install dependency:

```bash
uv pip install --python .venv/bin/python aioquic
```

2. Generate local test certificates:

```bash
mkdir -p certs

# CA
openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
	-keyout certs/ca.key -out certs/ca.crt -subj "/CN=udp-polling-ca"

# Server key + CSR with SAN for localhost + 127.0.0.1
openssl req -newkey rsa:2048 -nodes \
	-keyout certs/server.key -out certs/server.csr \
	-subj "/CN=127.0.0.1" \
	-addext "subjectAltName=IP:127.0.0.1,DNS:localhost"

# Sign server cert with CA
openssl x509 -req -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key \
	-CAcreateserial -out certs/server.crt -days 365 -sha256 \
	-copy_extensions copy
```

## Run

1. Start server:

```bash
python server.py
```

2. Run client:

```bash
python client.py
```

Client prompts for `client ID` and `vote` only. Sequence numbers are auto-incremented per client and stored in `client_state.json`.