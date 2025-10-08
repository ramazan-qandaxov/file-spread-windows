from cryptography.fernet import Fernet

key = Fernet.generate_key()
fernet = Fernet(key)

username = "senderovichsender99@gmail.com".encode()
password = "naxi htes cifj priz".encode()

enc_user = fernet.encrypt(username)
enc_pass = fernet.encrypt(password)

print("FERNET_KEY =", key)
print("ENC_SMTP_USERNAME =", enc_user)
print("ENC_SMTP_PASSWORD =", enc_pass)
