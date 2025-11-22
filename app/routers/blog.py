import os
from pathlib import Path
from typing import Annotated, Optional
from fastapi import APIRouter, Cookie,Depends, File, Form, HTTPException, Query,Request, UploadFile,status
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, func
from app.funciones_pass.token_manager import TokenManager
from app.routers.login_log import create_token_p
from db import SessionDep, engine
from models import Article, ArticleCreate, Comment, CommentCreate, Role, Tipo, User,UserCreate, UserPhotoUpdate, UserUpate, UserUpatePerfil
from sqlmodel import select
from password import get_password_hass, verify_password_f
from ..funciones_upload_photo import upload_photo
from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


SECRET_KEY = os.getenv("SECRET_KEY")

TOKEN_SCNODS_EXP = 60 * 45
ALGORITHM = "HS256"


@asynccontextmanager
async def app_lifespan(app:FastAPI):
    """
    app_lifespan Generar tablas y conexion base de datos

    _extended_summary_

    Args:
        app (FastAPI): Conexion a base de datos con fastapi
    """
    SQLModel.metadata.create_all(engine)
    yield

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(lifespan=app_lifespan)

router.mount("/app/static",StaticFiles(directory="app/static"),name="static")

templates = Jinja2Templates(directory="app/templates")


@router.get("/",response_class=HTMLResponse)
async def root(request:Request,tags=["Blog"]):
    """
    root Entrada principal de la base de datos
    _extended_summary_

    Args:
        request (Request): Requerimiento get inicio app 
        tags (list, optional): _description_. Defaults to ["Blog"]
        capa principal de la app.

    Returns:
        _type_: Retorna home de observatorio de seguirdad
    """
    return templates.TemplateResponse("base.html", {"request": request})



security = HTTPBasic()


@router.get("/home",response_class=HTMLResponse,tags=["Blog"])
async def articles(session:SessionDep,request:Request):
    """
    articles Retorna articulos creados

    _extended_summary_

    Args:
        session (SessionDep): Sesion en base de datos 
        request (Request): Requermineto a la base de datos para obtner Articulos

    Returns:
        _type_: Listado de todos los articulos guardados en la base de datos con un template llamado Home
    """
    ARTICLES = session.exec(select(Article).order_by(Article.id.desc())).all()
    return templates.TemplateResponse("home.html", {"request": request, "articles": ARTICLES})

# Colocar el Cookie de tiempo en get_user para ver si funcina aqui


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPBasicCredentials, Depends(security)]
) -> User:
    try:
        
        user_db = session.exec(select(User).where(User.name == credentials.username)).first()
        if not user_db:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
        hass_entrada = credentials.password

        if not verify_password_f(hass_entrada,user_db.pass_hass):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")

        return user_db

    except Exception as e:
        print("Error al conectar o verificar usuario:", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/register_form",response_class=HTMLResponse,tags=["Blog"])
async def register_form(session:SessionDep,request:Request,
                        ):
    return templates.TemplateResponse("formulario_registro.html", {"request": request})


@router.post("/register",response_class=HTMLResponse,tags=["Register"])
async def register(session:SessionDep,
                   name:Annotated[str,Form(...)],
                   email: Annotated[str,Form(...)],
                   pass_hass: Annotated[str,Form(...)],
                   ):
    
    dbuser = UserCreate(name=name,email=email,pass_hass=get_password_hass(pass_hass),
                  )
    
    user = User.model_validate(dbuser.model_dump())

    session.add(user)
    session.commit()
    session.refresh(user)
    return RedirectResponse("/",status_code=status.HTTP_302_FOUND)


@router.get("/leerarticulo/{article_id}", response_model=Article, tags=["Blog"])
async def read_article(request: Request,article_id: int,
    session: SessionDep,
):

    ARTICLE = session.exec(select(Article).where(Article.id == article_id)).first()
    COMMENTS = session.exec(select(Comment).where(Comment.articleid == article_id)).all()
    if not ARTICLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artículo no encontrado"
        )

    return templates.TemplateResponse("article_view.html", {"request": request,
                                                            "article":ARTICLE,
                                                            "comments":COMMENTS})


@router.get("/login",response_class=HTMLResponse,tags=["Blog"])
async def login(session:SessionDep,request:Request):
    return templates.TemplateResponse("formulario_login.html", {"request": request})


# Arreglar este endpoint

@router.post("/login/user")
async def login_uner(session: SessionDep,
                     credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    db_p = get_current_user(session=session,credentials=credentials)
    if not isinstance(db_p, User):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    token = create_token_p(db_p.name)
    response = RedirectResponse("/",status_code=status.HTTP_302_FOUND)
    response.set_cookie(
    key="access_token",
    value=token,
    max_age=TOKEN_SCNODS_EXP,
    httponly=True,
    secure=True,  # Solo si usas HTTPS
    samesite="Lax",  # O "Strict" según tu flujo
    path="/"
    )
    return response

@router.post("/upload", tags=["Blog"])
async def upload_image(
    session: SessionDep,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ext = upload_photo.validate_image(file)
    filepath = await upload_photo.save_image(file, ext)

    if isinstance(user, User): 
        update_data = UserPhotoUpdate(profilephotourl=filepath)

        user.sqlmodel_update(update_data.model_dump(exclude_unset=True))

        session.add(user)
        session.commit()
        session.refresh(user)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)



@router.get("/list_users", tags=["Blog"], response_class=HTMLResponse)
async def lista_usuarios(
    request: Request,
    session: SessionDep,
    access_token: Annotated[str | None, Cookie()] = None, 
    admin: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):

    if access_token is None or admin is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    decode_token = TokenManager(secret_key=SECRET_KEY)
    decode_token.decode_token(token=access_token)

    if admin.role != Role.admon:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    offset = (page - 1) * page_size
    # Consulta paginada
    users_query = select(User).order_by(User.id.desc()).offset(offset).limit(page_size)
    users = session.exec(users_query).all()

    # Conteo total corregido
    total_users = session.exec(select(func.count()).select_from(User)).one()
    total_pages = (total_users + page_size - 1) // page_size

    return templates.TemplateResponse(
        "listado_usuarios_2.html",
        {
            "request": request,
            "users": users,
            "page": page,
            "total_pages": total_pages
        }
    )


@router.get("/update_general_form/{user_id}",response_class=HTMLResponse,tags=["Blog"])
async def update_general_form_html(user_id: int,
                                   session: SessionDep,
                                   request:Request,
                                   access_token: Annotated[str | None, Cookie()] = None,
                                   admin: User = Depends(get_current_user)):

    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    decode_token = TokenManager(secret_key=SECRET_KEY)
    decode_token.decode_token(token=access_token)

    if not isinstance(admin, User) or admin.role != Role.admon:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    user = session.exec(select(User).where(User.id == user_id)).first()


    return templates.TemplateResponse("/formulario_update.html",{"request":request,"user":user})


@router.post("/update_general_form/{user_id}",tags=["Blog"])
async def update_general_form(
    user_id: int,
    session: SessionDep,
    name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    pass_hass: Annotated[str, Form(...)],
    role: Annotated[str, Form(...)],
    is_active: Annotated[bool, Form(...)],
    admin: User = Depends(get_current_user),
    access_token: Annotated[str | None, Cookie()] = None,
):
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    if not isinstance(admin, User) or admin.role != Role.admon:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")


    update_fields = {
        "name": name,
        "email": email,
        "role":role,
        "is_active":is_active
    }

    if pass_hass.strip():  # Solo si no está vacío
        update_fields["pass_hass"] = get_password_hass(pass_hass)

    update_data = UserUpate(**update_fields)

    user.sqlmodel_update(update_data.model_dump(exclude_unset=True))
    session.add(user)
    session.commit()
    session.refresh(user)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/create_general_form_articulo",response_class=HTMLResponse,tags=["Blog"])
async def create_form_articulo(session: SessionDep,
                               request:Request,
                               user: User = Depends(get_current_user),
                               access_token: Annotated[str | None, Cookie()] = None,):
    
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)
    
    if not isinstance(user, User):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    if user.role == Role.admon or user.role == Role.author or user.role == Role.moderator:
        return templates.TemplateResponse("/create_article.html",{"request":request,"user":user})

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")


@router.post("/creacionarticle", response_model=Article, tags=["Blog"])
async def creacionarticle(
    session: SessionDep,
    title: Annotated[str, Form(...)],
    content: Annotated[str, Form(...)],
    tipo: Annotated[Tipo, Form(...)],
    summary: Annotated[str, Form(...)],
    user: User = Depends(get_current_user),
    access_token: Annotated[str | None, Cookie()] = None,
):
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    if not isinstance(user, User):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    if user.role not in [Role.admon, Role.author, Role.moderator]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    articulo_data = ArticleCreate(
        title=title,
        content=content,
        tipo=tipo,
        summary=summary,
        authorid=user.id,
        author=user.name
    )

    # Crear instancia del modelo ORM
    articulo_db = Article.model_validate(articulo_data.model_dump())


    session.add(articulo_db)
    session.commit()
    session.refresh(articulo_db)

    # Si estás trabajando con formularios HTML, esto está bien:
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/upload/image", tags=["Blog"],response_model=User)
async def upload_image_image_article(
    request:Request,
    session: SessionDep,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):

    ext = upload_photo.validate_image(file)
    filepath = await upload_photo.save_image(file, ext)

    if isinstance(user, User): 
        update_data = UserPhotoUpdate(profilephotourl=filepath)

        user.sqlmodel_update(update_data.model_dump(exclude_unset=True))

        session.add(user)
        session.commit()
        session.refresh(user)

        # html_content = f"""
        # <html>
        #     <link href="/app/static/tailwind.css" rel="stylesheet" />
        #     <head><title>Mensaje</title></head>
        #     <body class="bg-gray-900 text-white font-sans">
        #         <script>
        #             alert("¡Hola {user.name}! Fue actualizada tu fotografia.");
        #         </script>
        #         <a href="/" class="p-6 max-w-3xl mx-auto" >Regresar</a>
        #     </body>
        # </html>
        # """


    return templates.TemplateResponse("htm_retorno.html",{"request":request,"user":user})


@router.get("/perfil", response_model=User, tags=["Blog"])
async def perfil(session: SessionDep,
                request:Request,
                user: User = Depends(get_current_user),
                access_token: Annotated[str | None, Cookie()] = None,):
    
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    else:
        return templates.TemplateResponse("panel_perfil.html",{"request":request,"user":user})


@router.post("/user/profile/{user_id}",tags=["Blog"])
async def user_profile(user_id:int,
                       session: SessionDep,
                       name: Annotated[str,Form(...)],
                       email: Annotated[str,Form(...)],
                       pass_hass: Annotated[str, Form(...)],
                       user: User = Depends(get_current_user),
                       access_token: Annotated[str | None, Cookie()] = None):

    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    if not isinstance(user, User):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    user_1 = session.exec(select(User).where(User.id == user_id)).first()
    if not user_1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    update_fields = {
        "name": name,
        "email": email,
    }

    if pass_hass.strip():  # Solo si no está vacío
        update_fields["pass_hass"] = get_password_hass(pass_hass)

    update_data = UserUpatePerfil(**update_fields)

    user_1.sqlmodel_update(update_data.model_dump(exclude_unset=True))
    session.add(user_1)
    session.commit()
    session.refresh(user_1)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/creacioncoment_response", response_model=User, tags=["Blog"])
async def create_coment_template(session: SessionDep,
                request:Request,
                user: User = Depends(get_current_user),
                access_token: Annotated[str | None, Cookie()] = None,):
    """
    create_coment_template Retorno de template de html con retorno a pagina principal

    _extended_summary_

    Args:
        session (SessionDep): Sesion en base de datos
        request (Request): Requerimiento al servidor
        user (User, optional): Usuario logeado en app
        access_token (Annotated[str  |  None, Cookie, optional): _description_. Defaults to None.

    Returns:
        _type_: Template html que con retorno a Home.
    """
    
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    else:
        return templates.TemplateResponse("htm_retorno.html",{"request":request,"user":user})


@router.post("/creacioncoment",response_class=HTMLResponse,tags=["Blog"])
async def create_coment(request: Request,
                        session:SessionDep,
                        comment: Annotated[str,Form(...)],
                        article_id: Annotated[str,Form(...)],
                        access_token: Annotated[str | None, Cookie()] = None,
                        user: User = Depends(get_current_user),
                        ):
    """
    create_coment Crear un comentario dentro de app de articulos

    _extended_summary_

    Args:
        request (Request): Requerimiento a servidor
        session (SessionDep): Sesion en base de datos
        comment (Annotated[str,Form): Comentario del usuario al articulo
        article_id (Annotated[str,Form): id unico de identificacion del articulo
        access_token (Annotated[str  |  None, Cookie, optional): _description_. Defaults to None.
        user (User, optional): _description_. Defaults to Depends(get_current_user).

    Returns:
        _type_: Anotación tipo string para comentar articulo, guardado en base de datos.
    """
   
    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    comentario_creado = CommentCreate(content=comment,user=user.name,userid=user.id,articleid=int(article_id))
    comentario = Comment.model_validate(comentario_creado.model_dump())
    session.add(comentario)
    session.commit()
    session.refresh(comentario)
    return RedirectResponse("/creacioncoment_response",status_code=status.HTTP_301_MOVED_PERMANENTLY)


@router.get("/search",response_class=HTMLResponse,tags=["Blog"])
async def search_function_formulario(session:SessionDep,request:Request):
    """
    search_function_formulario Retorna el formulario de busqueda


    Args:
        session (SessionDep): Sesion en base de datos
        request (Request): Redirección 

    Returns:
        _type_: Retorna el formulario html de busqueda
    """
    return templates.TemplateResponse("search.html", {"request": request})


@router.get("/search/action",tags=["Busqueda"],response_class=HTMLResponse)
async def searcharticles(request: Request,
                         session: SessionDep,
                         q:Optional[str] = Query(None),
                         access_token: Annotated[str | None, Cookie()] = None):
    """
    searcharticles Acción de buscar articulos-

    _extended_summary_

    Args:
        request (Request): Requerimiento de fastapi 
        session (SessionDep): Sesion en base de datos
        q (Optional[str], optional): Opción en string de busqueda en base de datos.
        access_token Token de seguridad generado con jose.

    Returns:
        _type_: Busqueda en la base de datos de articulos disponibles
    """

    if access_token is None:
        return RedirectResponse("/login",status_code=status.HTTP_302_FOUND)

    query = session.exec(select(Article).where(Article.searchvector.ilike(f"%{q}%"))).all()
    return templates.TemplateResponse("search_results.html",
                                      {"request":request,"articles":query})

