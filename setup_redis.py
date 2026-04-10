import urllib.request
import zipfile
import os
import subprocess
import time

def setup_redis():
    url = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
    zip_path = "redis.zip"
    extract_folder = "redis_windows"

    if not os.path.exists(extract_folder):
        print("📥 Redis yuklab olinmoqda (bu bir oz vaqt olishi mumkin)...")
        urllib.request.urlretrieve(url, zip_path)
        print("✅ Yuklab olindi. arxivdan chiqarilmoqda...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        
        # arxivni o'chirib tashlaymiz
        os.remove(zip_path)
        print("✅ Redis arxivdan chiqarildi.")
    else:
        print("⚡ Redis kompyuterga allaqachon yuklab olingan.")

    redis_exe = os.path.join(extract_folder, "redis-server.exe")
    
    print("🚀 Redis server ishga tushirilmoqda...")
    # Background (orqa fonda) oynani ochmasdan ishga tushirish (agar oynani yashirmoqchi bo'lsak kwargs ishlatamiz)
    # Shunchaki serverni ishlatvoramiz (alohida terminal ochilmasligi uchun CREATE_NO_WINDOW):
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen([redis_exe], creationflags=CREATE_NO_WINDOW)
    
    time.sleep(2)
    print("✅ Redis muvaffaqiyatli ishga tushdi va orqa fonda 6379 portida ishlamoqda!")
    print("Siz endi botni ishga tushirishingiz mumkin.")

if __name__ == "__main__":
    setup_redis()
