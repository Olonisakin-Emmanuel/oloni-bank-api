from argon2 import PasswordHasher

password_hasher = PasswordHasher()


def hash_pin(pin):
    return password_hasher.hash(pin)


def verify_pin(pin, pin_hash):
    try:
        password_hasher.verify(pin_hash, pin)
        return True
    except Exception:
        return False


def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, password_hash):
    try:
        password_hasher.verify(password_hash, password)
        return True
    except Exception:
        return False



if __name__ == "__main__":
    pin_hash = "$argon2id$v=19$m=65536,t=3,p=4$xnDLKL83BhIfHqBzG8j/iA$Y6LW44z0hBOaHC+JR/JZdPdqa57EyPuIJO/lXdhiZ0w"

    try:
        password_hasher.verify(pin_hash, "1234")
        print("PIN IS CORRECT")
    except Exception as e:
        print("PIN IS WRONG")
        print(type(e).__name__)