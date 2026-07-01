# Deploy na Google Cloud Run

Aplikacija je privatna (zaključana lozinkom), a baza se čuva u Google Cloud
Storage bucketu — pa preživi restart i redeploy, i nije u gitu.

## Preduvjeti (jednokratno)

1. Instaliraj **Google Cloud CLI**: https://cloud.google.com/sdk/docs/install
2. Prijava i odabir projekta:
   ```bash
   gcloud auth login
   gcloud config set project TVOJ_PROJEKT_ID
   ```
3. Uključi potrebne servise:
   ```bash
   gcloud services enable run.googleapis.com storage.googleapis.com cloudbuild.googleapis.com
   ```

## 1. Napravi bucket i ubaci početnu bazu

```bash
# Ime bucketa mora biti globalno jedinstveno.
gcloud storage buckets create gs://finan-baza-TVOJEIME --location=europe-west1

# Prebaci postojeću lokalnu bazu u bucket (jednom).
gcloud storage cp financije_baza.json gs://finan-baza-TVOJEIME/financije_baza.json
```

## 2. Deploy na Cloud Run

```bash
gcloud run deploy finan \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars FINAN_GCS_BUCKET=finan-baza-TVOJEIME \
  --set-env-vars FINAN_LOZINKA=ODABERI_JAKU_LOZINKU
```

- `--allow-unauthenticated` znači da je URL javno dostupan, ali app je iza
  **login ekrana** (lozinka iz `FINAN_LOZINKA`). Bez te varijable app se ne
  zaključava, pa je obavezno postavi.
- Za jaču zaštitu lozinku možeš staviti u **Secret Manager**:
  ```bash
  echo -n "ODABERI_JAKU_LOZINKU" | gcloud secrets create finan-lozinka --data-file=-
  gcloud run deploy finan --source . --region europe-west1 --allow-unauthenticated \
    --set-env-vars FINAN_GCS_BUCKET=finan-baza-TVOJEIME \
    --set-secrets FINAN_LOZINKA=finan-lozinka:latest
  ```

## 3. Daj Cloud Run pristup bucketu

Cloud Run koristi service account projekta. Daj mu pravo na bucket:

```bash
PROJ_NUM=$(gcloud projects describe TVOJ_PROJEKT_ID --format='value(projectNumber)')
gcloud storage buckets add-iam-policy-binding gs://finan-baza-TVOJEIME \
  --member="serviceAccount:${PROJ_NUM}-compute@developer.gserviceaccount.com" \
  --role=roles/storage.objectAdmin
```

Nakon deploya `gcloud` ispiše URL (npr. `https://finan-xxxxx.europe-west1.run.app`).
Otvoriš ga u pregledniku s bilo kojeg računala, upišeš lozinku i radiš — podaci
su u bucketu, kod je u gitu, a osobni podaci i tajne nisu.

## Lokalni razvoj

Bez postavljenih varijabli app radi po starome — lokalna `financije_baza.json`,
bez lozinke:

```bash
.venv\Scripts\streamlit run app.py
```

| Varijabla          | Čemu služi                                  |
|--------------------|---------------------------------------------|
| `FINAN_GCS_BUCKET` | ime GCS bucketa (bez njega → lokalni file)  |
| `FINAN_GCS_OBJECT` | ime objekta u bucketu (zadano `financije_baza.json`) |
| `FINAN_LOZINKA`    | lozinka za prijavu (bez nje → nema zaključavanja) |
| `FINAN_DB_PATH`    | putanja lokalne baze/cachea                 |
