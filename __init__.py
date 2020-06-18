import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for,session
from sqlalchemy import create_engine

db = create_engine('mysql+pymysql://root:@localhost/quami_try')
connection = db.raw_connection()
cursor = connection.cursor()
app = Flask(__name__)

pro_list = []

# In[3]:


dates = pd.date_range('2020-08-1', end='2024-12-31', freq='MS')
dates

# In[4]:


df = pd.DataFrame(columns=dates)

# In[5]:


r = list()
j = 5
for i in dates:
    r.append(j)
    j = min(j + 5, 200)
df.loc['Shops'] = r
df.reset_index(inplace=True)
df.rename(columns={'index': 'Shops and Units'}, inplace=True)
# In[6]:


fin = pd.Timestamp('2024-12-31')

# In[7]:


#st_dates = [pd.Timestamp('2020-08-01'), pd.Timestamp('2021-02-01'), pd.Timestamp('2020-11-01')]

# In[8]:


#collection = pd.Series(index=pro_list, data=st_dates)

# In[9]:


# df = df.append(pd.DataFrame(index=pro_list, columns=dates))

# In[10]:


# for i in collection.index:
#     j = collection.loc[i]
#     df.loc[i, j] = 30
#     period = 1
#     k = j + pd.DateOffset(months=1)
#     while (k <= fin):
#         if (period % 3 == 0):
#             df.loc[i, k] = min(df.loc[i, j] + 30, 200)
#         else:
#             df.loc[i, k] = min(df.loc[i, j], 200)
#         period = period + 1
#         j = k
#         k = j + pd.DateOffset(months=1)
# df.T.to_sql(con=db, name='lucknow_data', if_exists='append')

# In[11]:

from app import views
