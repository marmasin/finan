"""
Pohrana baze u Google Cloud Storage (za deploy na Google Cloud Run).

Cloud Run ima privremeni disk — datoteka zapisana lokalno nestaje pri svakom
restartu/redeployu. Zato bazu (financije_baza.json) čuvamo u GCS bucketu, a
lokalna datoteka služi samo kao radni cache tijekom rada instance.

Na Cloud Runu autentikacija ide automatski preko service accounta same usluge
(Application Default Credentials) — nema ključa ni lozinke u kodu ni u gitu.
Bucketu se pravo pristupa daje kroz IAM (vidi DEPLOY.md).

Uključuje se postavljanjem varijable okruženja:
  FINAN_GCS_BUCKET   ime bucketa (npr. finan-baza-tvojeime)  ← bez ovoga radi lokalno
  FINAN_GCS_OBJECT   ime objekta u bucketu (zadano: financije_baza.json)

Ako FINAN_GCS_BUCKET nije postavljen, modul je "isključen" i aplikacija radi
s običnom lokalnom datotekom kao i prije.
"""
import os


def omogucen():
    """ True ako je pohrana u GCS uključena (postavljen bucket). """
    return bool(os.environ.get("FINAN_GCS_BUCKET", "").strip())


def _bucket_i_objekt():
    bucket = os.environ["FINAN_GCS_BUCKET"].strip()
    objekt = os.environ.get("FINAN_GCS_OBJECT", "financije_baza.json").strip()
    return bucket, objekt


def _blob():
    try:
        from google.cloud import storage as gcs
    except ImportError as e:
        raise RuntimeError(
            "Nedostaje biblioteka. Instaliraj:  pip install google-cloud-storage"
        ) from e
    bucket, objekt = _bucket_i_objekt()
    klijent = gcs.Client()
    return klijent.bucket(bucket).blob(objekt)


def preuzmi(lokalna_putanja):
    """
    Skida bazu iz GCS-a u lokalnu datoteku.
    Vraća True ako je preuzeta, False ako objekt u bucketu još ne postoji.
    """
    blob = _blob()
    if not blob.exists():
        return False
    blob.download_to_filename(lokalna_putanja)
    return True


def posalji(lokalna_putanja):
    """ Šalje lokalnu bazu u GCS bucket (kreira ili prepisuje objekt). """
    blob = _blob()
    blob.upload_from_filename(lokalna_putanja, content_type="application/json")
