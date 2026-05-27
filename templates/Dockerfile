# 1. Îi spunem lui Google să pornească o mașină ușoară care are deja Python 3.10 instalat
FROM python:3.10-slim

# 2. Setăm folderul de lucru din interiorul mașinii virtuale
WORKDIR /app

# 3. Copiem lista de librării necesare de pe PC-ul nostru în mașină
COPY requirements.txt .

# 4. Instalam toate librăriile (Flask, boto3, google-cloud-storage etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiem tot restul codului (main.py, folderul templates, static etc.) în mașină
COPY . .

# 6. Deschidem portul 5000, cel pe care ascultă de obicei Flask
EXPOSE 5000

# 7. Comanda care pornește efectiv serverul web când pornește containerul
CMD ["python", "main.py"]