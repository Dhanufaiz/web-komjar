import os
import io
import re
import pandas as pd
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==========================================
# 1. KONFIGURASI UTAMA
# ==========================================
SERVICE_ACCOUNT_FILE = 'service_account.json' # Ganti dengan nama file JSON kredensialmu
SPREADSHEET_ID = '1m6RMqwkvffnhBi_6fTLcfY0RK_hMgdWC-ZYJzl47uI0'
ID_FOLDER_UTAMA = '16p15TNLSmt4-VfROTn40zP5VegC0tsGK' #[cite: 3]

NAMA_SHEET_PRESENSI = 'PRESENSI'       #[cite: 3]
NAMA_SHEET_PENDAFTARAN = 'PENDAFTARAN' #[cite: 3]

# Autentikasi API
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)
sheets_service = build('sheets', 'v4', credentials=creds)

# ==========================================
# 2. FUNGSI BANTUAN GOOGLE DRIVE
# ==========================================
def get_or_create_folder(folder_name, parent_id):
    """Mencari folder berdasarkan nama, jika tidak ada maka dibuat."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{parent_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0].get('id')

def extract_file_id(url):
    """Mengambil ID Drive dari URL."""
    match = re.search(r'[-\w]{25,}', url)
    return match.group(0) if match else None

# ==========================================
# 3. FUNGSI KOMPRESI & UPLOAD
# ==========================================
def process_image(file_url, target_folder_id, new_file_name):
    file_id = extract_file_id(file_url)
    if not file_id: return file_url

    try:
        # A. Dapatkan metadata file (untuk cek ekstensi asli)
        file_meta = drive_service.files().get(fileId=file_id, fields='name, mimeType').execute()
        
        # B. Download file ke memori (buffer)
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        
        # C. Kompresi Lokal menggunakan Pillow
        temp_filename = f"temp_{new_file_name}"
        img = Image.open(fh)
        
        # Konversi ke RGB jika format PNG/RGBA untuk kompresi JPEG lossless
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(temp_filename, format="JPEG", optimize=True, quality=80)
        
        # D. Upload ke Drive Target
        file_metadata = {
            'name': new_file_name,
            'parents': [target_folder_id]
        }
        media = MediaFileUpload(temp_filename, mimetype='image/jpeg', resumable=True)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        # E. Bersihkan file lokal & Hapus file asli di Drive
        os.remove(temp_filename)
        drive_service.files().delete(fileId=file_id).execute()
        print(f"✅ Sukses kompresi & pindah: {new_file_name}")
        
        return uploaded_file.get('webViewLink')

    except Exception as e:
        print(f"❌ Gagal memproses {file_url}: {e}")
        return file_url # Kembalikan URL lama jika gagal

# ==========================================
# 4. LOGIKA UTAMA SINKRONISASI DATA
# ==========================================
def main():
    print("Membaca data dari Spreadsheet...")
    # Ambil data Pendaftaran
    pendaftaran_data = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{NAMA_SHEET_PENDAFTARAN}!A1:Z").execute()
    df_pend = pd.DataFrame(pendaftaran_data.get('values', [])[1:], columns=pendaftaran_data.get('values', [])[0])
    
    # Ambil data Presensi
    presensi_range = f"{NAMA_SHEET_PRESENSI}!A1:Z"
    presensi_data = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=presensi_range).execute()
    presensi_rows = presensi_data.get('values', [])
    headers = presensi_rows[0]
    
    idx_nim = headers.index('NIM') if 'NIM' in headers else -1
    idx_dok = headers.index('Dokumentasi Kegiatan') if 'Dokumentasi Kegiatan' in headers else -1
    idx_hadir = headers.index('Daftar Peserta didik (Jika berbentuk file atau gambar)') if 'Daftar Peserta didik (Jika berbentuk file atau gambar)' in headers else -1

    # Loop setiap baris presensi (mulai dari baris ke-2)
    for r_idx, row in enumerate(presensi_rows[1:], start=2):
        if idx_nim == -1 or len(row) <= idx_nim: continue
        
        nim = str(row[idx_nim]).strip()
        if not nim: continue

        # Cek apakah ada file yang perlu diproses
        dok_urls = row[idx_dok] if idx_dok != -1 and len(row) > idx_dok else ""
        hadir_urls = row[idx_hadir] if idx_hadir != -1 and len(row) > idx_hadir else ""
        
        # Jika tidak ada link sama sekali, skip baris ini
        if not dok_urls and not hadir_urls: continue
        
        # Filter relawan di Pendaftaran
        pend_match = df_pend[df_pend['NIM'].str.strip() == nim]
        if pend_match.empty: continue
        
        relawan = pend_match.iloc[0]
        tipe = relawan.get('Tipe Pendaftaran', 'Individu')
        nama_lengkap = relawan.get('Nama Lengkap', 'Unknown')
        sekolah = relawan.get('Sekolah', '-')
        
        if pd.isna(sekolah) or sekolah == '-':
            sekolah = relawan.get('1', 'Belum Ditentukan')
            
        # Struktur Folder sesuai instruksi baru[cite: 3]
        if tipe == "Individu":
            folder_individu_id = get_or_create_folder("Individu", ID_FOLDER_UTAMA)
            target_folder_id = get_or_create_folder(sekolah, folder_individu_id)
        else:
            folder_sekolah_id = get_or_create_folder(sekolah, ID_FOLDER_UTAMA)
            target_folder_id = get_or_create_folder(nama_lengkap, folder_sekolah_id) #[cite: 3]

        # Fungsi proses string URL koma
        def process_url_string(url_string, prefix):
            if not url_string: return ""
            urls = [u.strip() for u in str(url_string).split(",") if u.strip()]
            new_urls = []
            for i, url in enumerate(urls, 1):
                if "drive.google.com" in url:
                    # Penamaan file
                    new_name = f"{nim}_{nama_lengkap}_{prefix}_{i}.jpg"
                    new_url = process_image(url, target_folder_id, new_name)
                    new_urls.append(new_url)
                else:
                    new_urls.append(url)
            return ", ".join(new_urls)

        # Proses Dokumentasi
        if dok_urls:
            new_dok = process_url_string(dok_urls, "Dokumentasi")
            # Update sel langsung ke Spreadsheet
            if new_dok != dok_urls:
                cell = f"{NAMA_SHEET_PRESENSI}!{chr(65 + idx_dok)}{r_idx}"
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID, range=cell,
                    valueInputOption="USER_ENTERED", body={"values": [[new_dok]]}
                ).execute()

        # Proses Daftar Hadir
        if hadir_urls:
            new_hadir = process_url_string(hadir_urls, "DaftarHadir")
            if new_hadir != hadir_urls:
                cell = f"{NAMA_SHEET_PRESENSI}!{chr(65 + idx_hadir)}{r_idx}"
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID, range=cell,
                    valueInputOption="USER_ENTERED", body={"values": [[new_hadir]]}
                ).execute()

if __name__ == '__main__':
    main()