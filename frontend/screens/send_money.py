from frontend.screens.transaction_form import TransactionFormScreen
from backend.transactions import account_details
from backend.user import User


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
        # Check the number now so mistakes show up before the PIN step.
        mobile = User.validate_mobile(values["number"])
        user = self.main_window.current_user
        if user is not None and mobile == user.mobile_number:
            raise ValueError("Cannot send money to your own account.")
        details = account_details(mobile, values["name"], amount)
        summary = [
            f"Send to: {values['name']}", f"Mobile Number: {mobile}",
            f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
