import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///bus_ticketing.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_CODE = 'ADMIN2024'  # Change this in production