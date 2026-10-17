"""Wallet users with salted PIN authentication and decimal balances."""

import hashlib
import hmac
import math
import os
import re
import time
from decimal import localcontext

from .transactions import amount_decimal, required_text

__all__ = ["User", "register", "login", "find_user", "AuthenticationError", "InsufficientFundsError"]


class InsufficientFundsError(ValueError):
    """Raised when a user tries to spend more than their balance."""


class AuthenticationError(ValueError):
    """Raised for invalid credentials or an account's PIN cooldown."""


class User:
    PIN_MAX_ATTEMPTS = 5
    PIN_COOLDOWN_SECONDS = 30

    # Helper to normalize the mobile number (keeps ASCII digits only).
    @staticmethod
    def normalize_mobile(mobile_number):
        """Keep only ASCII digits from a mobile number."""
        return "".join(char for char in str(mobile_number) if char in "0123456789")

    @staticmethod
    def validate_mobile(mobile_number):
        """Require eleven digits beginning with 09."""
        mobile = User.normalize_mobile(mobile_number)
        if len(mobile) != 11 or not mobile.startswith("09"):
            raise ValueError("Mobile number must be 11 digits and start with '09'.")
        return mobile

    @staticmethod
    def validate_pin(pin):
        """Require a four-digit ASCII PIN."""
        pin = str(pin)
        if re.fullmatch(r"[0-9]{4}", pin) is None:
            raise ValueError("PIN must be a 4-digit number.")
        return pin

    def __init__(self, name, mobile_number, pin_hash, balance=0):
        """Validate account fields and initialize the balance and PIN retry state."""
        self.name = required_text(name, "Name")
        self.mobile_number = self.validate_mobile(mobile_number)
        if not isinstance(pin_hash, str) or re.fullmatch(r"[0-9a-f]{32}\$[0-9a-f]{64}", pin_hash) is None:
            raise ValueError("Invalid salted PIN hash.")
        self.pin_hash = pin_hash
        self.balance = balance
        # Retry state is process-local and resets when this account is reloaded.
        self._failed_pin_attempts = 0
        self._pin_locked_until = 0.0

    @property
    def balance(self):
        """Return the current decimal balance."""
        return self._balance

    @balance.setter
    def balance(self, value):
        """Validate and store a nonnegative decimal balance."""
        self._balance = amount_decimal(value, allow_zero=True)

    # Hashing uses the intended draft's salt and PBKDF2 parameters.
    @staticmethod
    def hashPin(plain_pin, salt=None):
        """Derive a salted hash from the PIN."""
        pin = User.validate_pin(plain_pin)
        salt = os.urandom(16) if salt is None else salt
        if not isinstance(salt, bytes) or len(salt) != 16:
            raise ValueError("PIN salt must be 16 bytes.")
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100000)
        return salt.hex() + "$" + digest.hex()

    @classmethod
    def createNew(cls, name, mobile_number, plain_pin):
        """Validate registration details and construct an account."""
        name = required_text(name, "Name")
        mobile = cls.validate_mobile(mobile_number)
        return cls(name, mobile, cls.hashPin(plain_pin))

    def checkPin(self, plain_pin):
        """Check the shared login/confirmation retry limit on this account object."""
        now = time.monotonic()
        if now < self._pin_locked_until:
            remaining = math.ceil(self._pin_locked_until - now)
            unit = "second" if remaining == 1 else "seconds"
            raise AuthenticationError(f"Too many incorrect PIN attempts. Try again in {remaining} {unit}.")
        if self._pin_locked_until:
            self._failed_pin_attempts = 0
            self._pin_locked_until = 0.0

        try:
            salt_hex, _ = self.pin_hash.split("$")
            attempt_hash = self.hashPin(plain_pin, bytes.fromhex(salt_hex))
            valid = hmac.compare_digest(self.pin_hash, attempt_hash)
        except (ValueError, TypeError, AttributeError):
            valid = False

        if valid:
            self._failed_pin_attempts = 0
            return True
        self._failed_pin_attempts += 1
        if self._failed_pin_attempts >= self.PIN_MAX_ATTEMPTS:
            self._pin_locked_until = time.monotonic() + self.PIN_COOLDOWN_SECONDS
            raise AuthenticationError(
                f"Too many incorrect PIN attempts. Try again in {self.PIN_COOLDOWN_SECONDS} seconds."
            )
        return False

    def deposit(self, amount):
        """Increase the balance by a validated amount."""
        amount = amount_decimal(amount)
        with localcontext() as context:
            context.prec = max(28, self.balance.adjusted() + 4, amount.adjusted() + 4)
            self.balance = self.balance + amount

    def withdraw(self, amount):
        """Subtract a validated amount if funds are sufficient."""
        amount = amount_decimal(amount)
        if amount > self.balance:
            raise InsufficientFundsError("Insufficient funds for this withdrawal.")
        with localcontext() as context:
            context.prec = max(28, self.balance.adjusted() + 4, amount.adjusted() + 4)
            self.balance = self.balance - amount

    def toDict(self):
        """Convert the account to JSON-compatible fields."""
        return {
            "name": self.name,
            "mobile_number": self.mobile_number,
            "pin_hash": self.pin_hash,
            "balance": float(self.balance),
        }

    @classmethod
    def fromDict(cls, data):
        """Rebuild an account from stored fields."""
        return cls(data["name"], data["mobile_number"], data["pin_hash"], data.get("balance", 0))


def find_user(mobile_number, users):
    """Return the User with this mobile number, or None if not found."""
    mobile = User.normalize_mobile(mobile_number)
    return next((user for user in users if user.mobile_number == mobile), None)


def register(name, mobile_number, pin, users):
    """Validate and add a new user, rejecting duplicate mobile numbers."""
    new_user = User.createNew(name, mobile_number, pin)
    if find_user(new_user.mobile_number, users) is not None:
        raise ValueError("A user with this mobile number already exists.")
    users.append(new_user)
    return new_user


def login(mobile_number, pin, users):
    """Find the account and verify its PIN."""
    user = find_user(mobile_number, users)
    if user is None or not user.checkPin(pin):
        raise AuthenticationError("Invalid mobile number or PIN.")
    return user
