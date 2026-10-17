"""Canonical transaction details and validated receipt generation."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import math

__all__ = [
    "PAYMENT_STRUCTURE", "payment_details", "account_details", "deposit_details",
    "withdraw_details", "confirm_payment", "confirm_transaction", "confirm_deposit",
    "confirm_withdraw", "validate_payment", "validate_account", "validate_amount",
    "generate_reference_number", "create_receipt", "next_sequence",
]

global_sequence = 1

# bills: government, electricity, internet, water
# bank: loans, transfer; credits: shopping, games, load
PAYMENT_STRUCTURE = {
    "Bills": ["government", "electricity", "internet", "water"],
    "Bank": ["loans", "transfer"],
    "Credits": ["shopping", "games", "load"],
}


def required_text(value, label):
    """Require nonempty text and trim outer spaces."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be empty.")
    return value.strip()


def amount_decimal(value, *, allow_zero=False):
    """Parse money without rounding away invalid fractional cents."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Amount must be a finite number with at most 2 decimal places.")
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be a valid number.") from None
    if not amount.is_finite() or not math.isfinite(float(amount)):
        raise ValueError("Amount must be finite and within the supported numeric range.")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise ValueError("Amount must be positive." if not allow_zero else "Balance cannot be negative.")
    if amount.as_tuple().exponent < -2:
        raise ValueError("Amount must have at most 2 decimal places.")
    if Decimal(str(float(amount))) != amount:
        raise ValueError("Amount cannot be stored without losing precision.")
    return amount


def next_sequence():
    """Reserve the next fallback receipt counter."""
    global global_sequence
    current = global_sequence
    global_sequence += 1
    return current


# Reference number and receipt generator. Storage supplies its persisted sequence.
def generate_reference_number(transaction_type, sequence_value):
    """Format the transaction reference."""
    if isinstance(sequence_value, bool) or not isinstance(sequence_value, int) or sequence_value < 1:
        raise ValueError("Transaction sequence must be a positive integer.")
    return f"{transaction_type[:3].upper()}-{sequence_value:09d}"


def create_receipt(transaction_type, name, amount, account_details, sequence_value=None):
    """Validate receipt fields and assemble the receipt."""
    amount = amount_decimal(amount)
    name = required_text(name, "Name")
    account_details = required_text(account_details, "Account details")
    sequence = next_sequence() if sequence_value is None else sequence_value
    now = datetime.now()
    return {
        "Status": "Success",
        "Transaction Type": transaction_type,
        "Transaction Number": generate_reference_number(transaction_type, sequence),
        "Name": name,
        "Amount": float(amount),
        "Account Details": account_details,
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
    }


# Each confirm_* function checks the details and returns a receipt.
# Invalid details raise ValueError.
@dataclass
class payment_details:
    category: str
    subcategory: str
    biller: str
    account_reference: str
    amount: float


@dataclass
class account_details:
    account_number: str
    account_name: str
    amount: float


@dataclass
class deposit_details:
    source: str
    account_name: str
    amount: float


@dataclass
class withdraw_details:
    destination: str
    account_name: str
    account_number: str
    amount: float


def validate_amount(amount):
    """Report whether money validation succeeds."""
    try:
        amount_decimal(amount)
        return True
    except ValueError:
        return False


def validate_account(account_number, account_name):
    """Check that both account fields contain text."""
    return all(isinstance(value, str) and bool(value.strip())
               for value in (account_number, account_name))


def _payment_fields(details):
    """Validate and normalize payment details."""
    category = required_text(details.category, "Category").capitalize()
    subcategory = required_text(details.subcategory, "Subcategory").lower()
    if subcategory not in PAYMENT_STRUCTURE.get(category, []):
        raise ValueError("Invalid payment category.")
    biller = required_text(details.biller, "Biller")
    reference = required_text(details.account_reference, "Account reference")
    amount_decimal(details.amount)
    return category, subcategory, biller, reference


def validate_payment(details):
    """Report whether payment validation succeeds."""
    try:
        _payment_fields(details)
        return True
    except ValueError:
        return False


def confirm_payment(details, sequence_value=None):
    """Validate payment details and create a receipt."""
    category, subcategory, biller, reference = _payment_fields(details)
    return create_receipt(
        "Payment", biller, details.amount,
        f"Category: {category} / Sub: {subcategory.title()} / Ref: {reference}", sequence_value,
    )


def confirm_transaction(details, sequence_value=None):
    """Validate transfer details and create a receipt."""
    number = required_text(details.account_number, "Account number")
    name = required_text(details.account_name, "Account name")
    return create_receipt("Send", name, details.amount, number, sequence_value)


def confirm_deposit(details, sequence_value=None):
    """Validate deposit details and create a receipt."""
    source = required_text(details.source, "Source")
    name = required_text(details.account_name, "Account name")
    return create_receipt("Deposit", name, details.amount, f"Source: {source}", sequence_value)


def confirm_withdraw(details, sequence_value=None):
    """Validate withdrawal details and create a receipt."""
    destination = required_text(details.destination, "Destination")
    name = required_text(details.account_name, "Account name")
    number = required_text(details.account_number, "Account number")
    return create_receipt(
        "Withdraw", name, details.amount,
        f"Destination: {destination} / Account No: {number}", sequence_value,
    )
