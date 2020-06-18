from app import app, pd, db, render_template, request, fin, dates, df, cursor, connection, redirect, url_for, np, \
    session

app.secret_key = "hello"


def add_product(n, d, sd, q, iu, gr, mu):
    if n != 'Shops':
        name = "Units of " + n + "/Shops"
    else:
        name = n
    date = pd.Timestamp(d)
    iu = int(iu)
    gr = int(gr)
    mu = int(mu)
    # global pro_list
    # global st_dates
    # pro_list.append(name)
    # st_dates.append(date)
    c = pd.date_range(sd, end='2024-12-31', freq='MS')
    c = c.insert(0, 'Shops and Units')
    new_df = pd.DataFrame(columns=c)
    new_df.set_index('Shops and Units', inplace=True)
    new_df.loc[name, date] = iu
    k = date + pd.DateOffset(months=1)
    if q == 'on':
        period = 1
        while (k <= fin):
            if (period % 3 == 0):
                new_df.loc[name, k] = min(new_df.loc[name, date] + gr, mu)
            else:
                new_df.loc[name, k] = min(new_df.loc[name, date], mu)
            date = k
            period = period + 1
            k = date + pd.DateOffset(months=1)
    else:
        while (k <= fin):
            new_df.loc[name, k] = min(new_df.loc[name, date] + gr, mu)
            date = k
            k = date + pd.DateOffset(months=1)
    print(new_df)
    return new_df


def delete_product(city, product_to_delete):
    col_name = 'Shops and Units'
    query = "DELETE FROM %s_data WHERE `%s` = 'Units of %s/Shops'" % (city, col_name, product_to_delete)
    cursor.execute(query)
    connection.commit()


def table_exists(name):
    ret = db.dialect.has_table(db, name)
    print('Table "{}" exists: {}'.format(name, ret))
    return ret


def total_revenue(city_t, state):
    city_t.set_index('Shops and Units', inplace=True)
    city_t.replace(to_replace=[None], value='0', inplace=True)
    city_t.replace(to_replace=np.nan, value='0', inplace=True)
    state.set_index(['name'], inplace=True)
    # print(state)
    city_t2 = pd.DataFrame(columns=city_t.columns, index=['Total'])
    # print(city_t)
    for i in city_t2.columns:
        s = 0
        for j in state.index:
            for k in city_t.index:
                if j == k[9:-6]:
                    # print(j)
                    s = s + int(city_t.loc[k, i]) * state.loc[j, 'cost']

                    # print(type(city_t.loc[k,i]))
                    break
        city_t2.loc['Total', i] = s * int(city_t.loc['Shops', i])
    return city_t2.reset_index()


def calc_revenue(city_t2, d1, d2):
    s = 0
    c = pd.date_range(start=d1, end=d2, freq='MS').strftime("%m/%d/%Y")
    city_t2.set_index('index', inplace=True)
    print(city_t2)
    for i in c:
        s = s + int(city_t2.loc['Total', i])
    city_t2.reset_index(inplace=True)
    return s


def date_check(i_d, f_d):
    y1 = int(i_d[-4:])
    y2 = int(f_d[:4])
    if y1 > y2:
        return False
    m1 = int(i_d[:2])
    m2 = int(f_d[-2:])
    if m1 > m2:
        return False
    return True


def calc_state_revenue(state, l, name):
    d1 = session['ssd']
    d2 = session['sed'] + '-01'
    state_cost = pd.read_sql("SELECT * FROM `%s_data` WHERE `name` = '%s'" % (state, name), db, columns=['cost'],
                             index_col='name').loc[name, 'cost']
    sum = 0
    print(state_cost)
    for i in l:
        city = pd.read_sql('%s_data' % i, db)
        if date_check(str(city.columns[1]), d1):
            c = pd.date_range(start=d1, end=d2, freq='MS').strftime("%m/%d/%Y")
            print(c)
        else:
            c = pd.date_range(start=str(city.columns[1]), end=d2, freq='MS').strftime("%m/%d/%Y")
            print(c)
        city = pd.read_sql('%s_data' % i, db, columns=c, index_col='Shops and Units', coerce_float=True)
        city.replace(to_replace=[None], value=0, inplace=True)
        city.replace(to_replace=np.nan, value=0, inplace=True)
        for k in city.index:
            if k[9:-6] == name:
                for j in c:
                    sum = sum + city.loc[k, j] * state_cost * city.loc['Shops', j]

    return sum


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/up", methods=['GET', 'POST'])
def up_route():
    if not table_exists('up_data'):
        cursor.execute(
            "CREATE TABLE up_data (name VARCHAR(255) , cost DOUBLE)")
        connection.commit()
    temp = pd.read_sql_table('up_data', con=db)
    revenue = 0
    if 'ssd' in session:
        session.pop('ssd', None)
    if 'sed' in session:
        session.pop('sed', None)
    if request.method == 'POST':
        if request.form['btn'] == 'add':
            product_name = request.form.get('product_name')
            product_cost = request.form.get('product_cost')
            if not product_name or not product_cost or product_name in str(temp['name']):
                error = 'Invalid Values'
                return render_template('up.html', tables=[
                    temp.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                                 justify='center')], titles=temp.columns.values, listOfPro=(temp['name']),
                                       revenue=revenue,
                                       ssd=session['ssd'] if 'ssd' in session else None,
                                       sed=session['sed'] if 'sed' in session else None,
                                       set_product=session['set_p'] if 'set_p' in session else None)

            cursor.execute('''INSERT into up_data (name, cost)
                             values (%s, %s)''',
                           (product_name, product_cost))
            connection.commit()
        elif request.form['btn'] == 'revenue_product':
            if 'ssd' in session:
                session.pop('ssd', None)
            if 'sed' in session:
                session.pop('sed', None)
            if 'set_p' in session:
                session.pop('set_p', None)
            session['set_p'] = request.form.get('product_revenue')
            session['ssd'] = request.form.get('start_date')
            session['sed'] = request.form.get('end_date')
            if pd.Timestamp(session['ssd']) > pd.Timestamp(session['sed']):
                revenue = 'Illegal Date'
            else:
                l = ['lucknow', 'gorakhpur']
                revenue = calc_state_revenue('up', l, session['set_p'])
                print(revenue)
    temp = pd.read_sql_table('up_data', con=db)
    return render_template('up.html', tables=[
        temp.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                     justify='center')], titles=temp.columns.values, listOfPro=(temp['name']), revenue=revenue,
                           ssd=session['ssd'] if 'ssd' in session else None,
                           sed=session['sed'] if 'sed' in session else None,
                           set_product=session['set_p'] if 'set_p' in session else None
                           )


@app.route("/bihar")
def bihar_route():
    return render_template('bihar.html')


@app.route("/delhi")
def delhi_route():
    return render_template('delhi.html')


# @app.route("/lucknow", methods=['POST', 'GET'])
# def lucknow_route():
#     list_of_pro_to_be_added = []
#     if table_exists('up_data'):
#         temp1 = pd.read_sql_table('up_data', con=db)
#         list_of_pro_to_be_added = list(temp1['name'])
#     if not table_exists('lucknow_data'):
#         df.to_sql(con=db, name='lucknow_data', if_exists='append', index=False)
#     if (request.method == 'POST'):
#         if request.form['btn'] == 'add':
#             name = request.form.get('product_name')
#             date = request.form.get('launch_date')
#             quarterly = request.form.get('quarterly')
#             if not name or not date:
#                 temp = pd.read_sql_table('lucknow_data', db)
#                 k = list(temp['Shops and Units'][1:])
#                 return render_template('lucknow.html', tables=[temp.to_html(classes='data')],
#                                        titles=temp.columns.values,
#                                        listOfPro=k, listOfProToBeAdded=list_of_pro_to_be_added)
#
#             print(name)
#             print(date)
#             new_df = add_product(name, date, quarterly)
#             new_df.to_sql(con=db, name='lucknow_data', if_exists='append', index_label='Shops and Units')
#         if request.form['btn'] == 'delete':
#             product_to_delete = request.form.get('delete_product')
#             col_name = 'Shops and Units'
#             print("DELETE FROM lucknow_data WHERE `%s` = '%s'" % (col_name, product_to_delete))
#             query = "DELETE FROM lucknow_data WHERE `%s` = '%s'" % (col_name, product_to_delete)
#             cursor.execute(query)
#             connection.commit()
#     temp = pd.read_sql_table('lucknow_data', db)
#     k = list(temp['Shops and Units'][1:])
#
#     print(k)
#     return render_template('lucknow.html', tables=[temp.to_html(classes='data')], titles=temp.columns.values,
#                            listOfPro=k, listOfProToBeAdded=list_of_pro_to_be_added)
#

######
@app.route("/lucknow", methods=['POST', 'GET'])
def lucknow_route():
    if not table_exists('lucknow_data'):
        session['city'] = 'lucknow'
        return redirect(url_for('form_shop'))
    if request.method == 'POST':
        if request.form['btn'] == 'add':
            session['city'] = 'lucknow'
            session['state'] = 'up'
            city_t = pd.read_sql_table('lucknow_data', con=db)
            session['date'] = '%s' % city_t.columns[1]
            return redirect(url_for('form_product'))
        if request.form['btn'] == 'delete':
            product_to_delete = request.form.get('delete_product')
            delete_product('lucknow', product_to_delete)
    city_t = pd.read_sql_table('lucknow_data', con=db)
    state_t = pd.read_sql_table('up_data', con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    revenue = 0
    city_t2 = total_revenue(city_t, state_t)
    city_t.reset_index(inplace=True)
    if request.method == 'POST':
        if request.form['btn'] == 'revenue':
            d1 = request.form.get('start_date')
            d2 = request.form.get('end_date')
            session['sd'] = d1
            session['ed'] = d2
            revenue = calc_revenue(city_t2, d1, d2)
    return render_template('lucknow.html', tables=[
        city_t.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                       justify='center'),
        city_t2.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                        justify='center')], titles=city_t.columns.values, listOfPro=product_in_city, revenue=revenue,
                           sd=session['sd'] if 'sd' in session else None, ed=session['ed'] if 'ed' in session else None)


@app.route("/gorakhpur", methods=['POST', 'GET'])
def gorakhpur_route():
    if not table_exists('gorakhpur_data'):
        session['city'] = 'gorakhpur'
        return redirect(url_for('form_shop'))
    if request.method == 'POST':
        if request.form['btn'] == 'add':
            session['city'] = 'gorakhpur'
            session['state'] = 'up'
            city_t = pd.read_sql_table('gorakhpur_data', con=db)
            session['date'] = '%s' % city_t.columns[1]
            return redirect(url_for('form_product'))
        if request.form['btn'] == 'delete':
            product_to_delete = request.form.get('delete_product')
            delete_product('gorakhpur', product_to_delete)
    city_t = pd.read_sql_table('gorakhpur_data', con=db)
    state_t = pd.read_sql_table('up_data', con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    revenue = 0
    city_t2 = total_revenue(city_t, state_t)
    city_t.reset_index(inplace=True)
    if request.method == 'POST':
        if request.form['btn'] == 'revenue':
            d1 = request.form.get('start_date')
            d2 = request.form.get('end_date')
            session['sd'] = d1
            session['ed'] = d2
            revenue = calc_revenue(city_t2, d1, d2)

    return render_template('gorakhpur.html', tables=[
        city_t.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                       justify='center'),
        city_t2.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                        justify='center')], titles=city_t.columns.values, listOfPro=product_in_city, revenue=revenue,
                           sd=session['sd'] if 'sd' in session else None, ed=session['ed'] if 'ed' in session else None)


@app.route("/shop", methods=['POST', 'GET'])
def form_shop():
    if 'city' in session:
        if (request.method == 'POST'):
            date = request.form.get('launch_date') + "-01"
            i_s = request.form.get('initial_shops')
            gr = request.form.get('growth_rate')
            ms = request.form.get('max_shop')
            q = request.form.get('quarterly')
            column_names = pd.date_range(date, end='2024-12-31', freq='MS').strftime("%m/%d/%Y")
            column_names = column_names.insert(0, 'Shops and Units')
            for i in column_names:
                if i == column_names[0]:
                    cursor.execute("CREATE TABLE %s_data(`%s` VARCHAR(255))" % (session['city'], i))
                    connection.commit()
                else:
                    cursor.execute("ALTER TABLE %s_data ADD COLUMN `%s` float" % (session['city'], i))
                    connection.commit()
            new_df = add_product('Shops', date, date, q, i_s, gr, ms)
            new_df.columns = column_names[1:]
            new_df.to_sql(con=db, name='%s_data' % session['city'], if_exists='append', index_label='Shops and Units')
            return redirect(url_for("%s_route" % session['city']))

    return render_template('form_shop.html', city=session['city'].capitalize())


@app.route("/unit", methods=['POST', 'GET'])
def form_product():
    if (request.method == 'POST'):
        city = request.form.get('city')
        name = request.form.get('product_name')
        date = request.form.get('launch_date')
        iu = request.form.get('initial_units')
        gr = request.form.get('growth_rate')
        mu = request.form.get('max_units')
        q = request.form.get('quarterly')
        new_df = add_product(name, date, session['date'], q, iu, gr, mu)
        print(new_df)
        c = pd.date_range(session['date'], end='2024-12-31', freq='MS').strftime("%m/%d/%Y")
        new_df.columns = c
        new_df.to_sql(con=db, name='%s_data' % session['city'], if_exists='append', index_label='Shops and Units')
        return redirect(url_for("%s_route" % session['city']))
    city_t = pd.read_sql_table('%s_data' % session['city'], con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    state_t = pd.read_sql_table('up_data' % ['state'], con=db)
    product_in_state = set(state_t['name'])
    list_of_pro_to_be_added = product_in_state - product_in_city
    return render_template('form_product.html', listOfPro=list_of_pro_to_be_added, city=session['city'].capitalize())
