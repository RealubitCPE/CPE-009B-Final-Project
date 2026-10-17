from backend.transactions import withdraw_details
from frontend.screens.transaction_form import TransactionFormScreen


class CashOutScreen(TransactionFormScreen):
    kind = "cash_out"
    title = "Cash Out"
    action_text = "Cash Out"
    fields = [
        ("destination", "Destination", "Bank or cash-out outlet"),
        ("number", "Account Number", "000-000-000"),
    ]

    def build_details(self, values, amount):
        """Build withdrawal details using the signed-in account and destination."""
        user = self.main_window.current_user
        if user is None:
            raise ValueError("Log in before making a transaction.")
        details = withdraw_details(values["destination"], user.name, values["number"], amount)
        summary = [
            f"Destination: {details.destination}", f"Name: {details.account_name}",
            f"Account Number: {details.account_number}", f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
