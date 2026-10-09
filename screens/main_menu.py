from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QGridLayout

class MainMenuScreen(QWidget):
    def __init__(self, app_main):
        super().__init__()
        self.app_main = app_main
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Main Menu")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Balance Card
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout()
        card_layout.addWidget(QLabel("Current Balance"))
        balance = QLabel("PHP 5,000.00")
        balance.setObjectName("balanceLabel")
        card_layout.addWidget(balance)
        card.setLayout(card_layout)
        layout.addWidget(card)
        
        layout.addSpacing(20)
        
        # Grid of buttons
        grid = QGridLayout()
        grid.setSpacing(15)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setProperty("class", "menuButton")
        self.send_btn.setMinimumHeight(100)
        grid.addWidget(self.send_btn, 0, 0)
        
        self.pay_btn = QPushButton("Payment")
        self.pay_btn.setProperty("class", "menuButton")
        self.pay_btn.setMinimumHeight(100)
        grid.addWidget(self.pay_btn, 0, 1)
        
        self.cashin_btn = QPushButton("Cash In")
        self.cashin_btn.setProperty("class", "menuButton")
        self.cashin_btn.setMinimumHeight(100)
        grid.addWidget(self.cashin_btn, 1, 0)
        
        self.cashout_btn = QPushButton("Cash Out")
        self.cashout_btn.setProperty("class", "menuButton")
        self.cashout_btn.setMinimumHeight(100)
        grid.addWidget(self.cashout_btn, 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setProperty("class", "secondary")
        self.logout_btn.clicked.connect(self.app_main.go_to_login)
        layout.addWidget(self.logout_btn)
        
        self.setLayout(layout)
