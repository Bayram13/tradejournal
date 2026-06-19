# 📈 Trade Journal

Professional treyd qeydiyyat saytı — database, statistika və qrafik şəkli (chart screenshot) dəstəyi ilə. Flask + PostgreSQL əsasında qurulub və **Render**-də pulsuz yayımlamaq üçün hazırdır.

## Funksiyalar
- ✅ Trade əlavə et / düzəlt / sil (CRUD)
- ✅ Hər trade üçün **şəkil (chart screenshot)** yüklə — şəkillər database-də saxlanılır
- ✅ Avtomatik P&L və P&L % hesablanması (LONG / SHORT)
- ✅ Statistika: Ümumi P&L, Win Rate, Profit Factor, açıq/bağlı say
- ✅ Status (açıq/bağlı) və simvol üzrə filtr + axtarış
- ✅ Şəkil böyütmə (lightbox), responsive dizayn

## Lokal işə salma
```bash
pip install -r requirements.txt
python app.py
# http://localhost:5000
```
Lokal olaraq SQLite (`trades.db`) istifadə olunur — heç bir quraşdırma lazım deyil.

## 🚀 Render-də yayımlama (Blueprint ilə — ən asan)
1. Bu qovluğu GitHub repo-suna yüklə (push et).
2. Render → **New → Blueprint** seç və repo-nu bağla.
3. Render `render.yaml`-i oxuyacaq: web servis + pulsuz PostgreSQL database avtomatik yaranacaq.
4. **Apply** düy mə sinə bas. Bir neçə dəqiqəyə sayt canlı olacaq.

`DATABASE_URL` Render tərəfindən avtomatik təyin olunur — heç nə əlavə etmək lazım deyil.

## 🚀 Render-də əl ilə yayımlama (Blueprint istəmirsənsə)
1. Render → **New → PostgreSQL** yarat (pulsuz plan), `Internal Database URL`-i kopyala.
2. Render → **New → Web Service**, repo-nu bağla.
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
3. **Environment** bölməsində dəyişən əlavə et:
   - `DATABASE_URL` = (kopyaladığın PostgreSQL URL)
4. Deploy et.

## Texnologiyalar
- Backend: Flask, Flask-SQLAlchemy, gunicorn
- DB: PostgreSQL (prod) / SQLite (local)
- Frontend: Vanilla JS + CSS (framework yoxdur, sürətli)

## Qeyd
Şəkillər birbaşa database-də saxlanılır ki, Render-in pulsuz planında disk silinəndə də itməsin.
