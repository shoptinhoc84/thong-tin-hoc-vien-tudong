import os, re, sqlite3, tempfile, subprocess
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
DB_PATH = os.environ.get("DB_PATH", "students.db")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            gender TEXT DEFAULT '',
            dob TEXT DEFAULT '',
            cccd TEXT UNIQUE,
            course TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )""")

@app.before_request
def require_login():
    if request.endpoint in ("login", "static"):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Set ADMIN_PASSWORD in Render environment variables before deployment.
        if ADMIN_PASSWORD and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Mật khẩu không đúng. Hãy kiểm tra ADMIN_PASSWORD trên Render.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    with db() as conn:
        if q:
            rows = conn.execute("""SELECT * FROM students
                WHERE full_name LIKE ? OR cccd LIKE ? OR course LIKE ?
                ORDER BY id DESC""", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template("index.html", students=rows, q=q, today=datetime.now().strftime("%Y-%m-%d"))

@app.route("/save", methods=["POST"])
def save():
    sid = request.form.get("id", "").strip()
    name = request.form.get("full_name", "").strip()
    gender = request.form.get("gender", "").strip()
    dob = request.form.get("dob", "").strip()
    cccd = re.sub(r"\D", "", request.form.get("cccd", ""))
    course = request.form.get("course", "").strip()

    if not name:
        flash("Vui lòng nhập họ và tên.", "error")
        return redirect(url_for("index"))
    if cccd and len(cccd) != 12:
        flash("Số CCCD thường gồm 12 chữ số. Vui lòng kiểm tra lại.", "error")
        return redirect(url_for("index"))
    try:
        with db() as conn:
            if sid:
                conn.execute("""UPDATE students SET full_name=?, gender=?, dob=?, cccd=?, course=?
                                WHERE id=?""", (name, gender, dob, cccd or None, course, sid))
                flash("Đã cập nhật học viên.", "success")
            else:
                conn.execute("""INSERT INTO students(full_name,gender,dob,cccd,course,created_at)
                                VALUES(?,?,?,?,?,?)""",
                             (name, gender, dob, cccd or None, course, datetime.now().isoformat(timespec="seconds")))
                flash("Đã lưu học viên.", "success")
    except sqlite3.IntegrityError:
        flash("Số CCCD này đã tồn tại trong danh sách.", "error")
    return redirect(url_for("index"))

@app.route("/delete/<int:sid>", methods=["POST"])
def delete(sid):
    with db() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (sid,))
    flash("Đã xóa học viên.", "success")
    return redirect(url_for("index"))

def parse_ocr(text):
    lines = [re.sub(r"\s+", " ", x).strip(" :.-") for x in text.splitlines()]
    lines = [x for x in lines if x]
    joined = "\n".join(lines)
    data = {"full_name": "", "gender": "", "dob": "", "cccd": ""}
    # Prefer a 12-digit candidate, commonly the citizen ID number.
    m = re.search(r"(?<!\d)(\d(?:[\s.-]*\d){11})(?!\d)", joined)
    if m:
        data["cccd"] = re.sub(r"\D", "", m.group(1))
    # Date candidates: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    dates = re.findall(r"\b(0?[1-9]|[12]\d|3[01])[\s./-](0?[1-9]|1[0-2])[\s./-]((?:19|20)\d{2})\b", joined)
    if dates:
        d, mo, y = dates[0]
        data["dob"] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    for i, line in enumerate(lines):
        low = line.lower()
        if "giới tính" in low or "sex" in low:
            if re.search(r"\b(nam|male|m)\b", low): data["gender"] = "Nam"
            elif re.search(r"\b(nữ|nu|female|f)\b", low): data["gender"] = "Nữ"
        # Name usually appears after the "Họ và tên / Full name" label.
        if "họ và tên" in low or "full name" in low:
            candidate = re.sub(r"(?i).*?(họ và tên|full name)\s*:?\s*", "", line).strip()
            if candidate and not re.search(r"\d", candidate):
                data["full_name"] = candidate.upper()
            elif i + 1 < len(lines) and not re.search(r"\d", lines[i+1]):
                data["full_name"] = lines[i+1].upper()
    # Fallback: find a likely uppercase Vietnamese name near the beginning.
    if not data["full_name"]:
        skip = ("CĂN CƯỚC", "CITIZEN", "IDENTITY", "SOCIALIST", "VIỆT NAM", "VIET NAM",
                "ĐỘC LẬP", "HẠNH PHÚC", "SỐ", "NO.", "DATE", "SINH", "QUÊ", "NƠI")
        for line in lines[:12]:
            clean = re.sub(r"[^A-Za-zÀ-ỹĐđ\s]", "", line).strip()
            words = clean.split()
            if 2 <= len(words) <= 5 and all(len(w) > 1 for w in words) and clean.upper() == clean and not any(s in clean for s in skip):
                data["full_name"] = clean
                break
    return data, joined

@app.route("/ocr", methods=["POST"])
def ocr():
    f = request.files.get("cccd_image")
    if not f or not f.filename:
        flash("Vui lòng chọn ảnh CCCD.", "error")
        return redirect(url_for("index"))
    if "." not in f.filename or f.filename.rsplit(".", 1)[1].lower() not in ALLOWED_EXTENSIONS:
        flash("Chỉ nhận ảnh JPG, PNG hoặc WEBP.", "error")
        return redirect(url_for("index"))
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".img") as tmp:
            temp_path = tmp.name
            f.save(temp_path)
        with Image.open(temp_path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.grayscale(im)
            im = ImageOps.autocontrast(im)
            im = ImageEnhance.Contrast(im).enhance(1.5)
            im = im.resize((im.width * 2, im.height * 2))
            # Vietnamese + English OCR; installed by render.yaml.
            text = pytesseract.image_to_string(im, lang="vie+eng", config="--psm 6")
        data, raw = parse_ocr(text)
        session["ocr_data"] = data
        session["ocr_text"] = raw[:3000]
        flash("Đã đọc ảnh. Vui lòng kiểm tra các trường trước khi lưu; OCR có thể đọc sai.", "success")
    except Exception as e:
        flash("Không đọc được ảnh. Kiểm tra định dạng ảnh hoặc cấu hình Tesseract trên máy chủ.", "error")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    return redirect(url_for("index", ocr="1"))

@app.route("/export")
def export():
    with db() as conn:
        df = pd.read_sql_query("SELECT full_name AS 'Họ và tên', gender AS 'Giới tính', dob AS 'Ngày sinh', cccd AS 'Số CCCD', course AS 'Khóa học' FROM students ORDER BY id DESC", conn)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Hoc vien")
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="danh_sach_hoc_vien.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.context_processor
def inject_ocr():
    data = session.pop("ocr_data", None)
    raw = session.pop("ocr_text", "")
    return {"ocr_data": data, "ocr_text": raw}

init_db()
if not ADMIN_PASSWORD:
    print("WARNING: Set ADMIN_PASSWORD in Render environment variables to enable login.")
