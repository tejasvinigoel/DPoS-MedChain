from flask import Flask, render_template, request, redirect, url_for, flash
from blockchain import Blockchain, Transaction
from utils import log_action
import os
import pickle

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Filename for saving the blockchain state ---
BLOCKCHAIN_FILE = "blockchain.pkl"

# --- Function to save the blockchain ---
def save_blockchain(blockchain_obj):
    with open(BLOCKCHAIN_FILE, "wb") as f:
        pickle.dump(blockchain_obj, f)

# --- Check if a saved blockchain exists ---
if os.path.exists(BLOCKCHAIN_FILE):
    print("Loading existing blockchain from file...")
    with open(BLOCKCHAIN_FILE, "rb") as f:
        healthcare_blockchain = pickle.load(f)
else:
    print("No saved blockchain found. Creating a new one...")
    healthcare_blockchain = Blockchain(max_delegates=2)
    demo_users = [
        ("admin", "Admin User", "Administrator"),
        ("dr_alice", "Dr. Alice", "Doctor"),
        ("dr_bob", "Dr. Bob", "Doctor"),
        ("patient_x", "Patient X", "Patient"),
        ("patient_y", "Patient Y", "Patient"),
    ]
    for user_id, name, role in demo_users:
        healthcare_blockchain.register_user(user_id, name, role)
    save_blockchain(healthcare_blockchain)

def get_blockchain_stats():
    """Calculate real-time blockchain statistics, including pending consent."""
    stats = {}
    stats['total_blocks'] = len(healthcare_blockchain.chain)
    stats['verified_users'] = len(healthcare_blockchain.users)
    stats['pending_transactions'] = len(healthcare_blockchain.pending_transactions)
    stats['pending_consent'] = len(healthcare_blockchain.pending_consent_transactions)
    stats['current_delegates'] = len(healthcare_blockchain.delegates)
    stats['total_records'] = sum(len(b.transactions) for b in healthcare_blockchain.chain)
    return stats

# -------- Routes --------
@app.route("/")
def index():
    stats = get_blockchain_stats()
    blocks = [{'index': i, 'hash': b.hash, 'transaction_count': len(b.transactions)} for i, b in enumerate(healthcare_blockchain.chain)]
    delegates = healthcare_blockchain.get_delegate_list() or ["(none elected)"]
    next_delegate = (
        delegates[healthcare_blockchain.current_delegate_index]
        if healthcare_blockchain.delegates
        else "(none)"
    )
    return render_template("base.html", stats=stats, blocks=blocks, delegates=delegates, next_delegate=next_delegate)

@app.route("/add_record", methods=["GET", "POST"])
def add_record():
    if request.method == "POST":
        doctor_id = request.form["doctor_id"]
        if healthcare_blockchain.users.get(doctor_id, {}).get("role") != "Doctor":
            flash("Only doctors can add records!", "danger")
            return redirect(url_for("add_record"))

        patient_id = request.form["patient_id"]
        hospital_id = request.form["hospital_id"]
        insurance_id = request.form["insurance_id"]
        record_type = request.form["record_type"]
        operation = request.form["operation"]
        prescription = request.form["prescription"]
        amount = request.form["amount"]
        target_id = request.form.get("target_id")

        healthcare_blockchain.add_transaction(
            hospital_id, doctor_id, patient_id, insurance_id,
            record_type, operation, prescription, amount, target_id
        )
        save_blockchain(healthcare_blockchain)
        flash(f"Medical record submitted for patient consent!", "success")
        return redirect(url_for("index"))
    return render_template("add_record.html")

@app.route("/patient_dashboard", methods=["GET", "POST"])
def patient_dashboard():
    pending_records = []
    patient_id = None
    if request.method == "POST":
        patient_id = request.form["patient_id"]
        for tx in healthcare_blockchain.pending_consent_transactions:
            if tx.patient_id == patient_id:
                pending_records.append(tx)
        if not pending_records:
            flash("You have no records awaiting your approval.", "info")
    return render_template("patient_dashboard.html", records=pending_records, patient_id=patient_id)

@app.route("/approve_record/<patient_id>/<tx_hash>", methods=["POST"])
def approve_record(patient_id, tx_hash):
    approved_tx = healthcare_blockchain.approve_transaction(tx_hash, patient_id)
    if approved_tx:
        if approved_tx.operation == 'Share' and approved_tx.target_id:
            healthcare_blockchain.grant_access(patient_id, approved_tx.target_id)
        save_blockchain(healthcare_blockchain)
        flash("Record approved successfully! It is now ready to be forged.", "success")
    else:
        flash("Error approving record. It may have already been approved or you are not authorized.", "danger")
    return redirect(url_for('patient_dashboard'))

@app.route("/forge_block", methods=["GET", "POST"])
def forge_block():
    if request.method == "POST":
        delegate_id = request.form["delegate_id"]
        new_block = healthcare_blockchain.forge_block(delegate_id)
        if new_block:
            save_blockchain(healthcare_blockchain)
            flash(f"Block #{len(healthcare_blockchain.chain)-1} successfully forged by {delegate_id}!", "success")
        else:
            flash(f"Failed to forge block. Check if it's your turn and if there are pending transactions.", "warning")
        return redirect(url_for("index"))
    return render_template("forge_block.html")

@app.route("/view_history", methods=["GET", "POST"])
def view_history():
    history = None
    if request.method == "POST":
        viewer_id = request.form["viewer_id"]
        patient_id = request.form["patient_id"]
        if healthcare_blockchain.check_access(viewer_id, patient_id):
            history = healthcare_blockchain.get_patient_history(patient_id)
            flash(f"Successfully retrieved {len(history)} records for patient {patient_id}", "info")
            log_action(f"ACCESS: {viewer_id} viewed history for {patient_id}")
        else:
            flash("Access Denied: You are not authorized to view this patient's records.", "danger")
            log_action(f"ACCESS DENIED: {viewer_id} tried to access records for {patient_id}")
    return render_template("view_history.html", history=history)

@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        user_id = request.form["user_id"]
        name = request.form["name"]
        role = request.form["role"]
        if user_id in healthcare_blockchain.users:
            flash(f"User ID '{user_id}' already exists!", "warning")
            return redirect(url_for("register_user"))
        healthcare_blockchain.register_user(user_id, name, role)
        save_blockchain(healthcare_blockchain)
        flash(f"User {name} successfully registered as {role}!", "success")
        return redirect(url_for("index"))
    return render_template("register_user.html")

@app.route("/stake", methods=["GET", "POST"])
def stake():
    if request.method == "POST":
        user_id = request.form["user_id"]
        amount = int(request.form["amount"])
        if healthcare_blockchain.stake_tokens(user_id, amount):
            save_blockchain(healthcare_blockchain)
            flash(f"{user_id} successfully staked {amount} tokens!", "success")
        else:
            flash(f"Staking failed. Check user ID and amount.", "danger")
        return redirect(url_for("index"))
    return render_template("stake.html")

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        voter_id = request.form["voter_id"]
        candidate_id = request.form["candidate_id"]
        if healthcare_blockchain.vote_for_candidate(voter_id, candidate_id):
            save_blockchain(healthcare_blockchain)
            flash(f"{voter_id} successfully voted for {candidate_id}!", "success")
        else:
            flash("Voting failed. Ensure voter has staked tokens.", "danger")
        return redirect(url_for("index"))
    return render_template("vote.html")

@app.route("/elect_delegates")
def elect_delegates():
    new_delegates = healthcare_blockchain.elect_delegates()
    save_blockchain(healthcare_blockchain)
    flash(f"Delegates elected successfully: {', '.join(new_delegates)}!", "success")
    return redirect(url_for("index"))

@app.route("/view_access_log", methods=["GET", "POST"])
def view_access_log():
    log_content = None
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        if healthcare_blockchain.users.get(admin_id, {}).get("role") == "Administrator":
            try:
                with open("access_log.txt", "r") as f:
                    log_content = f.read()
            except FileNotFoundError:
                log_content = "Access log is empty or file not found."
        else:
            flash("Access Denied: Only administrators can view the access log.", "danger")
            return redirect(url_for("index"))
    return render_template("view_access_log.html", log_content=log_content)

@app.route("/view_blocks")
def view_blocks():
    blocks_data = []
    for i, block in enumerate(healthcare_blockchain.chain):
        blocks_data.append({ 'index': i, 'timestamp': block.timestamp, 'hash': block.hash, 'previous_hash': block.previous_hash, 'transaction_count': len(block.transactions) })
    return render_template("view_blocks.html", blocks=blocks_data)

@app.route("/view_block/<int:block_index>")
def view_block_detail(block_index):
    if block_index >= len(healthcare_blockchain.chain) or block_index < 0:
        flash(f"Block #{block_index} does not exist!", "danger")
        return redirect(url_for("view_blocks"))
    block = healthcare_blockchain.chain[block_index]
    block_detail = { 'index': block_index, 'timestamp': block.timestamp, 'merkle_root': block.merkle_root, 'previous_hash': block.previous_hash, 'nonce': block.nonce, 'hash': block.hash, 'transactions': [tx.to_dict() for tx in block.transactions], 'transaction_count': len(block.transactions) }
    return render_template("view_block_detail.html", block=block_detail)

@app.route("/validate")
def validate():
    is_valid = healthcare_blockchain.validate_chain()
    if is_valid:
        flash("Chain is valid and has not been tampered with!", "success")
    else:
        flash("CHAIN INVALID! Tampering has been detected. Check logs for details.", "danger")
    return redirect(url_for("index"))

@app.route("/deny_record/<patient_id>/<tx_hash>", methods=["POST"])
def deny_record(patient_id, tx_hash):
    success = healthcare_blockchain.deny_transaction(tx_hash, patient_id)
    if success:
        save_blockchain(healthcare_blockchain)
        flash("Record denied and removed successfully.", "info")
    else:
        flash("Error denying record.", "danger")
    
    return redirect(url_for('patient_dashboard'))

if __name__ == "__main__":
    app.run(debug=True, port=8000)