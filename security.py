import bcrypt

def hash_password(password: str) -> str:
    # Convert string password to bytes
    password_bytes = password.encode('utf-8')
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    
    # Return as standard string to store in MongoDB safely
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert string inputs back to bytes for comparison
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    
    # Securely check if they match
    return bcrypt.checkpw(plain_bytes, hashed_bytes)