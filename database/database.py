from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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

def is_admin(db, telegram_id: int) -> bool:
    user = get_user_by_telegram_id(db, telegram_id)
    return user.is_admin if user else False

