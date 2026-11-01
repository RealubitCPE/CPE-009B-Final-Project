"""JSON persistence for the educational wallet, with ordinary-error rollback."""

import json
import os
import tempfile
from datetime import date, datetime

from .transactions import (
    amount_decimal, confirm_deposit, confirm_payment, confirm_transaction,
    confirm_withdraw, generate_reference_code, required_text,
)
from .user import User, find_user, register

# Files stay in the project root, regardless of the current working directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "transactions.json")


class StorageError(Exception):
    """Raised when data cannot be read, validated, or safely saved."""

    def __init__(self, message, *, committed=False):
        """Keep the error message and whether data was committed."""
        super().__init__(message)
        self.committed = committed


def _pending_file():
    """Build the interrupted-save marker path."""
    # Derive this from USERS_FILE so temporary/test wallets stay fully isolated.
    return os.fspath(USERS_FILE) + ".pending"


def _check_pending():
    """Block use when an unfinished-save marker exists."""
    filename = _pending_file()
    try:
        os.stat(filename)
    except FileNotFoundError:
        return
    except OSError as error:
        raise StorageError(f"Cannot check pending wallet save: {error}") from error
    raise StorageError(
        f"An interrupted wallet save requires manual reconciliation before further use: {filename}"
    )


def _create_pending(original_users_path):
    """Create a durable marker before replacing wallet files."""
    try:
        with open(_pending_file(), "x", encoding="utf-8") as stream:
            json.dump({
                "message": "Incomplete wallet save; reconcile files before removing this marker.",
                "users_file": os.fspath(USERS_FILE),
                "transactions_file": os.fspath(TRANSACTIONS_FILE),
                "original_users_backup": original_users_path,
            }, stream, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise StorageError(f"Cannot create pending wallet save marker: {error}") from error


def _clear_pending(*, committed=False):
    """Remove the marker or report its cleanup failure."""
    try:
        os.remove(_pending_file())
    except FileNotFoundError:
        return
    except OSError as error:
        message = (
            "Transaction was saved, but the pending marker could not be removed. "
            if committed else "Balances were restored, but the pending marker could not be removed. "
        )
        raise StorageError(
            message + "The wallet remains locked for manual reconciliation.", committed=committed,
        ) from error


# Low-level file helpers. Corrupt input stays in place and blocks future attempts.
def _load(filename):
    """Read a JSON list from storage."""
    try:
        with open(filename, "r", encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError, ValueError) as error:
        raise StorageError(f"Cannot read {os.path.basename(filename)}: {error}") from error
    if not isinstance(data, list):
        raise StorageError(f"{os.path.basename(filename)} must contain a JSON list.")
    return data


def _cleanup(paths):
    """Remove temporary files without hiding the original error."""
    for path in paths:
        if path is not None:
            try:
                os.remove(path)
            except OSError:
                pass  # A leftover temporary file must not hide the original error.


def _stage(filename, data, *, raw=False):
    """Write and flush a temporary replacement file."""
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(filename)), suffix=".tmp")
        with os.fdopen(fd, "wb") as stream:
            payload = data if raw else json.dumps(data, indent=4, allow_nan=False).encode("utf-8")
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return temp_path
    except (OSError, TypeError, ValueError) as error:
        _cleanup([temp_path])
        raise StorageError(f"Cannot prepare {os.path.basename(filename)}: {error}") from error


def _save(filename, data):
    """Replace one storage file with staged JSON."""
    # Write to a temp file first, then swap it in, to avoid half-written JSON.
    temp_path = _stage(filename, data)
    try:
        os.replace(temp_path, filename)
    except OSError as error:
        raise StorageError(f"Cannot save {os.path.basename(filename)}: {error}") from error
    finally:
        _cleanup([temp_path])


def _validate_users(data):
    """Rebuild stored users and reject duplicate numbers."""
    try:
        users = [User.fromDict(item) for item in data]
        mobiles = [user.mobile_number for user in users]
        if len(mobiles) != len(set(mobiles)):
            raise ValueError("Duplicate mobile numbers.")
        return users
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise StorageError("users.json is not in the expected format.") from error


def load_users():
    """Load accounts after checking for an interrupted save."""
    _check_pending()
    return _validate_users(_load(USERS_FILE))


def save_users(users):
    """Validate and save the account list."""
    load_users()  # Never overwrite an existing corrupt file.
    data = [user.toDict() for user in users]
    _validate_users(data)
    _save(USERS_FILE, data)


def _validate_transactions(data):
    """Check required fields and unique transaction IDs."""
    ids = set()
    try:
        for item in data:
            txn_id = item["transaction_id"]
            if isinstance(txn_id, bool) or not isinstance(txn_id, int) or txn_id < 1 or txn_id in ids:
                raise ValueError("Invalid or duplicate transaction id.")
            ids.add(txn_id)
            mobile = item["mobile_number"]
            if User.validate_mobile(mobile) != mobile:
                raise ValueError("Invalid stored mobile number.")
            required_text(item["type"], "Transaction type")
            amount_decimal(item["amount"])
            date.fromisoformat(item["date"])
            if "time" in item:  # Older records have no time; it is optional.
                datetime.strptime(item["time"], "%H:%M:%S")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise StorageError("transactions.json is not in the expected format.") from error
    return data


def load_transactions():
    """Load transactions after checking for an interrupted save."""
    _check_pending()
    return _validate_transactions(_load(TRANSACTIONS_FILE))


def save_transactions(transactions):
    """Validate and save transaction records."""
    load_transactions()
    _validate_transactions(transactions)
    _save(TRANSACTIONS_FILE, transactions)


def _next_id(transactions):
    """Choose the ID following the highest transaction ID."""
    return max((txn["transaction_id"] for txn in transactions), default=0) + 1


def next_transaction_id():
    """Find the next ID from saved history."""
    return _next_id(load_transactions())


def _record(mobile_number, txn_type, amount, transaction_id, stamp=None):
    """Build one validated transaction record."""
    stamp = stamp or datetime.now()
    return {
        "transaction_id": transaction_id,
        "mobile_number": User.validate_mobile(mobile_number),
        "type": required_text(txn_type, "Transaction type"),
        "amount": float(amount_decimal(amount)),
        "date": stamp.date().isoformat(),
        "time": stamp.strftime("%H:%M:%S"),
    }


def add_transaction(mobile_number, txn_type, amount):
    """Append a record to saved transaction history."""
    transactions = load_transactions()
    txn = _record(mobile_number, txn_type, amount, _next_id(transactions))
    save_transactions(transactions + [txn])
    return txn


def get_transactions(mobile_number):
    """Return history belonging to one mobile number."""
    mobile = User.normalize_mobile(mobile_number)
    return [txn for txn in load_transactions() if txn["mobile_number"] == mobile]


def _commit(users, transactions):
    """Stage both files, restoring the original users file if the log swap fails.

    The two replacements are not a crash-atomic database transaction. A durable
    marker blocks subsequent launches after interruption or failed rollback;
    reconciliation is manual. No receipt is returned for those failures.
    """
    load_users()
    load_transactions()
    user_data = [user.toDict() for user in users]
    _validate_users(user_data)
    _validate_transactions(transactions)
    try:
        with open(USERS_FILE, "rb") as stream:
            original_users = stream.read()
    except FileNotFoundError:
        original_users = None
    except OSError as error:
        raise StorageError(f"Cannot read users.json for rollback: {error}") from error

    staged = []
    try:
        new_users = _stage(USERS_FILE, user_data)
        staged.append(new_users)
        new_transactions = _stage(TRANSACTIONS_FILE, transactions)
        staged.append(new_transactions)
        original_path = None
        if original_users is not None:
            original_path = _stage(USERS_FILE, original_users, raw=True)
            staged.append(original_path)
        _create_pending(original_path)
        users_replaced = False
        try:
            os.replace(new_users, USERS_FILE)
            users_replaced = True
            os.replace(new_transactions, TRANSACTIONS_FILE)
        except OSError as error:
            try:
                if users_replaced:
                    if original_path is None:
                        os.remove(USERS_FILE)
                    else:
                        os.replace(original_path, USERS_FILE)
            except OSError as rollback_error:
                if original_path is not None:
                    staged.remove(original_path)  # Preserve the copy referenced by the marker.
                raise StorageError(
                    "Save and rollback failed. Wallet files require manual reconciliation "
                    f"before further use. Pending marker: {_pending_file()}"
                ) from rollback_error
            _clear_pending()
            raise StorageError("Transaction could not be saved; balances were restored.") from error
        _clear_pending(committed=True)
    except OSError as error:
        raise StorageError(f"Cannot save wallet data: {error}") from error
    finally:
        _cleanup(staged)


def register_and_save(name, mobile_number, pin, users):
    """Save registration and undo it if saving fails."""
    user = register(name, mobile_number, pin, users)
    try:
        save_users(users)
    except Exception:
        users.remove(user)
        raise
    return user


# Actions: validate, change balances, persist both files, then return the receipt.
def _process(user, users, txn_type, details, confirm, recipient=None, recipient_mobile=None):
    """Validate an action, update balances, and save its records."""
    if not any(candidate is user for candidate in users):
        raise ValueError("The active user is not registered in this session.")
    transactions = load_transactions()
    sequence = _next_id(transactions)
    receipt = confirm(details, sequence)
    # The reference number must be unique across saved transactions.
    used = {item.get("reference_number") for item in transactions}
    while receipt["Reference Number"] in used:
        receipt["Reference Number"] = generate_reference_code()
    amount = amount_decimal(details.amount)
    # Use the receipt's date and time so the saved record always matches it.
    stamp = datetime.strptime(f"{receipt['Date']} {receipt['Time']}", "%Y-%m-%d %H:%M:%S")
    txn = _record(user.mobile_number, txn_type, amount, sequence, stamp)
    txn["reference_number"] = receipt["Reference Number"]
    records = [txn]
    if recipient is not None:
        txn["recipient_mobile_number"] = recipient.mobile_number
        received = _record(recipient.mobile_number, "receive", amount, sequence + 1, stamp)
        received["sender_mobile_number"] = user.mobile_number
        received["related_transaction_id"] = sequence
        received["reference_number"] = receipt["Reference Number"]
        records.append(received)
    elif recipient_mobile is not None:
        # Recipient has no account here: the money leaves the sender only.
        txn["recipient_mobile_number"] = recipient_mobile

    affected = [user] if recipient is None else [user, recipient]
    balances = [(person, person.balance) for person in affected]
    try:
        if txn_type == "deposit":
            user.deposit(amount)
        else:
            user.withdraw(amount)
        if recipient is not None:
            recipient.deposit(amount)
        _commit(users, transactions + records)
    except Exception as error:
        # A marker-cleanup error can occur after both data files were committed.
        if not isinstance(error, StorageError) or not error.committed:
            for person, balance in balances:
                person.balance = balance
        raise
    return receipt


def deposit_and_save(user, details, users):
    """Process and persist a deposit."""
    return _process(user, users, "deposit", details, confirm_deposit)


def withdraw_and_save(user, details, users):
    """Process and persist a withdrawal."""
    return _process(user, users, "withdrawal", details, confirm_withdraw)


def send_and_save(user, details, users):
    """Persist a transfer; the recipient does not need an account here."""
    number = required_text(details.account_number, "Account number")
    name = required_text(details.account_name, "Account name")
    mobile = User.validate_mobile(number)
    if mobile == user.mobile_number:
        raise ValueError("Cannot send money to your own account.")
    recipient = find_user(mobile, users)
    if recipient is None:
        # Not registered: deduct from the sender and record the transfer.
        return _process(user, users, "send", details, confirm_transaction, recipient_mobile=mobile)
    # A registered number must still match the registered name.
    if " ".join(name.split()).casefold() != " ".join(recipient.name.split()).casefold():
        raise ValueError("Recipient name does not match the registered account.")
    return _process(user, users, "send", details, confirm_transaction, recipient)


def pay_and_save(user, details, users):
    """Process and persist a bill payment."""
    return _process(user, users, "payment", details, confirm_payment)
