

class User:
    def __init__ (self, name, email, mobile_number, password_hash, balance = 0):
        self.name = name
        self.email = email.lower()
        self.mobile_number = mobile_number
        self.password_hash = password_hash
        self.balance = balance


def deposit(self, amount):
    if amount <= 0:
        raise ValueError("Deposit amount must be positive.")
    self.balance += amount

def withdraw(self, amount):
    if amount <= 0:
        raise ValueError("Withdraw amount must be positive.")
    if amount > self.balance:
        raise ValueError("Insufficient Funds")
    self.balance -= amount

