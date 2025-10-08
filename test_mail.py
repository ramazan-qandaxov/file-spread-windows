import smtplib
from email.mime.text import MIMEText

# --- CONFIG ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "senderovichsender99@gmail.com"
SMTP_PASSWORD = "naxi htes cifj priz"  # <-- paste your app password here

# --- EMAIL CONTENT ---
to_email = "r.gandaxov55@gmail.com"  # send to yourself for testing
subject = "Test Email from Python"
body = "✅ Success! Your Gmail App Password works."

msg = MIMEText(body)
msg["From"] = SMTP_USERNAME
msg["To"] = to_email
msg["Subject"] = subject

# --- SEND ---
try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
    print("✅ Email sent successfully!")
except Exception as e:
    print("❌ Failed to send email:", e)
