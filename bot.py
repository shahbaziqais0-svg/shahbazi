import sys
import os
import json
import requests
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, 
                            QTabWidget, QSplitter, QGroupBox, QFormLayout, QComboBox,
                            QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                            QButtonGroup, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QIcon

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext

# Import Google Generative AI
import google.generativeai as genai

# Fallback models in case API connection fails
FALLBACK_MODELS = {
    "Gemini 1.5 Flash": "gemini-1.5-flash",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemini 2.0 Flash": "gemini-2.0-flash",
    "Gemini 2.0 Pro": "gemini-2.0-pro"
}

def fetch_available_models(api_key):
    """Fetch available models from the Google Generative AI API."""
    models_dict = {}
    
    try:
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Get all available models
        models_iterator = genai.list_models()
        
        # Filter for Gemini models only and create a dictionary
        for model in models_iterator:
            model_name = model.name
            if "gemini" in model_name.lower():
                # Extract model ID from full name (e.g., 'models/gemini-1.5-flash' -> 'gemini-1.5-flash')
                model_id = model_name.split('/')[-1]
                display_name = getattr(model, 'display_name', model_id)
                description = getattr(model, 'description', 'No description available')
                supported_methods = getattr(model, 'supported_generation_methods', ['N/A'])
                version = getattr(model, 'version', 'N/A')
                
                models_dict[display_name] = {
                    'id': model_id,
                    'description': description,
                    'supported_methods': supported_methods,
                    'version': version
                }
        
        if not models_dict:
            # Convert fallback models to the new format
            fallback_dict = {}
            for display_name, model_id in FALLBACK_MODELS.items():
                fallback_dict[display_name] = {
                    'id': model_id,
                    'description': 'Fallback model',
                    'supported_methods': ['text'],
                    'version': 'N/A'
                }
            return fallback_dict
        
        return models_dict
    
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Convert fallback models to the new format
        fallback_dict = {}
        for display_name, model_id in FALLBACK_MODELS.items():
            fallback_dict[display_name] = {
                'id': model_id,
                'description': 'Fallback model',
                'supported_methods': ['text'],
                'version': 'N/A'
            }
        return fallback_dict

class ModelLoaderThread(QThread):
    models_loaded = pyqtSignal(dict)
    loading_failed = pyqtSignal(str)
    
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        
    def run(self):
        try:
            models = fetch_available_models(self.api_key)
            self.models_loaded.emit(models)
        except Exception as e:
            self.loading_failed.emit(str(e))
            # Convert fallback models to the new format
            fallback_dict = {}
            for display_name, model_id in FALLBACK_MODELS.items():
                fallback_dict[display_name] = {
                    'id': model_id,
                    'description': 'Fallback model',
                    'supported_methods': ['text'],
                    'version': 'N/A'
                }
            self.models_loaded.emit(fallback_dict)

class TelegramBotThread(QThread):
    message_received = pyqtSignal(str, str)
    bot_status = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, telegram_token, gemini_api_key, gemini_model, gemini_base_url="https://generativelanguage.googleapis.com/v1beta/models", system_instruction=""):
        super().__init__()
        self.telegram_token = telegram_token
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.gemini_base_url = gemini_base_url
        self.gemini_url = f"{gemini_base_url}/{gemini_model}:generateContent"
        self.system_instruction = system_instruction
        self.is_running = False
        self.application = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        await update.message.reply_text(
            "👋 Hello! I'm your AI assistant powered by Gemini. Just send me a message and I'll respond!"
        )
        self.message_received.emit("Bot", "User started the bot")
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        await update.message.reply_text(
            f"🤖 I can help you with various tasks using Gemini AI ({self.gemini_model}). Just send me any message and I'll respond!"
        )
        self.message_received.emit("Bot", "User requested help")
        
    def get_gemini_response(self, prompt: str) -> str:
        """Get response from Gemini AI API."""
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add system instruction if provided
        if self.system_instruction:
            data = {
                "contents": [{
                    "parts": [{"text": f"{self.system_instruction}\n\nUser: {prompt}"}]
                }]
            }
        else:
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
        
        try:
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract the text from the response
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            return "Sorry, I couldn't generate a response."
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return error_msg
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages and respond using Gemini AI."""
        user_message = update.message.text
        user_name = update.message.from_user.first_name
        
        self.message_received.emit(f"User ({user_name})", user_message)
        
        # Get response from Gemini
        ai_response = self.get_gemini_response(user_message)
        
        # Send the response back to the user
        await update.message.reply_text(ai_response)
        self.message_received.emit("Gemini AI", ai_response)
        
    def run(self):
        """Run the bot in a separate thread."""
        self.is_running = True
        self.bot_status.emit("Starting bot...")
        
        async def run_bot():
            try:
                # Create the Application and pass it your bot's token
                self.application = Application.builder().token(self.telegram_token).build()
                
                # Add handlers
                self.application.add_handler(CommandHandler("start", self.start_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                
                self.bot_status.emit(f"Bot is running with model: {self.gemini_model}")
                
                # Start the Bot
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                
                # Run the bot until the is_running flag is set to False
                while self.is_running:
                    await asyncio.sleep(1)
                    
                # Stop the bot
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.bot_status.emit("Bot stopped")
                
            except Exception as e:
                self.is_running = False
                error_msg = f"Bot error: {str(e)}"
                self.error_occurred.emit(error_msg)
                self.bot_status.emit("Bot crashed")
        
        import asyncio
        asyncio.run(run_bot())
    
    def stop(self):
        """Stop the bot."""
        self.is_running = False
        self.bot_status.emit("Stopping bot...")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.selected_models = {}  # Dictionary to store selected models
        
        self.setWindowTitle("Telegram Gemini Bot")
        self.setMinimumSize(800, 600)
        
        # Load saved settings if available
        self.settings = {}
        if os.path.exists("bot_settings.json"):
            try:
                with open("bot_settings.json", "r") as f:
                    self.settings = json.load(f)
            except:
                pass
        
        # Initialize UI
        self.init_ui()
        
        # Set values from settings if available
        if "telegram_token" in self.settings:
            self.telegram_token_input.setText(self.settings["telegram_token"])
        if "gemini_api_key" in self.settings:
            self.gemini_api_key_input.setText(self.settings["gemini_api_key"])
            
            # Start loading models if API key is available
            self.load_models(self.settings["gemini_api_key"])
            
        if "gemini_base_url" in self.settings:
            self.gemini_base_url_input.setText(self.settings["gemini_base_url"])
        else:
            # Default Gemini URL
            self.gemini_base_url_input.setText("https://generativelanguage.googleapis.com/v1beta/models")
            
        if "system_instruction" in self.settings:
            self.system_instruction_input.setText(self.settings["system_instruction"])
        else:
            # Default system instruction
            self.system_instruction_input.setText("You are a helpful AI assistant.")
            
        # Load selected models from settings if available
        if "selected_models" in self.settings:
            self.selected_models = self.settings["selected_models"]
        
        # Connect API key input to model loading
        self.gemini_api_key_input.editingFinished.connect(self.on_api_key_changed)
        
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Configuration Tab
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        
        # Bot Configuration Group
        config_group = QGroupBox("Bot Configuration")
        config_form = QFormLayout()
        
        self.telegram_token_input = QLineEdit()
        self.gemini_api_key_input = QLineEdit()
        self.gemini_base_url_input = QLineEdit()
        
        # Create model dropdown with loading indicator
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItem("Loading models... Please wait")
        self.model_dropdown.setEnabled(False)
        
        # System instruction input
        self.system_instruction_input = QTextEdit()
        self.system_instruction_input.setPlaceholderText("Enter system instruction for the AI (e.g., 'You are a helpful AI assistant.')")
        self.system_instruction_input.setMaximumHeight(100)
        
        config_form.addRow("Telegram Token:", self.telegram_token_input)
        config_form.addRow("Gemini API Key:", self.gemini_api_key_input)
        config_form.addRow("Gemini Base URL:", self.gemini_base_url_input)
        config_form.addRow("Gemini Model:", self.model_dropdown)
        config_form.addRow("System Instruction:", self.system_instruction_input)
        
        config_group.setLayout(config_form)
        
        # Bot Control Group
        control_group = QGroupBox("Bot Control")
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Bot")
        self.start_button.clicked.connect(self.start_bot)
        
        self.stop_button = QPushButton("Stop Bot")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.save_button)
        
        control_group.setLayout(control_layout)
        
        # Status and Log Group
        status_group = QGroupBox("Bot Status and Logs")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Not Running")
        status_layout.addWidget(self.status_label)
        
        # Add chat display to status group
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)
        status_layout.addWidget(self.chat_display)
        
        status_group.setLayout(status_layout)
        
        # Add groups to config tab
        config_layout.addWidget(config_group)
        config_layout.addWidget(control_group)
        config_layout.addWidget(status_group)
        config_layout.addStretch()
        
        # Models Tab
        models_tab = QWidget()
        models_layout = QVBoxLayout(models_tab)
        
        # Models table
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(5)  # Added one more column for checkbox
        self.models_table.setHorizontalHeaderLabels(["Select", "Model Name", "Version", "Supported Methods", "Description"])
        self.models_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.models_table.setColumnWidth(0, 50)  # Set width for checkbox column
        self.models_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.models_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Add models table to layout
        models_layout.addWidget(self.models_table)
        
        # Add buttons for model selection
        buttons_layout = QHBoxLayout()
        
        select_models_button = QPushButton("Apply Selected Models")
        select_models_button.clicked.connect(self.apply_selected_models)
        
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all_models)
        
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.clicked.connect(self.deselect_all_models)
        
        buttons_layout.addWidget(select_models_button)
        buttons_layout.addWidget(select_all_button)
        buttons_layout.addWidget(deselect_all_button)
        
        models_layout.addLayout(buttons_layout)
        
        # Add tabs to tab widget
        tab_widget.addTab(config_tab, "Configuration")
        tab_widget.addTab(models_tab, "Available Models")
        
        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)
        
        # Set main widget
        self.setCentralWidget(main_widget)
    
    def on_api_key_changed(self):
        """Called when the API key input loses focus."""
        api_key = self.gemini_api_key_input.text().strip()
        if api_key:
            self.load_models(api_key)
    
    def load_models(self, api_key):
        """Load models using the provided API key."""
        if not api_key:
            return
            
        # Show loading state
        self.model_dropdown.clear()
        self.model_dropdown.addItem("Loading models... Please wait")
        self.model_dropdown.setEnabled(False)
        
        # Clear models table
        self.models_table.setRowCount(0)
        
        # Start model loading thread
        self.model_loader = ModelLoaderThread(api_key)
        self.model_loader.models_loaded.connect(self.on_models_loaded)
        self.model_loader.loading_failed.connect(self.on_model_loading_failed)
        self.model_loader.start()
    
    @pyqtSlot(dict)
    def on_models_loaded(self, models):
        """Handle loaded models."""
        self.model_dropdown.clear()
        self.available_models = models
        
        # Populate models table
        self.populate_models_table(models)
        
        # Update dropdown with selected models
        self.update_model_dropdown()
        
        # Log success
        self.chat_display.append("<span style='color:green'><b>INFO:</b> Successfully loaded Gemini models</span>")
        self.chat_display.append("")
    
    def populate_models_table(self, models):
        """Populate the models table with available models."""
        self.models_table.setRowCount(0)
        
        for row, (display_name, model_data) in enumerate(models.items()):
            self.models_table.insertRow(row)
            
            # Create checkbox for model selection
            checkbox = QCheckBox()
            checkbox.setChecked(display_name in self.selected_models)
            checkbox.stateChanged.connect(lambda state, name=display_name: self.on_checkbox_changed(state, name))
            
            # Add checkbox to the first column
            self.models_table.setCellWidget(row, 0, checkbox)
            
            # Add model name
            name_item = QTableWidgetItem(display_name)
            self.models_table.setItem(row, 1, name_item)
            
            # Add version
            version_item = QTableWidgetItem(model_data.get('version', 'N/A'))
            self.models_table.setItem(row, 2, version_item)
            
            # Add supported methods
            methods = model_data.get('supported_methods', ['N/A'])
            methods_item = QTableWidgetItem(', '.join(methods))
            self.models_table.setItem(row, 3, methods_item)
            
            # Add description
            description_item = QTableWidgetItem(model_data.get('description', 'No description available'))
            self.models_table.setItem(row, 4, description_item)
    
    def on_checkbox_changed(self, state, model_name):
        """Handle checkbox state change in the models table."""
        if state == Qt.Checked:
            self.selected_models[model_name] = self.available_models[model_name]
        else:
            if model_name in self.selected_models:
                del self.selected_models[model_name]
    
    def select_all_models(self):
        """Select all models in the table."""
        for row in range(self.models_table.rowCount()):
            checkbox = self.models_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
                model_name = self.models_table.item(row, 1).text()
                self.selected_models[model_name] = self.available_models[model_name]
    
    def deselect_all_models(self):
        """Deselect all models in the table."""
        for row in range(self.models_table.rowCount()):
            checkbox = self.models_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
                model_name = self.models_table.item(row, 1).text()
                if model_name in self.selected_models:
                    del self.selected_models[model_name]
    
    def apply_selected_models(self):
        """Apply selected models to the dropdown."""
        self.update_model_dropdown()
        
        # Switch to the Configuration tab
        self.findChild(QTabWidget).setCurrentIndex(0)
        
        # Show message
        if self.selected_models:
            QMessageBox.information(self, "Models Applied", 
                                   f"{len(self.selected_models)} models have been added to the dropdown.")
        else:
            QMessageBox.warning(self, "No Models Selected", 
                               "Please select at least one model from the table.")
    
    def update_model_dropdown(self):
        """Update the model dropdown with selected models."""
        self.model_dropdown.clear()
        
        if not self.selected_models:
            self.model_dropdown.addItem("No models selected")
            self.model_dropdown.setEnabled(False)
            return
        
        # Add selected models to dropdown
        for display_name in self.selected_models.keys():
            self.model_dropdown.addItem(display_name)
        
        # Set previously selected model if available
        if "selected_model" in self.settings:
            selected_model_id = self.settings["selected_model"]
            
            for display_name, model_data in self.selected_models.items():
                if model_data['id'] == selected_model_id:
                    self.model_dropdown.setCurrentText(display_name)
                    break
        
        self.model_dropdown.setEnabled(True)
    
    @pyqtSlot(str)
    def on_model_loading_failed(self, error_message):
        """Handle model loading failure."""
        self.chat_display.append(f"<span style='color:orange'><b>WARNING:</b> Failed to load models: {error_message}</span>")
        self.chat_display.append("<span style='color:orange'><b>WARNING:</b> Using fallback model list</span>")
        self.chat_display.append("")
    
    def save_settings(self):
        """Save current settings to a file."""
        selected_model_display = self.model_dropdown.currentText()
        selected_model_code = self.selected_models.get(selected_model_display, {}).get('id', "gemini-2.0-flash")
        
        self.settings = {
            "telegram_token": self.telegram_token_input.text(),
            "gemini_api_key": self.gemini_api_key_input.text(),
            "gemini_base_url": self.gemini_base_url_input.text(),
            "selected_model": selected_model_code,
            "system_instruction": self.system_instruction_input.toPlainText(),
            "selected_models": self.selected_models
        }
        
        try:
            with open("bot_settings.json", "w") as f:
                json.dump(self.settings, f)
            QMessageBox.information(self, "Settings Saved", "Your bot settings have been saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save settings: {str(e)}")
    
    def start_bot(self):
        """Start the Telegram bot in a separate thread."""
        # Validate inputs
        telegram_token = self.telegram_token_input.text().strip()
        gemini_api_key = self.gemini_api_key_input.text().strip()
        gemini_base_url = self.gemini_base_url_input.text().strip()
        system_instruction = self.system_instruction_input.toPlainText().strip()
        
        if not telegram_token or not gemini_api_key or not gemini_base_url:
            QMessageBox.warning(self, "Missing Information", 
                               "Please provide both Telegram token and Gemini API key.")
            return
        
        # Get selected model
        selected_model_display = self.model_dropdown.currentText()
        
        if selected_model_display == "Loading models... Please wait" or selected_model_display == "No models selected":
            QMessageBox.warning(self, "Models Loading", 
                               "Please select at least one model before starting the bot.")
            return
            
        selected_model = self.selected_models.get(selected_model_display, {}).get('id', "gemini-2.0-flash")
        
        # Create and start bot thread
        self.bot_thread = TelegramBotThread(
            telegram_token, 
            gemini_api_key, 
            selected_model,
            gemini_base_url,
            system_instruction
        )
        self.bot_thread.message_received.connect(self.on_message_received)
        self.bot_thread.bot_status.connect(self.on_bot_status)
        self.bot_thread.error_occurred.connect(self.on_error)
        self.bot_thread.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.telegram_token_input.setEnabled(False)
        self.gemini_api_key_input.setEnabled(False)
        self.gemini_base_url_input.setEnabled(False)
        self.model_dropdown.setEnabled(False)
        self.system_instruction_input.setEnabled(False)
    
    def stop_bot(self):
        """Stop the running Telegram bot."""
        if self.bot_thread and self.bot_thread.is_running:
            self.bot_thread.stop()
            self.bot_thread.quit()
            self.bot_thread.wait()
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.telegram_token_input.setEnabled(True)
            self.gemini_api_key_input.setEnabled(True)
            self.gemini_base_url_input.setEnabled(True)
            self.model_dropdown.setEnabled(True)
            self.system_instruction_input.setEnabled(True)
    
    @pyqtSlot(str, str)
    def on_message_received(self, sender, message):
        """Handle received messages from the bot."""
        self.chat_display.append(f"<b>{sender}:</b> {message}")
        self.chat_display.append("")  # Add blank line for readability
    
    @pyqtSlot(str)
    def on_bot_status(self, status):
        """Update the bot status display."""
        self.status_label.setText(status)
    
    @pyqtSlot(str)
    def on_error(self, error_message):
        """Handle error messages from the bot."""
        self.chat_display.append(f"<span style='color:red'><b>ERROR:</b> {error_message}</span>")
        self.chat_display.append("")
        QMessageBox.warning(self, "Bot Error", error_message)
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.bot_thread and self.bot_thread.is_running:
            reply = QMessageBox.question(self, "Confirm Exit", 
                                        "The bot is still running. Are you sure you want to exit?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stop_bot()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    if hasattr(sys, 'frozen'):
        # Prevent console window from showing if app is frozen (using PyInstaller)
        import win32gui, win32con
        window = win32gui.GetForegroundWindow()
        win32gui.ShowWindow(window, win32con.SW_HIDE)
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 
