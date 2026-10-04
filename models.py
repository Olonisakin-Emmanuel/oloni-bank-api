from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Numeric,
    Text,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship

from sqlalchemy_database import Base


class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)

    accounts = relationship("Account", back_populates="customer")


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customer.customer_id"),
        nullable=False
    )

    account_number = Column(BigInteger, unique=True, nullable=False)
    account_type = Column(String(20), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    pin_hash = Column(Text, nullable=False)

    customer = relationship(
        "Customer",
        back_populates="accounts"
    )

    transactions = relationship(
        "Transaction",
        back_populates="account"
    )

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, index=True)

    account_id = Column(
        Integer,
        ForeignKey("accounts.account_id"),
        nullable=False
    )

    transaction_type = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_date = Column(DateTime)
    description = Column(Text, nullable=True)

    account = relationship(
        "Account",
        back_populates="transactions"
    )