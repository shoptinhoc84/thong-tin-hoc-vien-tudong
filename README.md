# Hướng dẫn chạy và triển khai Render

## 1. Kiểm tra trên máy cục bộ (Local)
- Cài đặt thư viện: `pip install -r requirements.txt`
- Khởi chạy web: `python app.py`
- Mở trình duyệt vào địa chỉ: `http://localhost:5000`
- Tài khoản: **admin** | Mật khẩu: **123456**

## 2. Đưa lên Render
- Giải nén thư mục này và tải (push) toàn bộ nội dung lên 1 GitHub repository.
- Vào Render (dashboard.render.com), chọn **New +** -> **Web Service**.
- Chọn repository vừa tạo.
- Điền:
  - **Runtime**: Python 3
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn app:app`
- Nhấn **Deploy Web Service** là xong!
