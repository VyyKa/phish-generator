# Phish Dataset Generator (Demo Offline)

**Mục đích:** công cụ local đơn giản để *tạo bộ dữ liệu email phishing tiếng Việt* từ templates + augmentation (homoglyph, shortener). Phù hợp để làm prototype cho đồ án, thử nghiệm baseline, và sinh dữ liệu để fine-tune mô hình.

> Phiên bản demo này **KHÔNG** gọi LLM bên ngoài. Có phần hướng dẫn để bật LLM sau nếu muốn.

---

## Cấu trúc repo

```
phish-generator/
├─ data/
│  ├─ templates_phishing.csv    # templates phishing (mẫu)
│  └─ templates_ham.csv         # mẫu ham/legit
├─ static/
│  └─ index.html                # UI đơn giản
├─ output/                      # (auto tạo) nơi lưu dataset tạo ra
├─ main.py                      # FastAPI backend (generate)
├─ requirements.txt
└─ README.md                    # (file này)
```

---

## Yêu cầu

* Python 3.8+ (khuyến nghị 3.10+)
* pip
* (tuỳ chọn) virtualenv

---

## Cài đặt (1 lần)

Mở terminal và chuyển tới thư mục dự án rồi chạy:

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu bạn không dùng virtualenv, có thể `pip install --user -r requirements.txt`.

---

## Chạy server

Trong thư mục dự án (sau khi active venv):

```bash
uvicorn main:app --reload --port 8000
```

Mở trình duyệt: `http://127.0.0.1:8000/` để truy cập giao diện.

---

## Sử dụng giao diện (UI)

1. Nhập **Số biến thể (mult)** — số biến thể (augmentation multiplier) cho mỗi template (ví dụ 10).
2. (Phiên bản demo offline) Bỏ qua tùy chọn LLM.
3. Bấm **Generate**.
4. UI sẽ trả JSON nhỏ trong ô Nhật ký chứa tên file output, ví dụ:

```json
{
  "ok": true,
  "num_phishing_generated": 50,
  "num_ham_source": 3,
  "output_csv": "output/dataset_1759336377.csv"
}
```

5. File CSV được lưu trong thư mục `output/`.

---

## Gọi API trực tiếp (curl)

Không cần UI, bạn có thể gọi API `/generate`:

```bash
curl -X POST "http://127.0.0.1:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"mult":10, "use_llm": false, "llm_count": 0}'
```

Kết quả JSON tương tự (với `output_csv`).

Tải file CSV:

```
http://127.0.0.1:8000/download/<tên_file.csv>
```

---

## Xem nhanh nội dung output

Trong Windows PowerShell:

```powershell
Get-Content .\output\dataset_1759336377.csv -TotalCount 20
```

Hoặc dùng Python:

```python
import pandas as pd
df = pd.read_csv("output/dataset_1759336377.csv", encoding="utf-8")
print(df.head(10))
```

---

## Tách Train / Val / Test (script mẫu)

Tạo file `split_dataset.py` với nội dung:

```python
import pandas as pd
df = pd.read_csv("output/dataset_1759336377.csv", encoding="utf-8")
train = df.sample(frac=0.8, random_state=42)
rest = df.drop(train.index)
val = rest.sample(frac=0.5, random_state=42)
test = rest.drop(val.index)
train.to_csv("output/train.csv", index=False)
val.to_csv("output/val.csv", index=False)
test.to_csv("output/test.csv", index=False)
print("Wrote train/val/test to output/")
```

Chạy:

```bash
python split_dataset.py
```

---

## Lưu ý encoding (UTF-8)

* CSV phải **UTF-8**. Nếu gặp lỗi `UnicodeDecodeError` khi server đọc CSV, hãy đảm bảo file `data/templates_phishing.csv` và `data/templates_ham.csv` được lưu bằng UTF-8 (không BOM).
* Nếu cần nhanh, mở file bằng VSCode → `Save with Encoding` → `UTF-8`.
* Hoặc dùng PowerShell (từ thư mục `data`):

```powershell
Get-Content .\templates_phishing.csv | Set-Content -Encoding UTF8 .\templates_phishing_utf8.csv
Remove-Item .\templates_phishing.csv
Rename-Item .\templates_phishing_utf8.csv templates_phishing.csv
```

---

## Cách hoạt động tóm tắt

* Đọc `data/templates_phishing.csv` và `data/templates_ham.csv`.
* Tạo `mult` biến thể cho mỗi template phishing bằng:

  * Homoglyph substitution (ví dụ `o -> 0`),
  * Tạo shortener giả (bit.ly hash),
  * Chèn URL vào body.
* Gộp ham mẫu (không augment trong demo offline).
* Xuất file CSV vào `output/`.

---

## Mở rộng (nên làm)

### 1) Bật LLM (sinh thêm mẫu bằng mô hình lớn)

* Cài `openai` hoặc dùng requests với endpoint tương thích.
* Thiết lập `OPENAI_API_KEY` làm biến môi trường:

  * macOS / Linux:

    ```bash
    export OPENAI_API_KEY="sk-..."
    ```
  * Windows PowerShell:

    ```powershell
    $env:OPENAI_API_KEY="sk-..."
    ```
* Sửa hoặc bật phần gọi LLM trong `main.py` để gửi prompt và parse CSV output.

> Lưu ý: gửi dữ liệu ra bên ngoài có thể gây privacy concerns. Không gửi PII thật.

### 2) Tăng augmentation

* Viết `augmentation_script.py` tách riêng để làm nhiều biến thể hơn (back-translation, base64 href, punycode...). Mình có thể cung cấp script nếu cần.

### 3) Thêm preview UI

* Hiển thị 10 dòng đầu file ngay trên trang sau khi generate để dễ kiểm tra.

---

## Troubleshooting (một số lỗi thường gặp)

* **`UnicodeDecodeError` khi đọc CSV** → fix encoding (xem mục Encoding).
* **`No phishing templates found`** → kiểm tra file `data/templates_phishing.csv` tồn tại và có header đúng.
* **Port 8000 đã dùng** → chạy `uvicorn main:app --port 8080` hoặc kill tiến trình đang dùng port.
* **Error 500 khi POST /generate** → xem log terminal để biết stacktrace; thường do file CSV corrupt hoặc header bị lẫn ký tự đặc biệt.

---

## Bảo mật & đạo đức

* Không lưu PII (số thẻ, CMND, OTP). Nếu sử dụng email thật, *anonymize* hoặc có consent.
* Không chèn hay phân phối file mã độc; attachments trong dataset chỉ ghi metadata (tên, extension).

