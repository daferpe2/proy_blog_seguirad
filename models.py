from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from sqlmodel import Relationship, SQLModel,Field
from pydantic import field_validator


class Token(BaseModel):
    token: str
    token_type: str

class Role(str,Enum):
    reader = "reader"
    author = "author"
    moderator = "moderator"
    admon = "admon"


class UserBase(SQLModel):
    name: str = Field(default=None,index=True)
    email: EmailStr = Field(default=None,index=True)
    pass_hass: str = Field(nullable=False, max_length=255)
    role: Role = Field(default=Role.reader)
    is_active: bool= Field(default=True)
    profilephotourl: Optional[str] = Field(default=None)

class UserCreate(UserBase):
    name: Optional[str] = "John Dove"
    email: Optional[EmailStr] = "John_Dove@example.com"
    pass_hass: Optional[str]
    role: Optional[Role] = Role.reader
    is_active: Optional[bool] = True


class UserUpate(SQLModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    pass_hass: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UserUpatePerfil(SQLModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    pass_hass: Optional[str] = None


class UserPhotoUpdate(SQLModel):
    profilephotourl: Optional[str] = None

class User(UserBase,table=True):
    id: int | None = Field(default=None,primary_key=True,index=True)
    posts: List["Article"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="user")


class Tipo(str,Enum):
    opinion = "opinión"
    analisis = "análisis"


class ArticleBase(SQLModel):
    title: str = Field(default=None)
    content: str = Field(default=None)
    tipo: Tipo = Field(default=Tipo.opinion)
    summary: str = Field(default=None)
    searchvector: Optional[str] = Field(default=None)

    @field_validator("searchvector", mode="before")
    @classmethod
    def build_searchvector(cls, value, info):
        title = info.data.get("title") or ""
        content = info.data.get("content") or ""
        tipo = info.data.get("tipo") or ""
        return f"{tipo} {title} {content}".strip()



class ArticleCreate(ArticleBase):
    authorid: int
    author: str


class Article(ArticleBase,table=True):
    id: int | None = Field(default=None,primary_key=True)
    authorid: Optional[int] = Field(foreign_key="user.id")
    author: Optional[User] | None = Relationship(back_populates="posts")
    createdat: datetime = Field(default_factory=datetime.now)


class CommentBase(SQLModel):
    content: str = Field(default=None)


class CommentCreate(CommentBase):
    user: Optional[str]
    userid: Optional[int]
    
    articleid: int


class Comment(CommentBase,table=True):
    id: int | None = Field(default=None,primary_key=True)
    createddat: datetime = Field(default_factory=datetime.now)
    user: Optional[User] | None = Relationship(back_populates="comments")
    articleid: int | None = Field(foreign_key="article.id")
    userid: int | None = Field(foreign_key="user.id")