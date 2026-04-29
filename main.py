import os
import datetime
from flask import Flask, render_template, request, redirect, url_for
from google.cloud import datastore, storage, vision, translate_v2 as translate

app = Flask(__name__)

# --- CONFIGURARE ---
PROJECT_ID = "tema3cloud-493711"
BUCKET_NAME = "smart-depozit" 

datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
vision_client = vision.ImageAnnotatorClient()
translate_client = translate.Client()

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
        keywords_pantofi = ["pantof", "adida", "tenisi", "incaltaminte", "slapi", "ghete", "bocanci", "shoes", "sneakers"]
        pantofi_count = sum(1 for t in tipuri if any(k in t for k in keywords_pantofi))
        
        # CATEGORIA: HAINE
        keywords_haine = ["pantaloni", "geaca", "hanorac", "maieu", "tricou", "blugi", "jacheta", "pulover", "camasa", "clothing", "shirt", "jacket"]
        haine_count = sum(1 for t in tipuri if any(k in t for k in keywords_haine))
        
        # CATEGORIA: ALTELE (Accesorii)
        # Tot ce ramane (ochelari, palarii, esarfe, etc.)
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
    return render_template("inventory.html", haine=results, depozit=dep_info)

@app.route("/upload/<depozit_id>", methods=["POST"])
def upload(depozit_id):
    file = request.files.get("file")
    descriere_user = request.form.get("descriere")

    if file:
        # Citim continutul fisierului o singura data pentru a-l trimite si la Storage si la Vision
        file_content = file.read()
        
        # 1. Salvare in Cloud Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        clean_name = "".join(x for x in file.filename if x.isalnum() or x in "._- ")
        blob_name = f"{depozit_id}/{datetime.datetime.now().timestamp()}_{clean_name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_content, content_type=file.content_type)
        
        # URL Public (Asigura-te ca ai allUsers -> Storage Object Viewer in consola GCP)
        img_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        # 2. Analiza Vision AI
        image = vision.Image(content=file_content)

        # --- DETECTIE CULOARE (RGB Logic) ---
        props_res = vision_client.image_properties(image=image)
        colors = props_res.image_properties_annotation.dominant_colors.colors
        top_color = colors[0].color
        r, g, b = top_color.red, top_color.green, top_color.blue
        
        # Determinam numele culorii bazat pe luminozitate si valori RGB
        brightness = (r + g + b) / 3
        if brightness < 45: 
            culoare_finala = "Negru"
        elif brightness > 215: 
            culoare_finala = "Alb"
        elif r > 150 and g < 100 and b < 100: 
            culoare_finala = "Roșu"
        elif b > 150 and r < 120: 
            culoare_finala = "Albastru"
        elif g > 150 and r < 120: 
            culoare_finala = "Verde"
        elif abs(r - g) < 20 and abs(g - b) < 20: 
            culoare_finala = "Gri"
        else: 
            culoare_finala = "Multicolor"

        # --- FILTRARE ETICHETE (Anti-Guler/Anti-Aliment) ---
        label_res = vision_client.label_detection(image=image)
        labels_en = [l.description.lower() for l in label_res.label_annotations]
        
        # Prioritati pentru clasificare corecta
        if any(x in labels_en for x in ["sunglasses", "eyewear", "glasses"]):
            tip_ro = "Ochelari"
        elif any(x in labels_en for x in ["sneakers", "shoe", "footwear", "boot"]):
            tip_ro = "Pantof"
        elif any(x in labels_en for x in ["jacket", "coat", "outerwear"]):
            tip_ro = "Geacă"
        elif any(x in labels_en for x in ["hat", "cap", "fedora"]):
            tip_ro = "Pălărie"
        elif any(x in labels_en for x in ["t-shirt", "shirt", "top"]):
            tip_ro = "Tricou/Cămașă"
        elif any(x in labels_en for x in ["pants", "trousers", "jeans"]):
            tip_ro = "Pantaloni"
        else:
            # Daca nu gasim nimic specific, traducem prima eticheta relevanta
            tip_ro = translate_client.translate(labels_en[0], target_language="ro")["translatedText"]

        # --- DETECTIE BRAND ---
        logo_res = vision_client.logo_detection(image=image)
        brand_ai = logo_res.logo_annotations[0].description if logo_res.logo_annotations else "Fără Brand"

        # 3. Salvare in Cloud Datastore
        key = datastore_client.key("Haina")
        haina = datastore.Entity(key=key)
        haina.update({
            "depozit_id": depozit_id,
            "nume": descriere_user,
            "brand": brand_ai,
            "tip_produs": tip_ro,
            "culoare": culoare_finala,
            "descriere_ai": f"Produs tip {tip_ro} detectat în nuanță dominantă de {culoare_finala}.",
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
    app.run(host="127.0.0.1", port=5000, debug=True)