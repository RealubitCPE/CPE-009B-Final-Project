import hashlib
import hmac
import os

class InsufficientFundsError(ValueError):
    """Exception raised when a user tries to withdraw more money than they have in their account."""

class User:

    #helper function to hash the pin
    @staticmethod
    def normalize_mobile(mobile_number):
        return "".join(filter(str.isdigit, mobile_number))

    #helper function to hash the pin
    @staticmethod
    def validate_pin(pin):
        pin = str(pin)
        if len(pin) != 4 or not pin.isdigit():
            raise ValueError("PIN must be a 4-digit number.")
        return pin

    #constructor
    def __init__ (self, name, mobile_number, pin_hash, balance = 0):
        self.name = name
        self.mobile_number = mobile_number
        self.pin_hash= pin_hash
        self.balance = balance

    #hashing 
    @staticmethod
    def hashPin(plain_pin, salt=None):
        pin = User.validate_pin(plain_pin)
        salt = salt if salt is not None else os.urandom(16)
        digest = hashlib.pbkdf2_hmac('sha256', pin.encode("utf-8"), salt, 100000)
        return salt.hex() +  "$" + digest.hex()

    @classmethod
    def createNew(cls, name, mobile_number, plain_pin):
        #checking if name is empty
        if not str(name).strip():
            raise ValueError("Name cannot be empty.")

        #checking if mobile number is valid
        mobile = User.normalize_mobile(mobile_number)
        if len(mobile) !=11 or not mobile.startswith("09"):
            raise ValueError("Mobile number must be 11 digits and start with '09'.")
        return cls(name, mobile, User.hashPin(plain_pin), 0)

    #logging in and verification

    def checkPin(self, plain_pin):
        try:
            salt_hex, _, attempt_hash = self.pin_hash.split("$")
            attempt_hash = User.hashPin(plain_pin, bytes.fromhex(salt_hex))
        except ValueError:
            return False
        return hmac.compare_digest(self.pin_hash, attempt_hash)

    #kane
    def deposit(self, amount):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance = round(self.balance + amount, 2)

    def withdraw(self,amount):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > self.balance:
            raise InsufficientFundsError("Insufficient funds for this withdrawal.")
        self.balance = round(self.balance - amount, 2)

    #storing and loading user data

    def toDict(self):
        return {
            "name": self.name,
            "mobile_number": self.mobile_number,
            "pin_hash": self.pin_hash,
            "balance": self.balance
        }

    @classmethod
    def fromDict(cls, data):
        return cls(
            data["name"],
            data["mobile_number"],
            data["pin_hash"],
            data.get("balance", 0.0)
        )



