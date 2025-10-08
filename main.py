from email.mime.text import MIMEText
from dotenv import load_dotenv
import tkinter as tk
import requests
import getpass
import smtplib
import random
import os

# --- Configuration ---
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
GITHUB_API_URL = os.getenv("GITHUB_API_URL")

# --- Core Logic ---
def get_file_list(url):
    """Fetches the list of files and directories from the GitHub repository API."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing GitHub API: {e}")
        return []

def select_random_files(api_data):
    all_files = [item for item in api_data if item['type'] == 'file']
    if not all_files:
        return []

    max_count = len(all_files)
    count = random.randint(min(10, max_count), min(15, max_count))
    count = min(count, max_count)

    selected_files = random.sample(all_files, count)
    return selected_files

def download_and_save_file(file_info, save_dir):
    raw_url = file_info.get('download_url')
    if not raw_url:
        return
    try:
        r = requests.get(raw_url)
        r.raise_for_status()
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file_info['name'])
        with open(file_path, 'wb') as f:
            f.write(r.content)
    except Exception as e:
        print(f"Failed to download {file_info['name']}: {e}")

def generate_report_and_save(username, selected_files):
    system_username = getpass.getuser()

    folder_paths = [
        r"C:\Users\Public\Documents",
        r"C:\Users\Public\Downloads",
        r"C:\Users\{username}\Desktop",
        r"C:\Users\{username}\Documents",
        r"C:\Users\{username}\Pictures",
        r"C:\Users\{username}\Music",
        r"C:\Users\{username}\Videos",
        r"C:\Users\{username}\Favorites",
        r"C:\Users\{username}\Contacts",
        r"C:\Users\{username}\AppData\Local\Temp",
        r"C:\Users\{username}\AppData\Local",
        r"C:\Users\{username}\AppData\Roaming",
        r"C:\Users\{username}\AppData\LocalLow",
        r"C:\Users\{username}\AppData\Local\Microsoft\Windows\INetCache",
        r"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\ProgramData",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\Program Files\Common Files",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Windows\System32\drivers",
        r"C:\Windows\System32\config",
        r"C:\Windows\Temp",
        r"C:\inetpub\wwwroot",
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        r"C:\ProgramData\ssh",
        r"C:\Windows\Logs",
        r"C:\Recovery",
    ]

    report_items = []
    for file_info in selected_files:
        save_path = random.choice(folder_paths).replace("{username}", system_username)
        download_and_save_file(file_info, save_path)
        report_items.append(f"- {file_info['name']} located at: {save_path}\n")

    report_body = (
        f"Asset Report for: {username}\n\n"
        f"Files chosen for ({len(selected_files)} items):\n"
        f"{''.join(report_items)}\n"
    )
    return report_body

def send_email(recipient_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

class ReportApp:
    def __init__(self, master):
        self.master = master
        master.title("Campaign Assets Reporter")
        master.geometry("400x250")

        tk.Label(master, text="User's Name & Surname:").pack(pady=(10, 0))
        self.name_entry = tk.Entry(master, width=40)
        self.name_entry.pack(pady=5)

        tk.Label(master, text="Instructor Email:").pack(pady=(10, 0))
        self.email_entry = tk.Entry(master, width=40)
        self.email_entry.pack(pady=5)

        self.submit_button = tk.Button(master, text="Report", command=self.run_process)
        self.submit_button.pack(pady=20)

    def run_process(self):
        username = self.name_entry.get().strip()
        instructor_email = self.email_entry.get().strip()
        if not username or not instructor_email:
            self.master.destroy()
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
        send_email(instructor_email, f"Files and locations report for {username}.", report_body)

        # Close the window
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReportApp(root)
    root.mainloop()