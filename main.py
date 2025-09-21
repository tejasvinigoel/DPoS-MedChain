from blockchain import Blockchain, Transaction
from utils import log_action

def main():
    healthcare_blockchain = Blockchain(max_delegates=2)  # change max_delegates as you like
    print("Healthcare Blockchain System Initialized.")
    log_action("SYSTEM: Application started.")

    # Pre-register demo users
    print("Registering demo users...")
    healthcare_blockchain.register_user("admin", "Admin User", "Administrator")
    healthcare_blockchain.register_user("dr_alice", "Dr. Alice", "Doctor")
    healthcare_blockchain.register_user("dr_bob", "Dr. Bob", "Doctor")
    healthcare_blockchain.register_user("patient_x", "Patient X", "Patient")
    healthcare_blockchain.register_user("patient_y", "Patient Y", "Patient")
    print("Demo users registered.")

    while True:
        print("\n========================================")
        print("   Healthcare Record Management System")
        delegates_display = healthcare_blockchain.get_delegate_list() or ["(none elected)"]
        next_delegate = delegates_display[healthcare_blockchain.current_delegate_index] if healthcare_blockchain.delegates else "(none)"
        print(f"   Next Delegate to Forge: {next_delegate}")
        print("========================================")
        print("1. Add a New Medical Record (Requires Doctor ID)")
        print("2. Forge a New Block (Requires Delegate ID)")
        print("3. View Patient History (Requires Patient/Admin ID)")
        print("4. View Access Log (Requires Admin ID)")
        print("6. Register New User")
        print("7. Stake Tokens (required before voting)")
        print("8. Vote for a Delegate Candidate")
        print("9. Elect Delegates (run election)")
        print("10. View Delegates and Votes")
        print("5. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\n--- Add New Medical Record ---")
            doctor_id = input("Enter your Doctor ID: ")
            if healthcare_blockchain.users.get(doctor_id, {}).get('role') != 'Doctor':
                print("\n[ERROR] Access Denied: Only users with the 'Doctor' role can add records.")
                log_action(f"ACCESS DENIED: Non-doctor {doctor_id} attempted to add a record.")
                continue

            patient_id = input("Enter Patient ID: ")
            if patient_id not in healthcare_blockchain.users:
                print(f"\n[WARNING] Patient '{patient_id}' is not registered in the system.")

            hospital_id = input("Enter Hospital ID/Name: ")
            insurance_id = input("Enter Insurance ID/Name: ")
            record_id = input("Enter Record ID (e.g., DIAG-001): ")
            operation = input("Enter Record Type (e.g., Diagnosis, Prescription): ")
            prescription = input("Enter Details (Prescription, Test Results, etc.): ")
            amount = input("Enter Amount (if applicable, else 0): ")

            new_tx = Transaction(hospital_id, doctor_id, patient_id, insurance_id, record_id, operation, prescription, amount)
            healthcare_blockchain.add_transaction(new_tx)

            print("\n[SUCCESS] Record added to the pending transactions pool.")
            log_action(f"TRANSACTION: Doctor {doctor_id} created a new record '{record_id}' for patient {patient_id}.")

        elif choice == '2':
            print("\n--- Forge a New Block ---")
            delegate_id = input("Enter your Delegate ID to forge the block: ")
            new_block = healthcare_blockchain.forge_block(delegate_id)
            if new_block:
                print(f"\n[SUCCESS] Block #{len(healthcare_blockchain.chain)-1} forged successfully!")
                print(f"   - Hash: {new_block.hash}")
                print(f"   - Merkle Root: {new_block.merkle_root}")

        elif choice == '3':
            print("\n--- View Patient Medical History ---")
            viewer_id = input("Enter your User ID to authenticate: ")
            patient_id_to_view = input("Enter Patient ID whose records you want to view: ")

            viewer_role = healthcare_blockchain.users.get(viewer_id, {}).get('role')
            if viewer_id == patient_id_to_view or viewer_role == 'Administrator':
                log_action(f"ACCESS: {viewer_id} viewed history for {patient_id_to_view}.")
                history = healthcare_blockchain.get_patient_history(patient_id_to_view)

                if not history:
                    print(f"\nNo records found for patient '{patient_id_to_view}'.")
                else:
                    print(f"\n--- Displaying Record History for {patient_id_to_view} ---")
                    for record in history:
                        print(f"  Record ID: {record['record_id']} ({record['operation']})")
                        print(f"    - Doctor: {record['doctor_id']}")
                        print(f"    - Hospital: {record['hospital_id']}")
                        print(f"    - Details: {record['prescription']}")
                        print(f"    - Timestamp: {record['timestamp']}\n")
                    print("--------------------------------------------------")
            else:
                print("\n[ERROR] Access Denied: You are not authorized to view this patient's records.")
                log_action(f"ACCESS DENIED: {viewer_id} attempted to view records for {patient_id_to_view}.")

        elif choice == '4':
            print("\n--- View System Access Log ---")
            admin_id = input("Enter your Administrator ID to authenticate: ")
            if healthcare_blockchain.users.get(admin_id, {}).get('role') == 'Administrator':
                log_action(f"ADMIN: {admin_id} viewed the access log.")
                try:
                    with open("access_log.txt", "r") as f:
                        print("\n--- Access Log ---")
                        print(f.read())
                        print("------------------")
                except FileNotFoundError:
                    print("\n[INFO] Access log is empty or has not been created yet.")
            else:
                print("\n[ERROR] Access Denied: Only administrators can view the access log.")
                log_action(f"ACCESS DENIED: Non-admin {admin_id} attempted to view the access log.")

        elif choice == '6':
            print("\n--- Register New User ---")
            user_id = input("Enter user ID (unique): ")
            name = input("Enter full name: ")
            role = input("Enter role (Patient / Doctor / Administrator): ")
            healthcare_blockchain.register_user(user_id, name, role)

        elif choice == '7':
            print("\n--- Stake Tokens ---")
            user_id = input("Enter your user ID: ")
            amount = input("Enter amount to stake: ")
            healthcare_blockchain.stake_tokens(user_id, amount)

        elif choice == '8':
            print("\n--- Vote for Delegate Candidate ---")
            voter_id = input("Enter your voter user ID: ")
            candidate_id = input("Enter candidate user ID (the person you want to vote for): ")
            healthcare_blockchain.vote_for_candidate(voter_id, candidate_id)

        elif choice == '9':
            print("\n--- Run Election (Elect Delegates) ---")
            healthcare_blockchain.elect_delegates()

        elif choice == '10':
            print("\n--- Delegates & Votes ---")
            print("Current stakes (user: stake):")
            for u, s in healthcare_blockchain.stakes.items():
                print(f"  {u}: {s}")
            print("\nVote totals (candidate: votes):")
            for c, v in healthcare_blockchain.votes.items():
                print(f"  {c}: {v}")
            print("\nElected delegates:")
            if healthcare_blockchain.delegates:
                for d in healthcare_blockchain.delegates:
                    print(f"  - {d}")
            else:
                print("  (none elected yet)")

        elif choice == '5':
            print("Shutting down the system...")
            log_action("SYSTEM: Application shutting down.")
            break

        else:
            print("\n[ERROR] Invalid choice. Please enter a number from the menu.")

if __name__ == "__main__":
    main()
