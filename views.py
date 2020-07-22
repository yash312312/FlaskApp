import os

from flask import send_file
from werkzeug.utils import secure_filename

from FlaskApp import app, pd, db, render_template, request, fin, cursor, connection, redirect, url_for, np, session, \
    colors

app.secret_key = "hello"
app.config['UPLOAD_FOLDER'] = "C:\\Users\\admin\\OneDrive\\Desktop\\FlaskApp\\FlaskApp\\static"


def save_excel(city_t, filename):
    xlsFilepath = app.config['UPLOAD_FOLDER'] + '\\%s_data.xlsx' % filename
    writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
    city_t.to_excel(writer, sheet_name='Sheet1', na_rep=0)
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']

    # Iterate through each column and set the width == the max length in that column. A padding length of 2 is also added.
    for i, col in enumerate(city_t.columns):
        # find length of column i
        column_len = city_t[col].astype(str).str.len().max()
        # Setting the length if the column header is larger
        # than the max column value length
        column_len = max(column_len, len(col)) + 2
        # set the column length
        worksheet.set_column(i, i, column_len)
    writer.save()


def add_product(name, sd, ed, initial, trend, mx, q):
    c = pd.date_range(sd, ed, freq='MS').strftime("%d/%m/%Y")
    sd = pd.Timestamp(sd).strftime("%d/%m/%Y")
    c = c.insert(0, 'Maximum')
    c = c.insert(0, 'Growth Rate')
    c = c.insert(0, 'Shops and Units')
    new_df = pd.DataFrame(columns=c)
    new_df.set_index('Shops and Units', inplace=True)
    new_df.loc[name, sd] = initial
    new_df.loc[name, 'Maximum'] = str(mx)
    new_df.loc[name, 'Growth Rate'] = str(trend)
    for k in range(4, len(c)):
        new_df.loc[name, c[k]] = new_df.loc[name, c[k - 1]] + trend
    return new_df


def update_data(city_data):
    c = city_data.columns
    for k in city_data.index:
        mx = city_data.loc[k, 'Maximum']
        trend = city_data.loc[k, 'Growth Rate']
        for j in range(3, len(c)):
            city_data.loc[k, c[j]] = int(city_data.loc[k, c[j - 1]]) + int(trend)
    print(city_data)
    return city_data


def delete_product(city, product_to_delete):
    col_name = 'Shops and Units'
    query = "DELETE FROM %s_data WHERE `%s` = 'Units of %s/Shops'" % (city, col_name, product_to_delete)
    cursor.execute(query)
    connection.commit()


def table_exists(name):
    ret = db.dialect.has_table(db, name)
    print('Table "{}" exists: {}'.format(name, ret))
    return ret


def total_revenue(city, state):
    city_t = pd.read_sql_table('%s_data' % city, con=db)
    state = pd.read_sql_table('%s_data' % state, con=db)
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
    city_t2.set_index('index', inplace=True)
    if not date_check(str(city_t2.columns[0]), d1):
        c = pd.date_range(start=str(city_t2.columns[0]), end=d2, freq='MS').strftime("%m/%d/%Y")
    else:
        c = pd.date_range(start=d1, end=d2, freq='MS').strftime("%m/%d/%Y")
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


def calc_state_revenue(state, l, name, d1, d2):
    d2 = d2 + '-01'
    state_cost = pd.read_sql("SELECT * FROM `%s_data` WHERE `name` = '%s'" % (state, name), db, columns=['cost'],
                             index_col='name').loc[name, 'cost']
    sum = 0
    print(state_cost)
    for i in l:
        if not table_exists("%s_data" % i):
            continue
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


def calc_city_wise_revenue(city, d1, d2, state):
    d2 = d2 + '-01'
    if not table_exists("%s_data" % city):
        return 0
    city_t = total_revenue(city, state)
    return calc_revenue(city_t, d1, d2)


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if request.form['btn'] == 'chosen_city':
            session['city_name'] = request.form.get('city_list')
            return redirect(url_for('city_input_route'))
    return render_template('index.html')


@app.route("/product", methods=['GET', 'POST'])
def product_cost():
    return render_template('product_cost.html')


@app.route("/city_input", methods=['GET', 'POST'])
def city_input_route():
    if 'city_name' in session:
        city_data = None
        city = session['city_name']
        if table_exists('%s_data' % city):
            city_data = pd.read_sql_table('%s_data' % city, con=db)
            city_data.replace(to_replace=[None], value='0', inplace=True)
            city_data.replace(to_replace=np.nan, value='0', inplace=True)
        else:
            session['city'] = city
            return redirect(url_for('form_shop'))
        # print(city_data)
        if request.method == 'POST':
            if request.form['btn'] == 'upload':
                f = request.files['city_data']
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], '%s_data' % city))
                city_data = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], '%s_data' % city))
                city_data.set_index('Shops and Units', inplace=True)
                city_data = update_data(city_data)

                city_data.to_sql(name='%s_data' % city, con=db, if_exists='replace', index_label='Shops and Units')
                city_data.reset_index(inplace=True)

        return render_template('city_input.html', tables=[
            city_data.to_html(classes='table table-bordered', col_space=150, index=False, table_id='product_table',
                              justify='center')], titles=city_data.columns.values, city=city.upper())
    else:
        return redirect(url_for('home'))


@app.route('/download')
def download_file():
    p = app.config['UPLOAD_FOLDER'] + "\\" + session['city_name'] + '_data.xlsx'
    return send_file(p, as_attachment=True)


@app.route("/state_input", methods=['GET', 'POST'])
def state_input_route():
    if 'state_name' in session:
        state = session['state_name']
        if not table_exists('%s_data' % state):
            cursor.execute(
                "CREATE TABLE %s_data (name VARCHAR(255) , cost DOUBLE)" % state)
            connection.commit()
        temp = pd.read_sql_table('%s_data' % state, con=db)
        if request.method == 'POST':
            product_name = request.form.get('product_name')
            product_cost = request.form.get('product_cost')

            if product_name and product_cost and product_name not in list(temp['name']):
                error = 'Invalid Values'
                cursor.execute('''INSERT into %s_data (name, cost)
                                             values ('%s', %s)''' %
                               (state, product_name, product_cost))
                connection.commit()
            print('''INSERT into %s_data (name, cost) values ('%s', %s)''' % (state, product_name, product_cost))
            temp = pd.read_sql_table('%s_data' % state, con=db)
        return render_template('state_input.html', tables=[
            temp.to_html(classes='table table-bordered', col_space=150, index=False, table_id='product_table',
                         justify='center')], titles=temp.columns.values, state=state.upper())
    else:
        return redirect(url_for('home'))


@app.route("/up", methods=['GET', 'POST'])
def up_route():
    if not table_exists('up_revenue'):
        cursor.execute(
            "CREATE TABLE up_revenue (parameter VARCHAR(255) , value VARCHAR(255))")
        connection.commit()
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('rps', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('rpe', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('rcs', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('rce', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('pwds', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('pwse', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('cwds', NULL)''')
        cursor.execute('''INSERT into up_revenue (parameter, value) values ('cwde', NULL)''')
        connection.commit()
    up_revenue = pd.read_sql_table('up_revenue', con=db)
    up_revenue.set_index('paramater', inplace=True)
    if request.method == 'POST':
        if request.form['btn'] == 'product_revenue':
            up_revenue.loc['rps', 'value'] = request.form.get('rps')
            up_revenue.loc['rpe', 'value'] = request.form.get('rpe')

    return render_template('up.html')


@app.route("/bihar", methods=['GET', 'POST'])
def bihar_route():
    if not table_exists('bihar_data'):
        cursor.execute(
            "CREATE TABLE bihar_data (name VARCHAR(255) , cost DOUBLE)")
        connection.commit()
    if request.method == 'GET':
        session.clear()
    list_city = ['patna']
    temp = pd.read_sql_table('bihar_data', con=db)
    session['lp'] = list(temp['name'])

    if request.method == 'POST':
        if request.form['btn'] == 'add':
            product_name = request.form.get('product_name')
            product_cost = request.form.get('product_cost')
            if not product_name or not product_cost or product_name in str(temp['name']):
                error = 'Invalid Values'
                product_name = request.form.get('product_name')
                product_cost = request.form.get('product_cost')
                if product_name and product_cost and product_name not in session['lp']:
                    error = 'Invalid Values'
                    cursor.execute('''INSERT into up_data (name, cost)
                                                 values (%s, %s)''',
                                   (product_name, product_cost))
                    connection.commit()
                    session['lp'].append(product_name)
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
                session['revenue'] = 'Illegal Date'
            else:

                session['revenue'] = calc_state_revenue('bihar', list_city, session['set_p'], session['ssd'],
                                                        session['sed'])
                print(session['revenue'])
        elif request.form['btn'] == 'revenue_product_p':
            if 'psd' in session:
                session.pop('psd', None)
            if 'ped' in session:
                session.pop('ped', None)
            temp = pd.read_sql_table('bihar_data', con=db)
            session['lp'] = list(temp['name'])
            print(session['lp'])
            session['psd'] = request.form.get('start_date_p')
            session['ped'] = request.form.get('end_date_p')
            session['list_revenue'] = [calc_state_revenue('bihar', list_city, i, session['psd'], session['ped']) for i
                                       in
                                       session['lp']]
            print(session['list_revenue'])
        elif request.form['btn'] == 'revenue_product_c':
            if 'csd' in session:
                session.pop('csd', None)
            if 'ced' in session:
                session.pop('ced', None)

            session['csd'] = request.form.get('start_date_c')
            session['ced'] = request.form.get('end_date_c')
            session['city_wise_revenue'] = [calc_city_wise_revenue(c, session['csd'], session['ced'], 'bihar') for c in
                                            list_city]
            print(session['city_wise_revenue'])

    temp = pd.read_sql_table('bihar_data', con=db)
    return render_template('bihar.html', tables=[
        temp.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                     justify='center')], titles=temp.columns.values, listOfPro=(temp['name']),
                           revenue=session['revenue'] if 'revenue' in session else 0,
                           ssd=session['ssd'] if 'ssd' in session else None,
                           sed=session['sed'] if 'sed' in session else None,
                           psd=session['psd'] if 'psd' in session else None,
                           ped=session['ped'] if 'ped' in session else None,
                           csd=session['csd'] if 'csd' in session else None,
                           ced=session['ced'] if 'ced' in session else None,
                           set_product=session['set_p'] if 'set_p' in session else None,
                           lp=session['lp'] if 'lp' in session else [],
                           list_revenue_city=session['city_wise_revenue'] if 'city_wise_revenue' in session else [],
                           list_city=list_city,
                           list_revenue_product=session['list_revenue'] if 'list_revenue' in session else [],
                           colors_state=colors, colors_city=colors[::-1],
                           data_state=zip(session['lp'], colors[:len(session['lp'])]),
                           data_city=zip(list_city, colors[::-1]))


@app.route("/delhi")
def delhi_route():
    return render_template('delhi.html')


@app.route("/lucknow", methods=['POST', 'GET'])
def lucknow_route():
    if not table_exists('lucknow_data'):
        session['city'] = 'lucknow'
        return redirect(url_for('form_shop'))
    if 'sd' in session:
        session.pop('sd', None)
    if 'ed' in session:
        session.pop('ed', None)
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
    city_t.replace(to_replace=[None], value='0', inplace=True)
    city_t.replace(to_replace=np.nan, value='0', inplace=True)
    state_t = pd.read_sql_table('up_data', con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    revenue = 0
    city_t2 = total_revenue('lucknow', 'up')

    if request.method == 'POST':
        if request.form['btn'] == 'revenue':
            if 'sd' in session:
                session.pop('sd', None)
            if 'ed' in session:
                session.pop('ed', None)
            d1 = request.form.get('start_date')
            d2 = request.form.get('end_date')
            session['sd'] = d1
            session['ed'] = d2
            if not d1 or not d2:
                revenue = 'Illegal Date'
            elif pd.Timestamp(session['sd']) > pd.Timestamp(session['ed']):
                revenue = 'Illegal Date'
            else:
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
    if 'sd' in session:
        session.pop('sd', None)
    if 'ed' in session:
        session.pop('ed', None)
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
    city_t.replace(to_replace=[None], value='0', inplace=True)
    city_t.replace(to_replace=np.nan, value='0', inplace=True)

    state_t = pd.read_sql_table('up_data', con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    revenue = 0
    city_t2 = total_revenue('gorakhpur', 'up')

    if request.method == 'POST':
        if request.form['btn'] == 'revenue':
            if 'sd' in session:
                session.pop('sd', None)
            if 'ed' in session:
                session.pop('ed', None)
            d1 = request.form.get('start_date')
            d2 = request.form.get('end_date')
            session['sd'] = d1
            session['ed'] = d2
            if not d1 or not d2:
                revenue = 'Illegal Date'
            elif pd.Timestamp(session['sd']) > pd.Timestamp(session['ed']):
                revenue = 'Illegal Date'
            else:
                revenue = calc_revenue(city_t2, d1, d2)
    return render_template('gorakhpur.html', tables=[
        city_t.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                       justify='center'),
        city_t2.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                        justify='center')], titles=city_t.columns.values, listOfPro=product_in_city, revenue=revenue,
                           sd=session['sd'] if 'sd' in session else None, ed=session['ed'] if 'ed' in session else None)


@app.route("/patna", methods=['POST', 'GET'])
def patna_route():
    if not table_exists('patna_data'):
        session['city'] = 'patna'
        return redirect(url_for('form_shop'))
    if 'sd' in session:
        session.pop('sd', None)
    if 'ed' in session:
        session.pop('ed', None)
    if request.method == 'POST':
        if request.form['btn'] == 'add':
            session['city'] = 'patna'
            session['state'] = 'bihar'
            city_t = pd.read_sql_table('patna_data', con=db)
            session['date'] = '%s' % city_t.columns[1]
            return redirect(url_for('form_product'))
        if request.form['btn'] == 'delete':
            product_to_delete = request.form.get('delete_product')
            delete_product('patna', product_to_delete)
    city_t = pd.read_sql_table('patna_data', con=db)
    city_t.replace(to_replace=[None], value='0', inplace=True)
    city_t.replace(to_replace=np.nan, value='0', inplace=True)
    state_t = pd.read_sql_table('bihar_data', con=db)
    product_in_city = set(z[9:-6] for z in city_t['Shops and Units'][1:])
    revenue = 0
    city_t2 = total_revenue('patna', 'bihar')

    if request.method == 'POST':
        if request.form['btn'] == 'revenue':
            if 'sd' in session:
                session.pop('sd', None)
            if 'ed' in session:
                session.pop('ed', None)
            d1 = request.form.get('start_date')
            d2 = request.form.get('end_date')
            session['sd'] = d1
            session['ed'] = d2
            if not d1 or not d2:
                revenue = 'Illegal Date'
            elif pd.Timestamp(session['sd']) > pd.Timestamp(session['ed']):
                revenue = 'Illegal Date'
            else:
                revenue = calc_revenue(city_t2, d1, d2)
    return render_template('patna.html', tables=[
        city_t.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                       justify='center'),
        city_t2.to_html(classes='table table-bordered', col_space=150, index=False, table_id='dataTable',
                        justify='center')], titles=city_t.columns.values, listOfPro=product_in_city, revenue=revenue,
                           sd=session['sd'] if 'sd' in session else None, ed=session['ed'] if 'ed' in session else None)


@app.route("/shop", methods=['POST', 'GET'])
def form_shop():
    if 'city' in session:
        if (request.method == 'POST'):
            sdate = request.form.get('launch_date')
            edate = request.form.get('end_date')
            initial = request.form.get('initial_shops')
            growth = request.form.get('growth_rate')
            max_shop = request.form.get('max_shop')
            q = request.form.get('quarterly')
            new_df = add_product('Shops', sdate, edate, int(initial), int(growth), int(max_shop), q)
            save_excel(new_df, session['city'])
            new_df.to_sql(con=db, name='%s_data' % session['city'], if_exists='append', index_label='Shops and Units')
            return redirect(url_for('city_input_route'))
    else:
        return redirect(url_for('home'))

    return render_template('form_shop.html')


@app.route("/unit", methods=['POST', 'GET'])
def form_product():
    if 'city_name' in session:
        if (request.method == 'POST'):
            sdate = request.form.get('launch_date')
            edate = request.form.get('end_date')
            initial = request.form.get('initial_units')
            growth = request.form.get('growth_rate')
            max_unit = request.form.get('max_units')
            q = request.form.get('quarterly')
            name = request.form.get('product_name')
            new_df = add_product(name, sdate, edate, int(initial), int(growth), int(max_unit), q)
            new_df.to_sql(con=db, name='%s_data' % session['city_name'], if_exists='append',
                          index_label='Shops and Units')
            temp = pd.read_sql_table('%s_data' % session['city_name'], con=db)
            temp.set_index('Shops and Units', inplace=True)
            save_excel(temp, session['city_name'])
            return redirect(url_for('city_input_route'))
        return render_template('form_product.html', listOfPro=['X', 'Y', 'Z'])
    return redirect(url_for('home'))
