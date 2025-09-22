from flask import Flask, render_template, request, redirect, url_for, flash, session
from blockchain import Blockchain
from utils import log_action
import os
import pickle
from flask_bcrypt import Bcrypt
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"
bcrypt = Bcrypt(app)

# --- Persistence Logic ---
BLOCKCHAIN_FILE = "blockchain.pkl"
def save_blockchain(blockchain_obj):
    with open(BLOCKCHAIN_FILE, "wb") as f:
        pickle.dump(blockchain_obj, f)

if os.path.exists(BLOCKCHAIN_FILE):
    with open(BLOCKCHAIN_FILE, "rb") as f:
        healthcare_blockchain = pickle.load(f)
else:
    healthcare_blockchain = Blockchain(max_delegates=2)
    demo_users = [
        ("admin", "Admin User", "Administrator", "password123"),
        ("dr_alice", "Dr. Alice", "Doctor", "password123"),
        ("dr_bob", "Dr. Bob", "Doctor", "password123"),
        ("patient_x", "Patient X", "Patient", "password123"),
        ("patient_y", "Patient Y", "Patient", "password123"),
    ]
    for user_id, name, role, password in demo_users:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        healthcare_blockchain.register_user(user_id, name, role, hashed_password)
    save_blockchain(healthcare_blockchain)

# --- Helper Functions ---
def get_blockchain_stats():
    stats = {}
    stats['total_blocks'] = len(healthcare_blockchain.chain)
    stats['verified_users'] = len(healthcare_blockchain.users)
    stats['pending_transactions'] = len(healthcare_blockchain.pending_transactions)
    stats['pending_consent'] = len(healthcare_blockchain.pending_consent_transactions)
    stats['current_delegates'] = len(healthcare_blockchain.delegates)
    stats['total_records'] = sum(len(b.transactions) for b in healthcare_blockchain.chain)
    return stats

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form['user_id']
        password = request.form['password']
        user = healthcare_blockchain.users.get(user_id)
        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user_id
            session['name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash("Login failed. Please check your user ID and password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        user_id = request.form["user_id"]
        name = request.form["name"]
        role = request.form["role"]
        password = request.form["password"]
        if user_id in healthcare_blockchain.users:
            flash(f"User ID '{user_id}' already exists!", "warning")
            return redirect(url_for("register_user"))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        healthcare_blockchain.register_user(user_id, name, role, hashed_password)
        save_blockchain(healthcare_blockchain)
        flash(f"User {name} successfully registered! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register_user.html")

# --- Main Application Routes ---
@app.route("/")
def index():
    stats = get_blockchain_stats()
    blocks = [{'index': i, 'hash': b.hash, 'transaction_count': len(b.transactions)} for i, b in enumerate(healthcare_blockchain.chain)]
    return render_template("base.html", stats=stats, blocks=blocks)

@app.route("/add_record", methods=["GET", "POST"])
@login_required
def add_record():
    if session['role'] != 'Doctor':
        flash("You are not authorized to add records.", "danger")
        return redirect(url_for('index'))
    if request.method == "POST":
        healthcare_blockchain.create_and_sign_transaction(
            hospital_id=request.form["hospital_id"], doctor_id=session['user_id'],
            patient_id=request.form["patient_id"], insurance_id=request.form["insurance_id"],
            record_type=request.form["record_type"], operation=request.form["operation"],
            prescription=request.form["prescription"], amount=request.form["amount"],
            target_id=request.form.get("target_id")
        )
        save_blockchain(healthcare_blockchain)
        flash(f"Medical record submitted for patient consent!", "success")
        return redirect(url_for("index"))
    return render_template("add_record.html")

@app.route("/patient_dashboard")
@login_required
def patient_dashboard():
    if session['role'] != 'Patient':
        flash("Only patients can access this dashboard.", "danger")
        return redirect(url_for('index'))
    patient_id = session['user_id']
    pending_records = [tx for tx in healthcare_blockchain.pending_consent_transactions if tx.patient_id == patient_id]
    return render_template("patient_dashboard.html", records=pending_records, patient_id=patient_id)

@app.route("/approve_record/<tx_hash>", methods=["POST"])
@login_required
def approve_record(tx_hash):
    patient_id = session['user_id']
    approved_tx = healthcare_blockchain.approve_transaction(tx_hash, patient_id)
    if approved_tx:
        if approved_tx.operation == 'Share' and approved_tx.target_id:
            healthcare_blockchain.grant_access(patient_id, approved_tx.target_id)
        save_blockchain(healthcare_blockchain)
        flash("Record approved successfully!", "success")
    else:
        flash("Error approving record.", "danger")
    return redirect(url_for('patient_dashboard'))

@app.route("/deny_record/<tx_hash>", methods=["POST"])
@login_required
def deny_record(tx_hash):
    if healthcare_blockchain.deny_transaction(tx_hash, session['user_id']):
        save_blockchain(healthcare_blockchain)
        flash("Record denied successfully.", "info")
    else:
        flash("Error denying record.", "danger")
    return redirect(url_for('patient_dashboard'))

@app.route("/forge_block", methods=["GET", "POST"])
@login_required
def forge_block():
    if request.method == "POST":
        if healthcare_blockchain.forge_block(session['user_id']):
            save_blockchain(healthcare_blockchain)
            flash(f"Block successfully forged!", "success")
        else:
            flash(f"Failed to forge block.", "warning")
        return redirect(url_for("index"))
    return render_template("forge_block.html")

@app.route("/view_history", methods=["GET", "POST"])
@login_required
def view_history():
    history = None
    # This block handles the search form submission from a Doctor or Admin
    if request.method == "POST":
        viewer_id = session['user_id']
        patient_id = request.form["patient_id"]
        
        if healthcare_blockchain.check_access(viewer_id, patient_id):
            history = healthcare_blockchain.get_patient_history(patient_id)
            log_action(f"ACCESS: {viewer_id} viewed history for {patient_id}")
        else:
            flash("Access Denied: You are not authorized to view this patient's records.", "danger")
            log_action(f"ACCESS DENIED: {viewer_id} tried to access records for {patient_id}")
            
    # This new block automatically loads data for a Patient on page visit
    if request.method == "GET" and session.get('role') == 'Patient':
        patient_id = session['user_id']
        history = healthcare_blockchain.get_patient_history(patient_id)
            
    return render_template("view_history.html", history=history)

@app.route("/stake", methods=["GET", "POST"])
@login_required
def stake():
    if request.method == "POST":
        amount = int(request.form["amount"])
        if healthcare_blockchain.stake_tokens(session['user_id'], amount):
            save_blockchain(healthcare_blockchain)
            flash(f"You successfully staked {amount} tokens!", "success")
        else:
            flash(f"Staking failed.", "danger")
    return render_template("stake.html")

@app.route("/vote", methods=["GET", "POST"])
@login_required
def vote():
    if request.method == "POST":
        voter_id = session['user_id']
        candidate_id = request.form["candidate_id"]
        if healthcare_blockchain.vote_for_candidate(voter_id, candidate_id):
            save_blockchain(healthcare_blockchain)
            flash(f"You successfully voted for {candidate_id}!", "success")
        else:
            flash("Voting failed. Ensure you have staked tokens and the candidate ID is valid.", "danger")
        return redirect(url_for("index"))
    
    # Pass a list of potential candidates (all users except the voter)
    candidates = [user for user in healthcare_blockchain.users if user != session.get('user_id')]
    return render_template("vote.html", candidates=candidates)

@app.route("/elect_delegates")
@login_required
def elect_delegates():
    new_delegates = healthcare_blockchain.elect_delegates()
    if new_delegates:
        save_blockchain(healthcare_blockchain)
        flash(f"Delegates elected successfully: {', '.join(new_delegates)}!", "success")
    else:
        flash("Election failed. No votes have been cast.", "warning")
    return redirect(url_for("index"))

@app.route("/view_access_log")
@login_required
def view_access_log():
    # Only allow administrators to view the log
    if session.get('role') != 'Administrator':
        flash("Access Denied: Only administrators can view the access log.", "danger")
        return redirect(url_for("index"))
    
    log_content = "Access log is empty or file not found."
    try:
        with open("access_log.txt", "r") as f:
            log_content = f.read()
        log_action(f"ADMIN: {session['user_id']} viewed the access log.")
    except FileNotFoundError:
        flash("No access log file found.", "warning")
        
    return render_template("view_access_log.html", log_content=log_content)

@app.route("/validate")
@login_required
def validate():
    if healthcare_blockchain.validate_chain():
        flash("Chain is valid and has not been tampered with!", "success")
    else:
        flash("CHAIN INVALID! Tampering has been detected.", "danger")
    return redirect(url_for("index"))

@app.route("/view_blocks")
@login_required
def view_blocks():
    """View a list of all blocks in the chain."""
    blocks_data = []
    for i, block in enumerate(healthcare_blockchain.chain):
        blocks_data.append({
            'index': i,
            'timestamp': block.timestamp,
            'hash': block.hash,
            'previous_hash': block.previous_hash,
            'transaction_count': len(block.transactions)
        })
    return render_template("view_blocks.html", blocks=blocks_data)


@app.route("/view_block/<int:block_index>")
@login_required
def view_block_detail(block_index):
    """View detailed information for a specific block."""
    if block_index >= len(healthcare_blockchain.chain) or block_index < 0:
        flash(f"Block #{block_index} does not exist!", "danger")
        return redirect(url_for("index"))

    block = healthcare_blockchain.chain[block_index]
    block_detail = {
        'index': block_index,
        'timestamp': block.timestamp,
        'merkle_root': block.merkle_root,
        'previous_hash': block.previous_hash,
        'nonce': block.nonce,
        'hash': block.hash,
        'transactions': [tx.to_dict() for tx in block.transactions],
        'transaction_count': len(block.transactions)
    }
    return render_template("view_block_detail.html", block=block_detail)

if __name__ == "__main__":
    app.run(debug=True, port=8000)