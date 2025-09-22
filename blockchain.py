import datetime
import hashlib
from utils import log_action

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

    # FIXED: The add_transaction method now accepts target_id
    def add_transaction(self, hospital_id, doctor_id, patient_id, insurance_id, record_type, operation, prescription, amount, target_id=None):
        self.record_id_counter += 1
        new_record_id = f"REC-{self.record_id_counter}"
        new_tx = Transaction(
            hospital_id=hospital_id, doctor_id=doctor_id, patient_id=patient_id,
            insurance_id=insurance_id, record_id=new_record_id, record_type=record_type,
            operation=operation, prescription=prescription, amount=amount, target_id=target_id
        )
        self.pending_consent_transactions.append(new_tx)
        log_action(f"CONSENT PENDING: Record {new_tx.record_id} by {new_tx.doctor_id} for {new_tx.patient_id}")

    # ADDED: This entire method was missing
    def approve_transaction(self, tx_hash, patient_id):
        for tx in self.pending_consent_transactions:
            if tx.hash == tx_hash:
                if tx.patient_id != patient_id:
                    log_action(f"CONSENT FAILED: {patient_id} tried to approve record for {tx.patient_id}")
                    return False # Unauthorized
                tx.consent_status = "approved"
                self.pending_transactions.append(tx)
                self.pending_consent_transactions.remove(tx)
                log_action(f"CONSENT APPROVED: {patient_id} approved record {tx.record_id}")
                return tx # Return the transaction object on success
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
        self.users[user_id] = {"name": name, "role": role}
        self.stakes.setdefault(user_id, 0)
        # When a patient is registered, create an empty access set for them
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