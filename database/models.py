from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    email = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    responses = relationship("PollResponse", back_populates="user")


class Poll(Base):
    __tablename__ = 'polls'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    access_code = Column(String, unique=True)

    questions = relationship("Question", back_populates="poll")
    responses = relationship("PollResponse", back_populates="poll")


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('polls.id'))
    text = Column(String)
    options = Column(JSON)  # Список вариантов ответов
    correct_answers = Column(JSON)  # Список правильных ответов
    order = Column(Integer)  # Порядок вопроса в опросе
    is_active = Column(Boolean, default=True)

    poll = relationship("Poll", back_populates="questions")
    responses = relationship("QuestionResponse", back_populates="question")


class PollResponse(Base):
    __tablename__ = 'poll_responses'

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('polls.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    poll = relationship("Poll", back_populates="responses")
    user = relationship("User", back_populates="responses")
    question_responses = relationship("QuestionResponse", back_populates="poll_response")


class QuestionResponse(Base):
    __tablename__ = 'question_responses'

    id = Column(Integer, primary_key=True)
    poll_response_id = Column(Integer, ForeignKey('poll_responses.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    selected_answers = Column(JSON)  # Список выбранных ответов
    score = Column(Float)

    poll_response = relationship("PollResponse", back_populates="question_responses")
    question = relationship("Question", back_populates="responses")
