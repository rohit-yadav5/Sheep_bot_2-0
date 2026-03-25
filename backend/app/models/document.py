from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    upload_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    sentiment = Column(String, nullable=True)


if __name__ == "__main__":
    from app.core.database import engine
    Base.metadata.create_all(bind=engine)
    print("Database tables created!")
