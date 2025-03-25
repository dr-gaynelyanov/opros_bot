from sqlalchemy import create_engine
from database.models import Base

DATABASE_URL = "sqlite:///opros_bot.db"

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db() 