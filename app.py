import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bi-mat-cccd-123")

def get_db_connection():
    conn = sqlite3.connect("students.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hoc_vien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ho_ten TEXT NOT NULL,
            so_cccd TEXT UNIQUE NOT NULL,
            ngay_sinh TEXT,
            que_quan TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/login", methods=["GET", "POST"])
def login():
    loi = None
    if request.method == "POST":
        tk = request.form.get("username")
        mk = request.form.get("password")
        if tk == "admin" and mk == "123456":
            session["user"] = tk
            return redirect(url_for("index"))
        else:
            loi = "Tài khoản hoặc mật khẩu không chính xác!"
    return render_template("login.html", loi=loi)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    thong_bao = None
    loi = None
    conn = get_db_connection()

    if request.method == "POST":
        ten = request.form.get("ho_ten", "").strip()
        cccd = request.form.get("so_cccd", "").strip()
        sinh = request.form.get("ngay_sinh", "").strip()
        que = request.form.get("que_quan", "").strip()

        if ten and cccd:
            try:
                conn.execute(
                    "INSERT INTO hoc_vien (ho_ten, so_cccd, ngay_sinh, que_quan) VALUES (?, ?, ?, ?)",
                    (ten, cccd, sinh, que)
                )
                conn.commit()
                thong_bao = "Thêm học viên thành công!"
            except sqlite3.IntegrityError:
                loi = "Lỗi: Số CCCD này đã tồn tại trên hệ thống!"
        else:
            loi = "Vui lòng nhập đầy đủ họ tên và số CCCD!"

    hoc_vien_list = conn.execute("SELECT ho_ten, so_cccd, ngay_sinh, que_quan FROM hoc_vien ORDER BY id DESC").fetchall()
    conn.close()

    return render_template("index.html", danh_sach=hoc_vien_list, thong_bao=thong_bao, loi=loi)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
