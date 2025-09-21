import datetime
import hashlib
from utils import log_action

class Transaction:
    def __init__(self, hospital_id, doctor_id, patient_id, insurance_id, record_id, operation, prescription, amount):
        self.hospital_id = hospital_id
        self.doctor_id = doctor_id
        self.patient_id = patient_id
        self.insurance_id = insurance_id
        self.record_id = record_id
        self.operation = operation  # "Add", "Update", "Share" or free text like "Diagnosis"
        self.prescription = prescription
        self.amount = amount
        self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self):
        return {
            "hospital_id": self.hospital_id,
            "doctor_id": self.doctor_id,
            "patient_id": self.patient_id,
            "insurance_id": self.insurance_id,
            "record_id": self.record_id,
            "operation": self.operation,
            "prescription": self.prescription,
            "amount": self.amount,
            "timestamp": self.timestamp
        }

    def calculate_hash(self):
        tx_string = f"{self.hospital_id}{self.doctor_id}{self.patient_id}{self.record_id}{self.operation}{self.timestamp}"
        return hashlib.sha256(tx_string.encode()).hexdigest()

class Block:
    def __init__(self, transactions, previous_hash, delegate_id):
        self.timestamp = datetime.datetime.now().isoformat()
        self.transactions = transactions  # list of Transaction objects
        self.previous_hash = previous_hash
        # merkle root computed from transaction hashes
        self.merkle_root = self.calculate_merkle_root()
        self.delegate_id = delegate_id  # who created this block
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.timestamp}{self.merkle_root}{self.previous_hash}{self.delegate_id}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def calculate_merkle_root(self):
        # If there are no transactions: return hash of empty string
        if not self.transactions:
            return hashlib.sha256("".encode()).hexdigest()

        transaction_hashes = [tx.calculate_hash() for tx in self.transactions]

        # If only one transaction, merkle root is its hash
        while len(transaction_hashes) > 1:
            if len(transaction_hashes) % 2 != 0:
                # Duplicate last if odd number
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
        self.users = {}  # user_id -> {"name": name, "role": role}
        # DPoS-related data structures
        self.stakes = {}  # user_id -> stake_amount (int or float)
        self.votes = {}   # candidate_id -> total_votes (sum of stakes delegated to candidate)
        self.voter_choice = {}  # voter_id -> candidate_id (to allow changing vote)
        self.delegates = []  # elected delegates (user_ids)
        self.current_delegate_index = 0
        self.max_delegates = max_delegates

    def create_genesis_block(self):
        return Block(transactions=[], previous_hash="0", delegate_id="genesis")

    def get_last_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        self.pending_transactions.append(transaction)
        log_action(f"TRANSACTION ADDED: {transaction.record_id} by {transaction.doctor_id} for {transaction.patient_id}")

    # -------- User management --------
    def register_user(self, user_id, name, role):
        if user_id in self.users:
            print(f"Error: User {user_id} already exists.")
            return False
        self.users[user_id] = {"name": name, "role": role}
        # initialize stake to 0
        self.stakes.setdefault(user_id, 0)
        print(f"User {name} registered as a {role}.")
        log_action(f"ADMIN ACTION: Registered user {user_id} ({name}) as {role}.")
        return True

    # -------- Staking & Voting (DPoS) --------
    def stake_tokens(self, user_id, amount):
        # amount should be positive numeric (int or float)
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
        print(f"{user_id} staked {amt}. Total stake: {self.stakes[user_id]}")
        log_action(f"STAKE: {user_id} staked {amt}. Total stake: {self.stakes[user_id]}")
        # If the user already voted, update candidate vote weight automatically
        prev_candidate = self.voter_choice.get(user_id)
        if prev_candidate:
            # increase candidate's total votes by amt
            self.votes[prev_candidate] = self.votes.get(prev_candidate, 0) + amt
            log_action(f"VOTE UPDATE: {user_id}'s stake increased; candidate {prev_candidate} gained {amt} votes.")
        return True

    def vote_for_candidate(self, voter_id, candidate_id):
        # basic checks
        if voter_id not in self.users:
            print("Voter is not registered.")
            return False
        if candidate_id not in self.users:
            print("Candidate is not registered.")
            return False
        # Candidate eligibility: in many systems delegates must be specific roles; we'll allow any registered user
        voter_stake = self.stakes.get(voter_id, 0)
        if voter_stake <= 0:
            print("You must stake tokens before voting.")
            return False

        # If voter previously voted, deduct their stake from previous candidate
        prev = self.voter_choice.get(voter_id)
        if prev:
            self.votes[prev] = max(0, self.votes.get(prev, 0) - voter_stake)
            log_action(f"VOTE: {voter_id} removed vote from {prev} (lost {voter_stake} weight).")

        # Add vote to new candidate
        self.votes[candidate_id] = self.votes.get(candidate_id, 0) + voter_stake
        self.voter_choice[voter_id] = candidate_id
        print(f"{voter_id} voted for {candidate_id} with weight {voter_stake}.")
        log_action(f"VOTE: {voter_id} voted for {candidate_id} (weight {voter_stake}).")
        return True

    def elect_delegates(self):
        # Elect top `max_delegates` candidates by vote total
        if not self.votes:
            print("No votes present. No delegates elected.")
            return []
        # Sort candidates by votes descending
        sorted_candidates = sorted(self.votes.items(), key=lambda kv: kv[1], reverse=True)
        top_candidates = [candidate for candidate, votes in sorted_candidates[:self.max_delegates]]
        self.delegates = top_candidates
        self.current_delegate_index = 0  # reset rotation
        print(f"Elected delegates: {', '.join(self.delegates)}")
        log_action(f"ELECTION: Delegates elected: {', '.join(self.delegates)}")
        return self.delegates

    def get_delegate_list(self):
        return list(self.delegates)

    # -------- Forging (DPoS) --------
    def forge_block(self, delegate_id):
        # 1. Check if delegates exist
        if not self.delegates:
            print("No delegates configured. Please elect delegates first.")
            log_action(f"FAILED FORGE ATTEMPT: {delegate_id} attempted to forge but no delegates are elected.")
            return None

        # 2. Check if the person forging is a registered delegate
        if delegate_id not in self.delegates:
            print(f"Error: {delegate_id} is not a registered delegate.")
            log_action(f"FAILED FORGE ATTEMPT: {delegate_id} is not a delegate.")
            return None

        # 3. Check if it's their turn
        expected_delegate = self.delegates[self.current_delegate_index]
        if delegate_id != expected_delegate:
            print(f"Error: It is not {delegate_id}'s turn. It is {expected_delegate}'s turn.")
            log_action(f"FAILED FORGE ATTEMPT: {delegate_id} tried to forge out of turn.")
            return None

        # 4. Check pending transactions
        if not self.pending_transactions:
            print("No pending transactions to forge.")
            return None

        last_block = self.get_last_block()
        new_block = Block(
            transactions=self.pending_transactions.copy(),  # use a copy to persist TXs correctly
            previous_hash=last_block.hash,
            delegate_id=delegate_id
        )

        # Append and clear pending txs
        self.chain.append(new_block)
        self.pending_transactions = []

        # 5. Rotate to next delegate
        self.current_delegate_index = (self.current_delegate_index + 1) % len(self.delegates)

        print(f"Block #{len(self.chain)-1} successfully forged by {delegate_id}.")
        log_action(f"CONSENSUS: Block forged by delegate {delegate_id}. Hash: {new_block.hash}")
        return new_block

    # -------- Helper: get patient history (returns data for main.py display) --------
    def get_patient_history(self, patient_id):
        history = []
        for block_index, block in enumerate(self.chain):
            for tx in block.transactions:
                if tx.patient_id == patient_id:
                    history.append({
                        "block_index": block_index,
                        "record_id": tx.record_id,
                        "operation": tx.operation,
                        "doctor_id": tx.doctor_id,
                        "hospital_id": tx.hospital_id,
                        "prescription": tx.prescription,
                        "timestamp": tx.timestamp
                    })
        return history

    # Optional: quick debug print for chain
    def print_chain(self):
        for i, b in enumerate(self.chain):
            print(f"--- Block #{i} ---")
            print(f"Timestamp: {b.timestamp}")
            print(f"Delegate: {b.delegate_id}")
            print(f"Prev Hash: {b.previous_hash}")
            print(f"Merkle Root: {b.merkle_root}")
            print(f"Hash: {b.hash}")
            print(f"Transactions: {len(b.transactions)}")
            for tx in b.transactions:
                print(f"  - {tx.record_id} @ {tx.patient_id} by {tx.doctor_id}")
            print("---------------")
