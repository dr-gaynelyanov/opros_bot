from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, User, Poll, Question, PollResponse, QuestionResponse
from datetime import datetime
from typing import List, Optional

DATABASE_URL = "sqlite:///opros_bot.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_user(db, telegram_id: int, username: str, first_name: str, 
                last_name: str, phone: str, email: str, is_admin: bool = False):
    db_user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        is_admin=is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_telegram_id(db, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def get_admins(db) -> List[User]:
    return db.query(User).filter(User.is_admin == True).all()

def add_admin(db, telegram_id: int) -> Optional[User]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    user.is_admin = True
    db.commit()
    db.refresh(user)
    return user

def remove_admin(db, telegram_id: int) -> Optional[User]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    user.is_admin = False
    db.commit()
    db.refresh(user)
    return user

from database.models import Poll
import secrets

def is_admin(db, telegram_id: int) -> bool:
    user = get_user_by_telegram_id(db, telegram_id)
    return user.is_admin if user else False

def get_admin_count(db: Session) -> int:
    """
    Возвращает количество администраторов в системе
    """
    return db.query(User).filter(User.is_admin == True).count()

def create_poll_db(db: Session, title: str, description: str, created_by: int):
    """
    Создает новый опрос в базе данных.
    """
    access_code = secrets.token_urlsafe(16)  # Generate a unique access code
    db_poll = Poll(
        title=title,
        description=description,
        created_by=created_by,
        access_code=access_code
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll

def create_question(db: Session, poll_id: int, text: str, options: list, correct_answers: list, order: int):
    """
    Создает новый вопрос в базе данных и связывает его с опросом.
    """
    db_question = Question(
        poll_id=poll_id,
        text=text,
        options=options,
        correct_answers=correct_answers,
        order=order
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def get_polls_by_creator(db: Session, creator_id: int) -> List[Poll]:
    """
    Возвращает список опросов, созданных пользователем с указанным ID.
    """
    return db.query(Poll).filter(Poll.created_by == creator_id).all()

def get_poll_by_access_code(db: Session, access_code: str) -> Optional[Poll]:
    """
    Возвращает опрос по коду доступа.
    """
    return db.query(Poll).filter(Poll.access_code == access_code).first()

def create_poll_response(db: Session, poll_id: int, user_id: int):
    """
    Создает запись об участии пользователя в опросе.
    """
    db_poll_response = PollResponse(
        poll_id=poll_id,
        user_id=user_id
    )
    db.add(db_poll_response)
    db.commit()
    db.refresh(db_poll_response)
    return db_poll_response

def get_answer_options(db: Session, question_id: int) -> List[str]:
    """
    Возвращает список вариантов ответов для вопроса.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if question:
        return question.options
    else:
        return []

def get_users_by_poll_id(db: Session, poll_id: int) -> List[int]:
    """
    Возвращает список ID пользователей, присоединившихся к опросу.
    """
    return [response.user_id for response in db.query(PollResponse).filter(PollResponse.poll_id == poll_id).all()]
