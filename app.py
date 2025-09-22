from flask import Flask, render_template, request, redirect, url_for, flash
from blockchain import Blockchain, Transaction
from utils import log_action
import os
from datetime import datetime
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
    # Initialize a new blockchain
    healthcare_blockchain = Blockchain(max_delegates=2)

    # Pre-register demo users ONCE
    demo_users = [
        ("admin", "Admin User", "Administrator"),
        ("dr_alice", "Dr. Alice", "Doctor"),
        ("dr_bob", "Dr. Bob", "Doctor"),
        ("patient_x", "Patient X", "Patient"),
        ("patient_y", "Patient Y", "Patient"),
    ]
    for user_id, name, role in demo_users:
        healthcare_blockchain.register_user(user_id, name, role)

    # Save the new blockchain for the first time
    save_blockchain(healthcare_blockchain)

def get_blockchain_stats():
    """Calculate real-time blockchain statistics"""
    try:
        # Total number of records (transactions across all blocks)
        total_records = 0
        for block in healthcare_blockchain.chain:
            if hasattr(block, 'transactions') and block.transactions:
                total_records += len(block.transactions)
        
        # Active validators (users with stake > 0)
        active_validators = 0
        if hasattr(healthcare_blockchain, 'stakes'):
            active_validators = len([user for user, stake in healthcare_blockchain.stakes.items() if stake > 0])
                
        # Verified users (total registered users)
        verified_users = len(healthcare_blockchain.users) if healthcare_blockchain.users else 0
        
        # Additional stats
        total_blocks = len(healthcare_blockchain.chain)
        pending_transactions = len(healthcare_blockchain.pending_transactions) if healthcare_blockchain.pending_transactions else 0
        current_delegates = len(healthcare_blockchain.delegates) if healthcare_blockchain.delegates else 0
        
        return {
            'total_records': total_records,
            'active_validators': active_validators,
            'verified_users': verified_users,
            'total_blocks': total_blocks,
            'pending_transactions': pending_transactions,
            'current_delegates': current_delegates
        }
    except Exception as e:
        # Fallback to default values if there's an error
        return {
            'total_records': 0,
            'active_validators': 0,
            'verified_users': len(healthcare_blockchain.users) if healthcare_blockchain.users else 0,
            'total_blocks': len(healthcare_blockchain.chain) if healthcare_blockchain.chain else 0,
            'pending_transactions': 0,
            'current_delegates': 0
        }


# def get_recent_blocks(limit=4):
#     """Get recent blocks for the blockchain visualization"""
#     try:
#         recent_blocks = []
#         chain_length = len(healthcare_blockchain.chain)
        
#         # Get the last 'limit' blocks
#         start_index = max(0, chain_length - limit)
#         for i in range(start_index, chain_length):
#             block = healthcare_blockchain.chain[i]
            
#             # Count transactions in this block
#             tx_count = len(block.transactions) if hasattr(block, 'transactions') and block.transactions else 0
            
#             # Calculate time ago (you might need to add timestamp to your Block class)
#             time_ago = f"{(i * 2) + 2}m ago"  # Placeholder calculation
            
#             recent_blocks.append({
#                 'index': i,
#                 'transaction_count': tx_count,
#                 'time_ago': time_ago
#             })
        
#         return recent_blocks
#     except Exception as e:
#         # Return sample data if there's an error
#         return [
#             {'index': 1024, 'transaction_count': 3, 'time_ago': '2m ago'},
#             {'index': 1025, 'transaction_count': 7, 'time_ago': '5m ago'},
#             {'index': 1026, 'transaction_count': 2, 'time_ago': '8m ago'},
#             {'index': 1027, 'transaction_count': 5, 'time_ago': '12m ago'},
#         ]


# -------- Routes --------
@app.route("/")
def index():
    # Get dynamic statistics
    stats = get_blockchain_stats()
    
    # Pass all blocks for visualization
    blocks = []
    for i, block in enumerate(healthcare_blockchain.chain):
        blocks.append({
            'index': i,
            'timestamp': getattr(block, 'timestamp', 'N/A'),
            'hash': getattr(block, 'hash', 'N/A'),
            'transaction_count': len(getattr(block, 'transactions', []))
        })

    delegates = healthcare_blockchain.get_delegate_list() or ["(none elected)"]
    next_delegate = (
        delegates[healthcare_blockchain.current_delegate_index]
        if healthcare_blockchain.delegates
        else "(none)"
    )
    
    return render_template(
        "base.html", 
        stats=stats,
        blocks=blocks,          # <-- pass blocks here
        delegates=delegates, 
        next_delegate=next_delegate
    )

# AFTER
@app.route("/add_record", methods=["GET", "POST"])
def add_record():
    if request.method == "POST":
        doctor_id = request.form["doctor_id"]
        # ... (doctor check) ...
        
        # Get all form data EXCEPT the record_id
        patient_id = request.form["patient_id"]
        hospital_id = request.form["hospital_id"]
        insurance_id = request.form["insurance_id"]
        record_type = request.form["record_type"]
        operation = request.form["operation"]
        prescription = request.form["prescription"]
        amount = request.form["amount"]

        # Call the new blockchain method, which will generate the ID
        healthcare_blockchain.add_transaction(
            hospital_id, doctor_id, patient_id, insurance_id, record_type, operation, prescription, amount
        )
        
        save_blockchain(healthcare_blockchain)
        flash(f"Medical record submitted for patient consent! It will be assigned a new ID upon creation.", "success")
        log_action(f"TRANSACTION: Doctor {doctor_id} created a new record for {patient_id}")
        return redirect(url_for("index"))

    return render_template("add_record.html")


@app.route("/forge_block", methods=["GET", "POST"])
def forge_block():
    if request.method == "POST":
        try:
            delegate_id = request.form["delegate_id"]
            
            # Check if user is authorized to forge blocks
            if not healthcare_blockchain.delegates or delegate_id not in healthcare_blockchain.delegates:
                flash(f"Error: {delegate_id} is not an authorized delegate!", "danger")
                return redirect(url_for("forge_block"))
            
            new_block = healthcare_blockchain.forge_block(delegate_id)
            if new_block:
                save_blockchain(healthcare_blockchain)
                flash(f"🎉 Block #{len(healthcare_blockchain.chain)-1} successfully forged by {delegate_id}!", "success")
                log_action(f"BLOCK FORGED: Delegate {delegate_id} forged block #{len(healthcare_blockchain.chain)-1}")
            else:
                flash("No pending transactions to forge into a block.", "warning")
                
        except Exception as e:
            flash(f"Error forging block: {str(e)}", "danger")
            
        return redirect(url_for("index"))
    return render_template("forge_block.html")


@app.route("/view_history", methods=["GET", "POST"])
def view_history():
    history = None
    if request.method == "POST":
        viewer_id = request.form["viewer_id"]
        patient_id = request.form["patient_id"]
        viewer_role = healthcare_blockchain.users.get(viewer_id, {}).get("role")
        
        if viewer_id == patient_id or viewer_role == "Administrator" or viewer_role == "Doctor":
            history = healthcare_blockchain.get_patient_history(patient_id)
            if history:
                flash(f"✅ Successfully retrieved {len(history)} records for patient {patient_id}", "success")
                log_action(f"ACCESS: {viewer_id} ({viewer_role}) viewed history for {patient_id}") # Log with role
            else:
                flash(f"No medical records found for patient {patient_id}", "info")
        else:
            flash("🚫 Access Denied: You are not authorized to view this patient's records.", "danger")
            log_action(f"ACCESS DENIED: {viewer_id} tried to access records for {patient_id}")
           
    return render_template("view_history.html", history=history)


@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        try:
            user_id = request.form["user_id"]
            name = request.form["name"]
            role = request.form["role"]
            
            # Check if user already exists
            if user_id in healthcare_blockchain.users:
                flash(f"⚠️ User {user_id} already exists!", "warning")
                return redirect(url_for("register_user"))
            
            healthcare_blockchain.register_user(user_id, name, role)
            save_blockchain(healthcare_blockchain) # <-- ADD THIS LINE

            flash(f"🎉 User {name} successfully registered as {role}!", "success")
            log_action(f"USER REGISTERED: {name} ({user_id}) registered as {role}")
            
        except Exception as e:
            flash(f"Registration error: {str(e)}", "danger")
            
        return redirect(url_for("index"))
    return render_template("register_user.html")


@app.route("/stake", methods=["GET", "POST"])
def stake():
    if request.method == "POST":
        try:
            user_id = request.form["user_id"]
            amount = int(request.form["amount"])
            
            if user_id not in healthcare_blockchain.users:
                flash(f"Error: User {user_id} is not registered!", "danger")
                return redirect(url_for("stake"))
            
            if amount <= 0:
                flash("Stake amount must be positive!", "danger")
                return redirect(url_for("stake"))
            
            healthcare_blockchain.stake_tokens(user_id, amount)
            save_blockchain(healthcare_blockchain) # <-- ADD THIS LINE

            flash(f"💰 {user_id} successfully staked {amount} tokens!", "success")
            log_action(f"STAKE: {user_id} staked {amount} tokens")
            
        except Exception as e:
            flash(f"Staking error: {str(e)}", "danger")
            
        return redirect(url_for("index"))
    return render_template("stake.html")


@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        try:
            voter_id = request.form["voter_id"]
            candidate_id = request.form["candidate_id"]
            
            if voter_id not in healthcare_blockchain.users:
                flash(f"Error: Voter {voter_id} is not registered!", "danger")
                return redirect(url_for("vote"))
            
            if candidate_id not in healthcare_blockchain.users:
                flash(f"Error: Candidate {candidate_id} is not registered!", "danger")
                return redirect(url_for("vote"))
            
            healthcare_blockchain.vote_for_candidate(voter_id, candidate_id)
            save_blockchain(healthcare_blockchain) # <-- ADD THIS LINE

            flash(f"🗳️ {voter_id} successfully voted for {candidate_id}!", "success")
            log_action(f"VOTE: {voter_id} voted for {candidate_id}")
            
        except Exception as e:
            flash(f"Voting error: {str(e)}", "danger")
            
        return redirect(url_for("index"))
    return render_template("vote.html")


@app.route("/elect_delegates")
def elect_delegates():
    try:
        healthcare_blockchain.elect_delegates()
        save_blockchain(healthcare_blockchain) # <-- ADD THIS LINE

        new_delegates = healthcare_blockchain.get_delegate_list()
        flash(f"🏆 Delegates elected successfully: {', '.join(new_delegates)}!", "success")
        log_action(f"DELEGATES ELECTED: {', '.join(new_delegates)}")
        
    except Exception as e:
        flash(f"Election error: {str(e)}", "danger")
        
    return redirect(url_for("index"))


@app.route("/view_access_log", methods=["GET", "POST"])
def view_access_log():
    log_content = None
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        
        # Check if the user is an administrator
        if healthcare_blockchain.users.get(admin_id, {}).get("role") == "Administrator":
            try:
                with open("access_log.txt", "r") as f:
                    log_content = f.read()
                flash("📋 Access log loaded successfully!", "info")
                log_action(f"ADMIN: {admin_id} viewed the access log.")
            except FileNotFoundError:
                log_content = "Access log is empty or file not found."
                flash("⚠️ No access log file found", "warning")
        else:
            flash("🚫 Access Denied: Only administrators can view the access log.", "danger")
            log_action(f"ACCESS DENIED: Non-admin {admin_id} attempted to view the access log.")
            return redirect(url_for("index")) # Redirect to home on failure

    return render_template("view_access_log.html", log_content=log_content)

@app.route("/view_blocks")
def view_blocks():
    """View detailed block structure"""
    try:
        blocks_data = []
        for i, block in enumerate(healthcare_blockchain.chain):
            block_info = {
                'index': i,
                'timestamp': getattr(block, 'timestamp', 'N/A'),
                'merkle_root': getattr(block, 'merkle_root', 'N/A'),
                'previous_hash': getattr(block, 'previous_hash', 'N/A'),
                'nonce': getattr(block, 'nonce', 'N/A'),
                'hash': getattr(block, 'hash', 'N/A'),
                'transactions': getattr(block, 'transactions', []),
                'transaction_count': len(getattr(block, 'transactions', []))
            }
            blocks_data.append(block_info)
        
        flash(f"📊 Displaying {len(blocks_data)} blocks from the blockchain", "info")
        return render_template("view_blocks.html", blocks=blocks_data)
        
    except Exception as e:
        flash(f"Error loading blocks: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/view_block/<int:block_index>")
def view_block_detail(block_index):
    """View detailed information for a specific block"""
    try:
        if block_index >= len(healthcare_blockchain.chain) or block_index < 0:
            flash(f"Block #{block_index} does not exist!", "danger")
            return redirect(url_for("view_blocks"))
        
        block = healthcare_blockchain.chain[block_index]
        
        block_detail = {
            'index': block_index,
            'timestamp': getattr(block, 'timestamp', 'N/A'),
            'merkle_root': getattr(block, 'merkle_root', 'N/A'),
            'previous_hash': getattr(block, 'previous_hash', 'N/A'),
            'nonce': getattr(block, 'nonce', 'N/A'),
            'hash': getattr(block, 'hash', 'N/A'),
            'transactions': getattr(block, 'transactions', []),
            'transaction_count': len(getattr(block, 'transactions', [])),
            'block_size': len(str(block)) if hasattr(block, '__str__') else 'N/A'
        }
        
        return render_template("view_block_detail.html", block=block_detail)
    except Exception as e:
        flash(f"Error loading block details: {str(e)}", "danger")
        return redirect(url_for("view_blocks"))

if __name__ == "__main__":
    app.run(debug=True, port=8000)