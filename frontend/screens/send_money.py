from frontend.screens.transaction_form import TransactionFormScreen
from backend.transactions import account_details


class SendMoneyScreen(TransactionFormScreen):
    kind = "send"
    title = "Send Money"
    action_text = "Send"
    fields = [
        ("number", "Mobile Number", "0917 000 0000"),
        ("name", "Name", "Juan Dela Cruz"),
    ]

    def build_details(self, values, amount):
        """Build recipient account details and a money-transfer summary."""
        details = account_details(values["number"], values["name"], amount)
        summary = [
            f"Send to: {values['name']}", f"Mobile Number: {values['number']}",
            f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
