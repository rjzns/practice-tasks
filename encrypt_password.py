from cryptography.fernet import Fernet

def generate_key():
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

def load_key():
    return open("secret.key", "rb").read()

def encrypt_password(password):
    key = load_key()
    f = Fernet(key)
    encrypted_password = f.encrypt(password.encode())
    with open("encrypted_password.bin", "wb") as password_file:
        password_file.write(encrypted_password)

if __name__ == "__main__":
    generate_key()
    db_password = input("Введите пароль для базы данных: ")
    encrypt_password(db_password)
    print("Пароль зашифрован и сохранен в файл encrypted_password.bin")