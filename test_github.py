import random
import tkinter as tk
from tkinter import messagebox
import smtplib
from email.mime.text import MIMEText
import requests
import os

# --- Configuration ---
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
GITHUB_API_URL = os.getenv("GITHUB_API_URL")

# --- Core Logic ---
def get_file_list(url):
    """Fetches the list of files and directories from the GitHub repository API."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing GitHub API: {e}")
        return []
    

def select_random_files(api_data):
    all_files = [item['name'] for item in api_data if item['type'] == 'file']
    
    if not all_files:
        return []

    max_count = len(all_files)
    count = random.randint(min(10, max_count), min(15, max_count))
    
    count = min(count, max_count)

    selected_files = random.sample(all_files, count)
    return selected_files

print(select_random_files(get_file_list(GITHUB_API_URL)))