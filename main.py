# main.py (demo offline)
import os, csv, hashlib, random, time
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd

# ---------- CONFIG ----------
DATA_DIR = "data"
OUTPUT_DIR = "output"
TEMPLATES_PHISH = os.path.join(DATA_DIR, "templates_phishing.csv")
TEMPLATES_HAM = os.path.join(DATA_DIR, "templates_ham.csv")
# For demo offline we DO NOT call any external LLM
# ----------------------------

app = FastAPI(title="Phish Dataset Generator (Demo Offline)")
app.mount("/static", StaticFiles(directory="static"), name="static")

# utils
HOMO = {'o':'0','a':'@','e':'3','i':'1','s':'$','l':'1','c':'('}

def homoglyph(text, p=0.12):
    if not text:
        return text
    out=[]
    for ch in text:
        if ch.lower() in HOMO and random.random() < p:
            out.append(HOMO[ch.lower()])
        else:
            out.append(ch)
    return ''.join(out)

def make_shortener(url):
    h = hashlib.md5(url.encode('utf-8')).hexdigest()[:6]
    return f"http://bit.ly/{h}"

def insert_url(body, url):
    if not body:
        return url
    if "[URL]" in body:
        return body.replace("[URL]", url)
    return body + "\n\n" + url

def read_templates(path):
    if not os.path.exists(path):
        return []
    df = pd.read_csv(path, dtype=str).fillna('')
    return df.to_dict(orient='records')

def write_csv(rows, path):
    if not rows:
        return
    keys = list(rows[0].keys())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def generate_variants_from_templates(templates, mult=10):
    out=[]
    # start ids to avoid collision
    cur_id = int(time.time()) % 1000000  # simple unique-ish start
    for t in templates:
        for i in range(mult):
            subj = homoglyph(t.get('subject',''), p=0.12)
            body = homoglyph(t.get('body',''), p=0.12)
            base_url = t.get('urls') or "http://example.com"
            url = make_shortener(base_url) if random.random() < 0.5 else base_url
            body = insert_url(body, url)
            row = dict(t)  # shallow copy
            row.update({
                "id": cur_id,
                "subject": subj,
                "body": body,
                "urls": url,
                "source": row.get("source","manual_template") if row.get("source") else "manual_template"
            })
            out.append(row)
            cur_id += 1
    return out

def merge_and_write(phish_rows, ham_rows, output_prefix="dataset_generated"):
    # Normalize columns (union of keys)
    all_rows = phish_rows + ham_rows
    if not all_rows:
        return None
    # ensure consistent field order
    keys = list(all_rows[0].keys())
    # fill missing keys for all rows
    for r in all_rows:
        for k in keys:
            if k not in r:
                r[k] = ""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{output_prefix}.csv")
    write_csv(all_rows, out_path)
    return out_path

# endpoints
@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse("static/index.html")

@app.post("/generate")
async def generate(req: Request):
    body = await req.json()
    mult = int(body.get("mult", 10))
    # demo offline ignores LLM options
    # read templates
    templates_phish = read_templates(TEMPLATES_PHISH)
    templates_ham = read_templates(TEMPLATES_HAM)

    if not templates_phish:
        return JSONResponse({"ok": False, "error": f"No phishing templates found at {TEMPLATES_PHISH}"}, status_code=400)
    if not templates_ham:
        # allow ham missing but warn
        templates_ham = []

    # produce variants
    phish_variants = generate_variants_from_templates(templates_phish, mult=mult)
    # For ham we simply copy ham templates (optionally could augment similarly)
    ham_rows = templates_ham.copy()

    # merge and write
    timestamp = int(time.time())
    prefix = f"dataset_{timestamp}"
    out_csv = merge_and_write(phish_variants, ham_rows, output_prefix=prefix)

    result = {
        "ok": True,
        "num_phishing_generated": len(phish_variants),
        "num_ham_source": len(ham_rows),
        "output_csv": out_csv
    }
    return JSONResponse(result)

@app.get("/download/{fname}")
async def download_file(fname: str):
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path):
        return FileResponse(path, filename=fname)
    return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)

# run uvicorn externally: uvicorn main:app --reload --port 8000
