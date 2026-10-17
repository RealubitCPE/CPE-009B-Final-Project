"""JSON persistence for the educational wallet, with ordinary-error rollback."""

import json  # Read and write JSON wallet data.
import os  # Use operating-system paths, files, and random bytes.
import tempfile  # Create temporary files for staged saves.
from datetime import date  # Validate and generate transaction dates.

from .transactions import (  # Import validation and receipt helpers for storage actions.
    amount_decimal, confirm_deposit, confirm_payment, confirm_transaction,  # Load money validation and deposit, payment, and transfer receipt helpers.
    confirm_withdraw, required_text,  # Load withdrawal receipt and required-text helpers.
)
from .user import User, find_user, register  # Use account reconstruction, lookup, and registration helpers.

# Files stay in the project root, regardless of the current working directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Locate the project root from this backend file.
USERS_FILE = os.path.join(BASE_DIR, "users.json")  # Set the account JSON path in the project root.
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "transactions.json")  # Set the transaction JSON path in the project root.


class StorageError(Exception):  # Represent wallet storage and reconciliation failures.
    """Raised when data cannot be read, validated, or safely saved."""

    def __init__(self, message, *, committed=False):  # Keep the error message and whether data was committed.
        super().__init__(message)  # Initialize the exception with its readable message.
        self.committed = committed  # Record whether wallet files were saved before this error.


def _pending_file():  # Build the interrupted-save marker path.
    # Derive this from USERS_FILE so temporary/test wallets stay fully isolated.
    return os.fspath(USERS_FILE) + ".pending"  # Place the recovery marker beside the account file.


def _check_pending():  # Block use when an unfinished-save marker exists.
    filename = _pending_file()  # Resolve the pending-marker path.
    try:  # Attempt the operation and handle failures below.
        os.stat(filename)  # Check whether the marker exists.
    except FileNotFoundError:  # Handle a file that does not exist.
        return  # Leave this function without a result.
    except OSError as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot check pending wallet save: {error}") from error  # Stop the operation and report this error.
    raise StorageError(  # Stop the operation and report this error.
        f"An interrupted wallet save requires manual reconciliation before further use: {filename}"
    )


def _create_pending(original_users_path):  # Create a durable marker before replacing wallet files.
    try:  # Attempt the operation and handle failures below.
        with open(_pending_file(), "x", encoding="utf-8") as stream:  # Create the recovery marker without replacing an existing marker.
            json.dump({  # Write recovery information into the marker.
                "message": "Incomplete wallet save; reconcile files before removing this marker.",  # Include the message field in this record.
                "users_file": os.fspath(USERS_FILE),  # Include the users file field in this record.
                "transactions_file": os.fspath(TRANSACTIONS_FILE),  # Include the transactions file field in this record.
                "original_users_backup": original_users_path,  # Include the original users backup field in this record.
            }, stream, indent=4)  # Finish writing the readable JSON marker.
            stream.flush()  # Flush Python buffered bytes to the operating system.
            os.fsync(stream.fileno())  # Ask the operating system to flush file contents to disk.
    except OSError as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot create pending wallet save marker: {error}") from error  # Stop the operation and report this error.


def _clear_pending(*, committed=False):  # Remove the marker or report its cleanup failure.
    try:  # Attempt the operation and handle failures below.
        os.remove(_pending_file())  # Remove the interrupted-save marker.
    except FileNotFoundError:  # Handle a file that does not exist.
        return  # Leave this function without a result.
    except OSError as error:  # Handle these read, validation, or save failures.
        message = (  # Choose the message for completed saving or rollback.
            "Transaction was saved, but the pending marker could not be removed. "
            if committed else "Balances were restored, but the pending marker could not be removed. "  # Select the rollback message when files were not committed.
        )
        raise StorageError(  # Stop the operation and report this error.
            message + "The wallet remains locked for manual reconciliation.", committed=committed,
        ) from error


# Low-level file helpers. Corrupt input stays in place and blocks future attempts.
def _load(filename):  # Read a JSON list from storage.
    try:  # Attempt the operation and handle failures below.
        with open(filename, "r", encoding="utf-8") as stream:  # Open the JSON file as UTF-8 text.
            data = json.load(stream)  # Parse the JSON file contents.
    except FileNotFoundError:  # Handle a file that does not exist.
        return []  # Treat a missing file as an empty collection.
    except (OSError, UnicodeError, ValueError) as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot read {os.path.basename(filename)}: {error}") from error  # Stop the operation and report this error.
    if not isinstance(data, list):  # Require a JSON list at the top level.
        raise StorageError(f"{os.path.basename(filename)} must contain a JSON list.")  # Stop the operation and report this error.
    return data  # Return the result to the caller.


def _cleanup(paths):  # Remove temporary files without hiding the original error.
    for path in paths:  # Visit each item in this collection.
        if path is not None:  # Skip temporary paths that were never created.
            try:  # Attempt the operation and handle failures below.
                os.remove(path)  # Remove this temporary file.
            except OSError:  # Handle these read, validation, or save failures.
                pass  # A leftover temporary file must not hide the original error.


def _stage(filename, data, *, raw=False):  # Write and flush a temporary replacement file.
    temp_path = None  # Track whether a temporary path was created.
    try:  # Attempt the operation and handle failures below.
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(filename)), suffix=".tmp")  # Create a temporary file beside the target for replacement.
        with os.fdopen(fd, "wb") as stream:  # Manage the temporary file as a binary output stream.
            payload = data if raw else json.dumps(data, indent=4, allow_nan=False).encode("utf-8")  # Keep backup bytes unchanged or encode strict JSON as UTF-8.
            stream.write(payload)  # Write the staged bytes.
            stream.flush()  # Flush Python buffered bytes to the operating system.
            os.fsync(stream.fileno())  # Ask the operating system to flush file contents to disk.
        return temp_path  # Return the staged file path.
    except (OSError, TypeError, ValueError) as error:  # Handle these read, validation, or save failures.
        _cleanup([temp_path])  # Remove the temporary file if it remains.
        raise StorageError(f"Cannot prepare {os.path.basename(filename)}: {error}") from error  # Stop the operation and report this error.


def _save(filename, data):  # Replace one storage file with staged JSON.
    # Write to a temp file first, then swap it in, to avoid half-written JSON.
    temp_path = _stage(filename, data)  # Stage the proposed data in a temporary file.
    try:  # Attempt the operation and handle failures below.
        os.replace(temp_path, filename)  # Replace the target with the complete staged file.
    except OSError as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot save {os.path.basename(filename)}: {error}") from error  # Stop the operation and report this error.
    finally:  # Run cleanup after success or failure.
        _cleanup([temp_path])  # Remove the temporary file if it remains.


def _validate_users(data):  # Rebuild stored users and reject duplicate numbers.
    try:  # Attempt the operation and handle failures below.
        users = [User.fromDict(item) for item in data]  # Rebuild and validate every stored account.
        mobiles = [user.mobile_number for user in users]  # Collect mobile numbers for duplicate detection.
        if len(mobiles) != len(set(mobiles)):  # Detect duplicate stored mobile numbers.
            raise ValueError("Duplicate mobile numbers.")  # Stop the operation and report this error.
        return users  # Return the result to the caller.
    except (KeyError, TypeError, ValueError, AttributeError) as error:  # Handle these read, validation, or save failures.
        raise StorageError("users.json is not in the expected format.") from error  # Stop the operation and report this error.


def load_users():  # Load accounts after checking for an interrupted save.
    _check_pending()  # Reject use until an interrupted save is reconciled.
    return _validate_users(_load(USERS_FILE))  # Read account JSON and validate the account records.


def save_users(users):  # Validate and save the account list.
    load_users()  # Never overwrite an existing corrupt file.
    data = [user.toDict() for user in users]  # Convert accounts to JSON-compatible fields.
    _validate_users(data)  # Validate serialized accounts before saving.
    _save(USERS_FILE, data)  # Write the validated account list.


def _validate_transactions(data):  # Check required fields and unique transaction IDs.
    ids = set()  # Track transaction IDs already encountered.
    try:  # Attempt the operation and handle failures below.
        for item in data:  # Visit each item in this collection.
            txn_id = item["transaction_id"]  # Read the saved transaction ID.
            if isinstance(txn_id, bool) or not isinstance(txn_id, int) or txn_id < 1 or txn_id in ids:  # Reject nonpositive, noninteger, or repeated transaction IDs.
                raise ValueError("Invalid or duplicate transaction id.")  # Stop the operation and report this error.
            ids.add(txn_id)  # Remember the ID to detect later duplicates.
            mobile = item["mobile_number"]  # Read the stored mobile number for validation.
            if User.validate_mobile(mobile) != mobile:  # Require the saved mobile number to already be normalized.
                raise ValueError("Invalid stored mobile number.")  # Stop the operation and report this error.
            required_text(item["type"], "Transaction type")  # Require a nonempty transaction type.
            amount_decimal(item["amount"])  # Validate the stored money amount.
            date.fromisoformat(item["date"])  # Validate the date using the ISO date parser.
    except (KeyError, TypeError, ValueError, AttributeError) as error:  # Handle these read, validation, or save failures.
        raise StorageError("transactions.json is not in the expected format.") from error  # Stop the operation and report this error.
    return data  # Return the result to the caller.


def load_transactions():  # Load transactions after checking for an interrupted save.
    _check_pending()  # Reject use until an interrupted save is reconciled.
    return _validate_transactions(_load(TRANSACTIONS_FILE))  # Read and validate saved transaction records.


def save_transactions(transactions):  # Validate and save transaction records.
    load_transactions()  # Check current saved history before continuing.
    _validate_transactions(transactions)  # Validate all proposed transaction records.
    _save(TRANSACTIONS_FILE, transactions)  # Write the validated transaction list.


def _next_id(transactions):  # Choose the ID following the highest transaction ID.
    return max((txn["transaction_id"] for txn in transactions), default=0) + 1  # Advance the highest ID, starting at one for an empty log.


def next_transaction_id():  # Find the next ID from saved history.
    return _next_id(load_transactions())  # Choose the next ID using saved history.


def _record(mobile_number, txn_type, amount, transaction_id):  # Build one validated transaction record.
    return {  # Return the fields in this dictionary.
        "transaction_id": transaction_id,  # Include the transaction id field in this record.
        "mobile_number": User.validate_mobile(mobile_number),  # Include the mobile number field in this record.
        "type": required_text(txn_type, "Transaction type"),  # Include the type field in this record.
        "amount": float(amount_decimal(amount)),  # Include the amount field in this record.
        "date": date.today().isoformat(),  # Include the date field in this record.
    }


def add_transaction(mobile_number, txn_type, amount):  # Append a record to saved transaction history.
    transactions = load_transactions()  # Load the validated transaction history.
    txn = _record(mobile_number, txn_type, amount, _next_id(transactions))  # Build the next validated transaction record.
    save_transactions(transactions + [txn])  # Save existing history with the new record appended.
    return txn  # Return the result to the caller.


def get_transactions(mobile_number):  # Return history belonging to one mobile number.
    mobile = User.normalize_mobile(mobile_number)  # Normalize or validate the mobile number.
    return [txn for txn in load_transactions() if txn["mobile_number"] == mobile]  # Keep only records for this normalized mobile number.


def _commit(users, transactions):  # Stage both wallet files and roll back account storage on failure.
    """Stage both files, restoring the original users file if the log swap fails.

    The two replacements are not a crash-atomic database transaction. A durable
    marker blocks subsequent launches after interruption or failed rollback;
    reconciliation is manual. No receipt is returned for those failures.
    """
    load_users()  # Check existing account data before continuing.
    load_transactions()  # Check current saved history before continuing.
    user_data = [user.toDict() for user in users]  # Prepare account balances as JSON-compatible records.
    _validate_users(user_data)  # Validate accounts before staging their save.
    _validate_transactions(transactions)  # Validate all proposed transaction records.
    try:  # Attempt the operation and handle failures below.
        with open(USERS_FILE, "rb") as stream:  # Read original account bytes for rollback.
            original_users = stream.read()  # Keep original account bytes for rollback.
    except FileNotFoundError:  # Handle a file that does not exist.
        original_users = None  # Remember that no account file existed.
    except OSError as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot read users.json for rollback: {error}") from error  # Stop the operation and report this error.

    staged = []  # Track temporary files requiring cleanup.
    try:  # Attempt the operation and handle failures below.
        new_users = _stage(USERS_FILE, user_data)  # Stage the updated account data.
        staged.append(new_users)  # Track the staged account file for cleanup.
        new_transactions = _stage(TRANSACTIONS_FILE, transactions)  # Stage the updated transaction log.
        staged.append(new_transactions)  # Track the staged log for cleanup.
        original_path = None  # Start without an account backup path.
        if original_users is not None:  # Back up account bytes when an original file existed.
            original_path = _stage(USERS_FILE, original_users, raw=True)  # Stage an exact backup of the original account bytes.
            staged.append(original_path)  # Track the backup for cleanup.
        _create_pending(original_path)  # Create a recovery marker before replacing saved data.
        users_replaced = False  # Track whether account storage has been replaced.
        try:  # Attempt the operation and handle failures below.
            os.replace(new_users, USERS_FILE)  # Install the updated account file.
            users_replaced = True  # Remember that a failed log save now requires account rollback.
            os.replace(new_transactions, TRANSACTIONS_FILE)  # Install the updated transaction log.
        except OSError as error:  # Handle these read, validation, or save failures.
            try:  # Attempt the operation and handle failures below.
                if users_replaced:  # Restore account storage only after it was replaced.
                    if original_path is None:  # Handle rollback without an original account file.
                        os.remove(USERS_FILE)  # Undo creation of a previously missing account file.
                    else:  # Handle the alternative case.
                        os.replace(original_path, USERS_FILE)  # Restore the original account file from its backup.
            except OSError as rollback_error:  # Handle failure while restoring the account file.
                if original_path is not None:  # Preserve the backup after rollback failure.
                    staged.remove(original_path)  # Preserve the copy referenced by the marker.
                raise StorageError(  # Stop the operation and report this error.
                    "Save and rollback failed. Wallet files require manual reconciliation "
                    f"before further use. Pending marker: {_pending_file()}"
                ) from rollback_error
            _clear_pending()  # Remove the marker after a successful rollback.
            raise StorageError("Transaction could not be saved; balances were restored.") from error  # Stop the operation and report this error.
        _clear_pending(committed=True)  # Remove the marker after both files were saved.
    except OSError as error:  # Handle these read, validation, or save failures.
        raise StorageError(f"Cannot save wallet data: {error}") from error  # Stop the operation and report this error.
    finally:  # Run cleanup after success or failure.
        _cleanup(staged)  # Clean up remaining staged files.


def register_and_save(name, mobile_number, pin, users):  # Save registration and undo it if saving fails.
    user = register(name, mobile_number, pin, users)  # Register the requested account.
    try:  # Attempt the operation and handle failures below.
        save_users(users)  # Persist all current accounts.
    except Exception:  # Handle failure so in-memory changes can be undone.
        users.remove(user)  # Undo registration in memory after saving fails.
        raise  # Propagate the original failure.
    return user  # Return the result to the caller.


# Actions: validate, change balances, persist both files, then return the receipt.
def _process(user, users, txn_type, details, confirm, recipient=None):  # Validate an action, update balances, and save its records.
    if not any(candidate is user for candidate in users):  # Require this active account object to belong to the session.
        raise ValueError("The active user is not registered in this session.")  # Stop the operation and report this error.
    transactions = load_transactions()  # Load the validated transaction history.
    sequence = _next_id(transactions)  # Reserve the next ID from the loaded history.
    receipt = confirm(details, sequence)  # Validate action details and construct the receipt.
    amount = amount_decimal(details.amount)  # Parse the amount as validated decimal money.
    txn = _record(user.mobile_number, txn_type, amount, sequence)  # Build the initiating account transaction record.
    records = [txn]  # Start with the initiating account record.
    if recipient is not None:  # Include the recipient in the transfer workflow.
        txn["recipient_mobile_number"] = recipient.mobile_number  # Record the receiving account number.
        received = _record(recipient.mobile_number, "receive", amount, sequence + 1)  # Build the matching incoming transfer record.
        received["sender_mobile_number"] = user.mobile_number  # Record the sender on the incoming transfer.
        received["related_transaction_id"] = sequence  # Link the incoming record to the outgoing transaction.
        records.append(received)  # Save the incoming record with the outgoing transfer.

    affected = [user] if recipient is None else [user, recipient]  # Identify the accounts whose balances may change.
    balances = [(person, person.balance) for person in affected]  # Remember original balances for rollback in memory.
    try:  # Attempt the operation and handle failures below.
        if txn_type == "deposit":  # Choose the balance-increase path for deposits.
            user.deposit(amount)  # Credit the initiating account for a deposit.
        else:  # Handle the alternative case.
            user.withdraw(amount)  # Debit the initiating account for spending or a transfer.
        if recipient is not None:  # Include the recipient in the transfer workflow.
            recipient.deposit(amount)  # Credit the recipient with the transferred amount.
        _commit(users, transactions + records)  # Save changed balances and the new history together.
    except Exception as error:  # Handle failure so in-memory changes can be undone.
        # A marker-cleanup error can occur after both data files were committed.
        if not isinstance(error, StorageError) or not error.committed:  # Restore memory unless both files were committed.
            for person, balance in balances:  # Visit each item in this collection.
                person.balance = balance  # Restore this account balance in memory.
        raise  # Propagate the original failure.
    return receipt  # Return the receipt after persistence succeeds.


def deposit_and_save(user, details, users):  # Process and persist a deposit.
    return _process(user, users, "deposit", details, confirm_deposit)  # Run the shared validation, balance, and save workflow.


def withdraw_and_save(user, details, users):  # Process and persist a withdrawal.
    return _process(user, users, "withdrawal", details, confirm_withdraw)  # Run the shared validation, balance, and save workflow.


def send_and_save(user, details, users):  # Validate the recipient and persist a transfer.
    # Validate required fields before resolving the registered recipient.
    required_text(details.account_number, "Account number")  # Require a recipient account number before lookup.
    name = required_text(details.account_name, "Account name")  # Validate and trim the account holder name.
    recipient = find_user(details.account_number, users)  # Find the registered recipient account.
    if recipient is None:  # Reject an unregistered recipient.
        raise ValueError("Recipient is not registered.")  # Stop the operation and report this error.
    if recipient.mobile_number == user.mobile_number:  # Reject transfers to the sender account.
        raise ValueError("Cannot send money to your own account.")  # Stop the operation and report this error.
    if " ".join(name.split()).casefold() != " ".join(recipient.name.split()).casefold():  # Compare names while ignoring case and repeated spaces.
        raise ValueError("Recipient name does not match the registered account.")  # Stop the operation and report this error.
    return _process(user, users, "send", details, confirm_transaction, recipient)  # Run the shared validation, balance, and save workflow.


def pay_and_save(user, details, users):  # Process and persist a bill payment.
    return _process(user, users, "payment", details, confirm_payment)  # Run the shared validation, balance, and save workflow.
