# 👕 SmartWear - Sistem Gestiune Depozit cu AI

Proiect dezvoltat pentru disciplina Cloud Computing. Aplicația folosește **Google Cloud Platform** pentru a automatiza inventarul unui depozit de haine prin recunoaștere vizuală.

---

## 🌟 Funcționalități Principale
* **Analiză AI (Google Vision):** Detectează automat tipul de produs (Geacă, Pantof, etc.), brandul și culoarea dominantă (RGB).
* **Dashboard Analytics:** Grafice interactive (Chart.js) care arată distribuția stocului pe categorii în timp real.
* **Gestiune Completă:** Adăugare, Editare, Ștergere și Căutare "Live" în inventar.
* **Cloud Native:** Integrare cu Google Datastore (DB) și Google Cloud Storage (Imagini).

---

## 🛠️ Instrucțiuni de Instalare (Pentru Colegi)

Urmează acești pași pentru a rula proiectul pe calculatorul tău:

### 1. Clonarea Proiectului
```bash
git clone https://github.com/ChristianBLT/SmartDepozit.git
cd SmartDepozit
```

### 2. Configurarea Mediului Virtual
```bash
# Creare mediu
python -m venv env

# Activare pe Windows (PowerShell/CMD):
.\env\Scripts\activate
```

### 3. Instalarea Librăriilor
```bash
pip install -r requirements.txt
```

### 4. Autentificarea în Google Cloud
IMPORTANT: Trebuie să ai drepturi de "Editor" pe proiectul Google Cloud tema3cloud-493711. Rulează comanda următoare și loghează-te în browser:

```bash
gcloud auth application-default login
```

### 5. Pornirea Aplicației
```bash
python main.py
```

Aplicația va fi disponibilă la adresa: http://127.0.0.1:8080

---

## 📂 Structura Proiectului

- **main.py** - Logica de backend și integrarea cu serviciile Google Cloud  
- **templates/** - Fișierele HTML (Dashboard și Inventar)  
- **static/** - Fișierele CSS (Design) și JS (Logica graficelor și căutarea)  
- **requirements.txt** - Lista dependențelor necesare  
- **.gitignore** - Fișierele excluse de la upload (ex: folderul env)  
