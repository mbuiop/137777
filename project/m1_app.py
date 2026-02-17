from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bot.db'
db = SQLAlchemy(app)
