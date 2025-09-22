import datetime
import hashlib
from utils import log_action
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class Transaction:
    # FIXED: Added target_id=None to the constructor
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
        self.target_id = target_id # The user access is being granted to
        self.timestamp = datetime.datetime.now().isoformat()
        self.consent_status = "pending"
        self.signature = None 

    @property
    def hash(self):
        return self.calculate_hash()

    def to_dict(self):
        return {
            "hospital_id": self.hospital_id,
            "doctor_id": self.doctor_id,
            "patient_id": self.patient_id,
            "insurance_id": self.insurance_id,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "operation": self.operation,
            "prescription": self.prescription,
            "amount": self.amount,
            "target_id": self.target_id,
            "timestamp": self.timestamp
        }

    def calculate_hash(self):
        tx_string = f"{self.hospital_id}{self.doctor_id}{self.patient_id}{self.record_id}{self.record_type}{self.operation}{self.timestamp}"
        return hashlib.sha256(tx_string.encode()).hexdigest()

class Block:
    # ... (This class is correct, no changes needed) ...
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
        self.pending_consent_transactions = [] # ADDED: This was missing
        self.users = {}
        self.record_id_counter = 0
        self.access_control = {}
        self.stakes = {}
        self.votes = {}
        self.voter_choice = {}
        self.delegates = []
        self.current_delegate_index = 0
        self.max_delegates = max_delegates

    # REPLACE your old add_transaction method with this
    def create_and_sign_transaction(self, hospital_id, doctor_id, patient_id, insurance_id, record_type, operation, prescription, amount, target_id=None):
        self.record_id_counter += 1
        new_record_id = f"REC-{self.record_id_counter}"

        new_tx = Transaction(
            hospital_id, doctor_id, patient_id, insurance_id, new_record_id,
            record_type, operation, prescription, amount, target_id
        )

        # Sign the transaction immediately upon creation
        if self.sign_transaction(new_tx, doctor_id):
            self.pending_consent_transactions.append(new_tx)
            log_action(f"CONSENT PENDING: Signed record {new_tx.record_id} by {doctor_id} for {patient_id}")
            return True
        else:
            log_action(f"SIGNATURE FAILED: Could not sign transaction from {doctor_id}")
            return False
        
    def approve_transaction(self, tx_hash, patient_id):
        for tx in self.pending_consent_transactions:
            if tx.hash == tx_hash:
                if tx.patient_id != patient_id:
                    return False

                # VERIFY SIGNATURE BEFORE APPROVING
                if not self.verify_transaction(tx):
                    log_action(f"CONSENT FAILED: Invalid signature on record {tx.record_id}")
                    return False

                # ... (rest of the method is the same) ...
                tx.consent_status = "approved"
                self.pending_transactions.append(tx)
                self.pending_consent_transactions.remove(tx)
                log_action(f"CONSENT APPROVED: {patient_id} approved record {tx.record_id}")
                return tx
        return False

    # ... (The rest of your Blockchain class methods: grant_access, check_access, register_user, etc., are correct) ...
    def create_genesis_block(self):
        return Block(transactions=[], previous_hash="0", delegate_id="genesis", nonce=0)

    def get_last_block(self):
        return self.chain[-1]
    
    def grant_access(self, patient_id, doctor_id):
        """Adds a doctor to a patient's access list."""
        if patient_id not in self.access_control:
            self.access_control[patient_id] = set()
        self.access_control[patient_id].add(doctor_id)
        log_action(f"ACCESS GRANTED: {doctor_id} was granted access to {patient_id}'s records.")
        return True

    def check_access(self, viewer_id, patient_id):
        """Checks if a user has permission to view a patient's records."""
        viewer = self.users.get(viewer_id)
        if not viewer:
            return False # Viewer isn't registered

        if viewer_id == patient_id:
            return True
        
        if viewer['role'] == "Administrator":
            return True
            
        if viewer['role'] == "Doctor":
            if viewer_id in self.access_control.get(patient_id, set()):
                return True
                
        return False

    def register_user(self, user_id, name, role):
        if user_id in self.users:
            print(f"Error: User {user_id} already exists.")
            return False

        # Generate private/public key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()

        # Serialize keys to PEM format for storage
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        self.users[user_id] = {
            "name": name,
            "role": role,
            "public_key": public_pem,
            "private_key": private_pem # For simulation purposes
        }

        # ... (rest of the method is the same)
        self.stakes.setdefault(user_id, 0)
        if role == "Patient":
            self.access_control.setdefault(user_id, set())
        print(f"User {name} registered as a {role}.")
        log_action(f"ADMIN ACTION: Registered user {user_id} ({name}) as {role}.")
        return True

    def stake_tokens(self, user_id, amount):
        try:
            amt = float(amount)
        except (ValueError, TypeError):
            print("Stake amount must be a number.")
            return False
        if amt <= 0:
            print("Stake amount must be positive.")
            return False
        if user_id not in self.users:
            print("User not registered.")
            return False
        self.stakes[user_id] = self.stakes.get(user_id, 0) + amt
        prev_candidate = self.voter_choice.get(user_id)
        if prev_candidate:
            self.votes[prev_candidate] = self.votes.get(prev_candidate, 0) + amt
        return True

    def vote_for_candidate(self, voter_id, candidate_id):
        if voter_id not in self.users or candidate_id not in self.users:
            return False
        voter_stake = self.stakes.get(voter_id, 0)
        if voter_stake <= 0:
            return False
        prev = self.voter_choice.get(voter_id)
        if prev:
            self.votes[prev] = max(0, self.votes.get(prev, 0) - voter_stake)
        self.votes[candidate_id] = self.votes.get(candidate_id, 0) + voter_stake
        self.voter_choice[voter_id] = candidate_id
        return True

    def elect_delegates(self):
        if not self.votes:
            return []
        sorted_candidates = sorted(self.votes.items(), key=lambda kv: kv[1], reverse=True)
        self.delegates = [c for c, v in sorted_candidates[:self.max_delegates]]
        self.current_delegate_index = 0
        return self.delegates

    def get_delegate_list(self):
        return list(self.delegates)

    def forge_block(self, delegate_id):
        if not self.delegates or delegate_id not in self.delegates:
            return None
        expected_delegate = self.delegates[self.current_delegate_index]
        if delegate_id != expected_delegate:
            return None
        if not self.pending_transactions:
            return None
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
        history = []
        for i, block in enumerate(self.chain):
            for tx in block.transactions:
                if tx.patient_id == patient_id:
                    history.append(tx.to_dict())
        return history
    
    def validate_chain(self):
        """
        Validates the integrity of the entire blockchain.
        Returns True if the chain is valid, False otherwise.
        """
        # Iterate from the second block to the end of the chain
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # 1. Verify the previous_hash link
            if current_block.previous_hash != previous_block.hash:
                print(f"Chain Invalid: Block #{i}'s previous_hash does not match Block #{i-1}'s hash.")
                log_action(f"TAMPER DETECTED: Chain invalid at Block #{i} (previous_hash mismatch).")
                return False

            # 2. Verify the block's own hash integrity
            if current_block.hash != current_block.calculate_hash():
                print(f"Chain Invalid: Block #{i}'s hash is incorrect.")
                log_action(f"TAMPER DETECTED: Block #{i} content has been altered (hash mismatch).")
                return False
            
            # 3. Verify the Merkle root to ensure transaction list integrity
            if current_block.merkle_root != current_block.calculate_merkle_root():
                print(f"Chain Invalid: Block #{i}'s Merkle root is incorrect.")
                log_action(f"TAMPER DETECTED: Block #{i}'s transactions have been altered (Merkle root mismatch).")
                return False
        
        # If the loop completes, the chain is valid
        log_action("CHAIN VALIDATION: Chain integrity verified successfully.")
        return True
    
    def deny_transaction(self, tx_hash, patient_id):
        """
        Denies a transaction waiting for consent and removes it.
        """
        for tx in self.pending_consent_transactions:
            if tx.hash == tx_hash:
                # Security check: Does the denier own this record?
                if tx.patient_id != patient_id:
                    log_action(f"CONSENT DENY FAILED: {patient_id} tried to deny record for {tx.patient_id}")
                    return False # Unauthorized

                self.pending_consent_transactions.remove(tx)
                # This is the new log entry for the audit trail
                log_action(f"CONSENT DENIED: {patient_id} denied record {tx.record_id} from Dr. {tx.doctor_id}.")
                return True
        return False # Transaction not found
    
    def sign_transaction(self, transaction, user_id):
        """Signs a transaction using the user's private key."""
        user = self.users.get(user_id)
        if not user or 'private_key' not in user:
            return False # User or key not found
        
        private_key = serialization.load_pem_private_key(user['private_key'], password=None)
        tx_hash = transaction.hash.encode() # The hash of the transaction data

        signature = private_key.sign(
            tx_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        transaction.signature = signature
        return True

    def verify_transaction(self, transaction):
        """Verifies a transaction's signature using the sender's public key."""
        sender_id = transaction.doctor_id
        user = self.users.get(sender_id)
        if not user or not transaction.signature:
            return False

        public_key = serialization.load_pem_public_key(user['public_key'])
        tx_hash = transaction.hash.encode()

        try:
            public_key.verify(
                transaction.signature,
                tx_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True # Signature is valid
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False # Signature is invalid