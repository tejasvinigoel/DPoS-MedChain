import datetime
import hashlib
from utils import log_action
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class Transaction:
    def __init__(self, hospital_id, doctor_id, patient_id, insurance_id, record_id, record_type, operation, prescription, amount, target_id=None):
        self.hospital_id = hospital_id
        self.doctor_id = doctor_id
        self.patient_id = patient_id
        self.insurance_id = insurance_id
        self.record_id = record_id
        self.record_type = record_type
        self.operation = operation
        self.prescription = prescription
        self.amount = amount
        self.target_id = target_id
        self.timestamp = datetime.datetime.now().isoformat()
        self.consent_status = "pending"
        self.signature = None

    @property
    def hash(self):
        return self.calculate_hash()

    def to_dict(self):
        sig_hex = self.signature.hex() if self.signature else None
        return {
            "hospital_id": self.hospital_id, "doctor_id": self.doctor_id, "patient_id": self.patient_id,
            "insurance_id": self.insurance_id, "record_id": self.record_id, "record_type": self.record_type,
            "operation": self.operation, "prescription": self.prescription, "amount": self.amount,
            "target_id": self.target_id, "timestamp": self.timestamp, "signature": sig_hex
        }

    def calculate_hash(self):
        tx_string = f"{self.hospital_id}{self.doctor_id}{self.patient_id}{self.record_id}{self.record_type}{self.operation}{self.timestamp}"
        return hashlib.sha256(tx_string.encode()).hexdigest()

class Block:
    def __init__(self, transactions, previous_hash, delegate_id, nonce=0):
        self.timestamp = datetime.datetime.now().isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.merkle_root = self.calculate_merkle_root()
        self.delegate_id = delegate_id
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.timestamp}{self.merkle_root}{self.previous_hash}{self.delegate_id}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def calculate_merkle_root(self):
        if not self.transactions:
            return hashlib.sha256("".encode()).hexdigest()
        transaction_hashes = [tx.hash for tx in self.transactions]
        while len(transaction_hashes) > 1:
            if len(transaction_hashes) % 2 != 0:
                transaction_hashes.append(transaction_hashes[-1])
            new_hashes = []
            for i in range(0, len(transaction_hashes), 2):
                combined = transaction_hashes[i] + transaction_hashes[i+1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)
            transaction_hashes = new_hashes
        return transaction_hashes[0]

class Blockchain:
    def __init__(self, max_delegates=5):
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.pending_consent_transactions = []
        self.users = {}
        self.record_id_counter = 0
        self.access_control = {}
        self.stakes = {}
        self.votes = {}
        self.voter_choice = {}
        self.delegates = []
        self.current_delegate_index = 0
        self.max_delegates = max_delegates

    def create_genesis_block(self):
        return Block(transactions=[], previous_hash="0", delegate_id="genesis", nonce=0)

    def register_user(self, user_id, name, role, password_hash):
        if user_id in self.users: return False
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        self.users[user_id] = {
            "name": name, "role": role, "password_hash": password_hash,
            "public_key": public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo),
            "private_key": private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
        }
        self.stakes.setdefault(user_id, 0)
        if role == "Patient": self.access_control.setdefault(user_id, set())
        log_action(f"ADMIN ACTION: Registered user {user_id} ({name}) as {role}.")
        return True

    def create_and_sign_transaction(self, hospital_id, doctor_id, patient_id, insurance_id, record_type, operation, prescription, amount, target_id=None):
        self.record_id_counter += 1
        new_record_id = f"REC-{self.record_id_counter}"
        new_tx = Transaction(
            hospital_id, doctor_id, patient_id, insurance_id, new_record_id,
            record_type, operation, prescription, amount, target_id
        )
        if self.sign_transaction(new_tx, doctor_id):
            self.pending_consent_transactions.append(new_tx)
            log_action(f"CONSENT PENDING: Signed record {new_tx.record_id} by {doctor_id} for {patient_id}")
            return True
        log_action(f"SIGNATURE FAILED: Could not sign transaction from {doctor_id}")
        return False

    def sign_transaction(self, transaction, user_id):
        user = self.users.get(user_id)
        if not user or 'private_key' not in user: return False
        private_key = serialization.load_pem_private_key(user['private_key'], password=None)
        signature = private_key.sign(
            transaction.hash.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256()
        )
        transaction.signature = signature
        return True

    def verify_transaction(self, transaction):
        sender = self.users.get(transaction.doctor_id)
        if not sender or not transaction.signature: return False
        public_key = serialization.load_pem_public_key(sender['public_key'])
        try:
            public_key.verify(
                transaction.signature, transaction.hash.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def approve_transaction(self, tx_hash, patient_id):
        for tx in self.pending_consent_transactions:
            if tx.hash == tx_hash:
                if tx.patient_id != patient_id:
                    log_action(f"CONSENT FAILED: {patient_id} tried to approve record for {tx.patient_id}")
                    return False
                if not self.verify_transaction(tx):
                    log_action(f"CONSENT FAILED: Invalid signature on record {tx.record_id}")
                    return False
                tx.consent_status = "approved"
                self.pending_transactions.append(tx)
                self.pending_consent_transactions.remove(tx)
                log_action(f"CONSENT APPROVED: {patient_id} approved record {tx.record_id}")
                return tx
        return False

    def deny_transaction(self, tx_hash, patient_id):
        for tx in self.pending_consent_transactions:
            if tx.hash == tx_hash:
                if tx.patient_id != patient_id:
                    log_action(f"CONSENT DENY FAILED: {patient_id} tried to deny record for {tx.patient_id}")
                    return False
                self.pending_consent_transactions.remove(tx)
                log_action(f"CONSENT DENIED: {patient_id} denied record {tx.record_id} from Dr. {tx.doctor_id}.")
                return True
        return False

    def grant_access(self, patient_id, doctor_id):
        self.access_control.setdefault(patient_id, set()).add(doctor_id)
        log_action(f"ACCESS GRANTED: {doctor_id} was granted access to {patient_id}'s records.")

    def check_access(self, viewer_id, patient_id):
        viewer = self.users.get(viewer_id)
        if not viewer: return False
        if viewer_id == patient_id or viewer['role'] == "Administrator": return True
        if viewer['role'] == "Doctor" and viewer_id in self.access_control.get(patient_id, set()): return True
        return False

    def validate_chain(self):
        for i in range(1, len(self.chain)):
            current_block, previous_block = self.chain[i], self.chain[i-1]
            if current_block.previous_hash != previous_block.hash: return False
            if current_block.hash != current_block.calculate_hash(): return False
            if current_block.merkle_root != current_block.calculate_merkle_root(): return False
        return True
    
    def get_last_block(self):
        return self.chain[-1]

    def stake_tokens(self, user_id, amount):
        if user_id not in self.users or not isinstance(amount, (int, float)) or amount <= 0: return False
        self.stakes[user_id] = self.stakes.get(user_id, 0) + amount
        if user_id in self.voter_choice:
            candidate = self.voter_choice[user_id]
            self.votes[candidate] = self.votes.get(candidate, 0) + amount
        return True

    def vote_for_candidate(self, voter_id, candidate_id):
        if voter_id not in self.users or candidate_id not in self.users or self.stakes.get(voter_id, 0) <= 0: return False
        if voter_id in self.voter_choice:
            prev_candidate = self.voter_choice[voter_id]
            self.votes[prev_candidate] = self.votes.get(prev_candidate, 0) - self.stakes[voter_id]
        self.votes[candidate_id] = self.votes.get(candidate_id, 0) + self.stakes[voter_id]
        self.voter_choice[voter_id] = candidate_id
        return True

    def elect_delegates(self):
        if not self.votes: return []
        sorted_candidates = sorted(self.votes.items(), key=lambda item: item[1], reverse=True)
        self.delegates = [c for c, v in sorted_candidates[:self.max_delegates]]
        self.current_delegate_index = 0
        return self.delegates

    def get_delegate_list(self):
        return list(self.delegates)

    def forge_block(self, delegate_id):
        if not self.delegates or delegate_id not in self.delegates: return None
        if delegate_id != self.delegates[self.current_delegate_index]: return None
        if not self.pending_transactions: return None
        
        last_block = self.get_last_block()
        new_block = Block(
            transactions=self.pending_transactions.copy(),
            previous_hash=last_block.hash,
            delegate_id=delegate_id,
            nonce=getattr(last_block, 'nonce', -1) + 1
        )
        self.chain.append(new_block)
        self.pending_transactions = []
        self.current_delegate_index = (self.current_delegate_index + 1) % len(self.delegates)
        return new_block

    def get_patient_history(self, patient_id):
        return [tx.to_dict() for block in self.chain for tx in block.transactions if tx.patient_id == patient_id]