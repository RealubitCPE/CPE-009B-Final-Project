from backend.transactions import deposit_details
from frontend.screens.transaction_form import TransactionFormScreen


class CashInScreen(TransactionFormScreen):
    kind = "cash_in"
    title = "Cash In"
    action_text = "Cash In"
    fields = [("source", "Source", "Bank or cash-in outlet")]

    def build_details(self, values, amount):
        """Build cash-in details using the signed-in account name."""
        user = self.main_window.current_user
        if user is None:
            raise ValueError("Log in before making a transaction.")
        details = deposit_details(values["source"], user.name, amount)
        summary = [
            f"Source: {details.source}", f"Name: {details.account_name}",
            f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
