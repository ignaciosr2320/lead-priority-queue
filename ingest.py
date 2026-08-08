"""Watcher automático: toma el único archivo de datos que aparezca en esta
carpeta (.csv o .xlsx), lo convierte a leads.csv, regenera index.html,
y hace commit + push a GitHub. Disparado por el LaunchAgent
com.leadqueue.watcher, no está pensado para correrse a mano (aunque
`python3 ingest.py` funciona igual para pruebas).
"""
import csv
import fcntl
import glob
import os
import subprocess
import sys
import time
from datetime import datetime

REPO = os.path.dirname(os.path.abspath(__file__))
LEADS_CSV = os.path.join(REPO, "leads.csv")
ARCHIVE_DIR = os.path.join(REPO, "procesados")
LOG_FILE = os.path.join(REPO, "ingest.log")
LOCK_FILE = os.path.join(REPO, ".ingest.lock")

KNOWN_FILES = {
    "leads.csv", "index.html", "template.html", "build.py", "ingest.py",
    "README.md", ".gitignore", "ingest.log", "run_ingest.sh",
}

sys.path.insert(0, REPO)


def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(*args, check=True):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=check)


def find_candidate():
    candidates = []
    for path in glob.glob(os.path.join(REPO, "*")):
        name = os.path.basename(path)
        if name in KNOWN_FILES or name.startswith(".") or name.startswith("~$"):
            continue
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in (".csv", ".xlsx", ".xls"):
            candidates.append(path)
    if not candidates:
        return None
    if len(candidates) > 1:
        candidates.sort(key=os.path.getmtime, reverse=True)
        log(f"AVISO: había {len(candidates)} archivos nuevos, uso el más reciente: {os.path.basename(candidates[0])}")
    return candidates[0]


def wait_until_stable(path, checks=3, interval=1.5):
    """Evita leer un archivo a medio copiar/guardar."""
    last_size = -1
    stable_count = 0
    for _ in range(20):
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            return False
        if size == last_size and size > 0:
            stable_count += 1
            if stable_count >= checks:
                return True
        else:
            stable_count = 0
        last_size = size
        time.sleep(interval)
    return False


def xlsx_to_csv_rows(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    # ojo: no usar .strip() acá — el export en CSV trae columnas con
    # espacio final ("...actualización ") y build.py busca esas claves
    # exactas; si las recortamos, el xlsx deja de matchear con el CSV.
    header = [str(h) if h is not None else "" for h in next(rows_iter)]
    rows = []
    for raw in rows_iter:
        if all(v is None for v in raw):
            continue
        row = {header[i]: ("" if raw[i] is None else str(raw[i])) for i in range(len(header))}
        rows.append(row)
    return header, rows


def write_leads_csv_from_xlsx(path):
    header, rows = xlsx_to_csv_rows(path)
    with open(LEADS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def main():
    os.chdir(REPO)
    lock_fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # otra corrida ya está en curso

    candidate = find_candidate()
    if not candidate:
        return

    log(f"Detectado archivo nuevo: {os.path.basename(candidate)}")

    if not wait_until_stable(candidate):
        log("No se pudo confirmar que el archivo terminó de copiarse, se reintentará en el próximo cambio.")
        return

    ext = os.path.splitext(candidate)[1].lower()
    try:
        if ext == ".csv":
            with open(candidate, "rb") as src, open(LEADS_CSV, "wb") as dst:
                dst.write(src.read())
        else:
            write_leads_csv_from_xlsx(candidate)
    except Exception as e:
        log(f"ERROR leyendo {os.path.basename(candidate)}: {e}")
        return

    import build
    try:
        result = build.build()
    except Exception as e:
        log(f"ERROR generando index.html: {e}")
        return

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archived_name = f"{stamp}__{os.path.basename(candidate)}"
    os.rename(candidate, os.path.join(ARCHIVE_DIR, archived_name))
    log(f"Archivo original movido a procesados/{archived_name}")

    status = sh("git", "status", "--porcelain").stdout.strip()
    if not status:
        log("Sin cambios reales respecto al último commit, no se publica nada.")
        return

    sh("git", "add", "-A")
    commit_msg = f"Actualizar leads ({stamp})"
    commit = sh("git", "commit", "-m", commit_msg, check=False)
    if commit.returncode != 0:
        log(f"git commit no hizo nada nuevo: {commit.stdout} {commit.stderr}")
        return
    log(f"Commit creado: {commit_msg}")

    push = sh("git", "push", check=False)
    if push.returncode != 0:
        log(f"ERROR en git push: {push.stderr}")
        return
    log("Publicado en GitHub correctamente.")


if __name__ == "__main__":
    main()
