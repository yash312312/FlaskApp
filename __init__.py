import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine

db = create_engine('mysql+pymysql://root:@localhost/quami_try')
connection = db.raw_connection()
cursor = connection.cursor()
app = Flask(__name__)

fin = pd.Timestamp('2024-12-31')


from app import views
