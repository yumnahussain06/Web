from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

import pandas as pd
import joblib

import json
from mongodb import metrics_collection
from mongodb import predictions_collection


# LOAD MODEL + PIPELINE
model = joblib.load("Ml/best_loan_risk_model.pkl")

preprocessing_pipeline = joblib.load(
    "Ml/preprocessor_pipeline.pkl"
)


# FASTAPI APP
app = FastAPI()


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


# HOME ROUTE
@app.get("/")
def home():

    return {
        "message": "Loan Approval API Running"
    }


# PREDICTION ROUTE
@app.post("/predict")
def predict(data: LoanInput):

    input_df = pd.DataFrame([data.model_dump()])

    prediction = model.predict(input_df)

    predictions_collection.insert_one({

    "input_data": input_df.to_dict(),

    "prediction": str(result)
})

    result = prediction[0]

    status = "Approved" if result in [1, 'Y'] else "Rejected"

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
def get_metrics():

    metrics = metrics_collection.find_one(
        {},
        {"_id": 0}
    )

    return metrics        