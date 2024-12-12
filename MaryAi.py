import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime
import threading

class MaryAiApp:
    def __init__(self, master):
        # Color palette
        self.BACKGROUND_COLOR = "#F0F4F8"
        self.PRIMARY_COLOR = "#007ACC"
        self.TEXT_COLOR = "#333333"

        # Master window setup
        self.master = master
        master.title("MaryAi | Intelligent Study Companion")
        master.geometry("1200x800")
        master.configure(bg=self.BACKGROUND_COLOR)

        # Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()

        # Database setup
        self.conn = sqlite3.connect('maryai_study.db', check_same_thread=False)
        self.create_tables()

        # Gemini AI Setup
        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            messagebox.showerror("AI Configuration Error", 
                                 f"Could not initialize AI: {str(e)}\n"
                                 "Please check your API key and internet connection.")
            master.quit()

        # Context Management
        self.MAX_CONTEXT_LENGTH = 10
        self.context_window = []

        # Feature Modes with Prompts
        self.FEATURE_PROMPTS = {
            "Study Tracker": "Help the user track and optimize their study progress. Provide actionable insights and motivation.",
            "Adaptive Learning": "Assist the user in creating personalized learning strategies based on their study patterns and goals.",
            "Interactive Tools": "Suggest interactive study techniques, quizzes, and learning methods.",
            "Motivational Support": "Provide encouraging and supportive guidance to help the user stay focused and motivated."
        }

        # Create UI
        self.create_ui()
        self.load_conversation_history()

    def _configure_styles(self):
        # Styling configurations (similar to previous implementation)
        self.style.configure('Main.TFrame', background=self.BACKGROUND_COLOR)
        self.style.configure('TLabel',
            background=self.BACKGROUND_COLOR,
            font=('Arial', 12),
            foreground=self.TEXT_COLOR
        )
        self.style.configure('Primary.TButton',
            font=('Arial', 11, 'bold'),
            background=self.PRIMARY_COLOR,
            foreground="white",
            padding=(10, 5)
        )
        self.style.map('Primary.TButton',
            background=[('active', '#005BB5')],
            foreground=[('active', 'white')]
        )

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                sender TEXT,
                message TEXT,
                feature_mode TEXT
            )
        ''')
        self.conn.commit()

    def create_ui(self):
        # Main container
        main_container = ttk.Frame(self.master, padding="20 20 20 20", style='Main.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)

        # Chat History
        self.chat_history = scrolledtext.ScrolledText(
            main_container,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=('Arial', 11),
            bg="white",
            fg=self.TEXT_COLOR,
            borderwidth=1,
            relief="solid",
            padx=10,
            pady=10
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Configure chat tags
        self.chat_history.tag_configure('user', foreground=self.PRIMARY_COLOR, font=('Arial', 12, 'bold'))
        self.chat_history.tag_configure('maryai', foreground=self.TEXT_COLOR, font=('Arial', 11))
        self.chat_history.tag_configure('system', foreground='gray', font=('Arial', 10, 'italic'))

        # Input Frame
        input_frame = ttk.Frame(main_container, style='Main.TFrame')
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # Feature Dropdown
        self.feature_var = tk.StringVar(value="Study Tracker")
        feature_dropdown = ttk.Combobox(
            input_frame, 
            textvariable=self.feature_var, 
            values=list(self.FEATURE_PROMPTS.keys()),
            width=20
        )
        feature_dropdown.pack(side=tk.LEFT, padx=(0, 10))

        # Input Entry
        self.input_entry = ttk.Entry(
            input_frame, 
            width=60, 
            font=('Arial', 11)
        )
        self.input_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        self.input_entry.bind("<Return>", self.send_message)

        # Send Button
        send_button = ttk.Button(
            input_frame, 
            text="SEND", 
            command=self.send_message,
            style='Primary.TButton'
        )
        send_button.pack(side=tk.LEFT)

    def send_message(self, event=None):
        user_message = self.input_entry.get().strip()
        if not user_message:
            return

        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Display user message
        feature_mode = self.feature_var.get()
        self.chat_history.insert(tk.END, f"You ({feature_mode}): {user_message}\n", "user")
        
        # Save user message to history
        self.save_message_to_history('You', user_message, feature_mode)
        
        # Prepare system prompt
        system_prompt = (
            f"You are MaryAi, an AI study assistant. "
            f"Current mode: {feature_mode}. "
            f"Mode Description: {self.FEATURE_PROMPTS[feature_mode]}\n\n"
            "Provide helpful, encouraging, and personalized assistance."
        )

        # Generate AI response in a separate thread
        threading.Thread(target=self.generate_ai_response, 
                         args=(user_message, system_prompt, feature_mode), 
                         daemon=True).start()

    def generate_ai_response(self, user_message, system_prompt, feature_mode):
        try:
            # Prepare the full context
            full_context = system_prompt + "\n\n" + user_message
            
            # Generate response
            response = self.chat.send_message(full_context)
            ai_response = response.text.strip()

            # Update UI from main thread
            self.master.after(0, self._display_ai_response, ai_response, feature_mode)

        except Exception as e:
            error_msg = f"AI Response Error: {str(e)}"
            self.master.after(0, self._display_system_message, error_msg)

    def _display_ai_response(self, response, feature_mode):
        # Display AI response
        self.chat_history.insert(tk.END, f"MaryAi ({feature_mode}): {response}\n\n", "maryai")
        self.chat_history.see(tk.END)
        
        # Save AI message to history
        self.save_message_to_history('MaryAi', response, feature_mode)

    def _display_system_message(self, message):
        # Display system messages
        self.chat_history.insert(tk.END, f"System: {message}\n\n", "system")
        self.chat_history.see(tk.END)

    def save_message_to_history(self, sender, message, feature_mode):
        cursor = self.conn.cursor()
        timestamp = datetime.now()
        cursor.execute('''
            INSERT INTO conversation_history 
            (timestamp, sender, message, feature_mode) 
            VALUES (?, ?, ?, ?)
        ''', (timestamp, sender, message, feature_mode))
        self.conn.commit()

    def load_conversation_history(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT sender, message, feature_mode FROM conversation_history ORDER BY id')

        # Clear existing chat history
        self.chat_history.delete('1.0', tk.END)

        # Reload conversation
        for sender, message, feature_mode in cursor.fetchall():
            if sender == 'You':
                self.chat_history.insert(tk.END, f"{sender} ({feature_mode}): {message}\n", "user")
            elif sender == 'MaryAi':
                self.chat_history.insert(tk.END, f"{sender} ({feature_mode}): {message}\n\n", "maryai")
            else:
                self.chat_history.insert(tk.END, f"{sender}: {message}\n\n", "system")

        self.chat_history.see(tk.END)

    def __del__(self):
        self.conn.close()

def main():
    root = tk.Tk()
    app = MaryAiApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()