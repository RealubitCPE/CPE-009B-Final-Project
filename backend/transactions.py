"""Canonical transaction details and validated receipt generation."""

from dataclasses import dataclass  # Generate constructors for transaction detail containers.
from datetime import datetime  # Read the local date and time for receipts.
from decimal import Decimal, InvalidOperation  # Parse exact decimal money and handle invalid decimal input.
import math  # Use finite-number checks or rounding helpers.

__all__ = [  # List public names exported by wildcard imports.
    "PAYMENT_STRUCTURE", "payment_details", "account_details", "deposit_details",
    "withdraw_details", "confirm_payment", "confirm_transaction", "confirm_deposit",
    "confirm_withdraw", "validate_payment", "validate_account", "validate_amount",
    "generate_reference_number", "create_receipt", "next_sequence",
]

global_sequence = 1  # Start the fallback receipt counter at one.

# bills: government, electricity, internet, water
# bank: loans, transfer; credits: shopping, games, load
PAYMENT_STRUCTURE = {  # Map payment categories to allowed subcategories.
    "Bills": ["government", "electricity", "internet", "water"],  # Include the Bills field in this record.
    "Bank": ["loans", "transfer"],  # Include the Bank field in this record.
    "Credits": ["shopping", "games", "load"],  # Include the Credits field in this record.
}


def required_text(value, label):  # Require nonempty text and trim outer spaces.
    if not isinstance(value, str) or not value.strip():  # Reject non-text and blank text.
        raise ValueError(f"{label} cannot be empty.")  # Stop the operation and report this error.
    return value.strip()  # Return required text without outer spaces.


def amount_decimal(value, *, allow_zero=False):  # Validate money without rounding fractional cents.
    """Parse money without rounding away invalid fractional cents."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):  # Reject booleans and unsupported money types.
        raise ValueError("Amount must be a finite number with at most 2 decimal places.")  # Stop the operation and report this error.
    try:  # Attempt the operation and handle failures below.
        amount = Decimal(str(value).strip())  # Read or parse the transaction amount.
    except (InvalidOperation, ValueError):  # Translate decimal parsing failure to a validation error.
        raise ValueError("Amount must be a valid number.") from None  # Stop the operation and report this error.
    if not amount.is_finite() or not math.isfinite(float(amount)):  # Reject nonfinite amounts and values beyond float range.
        raise ValueError("Amount must be finite and within the supported numeric range.")  # Stop the operation and report this error.
    if amount < 0 or (amount == 0 and not allow_zero):  # Reject negative amounts and disallowed zero values.
        raise ValueError("Amount must be positive." if not allow_zero else "Balance cannot be negative.")  # Stop the operation and report this error.
    if amount.as_tuple().exponent < -2:  # Reject amounts specifying more than two decimal places.
        raise ValueError("Amount must have at most 2 decimal places.")  # Stop the operation and report this error.
    if Decimal(str(float(amount))) != amount:  # Reject values that lose precision in stored float form.
        raise ValueError("Amount cannot be stored without losing precision.")  # Stop the operation and report this error.
    return amount  # Return the validated decimal amount.


def next_sequence():  # Reserve the next fallback receipt counter.
    global global_sequence  # Allow this function to update the module counter.
    current = global_sequence  # Remember the counter before advancing it.
    global_sequence += 1  # Advance the counter for the next receipt.
    return current  # Return this receipt counter value.


# Reference number and receipt generator. Storage supplies its persisted sequence.
def generate_reference_number(transaction_type, sequence_value):  # Format the transaction reference.
    if isinstance(sequence_value, bool) or not isinstance(sequence_value, int) or sequence_value < 1:  # Require a positive integer transaction sequence.
        raise ValueError("Transaction sequence must be a positive integer.")  # Stop the operation and report this error.
    return f"{transaction_type[:3].upper()}-{sequence_value:09d}"  # Combine the type prefix and nine-digit sequence.


def create_receipt(transaction_type, name, amount, account_details, sequence_value=None):  # Validate receipt fields and assemble the receipt.
    amount = amount_decimal(amount)  # Read or parse the transaction amount.
    name = required_text(name, "Name")  # Validate and trim the account holder name.
    account_details = required_text(account_details, "Account details")  # Validate and trim the receipt account description.
    sequence = next_sequence() if sequence_value is None else sequence_value  # Use the supplied sequence or reserve a fallback counter.
    now = datetime.now()  # Capture the receipt date and time.
    return {  # Return the fields in this dictionary.
        "Status": "Success",  # Include the Status field in this record.
        "Transaction Type": transaction_type,  # Include the Transaction Type field in this record.
        "Transaction Number": generate_reference_number(transaction_type, sequence),  # Include the Transaction Number field in this record.
        "Name": name,  # Include the Name field in this record.
        "Amount": float(amount),  # Include the Amount field in this record.
        "Account Details": account_details,  # Include the Account Details field in this record.
        "Date": now.strftime("%Y-%m-%d"),  # Include the Date field in this record.
        "Time": now.strftime("%H:%M:%S"),  # Include the Time field in this record.
    }


# Each confirm_* function checks the details and returns a receipt.
# Invalid details raise ValueError.
@dataclass  # Generate standard data-container methods.
class payment_details:  # Hold the category, biller, reference, and payment amount.
    category: str  # Declare this transaction-detail field and its type.
    subcategory: str  # Declare this transaction-detail field and its type.
    biller: str  # Declare this transaction-detail field and its type.
    account_reference: str  # Declare this transaction-detail field and its type.
    amount: float  # Declare this transaction-detail field and its type.


@dataclass  # Generate standard data-container methods.
class account_details:  # Hold the recipient number, name, and transfer amount.
    account_number: str  # Declare this transaction-detail field and its type.
    account_name: str  # Declare this transaction-detail field and its type.
    amount: float  # Declare this transaction-detail field and its type.


@dataclass  # Generate standard data-container methods.
class deposit_details:  # Hold the deposit source, account name, and amount.
    source: str  # Declare this transaction-detail field and its type.
    account_name: str  # Declare this transaction-detail field and its type.
    amount: float  # Declare this transaction-detail field and its type.


@dataclass  # Generate standard data-container methods.
class withdraw_details:  # Hold the withdrawal destination, account details, and amount.
    destination: str  # Declare this transaction-detail field and its type.
    account_name: str  # Declare this transaction-detail field and its type.
    account_number: str  # Declare this transaction-detail field and its type.
    amount: float  # Declare this transaction-detail field and its type.


def validate_amount(amount):  # Report whether money validation succeeds.
    try:  # Attempt the operation and handle failures below.
        amount_decimal(amount)  # Check the supplied money amount.
        return True  # Report success.
    except ValueError:  # Report validation failure without propagating the error.
        return False  # Report validation or authentication failure.


def validate_account(account_number, account_name):  # Check that both account fields contain text.
    return all(isinstance(value, str) and bool(value.strip())  # Require both account fields to contain text.
               for value in (account_number, account_name))  # Visit each item in this collection.


def _payment_fields(details):  # Validate and normalize payment details.
    category = required_text(details.category, "Category").capitalize()  # Choose or normalize the payment category.
    subcategory = required_text(details.subcategory, "Subcategory").lower()  # Choose or normalize the payment subcategory.
    if subcategory not in PAYMENT_STRUCTURE.get(category, []):  # Require the subcategory to belong to its payment category.
        raise ValueError("Invalid payment category.")  # Stop the operation and report this error.
    biller = required_text(details.biller, "Biller")  # Read or validate the biller name.
    reference = required_text(details.account_reference, "Account reference")  # Validate and trim the payment reference.
    amount_decimal(details.amount)  # Validate the payment amount.
    return category, subcategory, biller, reference  # Return the result to the caller.


def validate_payment(details):  # Report whether payment validation succeeds.
    try:  # Attempt the operation and handle failures below.
        _payment_fields(details)  # Check required fields and the category-subcategory pairing.
        return True  # Report success.
    except ValueError:  # Report validation failure without propagating the error.
        return False  # Report validation or authentication failure.


def confirm_payment(details, sequence_value=None):  # Validate payment details and create a receipt.
    category, subcategory, biller, reference = _payment_fields(details)  # Unpack the validated payment fields.
    return create_receipt(  # Build a receipt from the validated details.
        "Payment", biller, details.amount,
        f"Category: {category} / Sub: {subcategory.title()} / Ref: {reference}", sequence_value,
    )


def confirm_transaction(details, sequence_value=None):  # Validate transfer details and create a receipt.
    number = required_text(details.account_number, "Account number")  # Validate and trim the account number.
    name = required_text(details.account_name, "Account name")  # Validate and trim the account holder name.
    return create_receipt("Send", name, details.amount, number, sequence_value)  # Build a receipt from the validated details.


def confirm_deposit(details, sequence_value=None):  # Validate deposit details and create a receipt.
    source = required_text(details.source, "Source")  # Read or validate the deposit source.
    name = required_text(details.account_name, "Account name")  # Validate and trim the account holder name.
    return create_receipt("Deposit", name, details.amount, f"Source: {source}", sequence_value)  # Build a receipt from the validated details.


def confirm_withdraw(details, sequence_value=None):  # Validate withdrawal details and create a receipt.
    destination = required_text(details.destination, "Destination")  # Read or validate the withdrawal destination.
    name = required_text(details.account_name, "Account name")  # Validate and trim the account holder name.
    number = required_text(details.account_number, "Account number")  # Validate and trim the account number.
    return create_receipt(  # Build a receipt from the validated details.
        "Withdraw", name, details.amount,
        f"Destination: {destination} / Account No: {number}", sequence_value,
    )
