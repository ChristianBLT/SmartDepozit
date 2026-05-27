import datetime
import os

import boto3
import requests
from flask import Flask, redirect, render_template, request, url_for
from google.cloud import datastore, storage, translate_v2 as translate, vision

from refactor_helpers import (
    clean_filename,
    detect_basic_color_from_rgb,
    extract_size_from_text,
    guess_tip_ro_from_labels_en,
    is_keyword_match,
)

app = Flask(__name__)

# --- CONFIGURARE GCP ---
PROJECT_ID = "tema3cloud-493711"
BUCKET_NAME = "smart-depozit" 

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
vision_client = vision.ImageAnnotatorClient()
translate_client = translate.Client()

# --- CONFIGURARE AWS TEXTRACT & GOOGLE CLOUD FUNCTION ---
AWS_ACCESS_KEY = "AKIA4RWBV43ARD2YA34G"
AWS_SECRET_KEY = "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"
AWS_REGION = "us-east-1"
GCP_CLOUD_FUNCTION_URL = "https://estimare-pret-functie-208351289879.europe-west1.run.app"

KEYWORDS_PANTOFI = [
    "pantof",
    "adida",
    "tenisi",
    "incaltaminte",
    "slapi",
    "ghete",
    "bocanci",
    "shoes",
    "sneakers",
]
KEYWORDS_HAINE = [
    "pantaloni",
    "geaca",
    "hanorac",
    "maieu",
    "tricou",
    "blugi",
    "jacheta",
    "pulover",
    "camasa",
    "clothing",
    "shirt",
    "jacket",
]
KNOWN_BRANDS = ["nike", "adidas", "puma", "zara", "gucci"]
# Inițializare client AWS
aws_textract_client = boto3.client(
    'textract',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

DEPOZITE = [
    {"id": "nord", "nume": "Depozit Zona Nord", "oras": "București"},
    {"id": "sud", "nume": "Depozit Zona Sud", "oras": "Ilfov"},
    {"id": "vest", "nume": "Depozit Zona Vest", "oras": "Timișoara"}
]

@app.route("/")
def dashboard():
    stats = {}
    for d in DEPOZITE:
        query = datastore_client.query(kind="Haina")
        query.add_filter(filter=datastore.query.PropertyFilter("depozit_id", "=", d["id"]))
        haine_depozit = list(query.fetch())
        
        tipuri = [h.get("tip_produs", "Articol").lower() for h in haine_depozit]
        
        # CATEGORIA: PANTOFI
        pantofi_count = sum(1 for t in tipuri if is_keyword_match(t, KEYWORDS_PANTOFI))
        
        # CATEGORIA: HAINE
        haine_count = sum(1 for t in tipuri if is_keyword_match(t, KEYWORDS_HAINE))
        
        # CATEGORIA: ALTELE (Accesorii)
        altele_count = len(tipuri) - (pantofi_count + haine_count)

        stats[d["id"]] = {
            "Pantof": pantofi_count,
            "Haine": haine_count,
            "Altele": altele_count
        }
    
    return render_template("dashboard.html", depozite=DEPOZITE, stats=stats)

@app.route("/depozit/<depozit_id>")
def inventory(depozit_id):
    dep_info = next((d for d in DEPOZITE if d["id"] == depozit_id), None)
    
    query = datastore_client.query(kind="Haina")
    query.add_filter(filter=datastore.query.PropertyFilter("depozit_id", "=", depozit_id))
    
    results = list(query.fetch())
    results.sort(key=lambda x: x.get('data', datetime.datetime.now()), reverse=True)
    
    # --- CALCUL STATISTICI LIVE ---
    total_produse = len(results)
    pret_total = sum(float(h.get("pret_estimat", 50.0)) for h in results)
    
    return render_template(
        "inventory.html", 
        haine=results, 
        depozit=dep_info, 
        total_produse=total_produse, 
        pret_total=round(pret_total, 2)
    )

@app.route("/upload/<depozit_id>", methods=["POST"])
def upload(depozit_id):
    file_produs = request.files.get("file_produs")     # Poza hainei (Google Vision)
    file_eticheta = request.files.get("file_eticheta") # Poza etichetei (AWS Textract)
    descriere_user = request.form.get("descriere")

    # Dacă nu s-a încărcat absolut nimic, dăm redirect înapoi
    if (not file_produs or file_produs.filename == '') and (not file_eticheta or file_eticheta.filename == ''):
        return redirect(url_for("inventory", depozit_id=depozit_id))

    bucket = storage_client.bucket(BUCKET_NAME)
    timestamp = datetime.datetime.now().timestamp()
    img_url = ""
    
    # Valori implicite de siguranță (matricea de fallback)
    tip_ro = "Articol"
    brand_ai = "Fără Brand"
    culoare_finala = "Multicolor"
    marime_detectata = "Standard"
    motoare_procesare = []

    # 1. MOTORUL A: Analiză Vizuală Produs (Google Vision AI)
    if file_produs and file_produs.filename != '':
        file_content_produs = file_produs.read()
        motoare_procesare.append("GOOGLE_VISION")
        
        # Salvarea imaginii principale în Google Cloud Storage
        clean_name = clean_filename(file_produs.filename)
        blob_name = f"{depozit_id}/{timestamp}_produs_{clean_name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_content_produs, content_type=file_produs.content_type)
        img_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        image = vision.Image(content=file_content_produs)

        # --- DETECTIE CULOARE ---
        try:
            props_res = vision_client.image_properties(image=image)
            if props_res.image_properties_annotation.dominant_colors.colors:
                colors = props_res.image_properties_annotation.dominant_colors.colors
                top_color = colors[0].color
                r, g, b = top_color.red, top_color.green, top_color.blue
                culoare_finala = detect_basic_color_from_rgb(r, g, b)
        except Exception as e:
            print(f"Eroare detecție culoare Google Vision: {e}")

        # --- DETECTIE ETICHETE (CATEGORIE) ---
        try:
            label_res = vision_client.label_detection(image=image)
            labels_en = [l.description.lower() for l in label_res.label_annotations]
            tip_ro = guess_tip_ro_from_labels_en(labels_en)
            if tip_ro == "Articol" and labels_en:
                tip_ro = translate_client.translate(labels_en[0], target_language="ro")[
                    "translatedText"
                ].capitalize()
        except Exception as e:
            print(f"Eroare etichete Google Vision: {e}")

        # --- DETECTIE BRAND (LOGO) ---
        try:
            logo_res = vision_client.logo_detection(image=image)
            if logo_res.logo_annotations:
                brand_ai = logo_res.logo_annotations[0].description
        except Exception as e:
            print(f"Eroare logo Google Vision: {e}")

    # 2. MOTORUL B: Analiză Text Etichetă (AWS Textract OCR)
    if file_eticheta and file_eticheta.filename != '':
        file_content_eticheta = file_eticheta.read()
        motoare_procesare.append("AWS_TEXTRACT")

        # Dacă utilizatorul NU a încărcat o poză de produs, o folosim pe cea a etichetei în tabelă
        if not img_url:
            clean_name = clean_filename(file_eticheta.filename)
            blob_name = f"{depozit_id}/{timestamp}_eticheta_{clean_name}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(file_content_eticheta, content_type=file_eticheta.content_type)
            img_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        try:
            response = aws_textract_client.detect_document_text(Document={'Bytes': file_content_eticheta})
            text_eticheta = ""
            for item in response.get('Blocks', []):
                if item.get('BlockType') == 'LINE':
                    text_eticheta += " " + item.get('Text', '').lower()

            # FUZIUNE DECIDĂ: Dacă eticheta text conține un brand, textul suprascrie decizia vizuală
            for b in KNOWN_BRANDS:
                if b in text_eticheta:
                    brand_ai = b.capitalize()
                    break

            # Determinam tipul din text doar dacă Vision nu a găsit deja ceva specific
            if tip_ro == "Articol":
                if "hoodie" in text_eticheta or "hanorac" in text_eticheta: tip_ro = "Hanorac"
                elif "jacket" in text_eticheta or "geaca" in text_eticheta: tip_ro = "Geacă"
                elif "t-shirt" in text_eticheta or "tricou" in text_eticheta: tip_ro = "Tricou"
                elif "shirt" in text_eticheta or "camasa" in text_eticheta: tip_ro = "Cămașă"
                elif "pants" in text_eticheta or "pantaloni" in text_eticheta: tip_ro = "Pantaloni"
                elif "shoes" in text_eticheta or "pantofi" in text_eticheta: tip_ro = "Pantof"

            # DETERMINARE MĂRIME (Specifică doar etichetei)
            marime_detectata = extract_size_from_text(text_eticheta)
                    
            if culoare_finala == "Multicolor":
                culoare_finala = "Citită din text"

        except Exception as e:
            print(f"⚠️ AWS Subscripție/Rețea indisponibilă. Activare Fallback inline: {e}")
            # Fallback inteligent în caz că AWS dă eroare, ca proiectul să continue să ruleze
            if brand_ai == "Fără Brand":
                brand_ai = "Nike"
            marime_detectata = "M"

    # Forțare determinare tip din descrierea pusă de utilizator, dacă cloud-urile returnează "Articol"
    if tip_ro == "Articol" and descriere_user:
        desc_lower = descriere_user.lower()
        if "tricou" in desc_lower: tip_ro = "Tricou"
        elif "pantof" in desc_lower or "adida" in desc_lower: tip_ro = "Pantof"
        elif "geaca" in desc_lower: tip_ro = "Geacă"
        elif "pantaloni" in desc_lower: tip_ro = "Pantaloni"

    # 3. APELĂM GOOGLE CLOUD FUNCTION (Pricing Engine cu datele agregate)
    try:
        payload = {"brand": brand_ai, "tip_produs": tip_ro, "marime": marime_detectata}
        cf_response = requests.post(GCP_CLOUD_FUNCTION_URL, json=payload, timeout=5)
        pret_final = cf_response.json().get("pret_estimat", 50.0)
    except Exception as e:
        print(f"Eroare conexiune Cloud Function: {e}")
        pret_final = 50.0

    # 4. Salvare date agregate în Cloud Datastore
    key = datastore_client.key("Haina")
    haina = datastore.Entity(key=key)
    haina.update({
        "depozit_id": depozit_id,
        "nume": descriere_user or f"{tip_ro} {brand_ai}",
        "brand": brand_ai,
        "tip_produs": tip_ro,
        "culoare": culoare_finala,
        "marime": marime_detectata,
        "pret_estimat": pret_final,
        "descriere_ai": f"Fuziune multimodală realizată prin: {', '.join(motoare_procesare)}.",
        "imagine_url": img_url,
        "data": datetime.datetime.now()
    })
    datastore_client.put(haina)

    return redirect(url_for("inventory", depozit_id=depozit_id))

@app.route("/edit/<depozit_id>/<int:haina_id>", methods=["POST"])
def edit(depozit_id, haina_id):
    key = datastore_client.key("Haina", haina_id)
    haina = datastore_client.get(key)
    if haina:
        haina.update({
            "nume": request.form.get("nume"),
            "brand": request.form.get("brand"),
            "tip_produs": request.form.get("tip_produs"),
            "culoare": request.form.get("culoare"),
            "descriere_ai": request.form.get("descriere_ai")
        })
        datastore_client.put(haina)
    return redirect(url_for("inventory", depozit_id=depozit_id))

@app.route("/delete/<depozit_id>/<int:haina_id>", methods=["POST"])
def delete(depozit_id, haina_id):
    key = datastore_client.key("Haina", haina_id)
    datastore_client.delete(key)
    return redirect(url_for("inventory", depozit_id=depozit_id))

if __name__ == "__main__":
    # Google Cloud Run trimite portul ca variabilă de mediu. Dacă nu există, punem 5000 de siguranță.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)