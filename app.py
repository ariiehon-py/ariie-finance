from flask import Flask, render_template, request, redirect, url_for, make_response, session
import psycopg2
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)

# Ini wajib ada biar Flask bisa nginget kalau kamu udah login
app.secret_key = 'kunci_rahasia_bikin_sendiri_bebas'

# Password webnya ngambil dari Render, kalau ngetes di laptop pake 'nadaganteng123'
PASSWORD_WEB = os.environ.get('PASSWORD_WEB', '985765')

# Pastikan ini pakai link Supabase aslimu!
DB_URL = "postgresql://postgres.esmilibxjaaamrabzsos:6y4l4emjtUWtFrTm@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres" # GANTI DENGAN URL ASLI SAAT DEPLOY

def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                 (id SERIAL PRIMARY KEY,
                  tanggal TEXT, jenis TEXT, kategori TEXT, 
                  metode TEXT, sub_metode TEXT, nominal INTEGER, 
                  keterangan TEXT)''')
    conn.commit()
    c.close()
    conn.close()

# --- HALAMAN LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password_input = request.form['password']
        if password_input == PASSWORD_WEB:
            session['logged_in'] = True 
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Password salah, woi!")
    return render_template('login.html', error="")

# --- HALAMAN LOGOUT ---
@app.route('/logout')
def logout():
    session.pop('logged_in', None) 
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transaksi ORDER BY id DESC")
    data = c.fetchall()
    
    dashboard = {
        'Cash': 0, 'Seabank': 0, 'Bank Lain': 0,
        'ShopeePay': 0, 'Gopay': 0, 'Grab': 0, 'E-Wallet Lain': 0
    }

    riwayat_per_bulan = {}
    bulan_indo = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', 
                  '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', 
                  '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}

    for row in data:
        jenis, sub, nominal = row[2], row[5], row[6]
        if jenis == 'Pemasukan':
            if sub in dashboard: dashboard[sub] += nominal
        elif jenis == 'Pengeluaran':
            if sub in dashboard: dashboard[sub] -= nominal

        tanggal_str = row[1]
        raw_bulan = tanggal_str[:7]
        if raw_bulan not in riwayat_per_bulan:
            tahun, bulan = raw_bulan.split('-')
            nama_bulan = f"{bulan_indo.get(bulan)} {tahun}"
            riwayat_per_bulan[raw_bulan] = {'nama_bulan': nama_bulan, 'transaksi': []}
        riwayat_per_bulan[raw_bulan]['transaksi'].append(row)

    total_saldo = sum(dashboard.values())
    c.close()
    conn.close()
    return render_template('index.html', riwayat_per_bulan=riwayat_per_bulan, dashboard=dashboard, total=total_saldo)

@app.route('/tambah', methods=['POST'])
def tambah():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    jenis = request.form['jenis']
    kategori = request.form['kategori']
    metode = request.form['metode']
    sub_metode = request.form.get('sub_metode', metode)
    nominal = int(request.form['nominal'].replace('.', ''))
    keterangan = request.form['keterangan']
    tanggal = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO transaksi (tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan) VALUES (%s, %s, %s, %s, %s, %s, %s)",
              (tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan))
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('index'))

# --- FITUR HAPUS ---
@app.route('/hapus/<int:id_transaksi>')
def hapus(id_transaksi):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transaksi WHERE id = %s", (id_transaksi,))
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('index'))

# --- FITUR EDIT ---
@app.route('/edit/<int:id_transaksi>', methods=['POST'])
def edit(id_transaksi):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    jenis = request.form['jenis']
    kategori = request.form['kategori']
    metode = request.form['metode']
    sub_metode = request.form.get('sub_metode', metode)
    nominal = int(request.form['nominal'].replace('.', ''))
    keterangan = request.form['keterangan']
    
    # Kita TIDAK mengubah tanggal asli saat di-edit
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""UPDATE transaksi SET 
                 jenis=%s, kategori=%s, metode=%s, sub_metode=%s, nominal=%s, keterangan=%s 
                 WHERE id=%s""",
              (jenis, kategori, metode, sub_metode, nominal, keterangan, id_transaksi))
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/export/<raw_bulan>')
def export_excel(raw_bulan):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan FROM transaksi WHERE tanggal LIKE %s ORDER BY id DESC", (f"{raw_bulan}%",))
    data = c.fetchall()
    c.close()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Waktu', 'Jenis', 'Kategori', 'Metode Utama', 'Penyimpanan', 'Nominal (Rp)', 'Keterangan'])
    cw.writerows(data)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=Keuangan_Nada_{raw_bulan}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)