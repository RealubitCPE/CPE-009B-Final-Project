import getpass

from backend import storage
from backend.user import login
from backend.transactions import (PAYMENT_STRUCTURE, account_details, deposit_details,
                         payment_details, withdraw_details)


def print_receipt(receipt):
    """Display the receipt fields."""
    print("\n----- RECEIPT -----")
    for key, value in receipt.items():
        print(f"{key}: {value}")
    print("-------------------\n")


def pick(prompt, options):
    """Read a valid numbered selection."""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    choice = int(input(prompt))
    if not 1 <= choice <= len(options):
        raise ValueError("Invalid choice.")
    return options[choice - 1]


def do_deposit(user, users):
    """Collect and save a deposit."""
    source = input("Deposit source (e.g. Bank, Cash-in outlet): ").strip()
    amount = input("Amount: ").strip()
    return storage.deposit_and_save(user, deposit_details(source, user.name, amount), users)


def do_withdraw(user, users):
    """Collect and save a withdrawal."""
    destination = input("Withdraw to (e.g. Bank name): ").strip()
    acct_no = input("Account number: ").strip()
    amount = input("Amount: ").strip()
    return storage.withdraw_and_save(
        user, withdraw_details(destination, user.name, acct_no, amount), users)


def do_send(user, users):
    """Collect and save a transfer."""
    acct_no = input("Recipient account number: ").strip()
    acct_name = input("Recipient name: ").strip()
    amount = input("Amount: ").strip()
    return storage.send_and_save(user, account_details(acct_no, acct_name, amount), users)


def do_pay(user, users):
    """Collect and save a bill payment."""
    category = pick("Category: ", list(PAYMENT_STRUCTURE))
    subcategory = pick("Type: ", PAYMENT_STRUCTURE[category])
    biller = input("Biller: ").strip()
    ref = input("Account/reference number: ").strip()
    amount = input("Amount: ").strip()
    return storage.pay_and_save(
        user, payment_details(category, subcategory, biller, ref, amount), users)


def show_history(user):
    """Display the account transaction history."""
    txns = storage.get_transactions(user.mobile_number)
    if not txns:
        print("No transactions yet.")
    for t in txns:
        print(f"#{t['transaction_id']:>4}  {t['date']}  {t['type']:<10} {t['amount']:>12,.2f}")


ACTIONS = {"1": do_deposit, "2": do_withdraw, "3": do_send, "4": do_pay}


def user_menu(user, users):
    """Run the signed-in wallet menu."""
    while True:
        print(f"\n{user.name} | Balance: {user.balance:,.2f}")
        print("1. Deposit  2. Withdraw  3. Send  4. Pay  5. History  0. Logout")
        choice = input("> ").strip()
        if choice == "0":
            return
        try:
            if choice in ACTIONS:
                print_receipt(ACTIONS[choice](user, users))
            elif choice == "5":
                show_history(user)
            else:
                print("Invalid option.")
        except (ValueError, storage.StorageError) as e:  # also covers InsufficientFundsError
            print(f"Error: {e}")


def main():
    """Load accounts and run the registration and login menu."""
    try:
        users = storage.load_users()
    except storage.StorageError as e:
        print(e)
        return

    while True:
        print("\n== E-WALLET ==\n1. Register  2. Login  0. Exit")
        choice = input("> ").strip()
        try:
            if choice == "1":
                storage.register_and_save(
                    input("Name: "), input("Mobile (09XXXXXXXXX): "),
                    getpass.getpass("4-digit PIN: "), users)
                print("Registered! You can now log in.")
            elif choice == "2":
                user_menu(login(input("Mobile: "), getpass.getpass("PIN: "), users), users)
            elif choice == "0":
                break
            else:
                print("Invalid option.")
        except (ValueError, storage.StorageError) as e:  # ValueError covers AuthenticationError
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
