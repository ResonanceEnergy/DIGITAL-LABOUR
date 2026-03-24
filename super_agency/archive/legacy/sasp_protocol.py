#!/usr/bin/env python3
"""
DIGITAL LABOUR Secure Authentication Secure Protocol (SASP)
Secure cross-device communication framework
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import socket
import sqlite3
import ssl
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class SASPMessageType(Enum):
    """SASP message types"""
    HANDSHAKE_INIT = "handshake_init"
    HANDSHAKE_RESPONSE = "handshake_response"
    AUTHENTICATE = "authenticate"
    DATA_SYNC = "data_sync"
    COMMAND_EXEC = "command_exec"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class SASPSecurityLevel(Enum):
    """Security levels for SASP communication"""
    BASIC = "basic"      # HMAC-based
    STANDARD = "standard"  # RSA-based
    HIGH = "high"        # Full TLS with certificates

class SASPNode:
    """Represents a node in the SASP network"""

    def __init__(self, node_id: str, address: str, port: int,
                 security_level: SASPSecurityLevel = SASPSecurityLevel.STANDARD):
        self.node_id = node_id
        self.address = address
        self.port = port
        self.security_level = security_level
        self.last_seen = datetime.now()
        self.status = "unknown"
        self.public_key = None
        self.session_key = None

class SASPAuthenticationError(Exception):
    """Authentication error in SASP"""
    pass

class SASPCommunicationError(Exception):
    """Communication error in SASP"""
    pass

class SASPProtocol:
    """Core SASP protocol implementation"""

    def __init__(self, node_id: str = None, storage_path: Path = None, security_level: SASPSecurityLevel = SASPSecurityLevel.STANDARD):
        self.node_id = node_id or str(uuid.uuid4())
        self.storage_path = storage_path or Path("./sasp/protocol.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.security_level = security_level

        # Generate or load keys
        self.private_key, self.public_key = self._load_or_generate_keys()

        # Initialize database
        self._init_db()

        # Known nodes
        self.known_nodes: Dict[str, SASPNode] = {}
        self.active_sessions: Dict[str, Dict] = {}

        # Load known nodes
        self._load_known_nodes()

        print(f"🔐 SASP Protocol initialized for node: {self.node_id}")

    def _load_or_generate_keys(self) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Load existing keys or generate new ones"""

        key_path = self.storage_path.parent / f"{self.node_id}_private.pem"
        pub_key_path = self.storage_path.parent / f"{self.node_id}_public.pem"

        if key_path.exists() and pub_key_path.exists():
            # Load existing keys
            with open(key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            with open(pub_key_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )

            return private_key, public_key
        else:
            # Generate new keys
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()

            # Save keys
            with open(key_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            with open(pub_key_path, 'wb') as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

            return private_key, public_key

    def _init_db(self):
        """Initialize SASP database"""
        self.conn = sqlite3.connect(str(self.storage_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS known_nodes (
                node_id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                port INTEGER NOT NULL,
                security_level TEXT DEFAULT 'standard',
                public_key TEXT,
                last_seen TIMESTAMP,
                status TEXT DEFAULT 'unknown',
                trust_level REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                peer_node_id TEXT NOT NULL,
                session_key TEXT NOT NULL,
                established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                message_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                signature TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                received_at TIMESTAMP,
                status TEXT DEFAULT 'sent'
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_node_address ON known_nodes(address, port)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_session_peer ON sessions(peer_node_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_message_session ON messages(session_id)")

        self.conn.commit()

    def _load_known_nodes(self):
        """Load known nodes from database"""
        cursor = self.conn.execute("""
            SELECT node_id, address, port, security_level, public_key, last_seen, status
            FROM known_nodes
        """)

        for row in cursor.fetchall():
            node = SASPNode(
                node_id=row[0],
                address=row[1],
                port=row[2],
                security_level=SASPSecurityLevel(row[3])
            )
            node.last_seen = datetime.fromisoformat(row[4]) if row[4] else datetime.now()
            node.status = row[5]
            if row[6]:  # public_key
                node.public_key = serialization.load_pem_public_key(
                    row[6].encode(),
                    backend=default_backend()
                )

            self.known_nodes[node.node_id] = node

    def register_node(self, node_id: str, address: str, port: int,
                     security_level: SASPSecurityLevel = SASPSecurityLevel.STANDARD,
                     public_key_pem: str = None) -> bool:
        """Register a new node in the network"""

        if node_id in self.known_nodes:
            return False  # Already registered

        node = SASPNode(node_id, address, port, security_level)

        if public_key_pem:
            try:
                node.public_key = serialization.load_pem_public_key(
                    public_key_pem.encode(),
                    backend=default_backend()
                )
            except Exception as e:
                print(f"❌ Invalid public key for node {node_id}: {e}")
                return False

        # Store in database
        pub_key_str = public_key_pem if public_key_pem else None

        self.conn.execute("""
            INSERT INTO known_nodes
            (node_id, address, port, security_level, public_key, status)
            VALUES (?, ?, ?, ?, ?, 'registered')
        """, (node_id, address, port, security_level.value, pub_key_str))

        self.conn.commit()

        self.known_nodes[node_id] = node
        print(f"✅ Registered node: {node_id} at {address}:{port}")
        return True

    def initiate_handshake(self, target_node_id: str) -> Optional[str]:
        """Initiate SASP handshake with target node"""

        if target_node_id not in self.known_nodes:
            raise SASPCommunicationError(f"Unknown node: {target_node_id}")

        target_node = self.known_nodes[target_node_id]

        # Generate session key
        session_key = secrets.token_bytes(32)
        session_id = str(uuid.uuid4())

        # Create handshake message
        handshake_data = {
            "session_id": session_id,
            "initiator_id": self.node_id,
            "target_id": target_node_id,
            "timestamp": datetime.now().isoformat(),
            "security_level": self._get_node_security_level(target_node).value
        }

        # Sign the handshake
        signature = self._sign_message(json.dumps(handshake_data, sort_keys=True))

        message = {
            "type": SASPMessageType.HANDSHAKE_INIT.value,
            "data": handshake_data,
            "signature": signature
        }

        # Store session
        self.active_sessions[session_id] = {
            "peer_node_id": target_node_id,
            "session_key": session_key.hex(),
            "status": "handshake_initiated",
            "established_at": datetime.now()
        }

        # Store in database
        self.conn.execute("""
            INSERT INTO sessions
            (session_id, peer_node_id, session_key, status)
            VALUES (?, ?, ?, 'handshake_initiated')
        """, (session_id, target_node_id, session_key.hex()))

        self.conn.commit()

        print(f"🤝 Initiated handshake with {target_node_id}")
        return session_id

    def process_handshake_response(self, session_id: str, response_data: Dict,
                                  response_signature: str) -> bool:
        """Process handshake response from peer"""

        if session_id not in self.active_sessions:
            raise SASPCommunicationError(f"Unknown session: {session_id}")

        session = self.active_sessions[session_id]

        # Verify signature
        if not self._verify_message(json.dumps(response_data, sort_keys=True),
                                   response_signature, session["peer_node_id"]):
            raise SASPAuthenticationError("Invalid handshake response signature")

        # Verify response data
        if (response_data.get("session_id") != session_id or
            response_data.get("responder_id") != session["peer_node_id"]):
            raise SASPCommunicationError("Invalid handshake response data")

        # Mark session as established
        session["status"] = "established"
        session["last_activity"] = datetime.now()

        self.conn.execute("""
            UPDATE sessions SET
                status = 'established',
                last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))

        self.conn.commit()

        print(f"✅ Handshake completed with {session['peer_node_id']}")
        return True

    def send_secure_message(self, session_id: str, message_type: SASPMessageType,
                           payload: Dict) -> str:
        """Send a secure message through established session"""

        if session_id not in self.active_sessions:
            raise SASPCommunicationError(f"Session not found: {session_id}")

        session = self.active_sessions[session_id]
        if session["status"] != "established":
            raise SASPCommunicationError(f"Session not established: {session_id}")

        # Create message
        message_data = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "type": message_type.value,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "sender_id": self.node_id
        }

        # Encrypt payload if needed
        if message_type in [SASPMessageType.DATA_SYNC, SASPMessageType.COMMAND_EXEC]:
            message_data["encrypted_payload"] = self._encrypt_payload(
                json.dumps(payload), session["session_key"]
            )
            message_data["payload"] = None  # Remove unencrypted payload

        # Sign message
        signature = self._sign_message(json.dumps(message_data, sort_keys=True))

        message = {
            "data": message_data,
            "signature": signature
        }

        # Store message
        self.conn.execute("""
            INSERT INTO messages
            (id, session_id, message_type, payload, signature, status)
            VALUES (?, ?, ?, ?, ?, 'sent')
        """, (
            message_data["message_id"],
            session_id,
            message_type.value,
            json.dumps(payload),
            signature
        ))

        self.conn.commit()

        # Update session activity
        session["last_activity"] = datetime.now()
        self.conn.execute("""
            UPDATE sessions SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))

        self.conn.commit()

        return message_data["message_id"]

    def receive_secure_message(self, message: Dict) -> Optional[Dict]:
        """Receive and process a secure message"""

        try:
            message_data = message.get("data", {})
            signature = message.get("signature")

            if not message_data or not signature:
                raise SASPCommunicationError("Invalid message format")

            session_id = message_data.get("session_id")
            if not session_id or session_id not in self.active_sessions:
                raise SASPCommunicationError(f"Unknown session: {session_id}")

            session = self.active_sessions[session_id]

            # Verify signature
            if not self._verify_message(json.dumps(message_data, sort_keys=True),
                                       signature, session["peer_node_id"]):
                raise SASPAuthenticationError("Invalid message signature")

            # Decrypt payload if needed
            payload = message_data.get("payload")
            if message_data.get("encrypted_payload"):
                payload = json.loads(self._decrypt_payload(
                    message_data["encrypted_payload"], session["session_key"]
                ))

            # Store received message
            self.conn.execute("""
                INSERT INTO messages
                (id, session_id, message_type, payload, signature, received_at, status)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'received')
            """, (
                message_data.get("message_id"),
                session_id,
                message_data.get("type"),
                json.dumps(payload) if payload else None,
                signature
            ))

            self.conn.commit()

            # Update session activity
            session["last_activity"] = datetime.now()
            self.conn.execute("""
                UPDATE sessions SET last_activity = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))

            self.conn.commit()

            return {
                "message_id": message_data.get("message_id"),
                "type": message_data.get("type"),
                "payload": payload,
                "sender_id": message_data.get("sender_id"),
                "timestamp": message_data.get("timestamp")
            }

        except Exception as e:
            print(f"❌ Message processing error: {e}")
            return None

    def _sign_message(self, message: str) -> str:
        """Sign a message with private key"""
        signature = self.private_key.sign(
            message.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()

    def _verify_message(self, message: str, signature: str, signer_node_id: str) -> bool:
        """Verify message signature"""

        if signer_node_id not in self.known_nodes:
            return False

        node = self.known_nodes[signer_node_id]
        if not node.public_key:
            return False

        try:
            signature_bytes = base64.b64decode(signature)
            node.public_key.verify(
                signature_bytes,
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def _encrypt_payload(self, payload: str, session_key_hex: str) -> str:
        """Encrypt payload with session key (simplified - in production use proper encryption)"""
        # For demo purposes, using simple XOR with session key
        # In production, use AES-GCM or similar
        session_key = bytes.fromhex(session_key_hex)
        encrypted = bytearray()
        for i, byte in enumerate(payload.encode()):
            encrypted.append(byte ^ session_key[i % len(session_key)])
        return base64.b64encode(encrypted).decode()

    def _decrypt_payload(self, encrypted_payload: str, session_key_hex: str) -> str:
        """Decrypt payload with session key"""
        # Reverse of encryption
        session_key = bytes.fromhex(session_key_hex)
        encrypted = base64.b64decode(encrypted_payload)
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ session_key[i % len(session_key)])
        return decrypted.decode()

    def _get_node_security_level(self, node: SASPNode) -> SASPSecurityLevel:
        """Get effective security level for communication with node"""
        # Use the higher of the two nodes' security levels
        return max(self.security_level, node.security_level)

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def get_network_status(self) -> Dict[str, Any]:
        """Get current network status"""
        return {
            "node_id": self.node_id,
            "known_nodes": len(self.known_nodes),
            "active_sessions": len([s for s in self.active_sessions.values() if s["status"] == "established"]),
            "security_level": self.security_level.value,
            "public_key_fingerprint": self._get_key_fingerprint()
        }

    def _get_key_fingerprint(self) -> str:
        """Get fingerprint of public key"""
        pub_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(pub_key_bytes).hexdigest()[:16]

class SASPNetworkManager:
    """Manages SASP network operations and cross-device communication"""

    def __init__(self, protocol: SASPProtocol):
        self.protocol = protocol
        self.running = False
        self.server_thread = None
        self.heartbeat_thread = None

    def start_network_services(self, port: int = 8888):
        """Start network services for SASP communication"""

        if self.running:
            return

        self.running = True

        # Start server thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            args=(port,),
            daemon=True
        )
        self.server_thread.start()

        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._send_heartbeats,
            daemon=True
        )
        self.heartbeat_thread.start()

        print(f"🌐 SASP Network services started on port {port}")

    def stop_network_services(self):
        """Stop network services"""
        self.running = False
        print("🛑 SASP Network services stopped")

    def _run_server(self, port: int):
        """Run SASP server"""

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind(('0.0.0.0', port))
            server_socket.listen(5)
            server_socket.settimeout(1.0)  # Allow checking running flag

            print(f"🚀 SASP Server listening on port {port}")

            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    print(f"📡 Connection from {address}")

                    # Handle connection in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Server error: {e}")
                    break

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
        finally:
            server_socket.close()

    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle incoming client connection"""

        try:
            # Receive message
            data = client_socket.recv(4096)
            if not data:
                return

            message = json.loads(data.decode())

            # Process message
            response = self._process_incoming_message(message)

            if response:
                client_socket.send(json.dumps(response).encode())

        except Exception as e:
            print(f"❌ Client handling error: {e}")
        finally:
            client_socket.close()

    def _process_incoming_message(self, message: Dict) -> Optional[Dict]:
        """Process incoming SASP message"""

        try:
            message_type = message.get("type")

            if message_type == SASPMessageType.HANDSHAKE_INIT.value:
                return self._handle_handshake_init(message)
            elif message_type == SASPMessageType.DATA_SYNC.value:
                return self._handle_data_sync(message)
            elif message_type == SASPMessageType.HEARTBEAT.value:
                return self._handle_heartbeat(message)
            else:
                return {
                    "type": SASPMessageType.ERROR.value,
                    "error": "Unknown message type",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "type": SASPMessageType.ERROR.value,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _handle_handshake_init(self, message: Dict) -> Dict:
        """Handle handshake initiation"""

        data = message.get("data", {})
        signature = message.get("signature")

        try:
            # Verify the handshake
            session_id = data.get("session_id")
            initiator_id = data.get("initiator_id")

            if not session_id or not initiator_id:
                raise ValueError("Invalid handshake data")

            # Register the node if not known
            if initiator_id not in self.protocol.known_nodes:
                # For demo, assume the node is at the sender's address
                # In production, this would be more sophisticated
                pass

            # Create session
            session_key = secrets.token_bytes(32)
            self.protocol.active_sessions[session_id] = {
                "peer_node_id": initiator_id,
                "session_key": session_key.hex(),
                "status": "handshake_responded",
                "established_at": datetime.now()
            }

            # Store session
            self.protocol.conn.execute("""
                INSERT INTO sessions
                (session_id, peer_node_id, session_key, status)
                VALUES (?, ?, ?, 'handshake_responded')
            """, (session_id, initiator_id, session_key.hex()))
            self.protocol.conn.commit()

            # Create response
            response_data = {
                "session_id": session_id,
                "responder_id": self.protocol.node_id,
                "timestamp": datetime.now().isoformat()
            }

            signature = self.protocol._sign_message(json.dumps(response_data, sort_keys=True))

            return {
                "type": SASPMessageType.HANDSHAKE_RESPONSE.value,
                "data": response_data,
                "signature": signature
            }

        except Exception as e:
            return {
                "type": SASPMessageType.ERROR.value,
                "error": f"Handshake failed: {e}",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_data_sync(self, message: Dict) -> Dict:
        """Handle data synchronization message"""

        # Process the secure message
        result = self.protocol.receive_secure_message(message)

        if result:
            return {
                "type": "ack",
                "message_id": result["message_id"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "type": SASPMessageType.ERROR.value,
                "error": "Failed to process data sync message",
                "timestamp": datetime.now().isoformat()
            }

    def _handle_heartbeat(self, message: Dict) -> Dict:
        """Handle heartbeat message"""

        data = message.get("data", {})
        node_id = data.get("node_id")

        if node_id and node_id in self.protocol.known_nodes:
            self.protocol.known_nodes[node_id].last_seen = datetime.now()
            self.protocol.known_nodes[node_id].status = "online"

            # Update database
            self.protocol.conn.execute("""
                UPDATE known_nodes SET
                    last_seen = CURRENT_TIMESTAMP,
                    status = 'online'
                WHERE node_id = ?
            """, (node_id,))
            self.protocol.conn.commit()

        return {
            "type": "heartbeat_ack",
            "timestamp": datetime.now().isoformat()
        }

    def _send_heartbeats(self):
        """Send periodic heartbeats to known nodes"""

        while self.running:
            try:
                for node_id, node in self.protocol.known_nodes.items():
                    if node_id != self.protocol.node_id:
                        try:
                            self._send_heartbeat_to_node(node)
                        except Exception as e:
                            print(f"❌ Heartbeat to {node_id} failed: {e}")
                            node.status = "offline"

                time.sleep(30)  # Send heartbeat every 30 seconds

            except Exception as e:
                print(f"❌ Heartbeat thread error: {e}")
                time.sleep(5)

    def _send_heartbeat_to_node(self, node: SASPNode):
        """Send heartbeat to specific node"""

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((node.address, node.port))

            heartbeat = {
                "type": SASPMessageType.HEARTBEAT.value,
                "data": {
                    "node_id": self.protocol.node_id,
                    "timestamp": datetime.now().isoformat()
                }
            }

            sock.send(json.dumps(heartbeat).encode())

            # Wait for ack
            response = sock.recv(1024)
            if response:
                node.last_seen = datetime.now()
                node.status = "online"

        except Exception:
            node.status = "offline"
        finally:
            sock.close()

    def sync_data_with_node(self, target_node_id: str, data_type: str, data: Dict) -> bool:
        """Synchronize data with another node"""

        try:
            # Ensure we have a session
            session_id = None
            for sid, session in self.protocol.active_sessions.items():
                if (session["peer_node_id"] == target_node_id and
                    session["status"] == "established"):
                    session_id = sid
                    break

            if not session_id:
                # Initiate handshake
                session_id = self.protocol.initiate_handshake(target_node_id)
                if not session_id:
                    return False

                # In a real implementation, we'd wait for handshake completion
                # For demo, assume it completes
                time.sleep(1)

            # Send data sync message
            message_id = self.protocol.send_secure_message(
                session_id,
                SASPMessageType.DATA_SYNC,
                {
                    "data_type": data_type,
                    "data": data,
                    "sync_timestamp": datetime.now().isoformat()
                }
            )

            print(f"📤 Data sync initiated: {message_id}")
            return True

        except Exception as e:
            print(f"❌ Data sync failed: {e}")
            return False

# Global instances
_sasp_protocol = None
_sasp_network = None

def get_sasp_protocol() -> SASPProtocol:
    """Get global SASP protocol instance"""
    global _sasp_protocol
    if _sasp_protocol is None:
        _sasp_protocol = SASPProtocol()
    return _sasp_protocol

def get_sasp_network() -> SASPNetworkManager:
    """Get global SASP network manager instance"""
    global _sasp_network
    if _sasp_network is None:
        _sasp_network = SASPNetworkManager(get_sasp_protocol())
    return _sasp_network

# Convenience functions
def init_sasp_network(port: int = 8888) -> bool:
    """Initialize SASP network"""
    try:
        network = get_sasp_network()
        network.start_network_services(port)
        return True
    except Exception as e:
        print(f"❌ SASP network initialization failed: {e}")
        return False

def register_sasp_node(node_id: str, address: str, port: int,
                      public_key_pem: str = None) -> bool:
    """Register a SASP node"""
    return get_sasp_protocol().register_node(node_id, address, port, public_key_pem=public_key_pem)

def get_sasp_status() -> Dict[str, Any]:
    """Get SASP network status"""
    protocol = get_sasp_protocol()
    network = get_sasp_network()
    return {
        "protocol": protocol.get_network_status(),
        "network_running": network.running if network else False
    }

def sync_memory_with_node(target_node_id: str) -> bool:
    """Sync memory doctrine with another node"""
    from memory_doctrine_system import get_memory_doctrine_system

    memory_system = get_memory_doctrine_system()
    current_memory = memory_system.get_memory_stats()

    network = get_sasp_network()
    return network.sync_data_with_node(target_node_id, "memory_doctrine", current_memory)

if __name__ == "__main__":
    # Test SASP protocol
    print("🔐 Testing SASP Protocol...")

    try:
        # Initialize protocol
        protocol = get_sasp_protocol()
        print(f"✅ Protocol initialized: {protocol.node_id}")

        # Get network status
        status = protocol.get_network_status()
        print(f"✅ Network status: {status['known_nodes']} known nodes")

        # Test key operations
        pub_key = protocol.get_public_key_pem()
        print(f"✅ Public key generated ({len(pub_key)} chars)")

        # Initialize network (commented out to avoid port conflicts in testing)
        # network = get_sasp_network()
        # network.start_network_services(8888)
        # print("✅ Network services started")

        print("🎉 SASP Protocol ready!")

    except Exception as e:
        print(f"❌ SASP test failed: {e}")
        import traceback
        traceback.print_exc()


# Additional SASP Classes for QUSAR-QFORGE Communication

class SASPSecurityManager:
    """Manages security for SASP communication"""

    def __init__(self, key: str):
        self.key = key.encode() if isinstance(key, str) else key

    def sign_message(self, message: str) -> str:
        """Sign a message with HMAC"""
        signature = hmac.new(self.key, message.encode(), hashlib.sha256).hexdigest()
        return signature

    def verify_signature(self, message: str, signature: str) -> bool:
        """Verify message signature"""
        expected = self.sign_message(message)
        return hmac.compare_digest(expected, signature)


class SASPMessage:
    """Represents a SASP message"""

    def __init__(self, message_type: str, payload: Dict[str, Any], message_id: str = None):
        self.message_id = message_id or str(uuid.uuid4())
        self.message_type = message_type
        self.payload = payload
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type,
            'payload': self.payload,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SASPMessage':
        """Create message from dictionary"""
        msg = cls(data['message_type'], data['payload'], data.get('message_id'))
        msg.timestamp = data.get('timestamp', msg.timestamp)
        return msg


class SASPClient:
    """SASP client for connecting to SASP servers"""

    def __init__(self, host: str, port: int, security_manager: SASPSecurityManager, use_tls: bool = False):
        self.host = host
        self.port = port
        self.security = security_manager
        self.use_tls = use_tls
        self.socket = None
        self.connected = False

    def connect(self):
        """Connect to SASP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.use_tls:
                context = ssl.create_default_context()
                self.socket = context.wrap_socket(self.socket, server_hostname=self.host)

            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"🔗 Connected to SASP server at {self.host}:{self.port}")
        except Exception as e:
            raise SASPCommunicationError(f"Failed to connect: {e}") from e

    def send_message(self, message: SASPMessage):
        """Send a message to the server"""
        if not self.connected:
            raise SASPCommunicationError("Not connected to server")

        message_dict = message.to_dict()
        message_json = json.dumps(message_dict, sort_keys=True)
        signature = self.security.sign_message(message_json)

        signed_message = {
            'data': message_dict,
            'signature': signature
        }

        try:
            data = json.dumps(signed_message).encode()
            self.socket.sendall(data)
        except Exception as e:
            raise SASPCommunicationError(f"Failed to send message: {e}") from e

    def receive_response(self, timeout: float = 5.0) -> Optional[SASPMessage]:
        """Receive a response from the server"""
        if not self.connected:
            return None

        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(4096)
            if not data:
                return None

            response = json.loads(data.decode())
            message_data = response.get('data', {})
            signature = response.get('signature')
            message_json = json.dumps(message_data, sort_keys=True)

            if not self.security.verify_signature(message_json, signature):
                raise SASPAuthenticationError("Invalid message signature")

            return SASPMessage.from_dict(message_data)
        except socket.timeout:
            return None
        except Exception:
            return None

    def close(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False


class SASPServer:
    """SASP server for handling client connections"""

    def __init__(self, host: str, port: int, security_manager: SASPSecurityManager, use_tls: bool = False):
        self.host = host
        self.port = port
        self.security = security_manager
        self.use_tls = use_tls
        self.server_socket = None
        self.running = False
        self.message_handlers = {}

    def start(self):
        """Start the SASP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            if self.use_tls:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.server_socket = context.wrap_socket(self.server_socket, server_side=True)

            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
        except Exception as e:
            raise SASPCommunicationError(f"Failed to start server: {e}") from e

    def stop(self):
        """Stop the SASP server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

    def register_handler(self, message_type: str, handler: callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler

    def accept_connections(self):
        """Accept incoming connections (non-blocking check)"""
        if not self.running or not self.server_socket:
            return

        try:
            self.server_socket.settimeout(0.1)
            client_socket, address = self.server_socket.accept()

            client_thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket, address),
                daemon=True
            )
            client_thread.start()
        except socket.timeout:
            pass
        except Exception:
            pass

    def _handle_client(self, client_socket, address):
        """Handle a client connection"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode())
                message_data = message.get('data', {})
                signature = message.get('signature')
                message_json = json.dumps(message_data, sort_keys=True)

                if not self.security.verify_signature(message_json, signature):
                    continue

                msg_type = message_data.get('message_type')
                if msg_type in self.message_handlers:
                    response = self.message_handlers[msg_type](message_data.get('payload', {}))

                    response_data = {'message_type': 'response', 'payload': response}
                    response_json = json.dumps(response_data, sort_keys=True)
                    response_sig = self.security.sign_message(response_json)

                    client_socket.sendall(json.dumps({
                        'data': response_data,
                        'signature': response_sig
                    }).encode())
        except Exception:
            pass
        finally:
            client_socket.close()
