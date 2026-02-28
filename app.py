import os 
from dotenv import load_dotenv

load_dotenv()
DB_PASSWORD = os.getenv("DB_PASSWORD")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{DB_PASSWORD}@localhost/ecommerce_api'

