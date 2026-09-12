from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, send_file
from functools import wraps
from datetime import datetime
import sqlite3
import os
import shutil
import io
from werkzeug.security import check_password_hash, generate_password_hash

# ============================================
#   NIMORA - Bill System
#   Your Tech Era Begins
# ============================================

BUSINESS_NAME = "Nimora"
TAGLINE = "Your Tech Era Begins"
LOGO_URL = "https://pmd-img2url.koyeb.app/v/4c9f8e0273bc6f3fa9613b011c4d64f0.jpg"
PHONE = "0784280074"
EMAIL = "info@nimora.com"
ADDRESS = "Sri Lanka"
CURRENCY = "Rs."

DB = 'database.db'
BACKUP_DIR = 'backups'

app = Flask(__name__)
app.secret_key = 'nimora-secret-key-2025-change-this'

# ---------- Database Helpers ----------
def get_db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'staff'
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        sku TEXT
    );
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT
    );
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        date TEXT,
        total REAL,
        payment_method TEXT,
        discount REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        product_id INTEGER,
        qty INTEGER,
        price REAL
    );
    ''')
    conn.commit()
    conn.close()

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def create_default_admin():
    conn = get_db()
    existing = conn.execute('SELECT * FROM users WHERE username=?', ('admin',)).fetchone()
    if not existing:
        conn.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)',
                     ('admin', generate_password_hash('admin123'), 'admin'))
        conn.commit()
    conn.close()

# ---------- Branding ----------
@app.context_processor
def inject_branding():
    return {
        'business_name': BUSINESS_NAME,
        'tagline': TAGLINE,
        'logo_url': LOGO_URL,
        'phone': PHONE,
        'email': EMAIL,
        'address': ADDRESS,
        'currency': CURRENCY,
        'now': datetime.now()
    }

# ---------- Login Required ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin only!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrapper

# ---------- Auth ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- Dashboard ----------
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    tp = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    tc = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    ti = conn.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]
    ts = conn.execute('SELECT COALESCE(SUM(total),0) FROM invoices').fetchone()[0]
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = conn.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE date LIKE ?",
                                (today + '%',)).fetchone()[0]
    low_stock = conn.execute('SELECT * FROM products WHERE stock < 5 ORDER BY stock ASC').fetchall()
    recent = conn.execute('''SELECT i.*, c.name as customer_name FROM invoices i
                             LEFT JOIN customers c ON i.customer_id = c.id
                             ORDER BY i.id DESC LIMIT 5''').fetchall()
    conn.close()
    return render_template('dashboard.html', tp=tp, tc=tc, ti=ti, ts=ts,
                           today_sales=today_sales, low_stock=low_stock, recent=recent)

# ---------- Products ----------
@app.route('/products')
@login_required
def products():
    conn = get_db()
    items = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('products.html', products=items)

@app.route('/products/add', methods=['POST'])
@login_required
def add_product():
    conn = get_db()
    conn.execute('INSERT INTO products (name, price, stock, sku) VALUES (?,?,?,?)',
                 (request.form['name'], float(request.form['price']),
                  int(request.form['stock']), request.form.get('sku', '')))
    conn.commit()
    conn.close()
    flash('Product added successfully!', 'success')
    return redirect(url_for('products'))

@app.route('/products/edit/<int:id>', methods=['POST'])
@login_required
def edit_product(id):
    conn = get_db()
    conn.execute('UPDATE products SET name=?, price=?, stock=?, sku=? WHERE id=?',
                 (request.form['name'], float(request.form['price']),
                  int(request.form['stock']), request.form.get('sku', ''), id))
    conn.commit()
    conn.close()
    flash('Product updated!', 'success')
    return redirect(url_for('products'))

@app.route('/products/delete/<int:id>')
@login_required
def delete_product(id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Product deleted!', 'success')
    return redirect(url_for('products'))

# ---------- Customers ----------
@app.route('/customers')
@login_required
def customers():
    conn = get_db()
    items = conn.execute('SELECT * FROM customers ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('customers.html', customers=items)

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    conn = get_db()
    conn.execute('INSERT INTO customers (name, phone, email, address) VALUES (?,?,?,?)',
                 (request.form['name'], request.form['phone'],
                  request.form['email'], request.form['address']))
    conn.commit()
    conn.close()
    flash('Customer added successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/edit/<int:id>', methods=['POST'])
@login_required
def edit_customer(id):
    conn = get_db()
    conn.execute('UPDATE customers SET name=?, phone=?, email=?, address=? WHERE id=?',
                 (request.form['name'], request.form['phone'],
                  request.form['email'], request.form['address'], id))
    conn.commit()
    conn.close()
    flash('Customer updated!', 'success')
    return redirect(url_for('customers'))

@app.route('/customers/delete/<int:id>')
@login_required
def delete_customer(id):
    conn = get_db()
    conn.execute('DELETE FROM customers WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Customer deleted!', 'success')
    return redirect(url_for('customers'))

# ---------- Invoice ----------
@app.route('/invoice/new')
@login_required
def new_invoice():
    conn = get_db()
    products = conn.execute('SELECT * FROM products WHERE stock > 0').fetchall()
    customers = conn.execute('SELECT * FROM customers').fetchall()
    conn.close()
    return render_template('invoice.html', products=products, customers=customers)

@app.route('/invoice/save', methods=['POST'])
@login_required
def save_invoice():
    data = request.get_json()
    items = data['items']
    discount = float(data.get('discount', 0))
    subtotal = sum(i['qty'] * i['price'] for i in items)
    total = subtotal - discount
    date = datetime.now().strftime('%Y-%m-%d %H:%M')

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''INSERT INTO invoices (customer_id, date, total, payment_method, discount)
                   VALUES (?,?,?,?,?)''',
                (data['customer_id'], date, total, data['payment_method'], discount))
    invoice_id = cur.lastrowid

    for item in items:
        cur.execute('INSERT INTO invoice_items (invoice_id, product_id, qty, price) VALUES (?,?,?,?)',
                    (invoice_id, item['product_id'], item['qty'], item['price']))
        cur.execute('UPDATE products SET stock = stock - ? WHERE id=?',
                    (item['qty'], item['product_id']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'invoice_id': invoice_id})

@app.route('/invoice/view/<int:id>')
@login_required
def view_invoice(id):
    conn = get_db()
    invoice = conn.execute('SELECT * FROM invoices WHERE id=?', (id,)).fetchone()
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (invoice['customer_id'],)).fetchone()
    items = conn.execute('''SELECT ii.*, p.name FROM invoice_items ii
                            JOIN products p ON ii.product_id = p.id
                            WHERE ii.invoice_id=?''', (id,)).fetchall()
    conn.close()
    return render_template('invoice_view.html', invoice=invoice, customer=customer, items=items)

@app.route('/invoice/delete/<int:id>')
@login_required
def delete_invoice(id):
    conn = get_db()
    conn.execute('DELETE FROM invoice_items WHERE invoice_id=?', (id,))
    conn.execute('DELETE FROM invoices WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Invoice deleted!', 'success')
    return redirect(url_for('reports'))

# ---------- Reports ----------
@app.route('/reports')
@login_required
def reports():
    conn = get_db()
    invoices = conn.execute('''SELECT i.*, c.name as customer_name FROM invoices i
                               LEFT JOIN customers c ON i.customer_id = c.id
                               ORDER BY i.id DESC''').fetchall()
    total_sales = conn.execute('SELECT COALESCE(SUM(total),0) FROM invoices').fetchone()[0]
    today = datetime.now().strftime('%Y-%m-%d')
    today_sales = conn.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE date LIKE ?",
                                (today + '%',)).fetchone()[0]
    conn.close()
    return render_template('reports.html', invoices=invoices,
                           total_sales=total_sales, today_sales=today_sales)





# ---------- User Management (Settings) ----------
@app.route('/settings')
@login_required
def settings_page():
    conn = get_db()
    users = conn.execute('SELECT id, username, role FROM users ORDER BY id').fetchall()
    conn.close()
    return render_template('settings.html', users=users)

@app.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    old_pass = request.form['old_password']
    new_pass = request.form['new_password']
    confirm_pass = request.form['confirm_password']

    if new_pass != confirm_pass:
        flash('New passwords do not match!', 'error')
        return redirect(url_for('settings_page'))

    if len(new_pass) < 4:
        flash('Password must be at least 4 characters!', 'error')
        return redirect(url_for('settings_page'))

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    if not check_password_hash(user['password'], old_pass):
        conn.close()
        flash('Current password is wrong!', 'error')
        return redirect(url_for('settings_page'))

    conn.execute('UPDATE users SET password=? WHERE id=?',
                 (generate_password_hash(new_pass), session['user_id']))
    conn.commit()
    conn.close()
    flash('✅ Password changed successfully!', 'success')
    return redirect(url_for('settings_page'))

@app.route('/settings/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form['new_username'].strip()
    if len(new_username) < 3:
        flash('Username must be at least 3 characters!', 'error')
        return redirect(url_for('settings_page'))

    conn = get_db()
    existing = conn.execute('SELECT * FROM users WHERE username=? AND id!=?',
                            (new_username, session['user_id'])).fetchone()
    if existing:
        conn.close()
        flash('Username already taken!', 'error')
        return redirect(url_for('settings_page'))

    conn.execute('UPDATE users SET username=? WHERE id=?',
                 (new_username, session['user_id']))
    conn.commit()
    conn.close()
    session['username'] = new_username
    flash('✅ Username changed successfully!', 'success')
    return redirect(url_for('settings_page'))

@app.route('/settings/add-user', methods=['POST'])
@login_required
def add_user():
    if session.get('role') != 'admin':
        flash('Only admin can add users!', 'error')
        return redirect(url_for('settings_page'))

    username = request.form['username'].strip()
    password = request.form['password']
    role = request.form.get('role', 'staff')

    if len(username) < 3 or len(password) < 4:
        flash('Username (3+) and password (4+) required!', 'error')
        return redirect(url_for('settings_page'))

    conn = get_db()
    existing = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if existing:
        conn.close()
        flash('Username already exists!', 'error')
        return redirect(url_for('settings_page'))

    conn.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)',
                 (username, generate_password_hash(password), role))
    conn.commit()
    conn.close()
    flash(f'✅ User "{username}" added!', 'success')
    return redirect(url_for('settings_page'))

@app.route('/settings/delete-user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if session.get('role') != 'admin':
        flash('Only admin can delete users!', 'error')
        return redirect(url_for('settings_page'))

    if id == session['user_id']:
        flash('You cannot delete yourself!', 'error')
        return redirect(url_for('settings_page'))

    conn = get_db()
    conn.execute('DELETE FROM users WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('✅ User deleted!', 'success')
    return redirect(url_for('settings_page'))

@app.route('/settings/reset-user-password/<int:id>', methods=['POST'])
@login_required
def reset_user_password(id):
    if session.get('role') != 'admin':
        flash('Only admin can reset passwords!', 'error')
        return redirect(url_for('settings_page'))

    new_pass = request.form['new_password']
    if len(new_pass) < 4:
        flash('Password must be at least 4 characters!', 'error')
        return redirect(url_for('settings_page'))

    conn = get_db()
    conn.execute('UPDATE users SET password=? WHERE id=?',
                 (generate_password_hash(new_pass), id))
    conn.commit()
    conn.close()
    flash('✅ Password reset successfully!', 'success')
    return redirect(url_for('settings_page'))





# ---------- Reset ----------
@app.route('/reset')
@login_required
@admin_required
def reset_page():
    conn = get_db()
    counts = {
        'products': conn.execute('SELECT COUNT(*) FROM products').fetchone()[0],
        'customers': conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
        'invoices': conn.execute('SELECT COUNT(*) FROM invoices').fetchone()[0],
        'invoice_items': conn.execute('SELECT COUNT(*) FROM invoice_items').fetchone()[0],
    }
    conn.close()
    backups = sorted(os.listdir(BACKUP_DIR), reverse=True) if os.path.exists(BACKUP_DIR) else []
    return render_template('reset.html', counts=counts, backups=backups)

@app.route('/reset/products', methods=['POST'])
@login_required
@admin_required
def reset_products():
    conn = get_db()
    conn.execute('DELETE FROM products')
    conn.commit()
    conn.close()
    flash('All products deleted!', 'success')
    return redirect(url_for('reset_page'))

@app.route('/reset/customers', methods=['POST'])
@login_required
@admin_required
def reset_customers():
    conn = get_db()
    conn.execute('DELETE FROM customers')
    conn.commit()
    conn.close()
    flash('All customers deleted!', 'success')
    return redirect(url_for('reset_page'))

@app.route('/reset/invoices', methods=['POST'])
@login_required
@admin_required
def reset_invoices():
    conn = get_db()
    conn.execute('DELETE FROM invoice_items')
    conn.execute('DELETE FROM invoices')
    conn.commit()
    conn.close()
    flash('All invoices deleted!', 'success')
    return redirect(url_for('reset_page'))

@app.route('/reset/all', methods=['POST'])
@login_required
@admin_required
def reset_all():
    conn = get_db()
    conn.execute('DELETE FROM invoice_items')
    conn.execute('DELETE FROM invoices')
    conn.execute('DELETE FROM customers')
    conn.execute('DELETE FROM products')
    conn.commit()
    conn.close()
    flash('All data cleared! Fresh start.', 'success')
    return redirect(url_for('dashboard'))

# ---------- Backup ----------
@app.route('/backup/create')
@login_required
@admin_required
def backup_create():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'nimora_backup_{timestamp}.db'
    filepath = os.path.join(BACKUP_DIR, filename)
    shutil.copy(DB, filepath)
    flash(f'Backup created: {filename}', 'success')
    return redirect(url_for('reset_page'))

@app.route('/backup/download/<filename>')
@login_required
@admin_required
def backup_download(filename):
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    flash('Backup not found!', 'error')
    return redirect(url_for('reset_page'))

@app.route('/backup/delete/<filename>', methods=['POST'])
@login_required
@admin_required
def backup_delete(filename):
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash('Backup deleted!', 'success')
    return redirect(url_for('reset_page'))

# ---------- Run ----------
if __name__ == '__main__':
    init_db()
    create_default_admin()
    print("\n" + "="*50)
    print("  NIMORA - Bill System")
    print("  Your Tech Era Begins")
    print("="*50)
    print("  Open: http://localhost:5000")
    print("  Login: admin / admin123")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
