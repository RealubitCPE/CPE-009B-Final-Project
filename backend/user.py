"""Wallet users with salted PIN authentication and decimal balances."""

import hashlib  # Derive PIN hashes with PBKDF2.
import hmac  # Compare hashes with timing resistance.
import math  # Use finite-number checks or rounding helpers.
import os  # Use operating-system paths, files, and random bytes.
import re  # Check PIN and hash formats with regular expressions.
import time  # Measure PIN cooldowns with a monotonic clock.
from decimal import localcontext  # Temporarily adjust precision for money calculations.

from .transactions import amount_decimal, required_text  # Reuse money and required-text validation.

__all__ = ["User", "register", "login", "find_user", "AuthenticationError", "InsufficientFundsError"]  # List public names exported by wildcard imports.


class InsufficientFundsError(ValueError):  # Identify attempts to spend beyond the available balance.
    """Raised when a user tries to spend more than their balance."""


class AuthenticationError(ValueError):  # Identify invalid credentials and PIN cooldown failures.
    """Raised for invalid credentials or an account's PIN cooldown."""


class User:  # Represent an account, its PIN authentication, and its balance.
    PIN_MAX_ATTEMPTS = 5  # Allow five failed PIN attempts before a cooldown.
    PIN_COOLDOWN_SECONDS = 30  # Set the PIN cooldown to thirty seconds.

    # Helper to normalize the mobile number (keeps ASCII digits only).
    @staticmethod  # Call this helper without an account instance.
    def normalize_mobile(mobile_number):  # Keep only ASCII digits from a mobile number.
        return "".join(char for char in str(mobile_number) if char in "0123456789")  # Discard every character except ASCII digits.

    @staticmethod  # Call this helper without an account instance.
    def validate_mobile(mobile_number):  # Require eleven digits beginning with 09.
        mobile = User.normalize_mobile(mobile_number)  # Normalize or validate the mobile number.
        if len(mobile) != 11 or not mobile.startswith("09"):  # Require the expected local mobile number format.
            raise ValueError("Mobile number must be 11 digits and start with '09'.")  # Stop the operation and report this error.
        return mobile  # Return the valid normalized mobile number.

    @staticmethod  # Call this helper without an account instance.
    def validate_pin(pin):  # Require a four-digit ASCII PIN.
        pin = str(pin)  # Convert or validate the PIN text.
        if re.fullmatch(r"[0-9]{4}", pin) is None:  # Require exactly four ASCII digits.
            raise ValueError("PIN must be a 4-digit number.")  # Stop the operation and report this error.
        return pin  # Return the valid four-digit PIN text.

    def __init__(self, name, mobile_number, pin_hash, balance=0):  # Initialize the object and validate its starting fields.
        self.name = required_text(name, "Name")  # Store the validated account name.
        self.mobile_number = self.validate_mobile(mobile_number)  # Store the normalized valid mobile number.
        if not isinstance(pin_hash, str) or re.fullmatch(r"[0-9a-f]{32}\$[0-9a-f]{64}", pin_hash) is None:  # Require the expected salted PIN hash format.
            raise ValueError("Invalid salted PIN hash.")  # Stop the operation and report this error.
        self.pin_hash = pin_hash  # Keep the validated salted PIN hash.
        self.balance = balance  # Validate and set the account balance.
        # Retry state is process-local and resets when this account is reloaded.
        self._failed_pin_attempts = 0  # Clear the failed PIN attempt count.
        self._pin_locked_until = 0.0  # Clear the cooldown deadline.

    @property  # Expose the method as a readable attribute.
    def balance(self):  # Read or validate the account balance.
        return self._balance  # Return the validated decimal balance.

    @balance.setter  # Validate assignments through the balance property.
    def balance(self, value):  # Read or validate the account balance.
        self._balance = amount_decimal(value, allow_zero=True)  # Validate and store a nonnegative decimal balance.

    # Hashing uses the intended draft's salt and PBKDF2 parameters.
    @staticmethod  # Call this helper without an account instance.
    def hashPin(plain_pin, salt=None):  # Derive a salted hash from the PIN.
        pin = User.validate_pin(plain_pin)  # Convert or validate the PIN text.
        salt = os.urandom(16) if salt is None else salt  # Generate a random salt unless one was supplied.
        if not isinstance(salt, bytes) or len(salt) != 16:  # Require a sixteen-byte PIN salt.
            raise ValueError("PIN salt must be 16 bytes.")  # Stop the operation and report this error.
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100000)  # Derive the hash with SHA-256 and 100,000 PBKDF2 rounds.
        return salt.hex() + "$" + digest.hex()  # Join hexadecimal salt and hash with a dollar sign.

    @classmethod  # Pass the class automatically to this constructor helper.
    def createNew(cls, name, mobile_number, plain_pin):  # Validate registration details and construct an account.
        name = required_text(name, "Name")  # Validate and trim the account holder name.
        mobile = cls.validate_mobile(mobile_number)  # Normalize or validate the mobile number.
        return cls(name, mobile, cls.hashPin(plain_pin))  # Construct the account from these fields.

    def checkPin(self, plain_pin):  # Check the PIN and enforce the retry cooldown.
        """Check the shared login/confirmation retry limit on this account object."""
        now = time.monotonic()  # Read elapsed time independently of wall-clock changes.
        if now < self._pin_locked_until:  # Reject PIN checks during the active cooldown.
            remaining = math.ceil(self._pin_locked_until - now)  # Round the remaining cooldown up to whole seconds.
            unit = "second" if remaining == 1 else "seconds"  # Choose the matching singular or plural countdown unit.
            raise AuthenticationError(f"Too many incorrect PIN attempts. Try again in {remaining} {unit}.")  # Stop the operation and report this error.
        if self._pin_locked_until:  # Clear retry state after an expired cooldown.
            self._failed_pin_attempts = 0  # Clear the failed PIN attempt count.
            self._pin_locked_until = 0.0  # Clear the cooldown deadline.

        try:  # Attempt the operation and handle failures below.
            salt_hex, _ = self.pin_hash.split("$")  # Extract the saved salt from the stored hash.
            attempt_hash = self.hashPin(plain_pin, bytes.fromhex(salt_hex))  # Hash the attempted PIN with the original salt.
            valid = hmac.compare_digest(self.pin_hash, attempt_hash)  # Compare saved and attempted hashes with timing resistance.
        except (ValueError, TypeError, AttributeError):  # Treat malformed input as a failed PIN attempt.
            valid = False  # Treat malformed PIN or hash input as a failed attempt.

        if valid:  # Handle a matching PIN.
            self._failed_pin_attempts = 0  # Clear the failed PIN attempt count.
            return True  # Report success.
        self._failed_pin_attempts += 1  # Count this failed PIN attempt.
        if self._failed_pin_attempts >= self.PIN_MAX_ATTEMPTS:  # Start a cooldown after the failed-attempt limit.
            self._pin_locked_until = time.monotonic() + self.PIN_COOLDOWN_SECONDS  # Set the retry cooldown deadline.
            raise AuthenticationError(  # Stop the operation and report this error.
                f"Too many incorrect PIN attempts. Try again in {self.PIN_COOLDOWN_SECONDS} seconds."
            )
        return False  # Report validation or authentication failure.

    def deposit(self, amount):  # Increase the balance by a validated amount.
        amount = amount_decimal(amount)  # Read or parse the transaction amount.
        with localcontext() as context:  # Keep precision changes local to this calculation.
            context.prec = max(28, self.balance.adjusted() + 4, amount.adjusted() + 4)  # Keep enough precision for both money values.
            self.balance = self.balance + amount  # Credit the account and validate its new balance.

    def withdraw(self, amount):  # Subtract a validated amount if funds are sufficient.
        amount = amount_decimal(amount)  # Read or parse the transaction amount.
        if amount > self.balance:  # Reject withdrawals exceeding the balance.
            raise InsufficientFundsError("Insufficient funds for this withdrawal.")  # Stop the operation and report this error.
        with localcontext() as context:  # Keep precision changes local to this calculation.
            context.prec = max(28, self.balance.adjusted() + 4, amount.adjusted() + 4)  # Keep enough precision for both money values.
            self.balance = self.balance - amount  # Debit the account and validate its new balance.

    def toDict(self):  # Convert the account to JSON-compatible fields.
        return {  # Return the fields in this dictionary.
            "name": self.name,  # Include the name field in this record.
            "mobile_number": self.mobile_number,  # Include the mobile number field in this record.
            "pin_hash": self.pin_hash,  # Include the pin hash field in this record.
            "balance": float(self.balance),  # Include the balance field in this record.
        }

    @classmethod  # Pass the class automatically to this constructor helper.
    def fromDict(cls, data):  # Rebuild an account from stored fields.
        return cls(data["name"], data["mobile_number"], data["pin_hash"], data.get("balance", 0))  # Construct the account from these fields.


def find_user(mobile_number, users):  # Find an account by normalized mobile number.
    """Return the User with this mobile number, or None if not found."""
    mobile = User.normalize_mobile(mobile_number)  # Normalize or validate the mobile number.
    return next((user for user in users if user.mobile_number == mobile), None)  # Return the first matching account, or None if absent.


def register(name, mobile_number, pin, users):  # Create an account and reject duplicate mobile numbers.
    """Validate and add a new user, rejecting duplicate mobile numbers."""
    new_user = User.createNew(name, mobile_number, pin)  # Validate registration and construct the account.
    if find_user(new_user.mobile_number, users) is not None:  # Reject registration of an existing mobile number.
        raise ValueError("A user with this mobile number already exists.")  # Stop the operation and report this error.
    users.append(new_user)  # Add the validated account to the session.
    return new_user  # Return the result to the caller.


def login(mobile_number, pin, users):  # Find the account and verify its PIN.
    user = find_user(mobile_number, users)  # Find the account matching the supplied mobile number.
    if user is None or not user.checkPin(pin):  # Reject unknown accounts or unsuccessful PIN checks.
        raise AuthenticationError("Invalid mobile number or PIN.")  # Stop the operation and report this error.
    return user  # Return the result to the caller.
