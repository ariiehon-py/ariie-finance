from flask import Flask, render_template, request, redirect, url_for, make_response
import sqlite3
from datetime import datetime
import csv
import io

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('keuangan.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tanggal TEXT, jenis TEXT, kategori TEXT, 
                  metode TEXT, sub_metode TEXT, nominal INTEGER, 
                  keterangan TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('keuangan.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transaksi ORDER BY id DESC")
    data = c.fetchall()
    
    dashboard = {
        'Cash': 0, 'Seabank': 0, 'Bank Lain': 0,
        'ShopeePay': 0, 'Gopay': 0, 'Grab': 0, 'E-Wallet Lain': 0
    }

    # Untuk menyimpan data yang dikelompokkan per bulan
    riwayat_per_bulan = {}
    bulan_indo = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', 
                  '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', 
                  '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}

    for row in data:
        jenis, sub, nominal = row[2], row[5], row[6]
        
        # Hitung dashboard
        if jenis == 'Pemasukan':
            if sub in dashboard: dashboard[sub] += nominal
        elif jenis == 'Pengeluaran':
            if sub in dashboard: dashboard[sub] -= nominal

        # Kelompokkan per bulan untuk riwayat
        tanggal_str = row[1] # "2026-05-01 18:30"
        raw_bulan = tanggal_str[:7] # "2026-05"
        
        if raw_bulan not in riwayat_per_bulan:
            tahun, bulan = raw_bulan.split('-')
            nama_bulan = f"{bulan_indo.get(bulan)} {tahun}"
            riwayat_per_bulan[raw_bulan] = {'nama_bulan': nama_bulan, 'transaksi': []}
            
        riwayat_per_bulan[raw_bulan]['transaksi'].append(row)

    total_saldo = sum(dashboard.values())
    conn.close()
    
    return render_template('index.html', riwayat_per_bulan=riwayat_per_bulan, dashboard=dashboard, total=total_saldo)

@app.route('/tambah', methods=['POST'])
def tambah():
    jenis = request.form['jenis']
    kategori = request.form['kategori']
    metode = request.form['metode']
    sub_metode = request.form.get('sub_metode', metode)
    
    nominal_raw = request.form['nominal']
    nominal_bersih = nominal_raw.replace('.', '') 
    nominal = int(nominal_bersih)

    keterangan = request.form['keterangan']
    tanggal = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('keuangan.db')
    c = conn.cursor()
    c.execute("INSERT INTO transaksi (tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Route baru untuk export Excel (CSV)
@app.route('/export/<raw_bulan>')
def export_excel(raw_bulan):
    conn = sqlite3.connect('keuangan.db')
    c = conn.cursor()
    # Ambil data hanya yang bulannya cocok
    c.execute("SELECT tanggal, jenis, kategori, metode, sub_metode, nominal, keterangan FROM transaksi WHERE tanggal LIKE ? ORDER BY id DESC", (f"{raw_bulan}%",))
    data = c.fetchall()
    conn.close()

    # Bikin format CSV
    si = io.StringIO()
    # Pake delimiter titik koma (;) supaya Excel region Indonesia rapi masuk per kolom
    cw = csv.writer(si, delimiter=';') 
    cw.writerow(['Waktu', 'Jenis', 'Kategori', 'Metode Utama', 'Penyimpanan', 'Nominal (Rp)', 'Keterangan'])
    cw.writerows(data)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=Catatan_Keuangan_Nada_{raw_bulan}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)