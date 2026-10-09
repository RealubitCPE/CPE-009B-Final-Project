import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Import styles and screens
from utils.style import STYLE_SHEET
from screens.login import LoginScreen
from screens.create_account import CreateAccountScreen
from screens.main_menu import MainMenuScreen

class EWalletApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("E-Wallet")
        self.setFixedSize(450, 750)
        self.setStyleSheet(STYLE_SHEET)
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.login_screen = LoginScreen(self)
        self.create_account_screen = CreateAccountScreen(self)
        self.main_menu_screen = MainMenuScreen(self)
        
        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.create_account_screen)
        self.stacked_widget.addWidget(self.main_menu_screen)
        
    def go_to_login(self):
        self.stacked_widget.setCurrentWidget(self.login_screen)
        self.login_screen.pin_input.clear()

    def go_to_create_account(self):
        self.stacked_widget.setCurrentWidget(self.create_account_screen)

    def go_to_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.main_menu_screen)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EWalletApp()
    window.show()
    sys.exit(app.exec())
