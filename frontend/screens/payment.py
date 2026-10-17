from PyQt6.QtWidgets import QComboBox

from backend.transactions import PAYMENT_STRUCTURE, payment_details
from frontend.screens.transaction_form import TransactionFormScreen


class PaymentScreen(TransactionFormScreen):
    kind = "payment"
    title = "Payment"
    action_text = "Pay"
    fields = [
        ("category", "Category", ""),
        ("subcategory", "Type", ""),
        ("biller", "Pay To", "Biller name"),
        ("reference", "Account Number", "000-000-000"),
    ]

    def __init__(self, app_main):
        """Initialize payment controls and connect the category-dependent choices."""
        super().__init__(app_main)
        self.category_combo = self.inputs["category"]
        self.subcategory_combo = self.inputs["subcategory"]
        self.biller_input = self.inputs["biller"]
        self.account_input = self.inputs["reference"]
        self.pay_btn = self.action_btn
        self.category_combo.currentTextChanged.connect(self.update_subcategories)
        self.update_subcategories(self.category_combo.currentText())

    def create_input(self, key, placeholder):
        """Use dropdowns for payment categories and types, and text fields elsewhere."""
        if key in ("category", "subcategory"):
            combo = QComboBox()
            if key == "category":
                combo.addItems(list(PAYMENT_STRUCTURE))
            return combo
        return super().create_input(key, placeholder)

    def update_subcategories(self, category):
        """Replace payment types with those in the selected category."""
        self.subcategory_combo.clear()
        self.subcategory_combo.addItems(PAYMENT_STRUCTURE.get(category, []))

    def build_details(self, values, amount):
        """Build bill-payment details and a confirmation summary."""
        details = payment_details(
            values["category"], values["subcategory"], values["biller"],
            values["reference"], amount,
        )
        summary = [
            f"Pay to: {details.biller}",
            f"Category: {details.category} / Type: {details.subcategory}",
            f"Account Number: {details.account_reference}",
            f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
