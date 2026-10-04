from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, field_validator, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from security import hash_pin, hash_password, verify_password, verify_pin
from auth import create_access_token, SECRET_KEY, ALGORITHM
from sqlalchemy_database import engine, get_db
from models import Customer, Account, Transaction
import re
from random import randint
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from decimal import Decimal
from datetime import datetime
app = FastAPI(title="OloniBank API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        customer_id = payload.get("sub")

        if customer_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == int(customer_id))
            .first()
        )

        if not customer:
            raise HTTPException(
                status_code=401,
                detail="Customer not found"
            )

        return customer

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
class AccountRequest(BaseModel):
    name: str
    phone_number: str
    email: EmailStr
    password: str
    account_type: str
    pin: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        if not re.fullmatch(r"0\d{10}", value):
            raise ValueError(
                "Phone number must be exactly 11 digits"
            )
        return value

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value):
        if len(value) != 4 or not value.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        return value

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, value):
        if value not in ["Savings", "Current"]:
            raise ValueError("Account type must be Savings or Current")
        return value
    
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class DepositRequest(BaseModel):
    amount: Decimal
MAX_TRANSACTION_AMOUNT = Decimal("10000000000")

class WithdrawRequest(BaseModel):
    amount: Decimal
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value):
        if len(value) != 4 or not value.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        return value

class TransferRequest(BaseModel):
    recipient_account_number: int
    amount: Decimal
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value):
        if len(value) != 4 or not value.isdigit():
            raise ValueError("PIN must be exactly 4 digits")
        return value

def generate_account_number(db: Session):
    while True:
        account_number = randint(1000000000, 9999999999)

        existing_account = (
            db.query(Account)
            .filter(Account.account_number == account_number)
            .first()
        )


        if existing_account is None:
            return account_number


class AccountResponse(BaseModel):
    message: str
    customer_id: int
    account_number: int
    account_type: str
    balance: float

@app.get("/")
def root():
    return {"message": "Welcome to olonibank!!!!!"}


@app.get("/accounts/{account_number}")
def get_account(
    account_number: str,
    current_user = Depends(get_current_user)
):
    return {
        "account_number": account_number,
        "message": "Account endpoint is working",
        "user": current_user
    }


@app.get("/my-account")
def get_my_account(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = (
        db.query(Account)
        .filter(Account.customer_id == current_user.customer_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Bank account not found"
        )

    return {
        "customer_id": current_user.customer_id,
        "name": current_user.name,
        "email": current_user.email,
        "account_number": account.account_number,
        "account_type": account.account_type,
        "balance": float(account.balance)
    }

@app.post("/deposit")
def deposit(
    deposit: DepositRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if deposit.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Deposit amount must be greater than zero"
        )
    if deposit.amount > MAX_TRANSACTION_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail="Deposit amount exceeds the maximum allowed limit"
        )

    account = (
        db.query(Account)
        .filter(Account.customer_id == current_user.customer_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Bank account not found"
        )

    account.balance += deposit.amount

    transaction = Transaction(
    account_id=account.account_id,
    transaction_type="Deposit",
    amount=deposit.amount,
    transaction_date=datetime.now(),
    description="Account deposit"
    )
    
    db.add(transaction)


    db.commit()

    db.refresh(account)
    db.refresh(transaction)

    return {
        "message": "Deposit successful",
        "account_number": account.account_number,
        "amount_deposited": float(deposit.amount),
        "new_balance": float(account.balance),
        "transaction_id": transaction.transaction_id
    }

@app.post("/withdraw")
def withdraw(
    withdraw: WithdrawRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if withdraw.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Withdrawal amount must be greater than zero"
        )
    if withdraw.amount > MAX_TRANSACTION_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail="Withdrawal amount exceeds the maximum allowed limit"
        )

    account = (
        db.query(Account)
        .filter(Account.customer_id == current_user.customer_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Bank account not found"
        )

    if not verify_pin(
        withdraw.pin,
        account.pin_hash
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid PIN"
        )

    if withdraw.amount > account.balance:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

   
    account.balance -= withdraw.amount

    transaction = Transaction(
        account_id=account.account_id,
        transaction_type="Withdrawal",
        amount=withdraw.amount,
        transaction_date=datetime.now(),
        description="Cash withdrawal"
    )
    

    db.add(transaction)

   
    db.commit()

    db.refresh(account)
    db.refresh(transaction)

    return {
        "message": "Withdrawal successful",
        "account_number": account.account_number,
        "amount_withdrawn": float(withdraw.amount),
        "new_balance": float(account.balance),
        "transaction_id": transaction.transaction_id
    }

@app.post("/transfer")
def transfer(
    transfer: TransferRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if transfer.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Transfer amount must be greater than zero"
        )
    if transfer.amount > MAX_TRANSACTION_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail="Transfer amount exceeds the maximum allowed limit"
        )


    recipient_account = (
        db.query(Account)
        .filter(
            Account.account_number == transfer.recipient_account_number
        )
        .first()
    )

    if not recipient_account:
        raise HTTPException(
            status_code=404,
            detail="Recipient account not found"
        )


    recipient_customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == recipient_account.customer_id
        )
        .first()
    )

    if not recipient_customer:
        raise HTTPException(
            status_code=404,
            detail="Recipient customer not found"
        )

    sender_account = (
        db.query(Account)
        .filter(
            Account.customer_id == current_user.customer_id
        )
        .first()
    )

    if not sender_account:
        raise HTTPException(
            status_code=404,
            detail="Sender bank account not found"
        )


    if sender_account.account_id == recipient_account.account_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot transfer money to your own account"
        )


    if not verify_pin(
        transfer.pin,
        sender_account.pin_hash
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid PIN"
        )


    if transfer.amount > sender_account.balance:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )


    sender_account.balance -= transfer.amount


    recipient_account.balance += transfer.amount

    sender_transaction = Transaction(
        account_id=sender_account.account_id,
        transaction_type="Transfer",
        amount=transfer.amount,
        transaction_date=datetime.now(),
        description=f"Transfer to {recipient_customer.name}"
    )

    recipient_transaction = Transaction(
        account_id=recipient_account.account_id,
        transaction_type="Transfer",
        amount=transfer.amount,
        transaction_date=datetime.now(),
        description=f"Transfer from {current_user.name}"
    )

    db.add(sender_transaction)
    db.add(recipient_transaction)

    # Save everything together
    db.commit()

    db.refresh(sender_account)
    db.refresh(recipient_account)
    db.refresh(sender_transaction)
    db.refresh(recipient_transaction)

    return {
        "message": "Transfer successful",
        "recipient_name": recipient_customer.name,
        "recipient_account_number": recipient_account.account_number,
        "amount_transferred": float(transfer.amount),
        "new_balance": float(sender_account.balance),
        "transaction_id": sender_transaction.transaction_id
    }

@app.get("/transactions")
def get_transactions(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = (
        db.query(Account)
        .filter(
            Account.customer_id == current_user.customer_id
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Bank account not found"
        )

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == account.account_id
        )
        .order_by(
            Transaction.transaction_date.desc()
        )
        .all()
    )

    return {
        "account_number": account.account_number,
        "transactions": [
            {
                "transaction_id": transaction.transaction_id,
                "transaction_type": transaction.transaction_type,
                "amount": float(transaction.amount),
                "transaction_date": transaction.transaction_date,
                "description": transaction.description,
                "direction": (
                    "credit"
                    if transaction.transaction_type == "Deposit"
                    or (
                        transaction.transaction_type == "Transfer"
                        and transaction.description.startswith("Transfer from")
                    )
                    else "debit"
                )
            }
            for transaction in transactions
        ]
    }

@app.get("/accounts/{account_number}/recipient")
def get_recipient(
    account_number: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recipient_account = (
        db.query(Account)
        .filter(Account.account_number == account_number)
        .first()
    )

    if not recipient_account:
        raise HTTPException(
            status_code=404,
            detail="Recipient account not found"
        )

    recipient_customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == recipient_account.customer_id
        )
        .first()
    )

    if not recipient_customer:
        raise HTTPException(
            status_code=404,
            detail="Recipient customer not found"
        )

    return {
        "account_number": recipient_account.account_number,
        "account_name": recipient_customer.name
    }

@app.post(
    "/accounts",
    response_model=AccountResponse
)
def create_account(
    account: AccountRequest,
    db: Session = Depends(get_db)
):

    try:

        existing_customer = (
            db.query(Customer)
            .filter(Customer.email == account.email)
            .first()
        )

        if existing_customer:
            raise HTTPException(
                status_code=409,
                detail="Email already registered. Please use another email."
            )

 
        existing_phone = (
            db.query(Customer)
            .filter(Customer.phone_number == account.phone_number)
            .first()
        )

        if existing_phone:
            raise HTTPException(
                status_code=409,
                detail="Phone number already registered. Please use another phone number."
            )

        account_number = generate_account_number(db)

 
        customer = Customer(
            name=account.name,
            phone_number=account.phone_number,
            email=account.email,
            password_hash=hash_password(account.password)
        )

        db.add(customer)
        db.flush()

        new_account = Account(
            customer_id=customer.customer_id,
            account_number=account_number,
            account_type=account.account_type,
            balance=Decimal("0.00"),
            pin_hash=hash_pin(account.pin)
        )

        db.add(new_account)

        db.commit()

        db.refresh(customer)
        db.refresh(new_account)

        return AccountResponse(
            message="OloniBank account created successfully",
            customer_id=customer.customer_id,
            account_number=new_account.account_number,
            account_type=new_account.account_type,
            balance=float(new_account.balance)
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
    
@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(Customer.email == form_data.username)
        .first()
    )
    print("LOGIN EMAIL:", form_data.username)
    print("CUSTOMER FOUND:", customer is not None)
    if not customer:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        form_data.password,
        customer.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token_data = {
        "sub": str(customer.customer_id)
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
@app.get("/test-auth")
def test_auth(current_user = Depends(get_current_user)):
    return current_user

@app.get("/database-test")
def database_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        return {
            "message": "OloniBank database connected",
            "result": result.scalar()
        }