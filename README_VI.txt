HUONG DAN UPLOAD LAI WEBSITE QUAN LY HOC VIEN CCCD

1. Giai nen file ZIP nay tren may tinh.
2. Tao GitHub repository moi, dat Private.
3. Upload CAC FILE BEN TRONG thu muc cccd_hoc_vien_moi len goc repository. Khong upload ca thu muc long ben ngoai.
   O goc repository phai thay app.py, requirements.txt, render.yaml, templates/ va static/.
4. Tren Render, tao Web Service moi tu repository moi (khuyen nghi de giu service cu cho den khi service moi chay tot).
5. Neu Render hoi cac lenh:
   Build Command: apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-vie && pip install -r requirements.txt
   Start Command: gunicorn app:app
6. Trong Environment, them ADMIN_PASSWORD va dat mat khau rieng cua ban. SECRET_KEY co the tao gia tri ngau nhien rieng.
7. Neu tao Web Service tu render.yaml, kiem tra disk /var/data duoc tao va gan thanh cong. DB_PATH can la /var/data/students.db de luu du lieu ben vung.
8. Deploy va mo URL website. Dang nhap bang mat khau ADMIN_PASSWORD.

LUU Y:
- Khong dua anh CCCD that len repository GitHub.
- Day la thong tin ca nhan nhay cam; su dung repository Private, mat khau manh va gioi han nguoi co quyen truy cap.
- Neu service cu da co du lieu, du lieu khong tu dong chuyen sang service moi. Khong xoa service/disk cu cho den khi xac nhan du lieu da duoc sao luu.
- OCR co the doc sai. Luon kiem tra ho ten, ngay sinh va so CCCD truoc khi luu.
