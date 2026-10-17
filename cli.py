import getpass  # Read PINs without echoing typed characters.

from backend import storage  # Use the shared wallet storage operations.
from backend.user import login  # Use the shared account authentication function.
from backend.transactions import (PAYMENT_STRUCTURE, account_details, deposit_details,  # Import payment categories and transaction containers.
                         payment_details, withdraw_details)  # Import payment and withdrawal detail containers.


def print_receipt(receipt):  # Display the receipt fields.
    print("\n----- RECEIPT -----")  # Display this menu, receipt, status, or error text.
    for key, value in receipt.items():  # Visit each item in this collection.
        print(f"{key}: {value}")  # Display this menu, receipt, status, or error text.
    print("-------------------\n")  # Display this menu, receipt, status, or error text.


def pick(prompt, options):  # Read a valid numbered selection.
    for i, opt in enumerate(options, 1):  # Visit each item in this collection.
        print(f"  {i}. {opt}")  # Display this menu, receipt, status, or error text.
    choice = int(input(prompt))  # Read the selected menu choice.
    if not 1 <= choice <= len(options):  # Reject choices outside the displayed menu range.
        raise ValueError("Invalid choice.")  # Stop the operation and report this error.
    return options[choice - 1]  # Convert the one-based menu choice to a list index.


def do_deposit(user, users):  # Collect and save a deposit.
    source = input("Deposit source (e.g. Bank, Cash-in outlet): ").strip()  # Read or validate the deposit source.
    amount = input("Amount: ").strip()  # Read or parse the transaction amount.
    return storage.deposit_and_save(user, deposit_details(source, user.name, amount), users)  # Save the wallet action using the collected details.


def do_withdraw(user, users):  # Collect and save a withdrawal.
    destination = input("Withdraw to (e.g. Bank name): ").strip()  # Read or validate the withdrawal destination.
    acct_no = input("Account number: ").strip()  # Read and trim the destination account number.
    amount = input("Amount: ").strip()  # Read or parse the transaction amount.
    return storage.withdraw_and_save(  # Save the wallet action using the collected details.
        user, withdraw_details(destination, user.name, acct_no, amount), users)


def do_send(user, users):  # Collect and save a transfer.
    acct_no = input("Recipient account number: ").strip()  # Read and trim the destination account number.
    acct_name = input("Recipient name: ").strip()  # Read and trim the recipient name.
    amount = input("Amount: ").strip()  # Read or parse the transaction amount.
    return storage.send_and_save(user, account_details(acct_no, acct_name, amount), users)  # Save the wallet action using the collected details.


def do_pay(user, users):  # Collect and save a bill payment.
    category = pick("Category: ", list(PAYMENT_STRUCTURE))  # Choose or normalize the payment category.
    subcategory = pick("Type: ", PAYMENT_STRUCTURE[category])  # Choose or normalize the payment subcategory.
    biller = input("Biller: ").strip()  # Read or validate the biller name.
    ref = input("Account/reference number: ").strip()  # Read and trim the payment reference.
    amount = input("Amount: ").strip()  # Read or parse the transaction amount.
    return storage.pay_and_save(  # Save the wallet action using the collected details.
        user, payment_details(category, subcategory, biller, ref, amount), users)


def show_history(user):  # Display the account transaction history.
    txns = storage.get_transactions(user.mobile_number)  # Load this account transaction history.
    if not txns:  # Handle an account with no transaction history.
        print("No transactions yet.")  # Display this menu, receipt, status, or error text.
    for t in txns:  # Visit each item in this collection.
        print(f"#{t['transaction_id']:>4}  {t['date']}  {t['type']:<10} {t['amount']:>12,.2f}")  # Display this menu, receipt, status, or error text.


ACTIONS = {"1": do_deposit, "2": do_withdraw, "3": do_send, "4": do_pay}  # Map wallet menu numbers to action functions.


def user_menu(user, users):  # Run the signed-in wallet menu.
    while True:  # Repeat the menu until an exit choice.
        print(f"\n{user.name} | Balance: {user.balance:,.2f}")  # Display this menu, receipt, status, or error text.
        print("1. Deposit  2. Withdraw  3. Send  4. Pay  5. History  0. Logout")  # Display this menu, receipt, status, or error text.
        choice = input("> ").strip()  # Read the selected menu choice.
        if choice == "0":  # Handle logout or application exit.
            return  # Leave this function without a result.
        try:  # Attempt the operation and handle failures below.
            if choice in ACTIONS:  # Handle a recognized wallet action.
                print_receipt(ACTIONS[choice](user, users))  # Run the selected action and display its saved receipt.
            elif choice == "5":  # Handle the transaction-history option.
                show_history(user)  # Display the signed-in account transaction history.
            else:  # Handle the alternative case.
                print("Invalid option.")  # Display this menu, receipt, status, or error text.
        except (ValueError, storage.StorageError) as e:  # also covers InsufficientFundsError
            print(f"Error: {e}")  # Display this menu, receipt, status, or error text.


def main():  # Run account registration and login.
    try:  # Attempt the operation and handle failures below.
        users = storage.load_users()  # Load and validate registered accounts.
    except storage.StorageError as e:  # Display validation and storage errors to the user.
        print(e)  # Display this menu, receipt, status, or error text.
        return  # Leave this function without a result.

    while True:  # Repeat the menu until an exit choice.
        print("\n== E-WALLET ==\n1. Register  2. Login  0. Exit")  # Display this menu, receipt, status, or error text.
        choice = input("> ").strip()  # Read the selected menu choice.
        try:  # Attempt the operation and handle failures below.
            if choice == "1":  # Handle account registration.
                storage.register_and_save(  # Create and persist the entered account.
                    input("Name: "), input("Mobile (09XXXXXXXXX): "),
                    getpass.getpass("4-digit PIN: "), users)
                print("Registered! You can now log in.")  # Display this menu, receipt, status, or error text.
            elif choice == "2":  # Handle account login.
                user_menu(login(input("Mobile: "), getpass.getpass("PIN: "), users), users)  # Authenticate the account and open the wallet menu.
            elif choice == "0":  # Handle application exit.
                break  # Exit the menu loop.
            else:  # Handle the alternative case.
                print("Invalid option.")  # Display this menu, receipt, status, or error text.
        except (ValueError, storage.StorageError) as e:  # ValueError covers AuthenticationError
            print(f"Error: {e}")  # Display this menu, receipt, status, or error text.


if __name__ == "__main__":  # Launch the CLI only when this file runs directly.
    main()  # Start the command-line wallet.
