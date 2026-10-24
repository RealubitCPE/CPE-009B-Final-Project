<div align="center">

<img src="assets/digicash-logo.webp" alt="DIGICASH logo - Your money, just a tap away." width="260">

# 💳 DIGICASH - PIN-Based E-Wallet Desktop Application
**CPE-009B (OOP 2) Final Group Project**

[![Python Version](https://img.shields.io/badge/Python-3.x-blue.svg?logo=python&logoColor=white)](#)
[![PyQt6](https://img.shields.io/badge/PyQt6-Framework-green.svg?logo=qt&logoColor=white)](#)
[![Status](https://img.shields.io/badge/Status-In_Development-orange.svg)](#)

*A secure, modular, and object-oriented digital wallet simulation.*

</div>

---

## 🌟 Project Overview

This application simulates a digital E-Wallet with a secure, PIN-based interface. It allows users to perform standard wallet operations in a clean, modern desktop environment. 

### ✨ Key Features
- 🔒 **Secure Login & Registration** with 4-digit PIN verification.
- 💰 **Dashboard** to instantly view current balances.
- 💸 **P2P Transfers** to send money to other users.
- 🧾 **Bill Payments** for utilities and services.
- 💳 **Cash In / Cash Out** simulations.
- 🧾 **Detailed Receipts** generated for every successful transaction.

---

## 🛠️ Technologies Used

| Category | Technology | Description |
| :--- | :--- | :--- |
| **Language** | `Python 3` | Core programming language. |
| **Frontend** | `PyQt6` | Desktop GUI framework, styled with custom QSS. |
| **Backend** | `Python` | Local JSON storage, salted PIN hashes, and validated wallet transactions in `backend/`. |

---


## 🚀 How to Run:

Follow these steps to run the presentation layer locally:

**1. Clone this repository:**
```bash
git clone https://github.com/RealubitCPE/CPE-009B-Final-Project.git
cd CPE-009B-Final-Project
```

**2. Install dependencies:**
```bash
pip install PyQt6
```

**3. Launch the application:**
```bash
python main.py
```

The terminal interface is available with `python cli.py`. Both interfaces use the
same backend and local `users.json` and `transactions.json` files. New accounts
start with a zero balance; use Cash In to fund the simulation.

Run one wallet instance at a time. JSON storage is intended for this local
simulation. An interrupted save leaves `users.json.pending` and blocks further
wallet operations until the account and history files are reconciled.

Five incorrect PIN attempts trigger a 30-second cooldown shared by login and
transaction confirmation. This guard is local to the loaded account and resets
when the application restarts.

## Project Structure

```text
CPE-009B-Final-Project/
├── assets/
│   ├── digicash-logo.webp     Logo used in this README
│   ├── digicash_logo.png      Logo (PNG)
│   └── digicash.ico           Application icon
├── backend/
│   ├── __init__.py
│   ├── storage.py             Local JSON storage (users, transactions)
│   ├── transactions.py        Transaction rules and validation
│   └── user.py                User accounts and salted PIN hashing
├── frontend/
│   ├── components/            Shared PIN input widget
│   ├── screens/               Login, registration, forms, confirmation, receipt
│   ├── __init__.py
│   ├── app.py                 PyQt6 application and screen routing
│   └── style.py               Shared Qt stylesheet
├── tests/
│   ├── test_backend.py        Backend regression checks
│   └── test_ui.py             Offscreen UI regression checks
├── utils/
│   └── transactions.py        Compatibility transaction imports
├── Transaction.py             Compatibility transaction import
├── cli.py                     Terminal interface
├── confirm_transaction.py     Transaction confirmation
├── create_account.py          Account creation
├── login.py                   Login
├── main.menu.py               Main menu
├── main.py                    Desktop launcher
├── storage.py                 Compatibility import for existing callers
├── user.py                    Compatibility import for existing callers
└── README.md
```

## Checks

```bash
python -m unittest discover -s tests -v
```

UI tests use Qt's offscreen platform. Tests isolate wallet files in temporary
directories and do not change local accounts or balances.

<br>

<div align="center">
  <i>Developed with Mwah Mwah Chup Chup for CPE-009B</i>
</div>
