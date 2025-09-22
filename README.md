# **MedChain: A DPoS Healthcare Blockchain Platform**

## **Introduction**
In the modern healthcare landscape, managing patient records securely is a paramount challenge. Traditional centralized systems are often vulnerable to data tampering, unauthorized edits, and disputes over record authenticity.  

This project, **MedChain**, addresses these challenges by implementing a secure, tamper-proof patient record management system using blockchain technology.

The platform is a fully functional web application built with **Python** and **Flask**. It utilizes a custom blockchain with a **Delegated Proof-of-Stake (DPoS)** consensus mechanism, **digital signatures**, and a robust **patient consent model** to create a transparent and auditable environment for handling sensitive medical data.

---

## **Feature Implementation**
This section details how each specific requirement from the assignment brief has been implemented.

### **1. User Registration and Record Management**
**Requirement:** Register new patients, doctors, and hospital administrators. Doctors can add or update patient records with patient consent.

- The system supports three distinct user roles: **Patient, Doctor, Administrator**.  

**Registration:**  
- New users are created through the `/register_user` route in `app.py`.  
- The `register_user` method in `blockchain.py` handles the core logic.  
- Upon creation, each user is assigned:
  - A securely hashed password using **Flask-Bcrypt**.  
  - A unique RSA **public/private key pair** via the **cryptography** library for signing transactions.

**Patient Consent Workflow:**  
1. A doctor submits a new record → enters `pending_consent_transactions` pool.  
2. Patient logs in to `/patient_dashboard` → explicitly **Approve** or **Deny** the record.  
3. Only approved transactions are included in a block by a delegate.

---

### **2. Consensus Algorithm: Delegated Proof-of-Stake (DPoS)**
**Requirement:** Include the assigned consensus algorithm (DPoS).  

- **Staking:** Users can stake tokens via `/stake` and `stake_tokens` in `blockchain.py`.  
- **Voting:** Staked tokens act as voting power. Users vote via `/vote` → `vote_for_candidate`.  
- **Election:** `/elect_delegates` triggers delegate elections.  
- **Block Forging:** Only elected delegates can create new blocks (`forge_block` in `blockchain.py`).

---

### **3. Merkle Tree**
**Requirement:** Calculate the Merkle root to hash all medical record transactions in a block.

- **Implementation:** `calculate_merkle_root` method in `Block` class (`blockchain.py`).  
- **Process:** Hash all transaction hashes recursively to get a single root.  
- Stored as `merkle_root` in the block → ensures integrity.

---

### **4. Record History Viewing**
**Requirement:** Allow authorized users to view complete, tamper-proof history of any medical record.

- **Interface:** `/view_history` route in `app.py`.  
- **Authorization:** `check_access` in `blockchain.py` enforces rules:
  - Patient themselves  
  - Administrator for auditing

---

### **5. Access Logs**
**Requirement:** Maintain logs for every access/modification attempt.

- **Logging Mechanism:** `log_action` in `utils.py` writes timestamped messages to `access_log.txt`.  
- **Logged Events:** Registrations, logins, failed access, record submissions, block forging, patient consent actions.  
- **Administrator View:** `/view_access_log` → protected page for admin audit.

---

## **Data Structure Implementation**

### **Transaction Structure**
Attributes in `Transaction` class:
- `hospital_id`, `doctor_id`, `patient_id`, `insurance_id`  
- `record_id`, `record_type`, `operation` (Add/Update/Share)  
- `prescription`, `amount`, `timestamp`  
- Additional security fields: `signature`, `target_id` (for sharing)

### **Block Structure**
Attributes in `Block` class:
- `timestamp`  
- `merkle_root` (Merkle root of transactions)  
- `previous_hash`  
- Nonce/Consensus data:
  - `nonce` (auto-incrementing number for hash uniqueness)  
  - `delegate_id` (ID of the DPoS delegate who forged the block)

---

## **How to Run the Application**

### **Prerequisites**
- Python 3 and pip installed

### **Installation**
```bash
git clone <your-repo-url>
pip install -r requirements.txt
