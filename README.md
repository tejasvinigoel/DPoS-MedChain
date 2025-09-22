MedChain: A DPoS Healthcare Blockchain Platform

Introduction
In the modern healthcare landscape, managing patient records securely is a paramount challenge. Traditional centralized systems are often vulnerable to data tampering, unauthorized edits, and disputes over record authenticity. This project, MedChain, addresses these challenges by implementing a secure, tamper-proof patient record management system using blockchain technology.

The platform is a fully functional web application built with Python and Flask. It utilizes a custom blockchain with a Delegated Proof-of-Stake (DPoS) consensus mechanism, digital signatures, and a robust patient consent model to create a transparent and auditable environment for handling sensitive medical data.

Feature Implementation
This section details how each specific requirement from the assignment brief has been implemented.

1. User Registration and Record Management

Requirement: Register new patients, doctors, and hospital administrators. Doctors can add or update patient records with patient consent.

The system fully supports the registration and management of three distinct user roles: Patient, Doctor, and Administrator.

Registration: New users are created through the /register_user route in app.py. The register_user method in blockchain.py handles the core logic. Upon creation, each user is assigned:

A securely hashed password using Flask-Bcrypt for authentication.

A unique RSA public/private key pair via the cryptography library for signing transactions.

Patient Consent: The requirement for "patient consent" has been implemented as a robust, two-step workflow:

A doctor submits a new record, which enters a pending_consent_transactions pool.

The specific patient must log in to their personal dashboard (/patient_dashboard) and explicitly Approve or Deny the record.

Only upon approval is the transaction considered valid and eligible to be included in a block by a delegate.

2. Consensus Algorithm: Delegated Proof-of-Stake (DPoS)

Requirement: Include the assigned consensus algorithm (DPoS).

The Delegated Proof-of-Stake algorithm is the core mechanism for achieving consensus and adding new blocks to the chain. It is fully implemented through the following components:

Staking: Users can stake tokens to gain influence in the network. This is handled by the /stake route in app.py and the stake_tokens method in blockchain.py.

Voting: A user's staked tokens act as their voting power. They can cast a vote for a delegate candidate via the /vote route, which calls the vote_for_candidate method.

Election: The /elect_delegates route triggers an election, where the candidates with the highest total vote weight are chosen as the active delegates.

Block Forging: Forging new blocks is restricted to the elected delegates. The forge_block method in blockchain.py strictly enforces that only the correct delegate, acting in their designated turn, can create and add the next block to the chain.

3. Merkle Tree

Requirement: Calculate the Merkle root to hash all medical record transactions in a block.

Every block on the chain contains a Merkle root to ensure the integrity of its transaction list.

Implementation: The Block class in blockchain.py contains a calculate_merkle_root method.

Process: When a block is created, this method takes the unique hash of every transaction within it. It then recursively pairs and hashes these values until a single root hash is produced. This merkle_root is stored as an attribute of the block and is included in the block's own hash calculation, making it impossible to alter any transaction without invalidating the entire chain.

4. Record History Viewing

Requirement: Allow any authorized user (patient or administrator) to view the complete, tamper-proof history of any individual medical record.

The application provides a secure interface for viewing patient history, with an access control model that is more granular and secure than the base requirement.

Interface: The /view_history route in app.py provides the user interface.

Authorization: The check_access method in blockchain.py enforces the authorization rules. Access to a patient's history is granted only if the viewer is:

The patient themselves.

An Administrator (for auditing purposes).

5. Access Logs

Requirement: Consolidate a log of every attempted access and modification to each record, visible to administrators.

A comprehensive audit trail is generated for all significant system events.

Logging Mechanism: The log_action function in utils.py writes a timestamped message for each event to the access_log.txt file.

Logged Events: This includes user registrations, logins, failed access attempts, record submissions, block forging, and, critically, all proof of consent actions (who approved or denied a specific record and when).

Administrator View: The /view_access_log route is a protected page in app.py that allows a logged-in Administrator to view the full content of the access log.

Data Structure Implementation
The Transaction and Block classes in blockchain.py are structured to meet all specified requirements.

Transaction Structure

The Transaction class includes the following attributes:

Hospital ID/Name (hospital_id)

Doctor ID/Name (doctor_id)

Patient ID/Name (patient_id)

Insurance ID/Name (insurance_id)

Record ID/Type (record_id, record_type)

Operation (Add/Update/Share) (operation)

Prescription (prescription)

Amount (amount)

Timestamp (timestamp)

Additional Security Fields: signature and target_id (for sharing).

Block Structure

The Block class includes the following attributes:

Timestamp (timestamp)

Merkle Root of Transactions (merkle_root)

Hash of Previous Block (previous_hash)

Nonce/Consensus-related Data:

nonce: An auto-incrementing number for hash uniqueness.

delegate_id: The ID of the DPoS delegate who forged the block.

How to Run the Application
Prerequisites: Ensure you have Python 3 and pip installed.

Installation: Clone the repository and install the required dependencies from requirements.txt.

Bash
pip install -r requirements.txt
Running: Execute the main Flask application.

Bash
python app.py
Access: Open a web browser and navigate to http://127.0.0.1:8000.
