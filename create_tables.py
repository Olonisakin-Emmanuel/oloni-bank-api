from sqlalchemy_database import engine, Base
from models import Customer, Account, Transaction

print("Creating OloniBank database tables...")

Base.metadata.create_all(bind=engine)

print("OloniBank database tables created successfully!")