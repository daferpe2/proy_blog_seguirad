import hashlib
import bcrypt

# Función para hashear contraseñas
def crear_hash_con(password: str) -> str:
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hashed_password


# Función para verificar contraseñas
def verify_password_d(plain_password: str, hashed_password: str) -> bool:

    if plain_password == hashed_password:
            return True
    else:
         return False

# Nueva forma para probar

def get_password_hass(password:str):
     satl = bcrypt.gensalt()

     hashed = bcrypt.hashpw(password.encode('utf-8'),salt=satl)
     return hashed.decode("utf-8")


def verify_password_f(palin_password: str, hashed_password: str) -> bool:
     # Verificación de constraseña
     return bcrypt.checkpw(palin_password.encode('utf-8'),hashed_password.encode('utf-8'))

