"""Regenera index.html a partir de leads.csv y template.html.

Uso: reemplaza leads.csv con tu export actualizado y corre:
    python3 build.py
"""
import csv, json, re
from collections import Counter

SRC = "leads.csv"
TEMPLATE = "template.html"
OUT = "index.html"

STAGE_WEIGHT = {
    "Legalidad (contrato y escrituración)": 7,
    "Oferta, Negociación/Cierre": 6,
    "Visita confirmada": 5,
    "Solicitud": 4,
    "Seguimiento": 3,
    "Remarketing": 2,
    "Lead nuevo": 1,
    "No viable": 0,
}
STAGE_SHORT = {
    "Legalidad (contrato y escrituración)": "Legalidad / Cierre",
    "Oferta, Negociación/Cierre": "Oferta / Negociación",
    "Visita confirmada": "Visita confirmada",
    "Solicitud": "Solicitud",
    "Seguimiento": "Seguimiento",
    "Remarketing": "Remarketing",
    "Lead nuevo": "Lead nuevo",
    "No viable": "No viable",
}
STAGE_TIER = {
    "Legalidad (contrato y escrituración)": "good",
    "Oferta, Negociación/Cierre": "good",
    "Visita confirmada": "mid",
    "Solicitud": "mid",
    "Seguimiento": "warn",
    "Remarketing": "warn",
    "Lead nuevo": "warn",
    "No viable": "bad",
}
STAGE_COUNT = 7  # etapas activas (sin contar "No viable"), usado para los puntos de avance


def parse_dias(s):
    s = (s or "").strip()
    if not s or s.lower() == "hoy":
        return 0
    m = re.match(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def clean(s):
    return (s or "").strip().replace("\n", " ").replace("\r", " ")


def build():
    with open(SRC, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    leads = []
    for row in rows:
        fase = row["fase"].strip()
        estado = row["estado"].strip()
        dias_act = parse_dias(row["Días desde la última actualización "])
        dias_etapa = parse_dias(row["Días desde el último cambio de etapa "])
        discard = (fase == "No viable") or (estado == "lost")
        weight = STAGE_WEIGHT.get(fase, 0)
        score = weight * 1000 + min(dias_act, 90)
        leads.append({
            "id": row["ID de oportunidad"],
            "nombre": clean(row["Nombre de la oportunidad"]) or clean(row["Nombre del contacto"]) or "(Sin nombre)",
            "telefono": clean(row["teléfono"]),
            "email": clean(row["correo electrónico"]),
            "fase": fase,
            "faseCorta": STAGE_SHORT.get(fase, fase),
            "tier": STAGE_TIER.get(fase, "mid"),
            "peso": weight,
            "diasActualizacion": dias_act,
            "diasEtapa": dias_etapa,
            "notas": clean(row["Notas"])[:220],
            "asignado": clean(row["asignado"]),
            "creado": row["Creado el"][:10] if row["Creado el"] else "",
            "discard": discard,
            "score": score,
        })

    active = sorted([l for l in leads if not l["discard"]], key=lambda l: -l["score"])
    discarded = sorted([l for l in leads if l["discard"]], key=lambda l: -l["diasActualizacion"])

    data = {
        "total": len(leads),
        "activeCount": len(active),
        "discardCount": len(discarded),
        "active": active,
        "discarded": discarded,
    }

    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK: {OUT} generado. total={len(leads)} activos={len(active)} descarte={len(discarded)}")
    print("Distribución activos por etapa:", Counter(l["faseCorta"] for l in active))


if __name__ == "__main__":
    build()
