from flask import Flask,render_template,request,session,redirect,url_for,flash,Response
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash,check_password_hash
import MySQLdb.cursors
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_mail import Mail,Message

import io
import xlwt

app = Flask(__name__)

app.config['SECRET_KEY'] = 'this is secret key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myproject'


mysql = MySQL(app)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USERNAME'] = 'kapilabakers123@gmail.com'
app.config['MAIL_PASSWORD'] = 'kapila@123'
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)



UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/')
def index():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("select * from items")
    data = cursor.fetchall()
    return render_template("index.html",data=data)





# send message box
@app.route('/contactus',methods=['POST'])
def send_message():
    if request.method == 'POST':
        fist_name = request.form['firstname']
        last_name = request.form['lastname']
        mobile_number = request.form['mobile']
        email_address = request.form['email']
        description = request.form['description']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("INSERT INTO inbox (first_name,last_name,mobile_number,email,description) VALUES (%s,%s,%s,%s,%s)",(fist_name,last_name,mobile_number,email_address,description,))
        mysql.connection.commit()
        cursor.close()

    return render_template("index.html")



@app.route('/add', methods=['POST'])
def add_product_to_cart():
    if 'session_username' in session:
        if request.method == 'POST':
            _customer_id = request.form['customerid']
            _user_name = request.form['username']
            _code = request.form['code']
            _quantity = int(request.form['quantity'])

            status = "pending"

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("INSERT INTO orders (customer_id,username,item_name,quantity,status) VALUES (%s, %s, %s, %s, %s)",(_customer_id,_user_name,_code,_quantity,status,))
            mysql.connection.commit()
            cursor.close()


            if _quantity and _code and request.method == 'POST':
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute("SELECT * FROM items WHERE name = %s", [_code])
                row = cursor.fetchone()

                itemArray = {row['name']: {'item_id': row['item_id'], 'name': row['name'], 'quantity': _quantity,'price': row['price'], 'file_name': row['file_name'],'total_price': _quantity * row['price']}}

                all_total_price = 0
                all_total_quantity = 0

                session.modified = True
                if 'cart_item' in session:
                    if row['name'] in session['cart_item']:
                        for key, value in session['cart_item'].items():
                            if row['name'] == key:
                                old_quantity = session['cart_item'][key]['quantity']
                                total_quantity = old_quantity + _quantity
                                session['cart_item'][key]['quantity'] = total_quantity
                                session['cart_item'][key]['total_price'] = total_quantity * row['price']
                    else:
                        session['cart_item'] = array_merge(session['cart_item'], itemArray)

                    for key, value in session['cart_item'].items():
                        individual_quantity = int(session['cart_item'][key]['quantity'])
                        individual_price = float(session['cart_item'][key]['total_price'])
                        all_total_quantity = all_total_quantity + individual_quantity
                        all_total_price = all_total_price + individual_price
                else:
                    session['cart_item'] = itemArray
                    all_total_quantity = all_total_quantity + _quantity
                    all_total_price = all_total_price + _quantity * row['price']

                session['all_total_quantity'] = all_total_quantity
                session['all_total_price'] = all_total_price

        return redirect('/#menu')
    else:
        return redirect("/login")



@app.route('/empty')
def empty_cart():
    try:
        session.clear()
        return render_template("user_cart.html")
    except Exception as e:
        print(e)


@app.route('/cart_delete/<string:code>,<string:us>')
def delete_product(code,us):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM orders WHERE username = %s and item_name = %s",(us,code))
    mysql.connection.commit()


    for item in session['cart_item'].items():
        if item[0] == code:
            session['cart_item'].pop(item[0], None)
            if 'cart_item' in session:
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quantity'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            break

    if all_total_quantity == 0:
        session.clear()
    else:
        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price

    return redirect('/user_cart')
'''
@app.route('/testitem')
def testitem():
    if 'cart_item' in session:
        obj = session.items()
        return render_template("test.html",obj=obj)
'''

@app.route('/user_cart')
def user_cart():
    return render_template("user_cart.html")



def array_merge(first_array, second_array):
    if isinstance(first_array, list) and isinstance(second_array, list):
        return first_array + second_array
    elif isinstance(first_array, dict) and isinstance(second_array, dict):
        return dict(list(first_array.items()) + list(second_array.items()))
    elif isinstance(first_array, set) and isinstance(second_array, set):
        return first_array.union(second_array)
    return False

@app.route('/submit_order', methods=['POST'])
def submit_order():

    status = "pending"

    user_name = request.form['username']

    total_quantity = request.form['totalquantity']
    total_price = request.form['totalprice']

    first_name = request.form['fname']
    last_name = request.form['lname']
    address = request.form['address']
    mobile_number = request.form['mobile']

    customer_id = request.form['customer_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("INSERT INTO orders_info(customer_id,username,status,total_quantity,total_price,first_name,last_name,address,contact_number) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(customer_id,user_name,status,total_quantity,total_price,first_name,last_name,address,mobile_number,))
    mysql.connection.commit()
    cursor.close()

    return redirect('/user_account/my_orders')

# test
@app.route('/test', methods=['GET', 'POST'])
def test():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        secret_key = request.form['secretkey']

        _hashed_password = generate_password_hash(password)
        _hashed_secretkey = generate_password_hash(secret_key)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("INSERT INTO admin_info (username, email, password,secret_key) VALUES (%s, %s, %s, %s)", (username,email,_hashed_password,_hashed_secretkey))
        mysql.connection.commit()
        cursor.close()
    return render_template("test.html")


# customer login
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    msg1 = ''
    msg2 = ''

    if request.method == 'POST':
        # Get Form Fields
        _username = request.form['username']
        _password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get user by username
        result = cursor.execute("SELECT * FROM register_info WHERE username = %s", [_username])

        if result > 0:
            # Get stored hash
            data = cursor.fetchone()
            password = data['password']
            # Compare Passwords
            if check_password_hash(password, _password):
                cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                use = cur.execute("SELECT * FROM register_info WHERE username = %s", [_username])
                use =cur.fetchone()
                # Passed
                session['logged_in'] = True
                session['session_username'] = _username
                session['session_customer_id'] = use['customer_id']
                session['session_first_name'] = use['first_name']
                session['session_last_name'] = use['last_name']
                session['session_email'] = use['email']
                session['session_address'] = use['address']
                session['session_mobile_number'] = use['mobile_number']
                return redirect(url_for('user_account'))
                #return render_template('index.html',msg1=msg1,msg2=msg2)
            else:
                msg = 'Incorrect username / password !'
                session.clear()
                return render_template('login.html',msg = msg)
            # Close connection
                cursor.close()
        else:
            msg = 'Invalid login'
    return render_template('login.html', msg=msg)



'''    

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM register_info WHERE username = % s AND password = % s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['customer_id'] = account['customer_id']
            session['username'] = account['username']
            msg1 = 'Hello '
            msg2 = 'Welcome to Kapila bakers'
            return render_template('index.html',msg1=msg1,msg2=msg2)
        else:
            msg3 = 'Incorrect username / password !'
    return render_template('login.html', msg3=msg3)
'''
# user forgot password
@app.route('/forgot_password')
def forgot_password():
    return render_template("user_forgot_password.html")



# customer user account
@app.route('/user_account')
def user_account():
    if 'session_username' in session:
        username = session['session_username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM register_info WHERE username = % s', (username,))
        data = cursor.fetchone()
        return render_template('user_account.html',data=data)
    else:
        return redirect(url_for('index'))




# customer user account settings
@app.route('/user_account/user_account_settings')
def user_account_settings():
    if 'session_username' in session:
        username = session['session_username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM register_info WHERE username = % s', (username,))
        data = cursor.fetchone()
    return render_template('user_account_settings.html',data=data)





# customer user account change settings
@app.route('/user_account/user_account_settings/edit_user_details/<int:customer_id>',methods=['GET', 'POST'])
def edit_user_details(customer_id):
    if request.method == 'POST':
        #if and 'username' in request.form and 'first_name' in request.form and 'last_name' in request.form and 'email' in request.form and 'password' in request.form and 'address' in request.form and 'mobile_number' in request.form:
        _first_name = request.form['firstname']
        _last_name = request.form['lastname']
        _email_address = request.form['email']
        _address = request.form['address']
        _mobile_number = request.form['mobile_number']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE register_info SET first_name = %s,last_name = %s,email = %s,address = %s,mobile_number = %s WHERE customer_id = %s',(_first_name, _last_name, _email_address, _address, _mobile_number, customer_id))
        mysql.connection.commit()
        cursor.close()
        return redirect('/user_account/user_account_settings')


    return redirect('/user_account/user_account_settings')




# change user account password
@app.route('/user_account/user_account_settings/change_password/<int:customer_id>',methods = ['GET','POST'])
def change_password(customer_id):
    msg = ''

    if request.method == 'POST':

        old_password = request.form['oldpassword']
        new_password = request.form['newpassword']
        confirm_password = request.form['confirmpassword']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        data = cursor.execute('SELECT * FROM register_info WHERE customer_id = % s', (customer_id,))

        if data > 0:
            # Get stored hash
            data = cursor.fetchone()
            password = data['password']
            # Compare Passwords
            if check_password_hash(password, old_password):
                if new_password == confirm_password:
                    _hashed_password = generate_password_hash(new_password)
                    cursor.execute('UPDATE register_info SET password = %s WHERE customer_id = %s',(_hashed_password,customer_id))
                    mysql.connection.commit()
                    msg = "successful"
                    return render_template("user_change_password.html",msg=msg)
                else:
                    msg = 'New Password and Old Password Mismatch !!'
                    return render_template("user_change_password.html",msg=msg)
            else:
                msg = 'Old Password is Mismatch !!'
                return render_template("user_change_password.html",msg=msg)

    else:

        return render_template("user_change_password.html")



# customer orders display
@app.route('/user_account/my_orders')
def my_orders():
    status1 = "pending"
    status2 = "done"
    username = session['session_username']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM orders WHERE username = %s and status = %s', (username,status1,))
    data = cursor.fetchall()
    cursor.execute('SELECT * FROM orders_info WHERE username = %s and status = %s', (username, status1,))
    info = cursor.fetchall()

    cursor.execute('SELECT * FROM orders WHERE username = %s and status = %s', (username, status2,))
    donedata = cursor.fetchall()
    cursor.execute('SELECT * FROM orders_info WHERE username = %s and status = %s', (username, status2,))
    doneinfo = cursor.fetchall()


    return render_template("user_orders.html",data=data,info=info,donedata=donedata,doneinfo=doneinfo)






# customer orders display
@app.route('/user_account/my_orders/delete')
def my_orders_delete():
    status = "pending"
    username = session['session_username']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM orders WHERE username = %s and status = %s ', (username, status))
    mysql.connection.commit()
    cursor.execute('DELETE FROM orders_info WHERE username = %s and status = %s ', (username, status))
    mysql.connection.commit()

    return render_template("user_orders.html")







'''

        if old_password == '' and old_secret_key == '' and new_password == '' and new_secret_key == '':
            return redirect('/admin/home')
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            data = cursor.execute('SELECT * FROM admin_info WHERE username = % s', (username,))

            if data > 0:
                data = cursor.fetchone()
                _password = data['password']
                _secret_key = data['secret_key']

                if check_password_hash(_password,old_password) and check_password_hash(_secret_key,old_secret_key):
                    _hashed_new_password = generate_password_hash(new_password)
                    _hashed_new_secret_key = generate_password_hash(new_secret_key)
                    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                    cursor.execute('UPDATE admin_info SET password = %s,secret_key = %s WHERE username = %s',(_hashed_new_password,_hashed_new_secret_key,username))
                    mysql.connection.commit()
                    cursor.close()
                    return redirect('/admin/home')

                else:
                    session.clear()
                    return redirect(url_for('admin_logout'))

    return redirect('/admin/home')




'''





'''
        _username = request.form['username']
        _first_name = request.form['firstname']
        _last_name = request.form['lastname']
        _email = request.form['email']
        _password = request.form['password']
        _address = request.form['address']
        _mobile_number = request.form['mobile_number']
        #if 'username' in request.form and 'firstname' in request.form and 'lastname' in request.form and 'email' in request.form and 'password' in request.form and 'address' in request.form and 'mobile_number' in request.form:
        if _username and _first_name and _last_name and _email and _password and _address and _mobile_number == True:
            print(_username)
        else:
            print(_mobile_number)
'''
# customer user account contact
@app.route('/user_account/contact')
def user_account_contact():
    return render_template("user_account_contact.html")


# customer logout
@app.route('/logout')
def logout():
    session.clear()
    session.pop('cart_item',None)
    return redirect(url_for('index'))


# customer register form
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        _username = request.form['username']
        _first_name = request.form['firstname']
        _last_name = request.form['lastname']
        _email = request.form['emailaddress']
        _password = request.form['password']
        _address = request.form['address']
        _mobile_number = request.form['mobile_number']

        if _username and _first_name and _last_name and _email and _password and _address and _mobile_number:
            _hashed_password = generate_password_hash(_password)
            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM register_info WHERE username = %s", (_username,))
            user = curl.fetchone()
            # print(user)
            if user is None:
                curl.execute("INSERT INTO register_info (username,first_name,last_name,email,password,address,mobile_number) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                             (_username,_first_name,_last_name,_email, _hashed_password,_address,_mobile_number))
                mysql.connection.commit()
                curl.close()
                msg = 'Account Created Successfully !'
                return render_template("register.html",msg=msg)
            else:
                msg = 'This username already use another customer'
                return render_template("register.html",msg=msg)

        else:
            msg = 'Please fill out the form !'
            return render_template("register.html",msg=msg)
    else:
        return render_template("register.html",msg=msg)



# ------------------------- admin panel ---------------------

# admin login page
@app.route('/admin',methods=['GET', 'POST'])
def admin_login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        secret_key = request.form['secret_key']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        data = cursor.execute("SELECT * FROM admin_info WHERE username = %s", [username])

        if data > 0:
            data = cursor.fetchone()
            _password = data['password']
            _secret_key = data['secret_key']
            if check_password_hash(_password,password):
                if check_password_hash(_secret_key,secret_key):
                    session['session_admin_username'] = username
                    return redirect('/admin/home')
                else:
                    msg = 'Incorrect username / password !'
                    return redirect('/admin')

    return render_template("admin_login.html")


'''


        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admin_info WHERE username = % s AND password = % s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['username'] = account['username']
            session['password'] = account['password']
            return redirect('/admin/home')
        else:
            msg3 = 'Incorrect username / password !'
    return render_template("admin_login.html")
'''



# admin logout
@app.route('/admin_logout')
def admin_logout():
    session.pop('session_admin_username',None)
    return redirect(url_for('admin_login'))

# admin home page.after longin successful and load this page
@app.route('/admin/home')
def admin_home():
    if 'session_admin_username' in session:
        username = session['session_admin_username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM admin_info WHERE username = % s', (username,))
        addata=cursor.fetchone()
        return render_template('admin_home.html' ,addata=addata)

    return render_template("admin_login.html")





# admin home page,change admin password
@app.route('/admin/home/change/<string:username>',methods=['GET', 'POST'])
def admin_home_change(username):
    if request.method == 'POST':
        old_password = request.form['oldpassword']
        old_secret_key = request.form['oldsecretkey']
        new_password = request.form['newpassword']
        new_secret_key = request.form['newsecretkey']

        if old_password == '' and old_secret_key == '' and new_password == '' and new_secret_key == '':
            return redirect('/admin/home')
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            data = cursor.execute('SELECT * FROM admin_info WHERE username = % s', (username,))

            if data > 0:
                data = cursor.fetchone()
                _password = data['password']
                _secret_key = data['secret_key']

                if check_password_hash(_password,old_password) and check_password_hash(_secret_key,old_secret_key):
                    _hashed_new_password = generate_password_hash(new_password)
                    _hashed_new_secret_key = generate_password_hash(new_secret_key)
                    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                    cursor.execute('UPDATE admin_info SET password = %s,secret_key = %s WHERE username = %s',(_hashed_new_password,_hashed_new_secret_key,username))
                    mysql.connection.commit()
                    cursor.close()
                    return redirect('/admin/home')

                else:
                    session.clear()
                    return redirect(url_for('admin_logout'))

    return redirect('/admin/home')




# admin generate report
@app.route('/download/report/excel')
def download_report():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT customer_id, username, total_quantity, total_price, first_name, last_name, address, contact_number FROM orders_info")
    result = cursor.fetchall()

    # output in bytes
    output = io.BytesIO()
    # create WorkBook object
    workbook = xlwt.Workbook()
    # add a sheet
    sh = workbook.add_sheet('Orders Report')

    # add headers
    sh.write(0, 0, 'customer id')
    sh.write(0, 1, 'user name')
    sh.write(0, 2, 'total quantity')
    sh.write(0, 3, 'total price')
    sh.write(0, 4, 'first name')
    sh.write(0, 5, 'last name')
    sh.write(0, 6, 'address')
    sh.write(0, 7, 'contact number')



    idx = 0
    for row in result:
        sh.write(idx + 1, 0, str(row['customer_id']))
        sh.write(idx + 1, 1, row['username'])
        sh.write(idx + 1, 2, row['total_quantity'])
        sh.write(idx + 1, 3, row['total_price'])
        sh.write(idx + 1, 4, row['first_name'])
        sh.write(idx + 1, 5, row['last_name'])
        sh.write(idx + 1, 6, row['address'])
        sh.write(idx + 1, 7, row['contact_number'])

        idx += 1

    workbook.save(output)
    output.seek(0)

    return Response(output, mimetype="application/ms-excel",headers={"Content-Disposition": "attachment;filename=orders_report.xls"})


# admin orders
@app.route('/admin/orders')
def admin_orders():
    status = "pending"
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM orders WHERE status = %s', (status,))
    data = cursor.fetchall()

    cursor.execute('SELECT * FROM orders_info WHERE status = %s', (status,))
    info = cursor.fetchall()

    return render_template("admin_orders.html",data=data,info=info)

@app.route('/admin/orders/done/<string:id>')
def admin_orders_done(id):
    current_status = "pending"
    new_status = "done"

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE orders_info SET status = %s WHERE customer_id = %s',(new_status,id))
    cursor.execute('UPDATE orders SET status = %s WHERE customer_id = %s', (new_status, id))


    mysql.connection.commit()
    cursor.close()
    return redirect('/admin/orders')

'''

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM orders WHERE status = %s', (status,))
    data = cursor.fetchall()

    cursor.execute('SELECT * FROM orders_info WHERE status = %s', (status,))
    info = cursor.fetchall()
'''




# admin panel.account settings
@app.route('/admin/account_settings')
def admin_account_settings():
    if 'session_admin_username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select * from register_info")
        data = cursor.fetchall()
        return render_template("admin_account_settings.html",data=data)
    else:
        return redirect('/admin')

# admin panel,account settings/account delete
@app.route('/admin/account_settings/delete/<int:customer_id>',methods=['GET', 'POST'])
def admin_account_settings_delete(customer_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM register_info WHERE customer_id = %s", (customer_id,))
    mysql.connection.commit()
    flash("Record Has Been Deleted Successfully")
    return redirect( url_for('admin_account_settings'))

    '''
    if request.method == 'POST':
        _customer_id = request.form['customer_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("DELETE FROM register_info WHERE customer_id = %s", (_customer_id,))
        cursor.fetchall()
    return redirect('/admin/account_settings')
'''

# admin panel.show items list
@app.route('/admin/items')
def admin_items():
    if 'session_admin_username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select * from items")
        data = cursor.fetchall()
        return render_template("admin_items.html",data=data)
    else:
        return redirect('/admin')




# admin panel.Manage Item List
@app.route('/admin/manage_items_list')
def admin_manage_items_list():
    if 'session_admin_username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select * from items")
        data = cursor.fetchall()
        return render_template("admin_manage_items_list.html",data=data)
    else:
        return redirect('/admin')

# admin panel.item delete
@app.route('/manage_items/delete/<string:item_id>/<string:file_name>', methods=['POST', 'GET'])
def delete(item_id,file_name):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM items WHERE item_id = %s and file_name = %s ',(item_id,file_name))
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'],file_name))

    mysql.connection.commit()
    return redirect('/admin/manage_items_list')


@app.route('/manage_items/update/<int:item_id>',methods=["POST", "GET"])
def update_item(item_id):

    msg = ''

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM items WHERE item_id = % s', (item_id,))
    data = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        include = request.form['include']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE items SET name = %s,price = %s,include = %s WHERE item_id = %s', (name,price,include,item_id))
        mysql.connection.commit()
        msg = "Update Successful"
        return render_template("admin_update_item.html",data=data,msg=msg)

    return render_template("admin_update_item.html",data=data)



# admin panel.Add item
@app.route("/upload", methods=["POST", "GET"])
def upload():
        cur = mysql.connection.cursor()
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        now = datetime.now()
        if request.method == 'POST':

            files = request.files.getlist('files[]')
            # print(files)
            for file in files:
                if file and allowed_file(file.filename):
                    name = request.form['name']
                    price = request.form['price']
                    includes = request.form['includes']
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    cur.execute("INSERT INTO items (name,price,include,file_name,uploaded_on) VALUES (%s,%s,%s,%s,%s)", [name,price,includes,filename,now])
                    mysql.connection.commit()
                print(file)
            cur.close()
        return redirect('/admin/manage_items_list')





@app.route('/admin/inbox')
def inbox():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("select * from inbox")
    data = cursor.fetchall()
    return render_template("admin_inbox.html",data=data)



@app.route('/admin/inbox/delete/<int:id>')
def inbox_delete(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM inbox WHERE inbox_id = %s", (id,))
    mysql.connection.commit()
    return redirect('/admin/inbox')




@app.route('/admin/inbox/reply',methods = ["POST"])
def inbox_reply():
    msg = ''
    if request.method == "POST":
        _email = request.form['email']
        _subject = request.form['subject']
        _message = request.form['textbox']

        message = Message(_subject, sender="kapilabakers123@gmail.com", recipients=[_email])
        message.body = _message
        mail.send(message)

        return redirect('/admin/inbox')

    return render_template("admin_inbox.html")


if __name__ == "__main__":
    app.run(debug=True)