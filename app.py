from cryptography.fernet import Fernet
from email.mime.text import MIMEText
from tkinter import messagebox
from datetime import datetime
import tkinter as tk
import requests
import getpass
import smtplib
import random
import sys
import os
import re

# --- Random Timestamp Generator ---
def get_random_timestamp():
    # Define start and end dates
    start_date = datetime(2023, 1, 1, 0, 0, 0)
    end_date = datetime(2024, 12, 31, 23, 59, 59)
    start_timestamp = start_date.timestamp()
    end_timestamp = end_date.timestamp()
    random_ts = random.uniform(start_timestamp, end_timestamp)
    return (random_ts, random_ts) 

# --- Helper Function ---
def resource_path(relative_path):
    try:
        # PyInstaller temp folder path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback for development environment
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []

# --- Core Logic ---
def select_random_files(api_data):
    all_files = [item for item in api_data if item['type'] == 'file']
    if not all_files:
        return []
    max_count = len(all_files)
    count = min(15, max_count)
    return random.sample(all_files, count)

def download_and_save_file(file_info, save_dir):
    raw_url = file_info.get('download_url')
    if not raw_url:
        return
    random_times = get_random_timestamp()
    try:
        r = requests.get(raw_url)
        r.raise_for_status()
        os.makedirs(save_dir, exist_ok=True)
        os.utime(save_dir, random_times)
        file_path = os.path.join(save_dir, file_info['name'])
        with open(file_path, 'wb') as f:
            f.write(r.content)
        os.utime(file_path, random_times)
    except Exception:
        pass

def generate_report_and_save(username, selected_files):
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
    ]
    privesc_paths = [
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Windows\System32\drivers",
        r"C:\Windows\System32\config",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\Program Files\Common Files",
        r"C:\ProgramData",
    ]
    obvious_paths = [
        r"C:\Users\Public\Documents",
        r"C:\Users\Public\Downloads",
        r"C:\Users\{username}\Documents",
        r"C:\Users\{username}\Downloads",
        r"C:\Users\{username}\Favorites",
    ]

    # Replace {username} with the actual system username
    ordinary_paths = [path.replace("{username}", system_username) for path in ordinary_paths]
    privesc_paths = [path.replace("{username}", system_username) for path in privesc_paths]
    obvious_paths = [path.replace("{username}", system_username) for path in obvious_paths]

    # Distribute files across the paths
    report_items = []
    for file_info, save_path in zip(selected_files[:4], random.choices(privesc_paths, k=4)):
        download_and_save_file(file_info, save_path)
        report_items.append(f"- {file_info['name']} located at: {save_path}\n")

    for file_info, save_path in zip(selected_files[4:9], random.choices(obvious_paths, k=5)):
        download_and_save_file(file_info, save_path)
        report_items.append(f"- {file_info['name']} located at: {save_path}\n")

    for file_info, save_path in zip(selected_files[9:], random.choices(ordinary_paths, k=6)):
        download_and_save_file(file_info, save_path)
        report_items.append(f"- {file_info['name']} located at: {save_path}\n")

    report_body = f"Asset Report for: {username}\n\nFiles chosen for ({len(selected_files)} items):\n{''.join(report_items)}\n"
    return report_body

def send_email(recipient_email, subject, body):
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
    pass

# --- GUI ---
class ReportApp:
    def __init__(self, master):
        self.master = master
        icon_file_path = resource_path('icon.ico')
        master.iconbitmap(icon_file_path)
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
        tk.Label(master, text="User's Name & Surname:").pack(pady=(10, 0))
        self.name_entry = tk.Entry(master, width=40)
        self.name_entry.pack(pady=5)
        tk.Label(master, text="Instructor's Email:").pack(pady=(10, 0))
        self.email_entry = tk.Entry(master, width=40)
        self.email_entry.pack(pady=5)
        self.email_entry.bind("<KeyRelease>", self.validate_email)
        self.email_valid_label = tk.Label(master, text="", fg="red")
        self.email_valid_label.pack(pady=(5, 0))
        tk.Button(master, text="Report", command=self.run_process).pack(pady=20)

    def validate_email(self, event=None):
        email = self.email_entry.get().strip()
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(email_regex, email):
            self.email_valid_label.config(text="Valid email", fg="green")
        else:
            self.email_valid_label.config(text="Invalid email format", fg="red")

    def run_process(self):
        username = self.name_entry.get().strip()
        instructor_email = self.email_entry.get().strip()
        if not username or not instructor_email:
            self.master.destroy()
            return
        if self.email_valid_label.cget("text") != "Valid email":
            messagebox.showerror("Error", "Please enter a valid email address.")
            return
        api_data = get_file_list(GITHUB_API_URL)
        if not api_data:
            self.master.destroy()
            return
        selected_files = select_random_files(api_data)
        if not selected_files:
            self.master.destroy()
            return
        report_body = generate_report_and_save(username, selected_files)
        email_sent = False
        while not email_sent:
            try:
                send_email(instructor_email, f"Files and locations report for {username}.", report_body)
                email_sent = True
            except Exception as e:
                continue
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()