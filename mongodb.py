from pymongo import MongoClient

# local mongodb connection
client = MongoClient(
    "mongodb://localhost:27017"
)

# database
db = client["loan_approval_project"]

# collections
predictions_collection = db["predictions"]

metrics_collection = db["metrics"]

users_collection = db["users"]