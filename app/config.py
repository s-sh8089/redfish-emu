import os

class Config:
    DB_PATH = os.environ.get('DB_PATH', 'data/redfish.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'redfish-emu-secret-key')
