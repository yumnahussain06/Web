from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

import pandas as pd
import joblib

import json
from mongodb import metrics_collection
from mongodb import predictions_collection
from mongodb import users_collection
from mongodb import user_activity_collection

from security import (hash_password, verify_password)
from auth import create_access_token

from fastapi import Depends, HTTPException, Header
from auth import verify_token
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from datetime import datetime, timezone


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    username = verify_token(token)

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    return username



# LOAD MODEL + PIPELINE
model = joblib.load("Ml/best_loan_risk_model.pkl")

preprocessing_pipeline = joblib.load(
    "Ml/preprocessor_pipeline.pkl"
)


# FASTAPI APP
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# INPUT SCHEMA
class LoanInput(BaseModel):

    Gender: Literal['Male', 'Female'] = Field(...)
    Married: Literal['Yes', 'No'] = Field(...)
    Dependents: int = Field(..., ge=0, le=100)
    Education: Literal['Graduate', 'Not Graduate'] = Field(...)
    Self_Employed: Literal['Yes', 'No'] =  Field(...)

    ApplicantIncome: int = Field(...,ge = 0)
    CoapplicantIncome: int = Field(...,ge = 0)
    LoanAmount: int = Field(...,ge = 1)
    Loan_Amount_Term: int = Field(..., ge = 1, description = "loan amount term is in months")
    Credit_History: Literal[1, 0] = Field(...)

    Property_Area: Literal['Urban', 'Semiurban', 'Rural'] = Field(...)


class UserRegister(BaseModel):

    username: str =  Field(...)

    password: str =  Field(...)

# HOME ROUTE
@app.get("/")
def home():

    return {
        "message": "Loan Approval API Running"
    }


# PREDICTION ROUTE
@app.post("/predict")
def predict(data: LoanInput, current_user: str = Depends(get_current_user)):
    input_df = pd.DataFrame([data.model_dump()])
    prediction = model.predict(input_df)
    
    result = prediction[0]
    status = "Approved" if result in [1, 'Y'] else "Rejected"

    predictions_collection.insert_one({
        "username": current_user,
        "input_data": data.model_dump(),
        "prediction": status,
        "timestamp": datetime.now(timezone.utc)
    })

    return {
        "loan_status_code": str(result),
        "prediction": status
    }

@app.on_event("startup")
def save_metrics():

    with open("Ml/model_metrics.json") as f:
        metrics = json.load(f)

    # avoid duplicate insertion
    if metrics_collection.count_documents({}) == 0:
        metrics_collection.insert_one(metrics)


@app.get("/metrics")
def get_metrics(current_user: str = Depends(get_current_user)):

    metrics = metrics_collection.find_one(
        {},
        {"_id": 0}
    )

    return metrics     


@app.post("/register")
def register(user: UserRegister):

    existing_user = users_collection.find_one(
        {"username": user.username}
    )

    if existing_user:

        return {
            "message":
            "Username already exists"
        }

    hashed_password = hash_password(
        user.password
    )

    users_collection.insert_one({

        "username": user.username,

        "hashed_password": hashed_password
    })

    return {
        "message":
        "User registered successfully"
    }


@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db_user = users_collection.find_one({"username": form_data.username})

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid username")

    if not verify_password(form_data.password, db_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    token = create_access_token({"sub": form_data.username})

    users_collection.update_one(
        {"username": form_data.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )

    user_activity_collection.insert_one({
        "username": form_data.username,
        "action": "login",
        "timestamp": datetime.utcnow()
    })
    
    return {
        "access_token": token,
        "token_type": "bearer"
    }