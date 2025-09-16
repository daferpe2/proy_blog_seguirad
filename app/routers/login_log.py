import os
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Form, HTTPException, Request,status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select
from password import verify_password_f
from db import SessionDep
from models import User
from ..funciones_pass import token_manager

from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


SECRET_KEY = os.getenv("SECRET_KEY")
TIME_EXPIRE = 60 * 45 
router = APIRouter()



templates = Jinja2Templates(directory="app/templates")


def create_token_p(name):
    tok = token_manager.TokenManager(SECRET_KEY)
    tok_c = tok.create_token({"name":name})
    return tok_c


def get_current_user_b(
    session: SessionDep,
    name: str,
    password: str
) -> User:
    try:
        user_db = session.exec(select(User).where(User.name == name)).first()

        if not user_db:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        hass_entrada = password

        if not verify_password_f(hass_entrada,user_db.pass_hass):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")

        return user_db

    except Exception as e:
        print("Error al conectar o verificar usuario:", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/login_2",response_class=HTMLResponse,tags=["Registro"])
async def login_form(session:SessionDep,request:Request):
    return templates.TemplateResponse("formulario_login.html", {"request": request})

#   return HTMLResponse("/",status_code=status.HTTP_201_CREATED)

@router.post("/users/login",tags=["Registro"])
async def login(session:SessionDep,
          username: Annotated[str,Form(...)],
          password: Annotated[str,Form(...)]):
      db_p = get_current_user_b(name=username,password=password,session=session)
      if not isinstance(db_p, User):
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

      token = create_token_p(db_p.name)
      response = RedirectResponse("/",status_code=status.HTTP_302_FOUND)
      response.set_cookie(
        key="access_token",
        value=token,
        max_age=TIME_EXPIRE,
        httponly=True,
        secure=True,  # Solo si usas HTTPS
        samesite="Lax",  # O "Strict" según tu flujo
        path="/"
    )
      return response


