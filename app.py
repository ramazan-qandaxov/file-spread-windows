from cryptography.fernet import Fernet
from email.mime.text import MIMEText
from tkinter import messagebox
from datetime import datetime
import tkinter as tk
import threading
import requests
import getpass
import smtplib
import random
import sys
import os
import re

# --- Random Timestamp Generator ---
def get_random_timestamp():
    """Generates a random timestamp tuple for file modification times."""
    # Define start and end dates
    start_date = datetime(2023, 1, 1, 0, 0, 0)
    end_date = datetime(2024, 12, 31, 23, 59, 59)
    start_timestamp = start_date.timestamp()
    end_timestamp = end_date.timestamp()
    random_ts = random.uniform(start_timestamp, end_timestamp)
    # Return (access_time, modification_time)
    return (random_ts, random_ts) 

# --- Helper Function for PyInstaller ---
def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    Used for loading the icon file.
    """
    try:
        # PyInstaller temp folder path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback for development environment
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Configuration ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com/repos/Diemarx/file/contents/")

OBFUSCATED_KEY_PARTS = [b'0', b's', b'g', b'j', b'W', b'v', b'c', b'P', b'E', b'4', b'8', b'0', b'A', b'1', b'c', b'f', b'D', b'a', b'f', b'K', b'b', b'F', b'F', b's', b'5', b'Y', b'b', b'Y', b'V', b'i', b'z', b'p', b'X', b'k', b'G', b'o', b'k', b'Q', b'_', b'8', b'C', b'_', b'4', b'=']
FERNET_KEY = b"".join(OBFUSCATED_KEY_PARTS)
fernet = Fernet(FERNET_KEY)

ENC_SMTP_USERNAME = b'gAAAAABo47LJizt9_c5yctHtbg6InukA3gwXMawJwlBvADCr79wFro9a5ayOXYGBHd0xgmafIIHgD_cNUJbNvv5VmCCHXkfDgr7FKEaquaB5hNbYXG5XvpE='
ENC_SMTP_PASSWORD = b'gAAAAABo47LJoI3-HhyoWQ0bw2bapSva_6Np00mfuQqjDa-CUAGCqlrjTQVfIgKWMx-UNvEbK2WU4TvL9nRCmWpGbv_cF-77r8vfZ2jVkOBNokkspLpalLI='

SMTP_USERNAME = fernet.decrypt(ENC_SMTP_USERNAME).decode()
SMTP_PASSWORD = fernet.decrypt(ENC_SMTP_PASSWORD).decode()

# --- Core Logic ---
def get_file_list(url):
    # Fetch files from GitHub repo
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []

def select_random_files(api_data):
    # Select 15 random files from the API data.
    all_files = [item for item in api_data if item['type'] == 'file']
    if not all_files:
        return []
    max_count = len(all_files)
    count = min(15, max_count)
    return random.sample(all_files, count)

def download_and_save_file(file_info, save_dir):
    # Download a file and save it with random timestamps.
    raw_url = file_info.get('download_url')
    if not raw_url:
        return
    random_times = get_random_timestamp()
    try:
        r = requests.get(raw_url)
        r.raise_for_status()
        
        # Check if directory exists and set its modification time
        os.makedirs(save_dir, exist_ok=True)
        os.utime(save_dir, random_times)
        
        file_path = os.path.join(save_dir, file_info['name'])
        with open(file_path, 'wb') as f:
            f.write(r.content)
            
        # Set file modification time
        os.utime(file_path, random_times)
    except Exception:
        # Ignore errors
        pass

def generate_report_and_save(username, selected_files):
    
    # Download files to categorized paths and generate a structured report.
    system_username = getpass.getuser()
    
    ordinary_paths = [
        r"C:\Users\{username}\AppData\Local\Temp",
        r"C:\Users\{username}\AppData\Local",
        r"C:\Users\{username}\AppData\Roaming",
        r"C:\Users\{username}\AppData\LocalLow",
        r"C:\Users\{username}\AppData\Local\Microsoft\Windows\INetCache",
        r"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\Windows\Temp",
        r"C:\inetpub\wwwroot",
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        r"C:\ProgramData\ssh",
        r"C:\Windows\Logs",
        r"C:\Recovery",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Windows\System32\drivers",
        r"C:\Windows\System32\config",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\Program Files\Common Files",
        r"C:\ProgramData",
        r"C:\Windows\System32\Tasks",
        r"C:\Windows\System32\spool",
        r"C:\Windows\System32\wbem",
        r"C:\Windows\SystemResources",
        r"C:\Windows\Fonts",
        r"C:\Windows\inf",
        r"C:\Windows\System32\catroot2",
        r"C:\Windows\System32\LogFiles",
        r"C:\Windows\System32\GroupPolicy",
        r"C:\Windows\System32\drivers\etc",
    ]

    privesc_paths = [
        r"C:\Users\Admin\AppData\Local\Temp",
        r"C:\Users\Admin\AppData\Local",
        r"C:\Users\Admin\AppData\Roaming",
        r"C:\Users\Admin\AppData\LocalLow",
        r"C:\Users\Admin\AppData\Local\Microsoft\Windows\INetCache",
        r"C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\Users\Admin\Documents",
        r"C:\Users\Admin\Downloads",
        r"C:\Users\Admin\Favorites",
        r"C:\Users\Admin\3D Objects",
        r"C:\Users\Admin\Searches",
        r"C:\Users\Admin\Links",
    ]
    
    obvious_paths = [
        r"C:\Users\Public\Documents",
        r"C:\Users\Public\Downloads",
        r"C:\Users\{username}\Documents",
        r"C:\Users\{username}\Downloads",
        r"C:\Users\{username}\Favorites",
        r"C:\Users\{username}\3D Objects",
        r"C:\Users\{username}\Searches",
        r"C:\Users\{username}\Links",
    ]

    # Replace {username} with the actual system username
    ordinary_paths = [path.replace("{username}", system_username) for path in ordinary_paths]
    obvious_paths = [path.replace("{username}", system_username) for path in obvious_paths]

    # Distribute files and collect report items for each category
    privesc_reports = []
    obvious_reports = []
    ordinary_reports = []

    # Category 1: Privilege Escalation Paths (First 4 files)
    privesc_files = selected_files[:4]
    for file_info in privesc_files:
        save_path = random.choice(privesc_paths)
        download_and_save_file(file_info, save_path)
        privesc_reports.append(f"- {file_info['name']} located at: {save_path}")

    # Category 2: Obvious Paths (Next 5 files)
    obvious_files = selected_files[4:9]
    for file_info in obvious_files:
        save_path = random.choice(obvious_paths)
        download_and_save_file(file_info, save_path)
        obvious_reports.append(f"- {file_info['name']} located at: {save_path}")

    # Category 3: Ordinary System Paths (Remaining files)
    ordinary_files = selected_files[9:]
    for file_info in ordinary_files:
        save_path = random.choice(ordinary_paths)
        download_and_save_file(file_info, save_path)
        ordinary_reports.append(f"- {file_info['name']} located at: {save_path}")

    # Construct the final report body with clear sectional headings
    report_body = f"Asset Distribution Report for: {username}\n\n"
    report_body += "=================================================\n"
    report_body += f"Total Files Deployed: {len(selected_files)}\n"
    report_body += "=================================================\n\n"

    report_body += "--- CATEGORY 1: High-Value (PrivEsc) Paths ---\n"
    report_body += "\n".join(privesc_reports) + "\n\n"

    report_body += "--- CATEGORY 2: Ordinary System Paths ---\n"
    report_body += "\n".join(ordinary_reports) + "\n\n"
    
    report_body += "--- CATEGORY 3: Obvious User Paths ---\n"
    report_body += "\n".join(obvious_reports) + "\n"

    return report_body

def send_email(recipient_email, subject, body):
    # Send the structured report via SMTP.
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient_email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        return False

def do_nothing(event=None):
    # Placeholder function to disable closing the window.
    pass

# --- GUI ---
class ReportApp:
    def __init__(self, master):
        self.master = master
        
        # Load icon if available
        try:
            icon_file_path = resource_path('icon.ico')
            master.iconbitmap(icon_file_path)
        except Exception:
            pass # Ignore if icon fails to load
            
        # Prevent closure/minimization
        master.wm_attributes("-topmost", 1)
        master.resizable(False, False)
        master.geometry("400x250")
        master.minsize(400, 250)
        master.maxsize(400, 250)
        master.protocol("WM_DELETE_WINDOW", do_nothing)
        master.bind("<Escape>", do_nothing)
        master.bind("<Control-q>", do_nothing)
        master.bind("<Control-w>", do_nothing)
        master.bind("<Alt-F4>", do_nothing)
        master.title("Campaign Assets Reporter")
        
        # UI Elements
        tk.Label(master, text="User's Name & Surname:").pack(pady=(10, 0))
        self.name_entry = tk.Entry(master, width=40)
        self.name_entry.pack(pady=5)
        
        tk.Label(master, text="Instructor's Email:").pack(pady=(10, 0))
        self.email_entry = tk.Entry(master, width=40)
        self.email_entry.pack(pady=5)
        self.email_entry.bind("<KeyRelease>", self.validate_email)
        
        self.email_valid_label = tk.Label(master, text="Waiting for input...", fg="gray")
        self.email_valid_label.pack(pady=(5, 0))
        
        self.report_button = tk.Button(master, text="Report", command=self.run_process)
        self.report_button.pack(pady=20)
        self.is_processing = False 

    def validate_email(self, event=None):
        # Validate the email format in real-time.
        email = self.email_entry.get().strip()
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not email:
            self.email_valid_label.config(text="Waiting for input...", fg="gray")
        elif re.match(email_regex, email):
            self.email_valid_label.config(text="Valid email", fg="green")
        else:
            self.email_valid_label.config(text="Invalid email format", fg="red")

    def run_process(self):
            # Run validation and start the payload sequence in a new thread.
            
            username = self.name_entry.get().strip()
            instructor_email = self.email_entry.get().strip()
            
            # Prevent re-execution if already running
            if self.is_processing:
                return
            
            # Perform basic validation
            if not username:
                messagebox.showerror("Error", "Please enter the User's Name & Surname.")
                return
            if not instructor_email:
                messagebox.showerror("Error", "Please enter the Instructor's Email.")
                return
            if self.email_valid_label.cget("text") != "Valid email":
                messagebox.showerror("Error", "Please enter a valid email address.")
                return
            
            # Set processing flag and disable button after successful validation
            self.is_processing = True
            self.report_button.config(state=tk.DISABLED)

            # Start the payload process in a separate thread
            threading.Thread(target=self._process_payload, args=(username, instructor_email), daemon=True).start()

    def _process_payload(self, username, instructor_email):
        # 1. Get file list
        api_data = get_file_list(GITHUB_API_URL)
        if not api_data:
            self.master.destroy()
            return
            
        # 2. Select files
        selected_files = select_random_files(api_data)
        if not selected_files:
            self.master.destroy()
            return
            
        # 3. Download, save, and generate structured report
        report_body = generate_report_and_save(username, selected_files)
        
        # 4. Send email
        email_sent = False
        # Simple loop to continuously attempt sending the email
        while not email_sent:
            try:
                send_email(instructor_email, f"Asset Distribution Report for {username}", report_body)
                email_sent = True
            except Exception:
                # Continue loop on failure, no sleep to make it fast
                continue
                
        # 5. Terminate the application
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()