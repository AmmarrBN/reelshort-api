# ReelShort API

API untuk mengakses konten ReelShort - Platform Nonton Drama. API ini menyediakan endpoint untuk mencari drama, mendapatkan daftar episode, dan mengambil URL video.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![Vercel](https://img.shields.io/badge/Vercel-Serverless-black.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🚀 Demo Langsung

API ini sudah di-deploy dan siap digunakan:

```

https://reelshort-api.vercel.app/api/v1/reelshort/search?keywords=love

```

Akses dokumentasi interaktif (Swagger UI):
```

https://reelshort-api.vercel.app/docs

```

## 📋 Fitur

- 🔍 **Search Drama** - Cari drama berdasarkan kata kunci
- 📋 **List Episodes** - Dapatkan daftar episode dari drama
- 🎬 **Get Video URL** - Ambil URL video langsung ke episode (format .m3u8)
- 📚 **Swagger UI** - Dokumentasi API interaktif
- 🔄 **Auto Next Episode** - Dapatkan info episode berikutnya otomatis
- ⚡ **Serverless** - Deploy di Vercel dengan auto-scaling

## 🛠️ Instalasi & Development Lokal

### Prerequisites
- Python 3.9+
- pip

### Setup

```bash
# Clone repository
git clone https://github.com/username/reelshort-api.git
cd reelshort-api

# Install dependencies
pip install -r requirements.txt

# Jalankan server development
python api/index.py
```

Server akan berjalan di `http://localhost:5000`

🌐 Deploy ke Vercel

1. Install Vercel CLI

```bash
npm install -g vercel
```

2. Login & Deploy

```bash
# Login ke akun Vercel
vercel login

# Deploy ke preview environment
vercel

# Deploy ke production
vercel --prod
```

Konfigurasi Vercel (vercel.json)

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

📖 Alur Penggunaan API

API menggunakan 3 step berurutan:

Step 1: Search Drama

Endpoint: `GET /api/v1/reelshort/search`

Parameter:

Parameter	Type	Required	Deskripsi	
keywords	query	Yes	Kata kunci pencarian	

Contoh Request:

```bash
curl "https://reelshort-api.vercel.app/api/v1/reelshort/search?keywords=love"
```

Response:

```json
{
  "results": [
    {
      "book_id": "65a1b2c3d4e5f6g7h8i9j0k1",
      "book_title": "Love Story Drama",
      "filtered_title": "love-story-drama",
      "book_pic": "https://...",
      "chapter_count": 50
    }
  ]
}
```

> 💡 Simpan `book_id` dan `filtered_title` untuk step 2

---

Step 2: Get Episodes

Endpoint: `GET /api/v1/reelshort/episodes/{book_id}`

Parameter:

Parameter	Type	Required	Deskripsi	
book_id	path	Yes	ID dari hasil search	
filtered_title	query	Yes	Slug dari hasil search	

Contoh Request:

```bash
curl "https://reelshort-api.vercel.app/api/v1/reelshort/episodes/65a1b2c3d4e5f6g7h8i9j0k1?filtered_title=love-story-drama"
```

Response:

```json
{
  "episodes": [
    {
      "episode": 1,
      "chapter_id": "chapter_001"
    },
    {
      "episode": 2,
      "chapter_id": "chapter_002"
    }
  ]
}
```

> 💡 Simpan `episode` dan `chapter_id` untuk step 3

---

Step 3: Get Video URL

Endpoint: `GET /api/v1/reelshort/video/{book_id}/{episode_num}`

Parameter:

Parameter	Type	Required	Deskripsi	
book_id	path	Yes	ID dari hasil search	
episode_num	path	Yes	Nomor episode	
filtered_title	query	Yes	Slug dari hasil search	
chapter_id	query	Yes	ID chapter dari episodes	

Contoh Request:

```bash
curl "https://reelshort-api.vercel.app/api/v1/reelshort/video/65a1b2c3d4e5f6g7h8i9j0k1/1?filtered_title=love-story-drama&chapter_id=chapter_001"
```

Response:

```json
{
  "video_url": "https://cdn.reelshort.com/video.m3u8",
  "episode": 1,
  "duration": 120,
  "next_episode": {
    "episode": 2,
    "chapter_id": "chapter_002"
  }
}
```

> 📝 Catatan: URL video berformat `.m3u8` (HLS streaming). Untuk playback, gunakan player yang support HLS seperti Video.js, Plyr, atau konversi ke MP4 menggunakan FFmpeg.

---

🧪 Contoh Penggunaan Lengkap

Python

```python
import requests

BASE_URL = "https://reelshort-api.vercel.app/api/v1/reelshort"

# Step 1: Search
search_resp = requests.get(f"{BASE_URL}/search", params={"keywords": "love"})
results = search_resp.json()["results"]

if not results:
    print("Drama tidak ditemukan")
    exit()

book = results[0]
book_id = book["book_id"]
filtered_title = book["filtered_title"]
print(f"Ditemukan: {book['book_title']} ({book['chapter_count']} episode)")

# Step 2: Get Episodes
episodes_resp = requests.get(
    f"{BASE_URL}/episodes/{book_id}",
    params={"filtered_title": filtered_title}
)
episodes = episodes_resp.json()["episodes"]
print(f"Total episode tersedia: {len(episodes)}")

# Step 3: Get Video URL (Episode 1)
video_resp = requests.get(
    f"{BASE_URL}/video/{book_id}/{episodes[0]['episode']}",
    params={
        "filtered_title": filtered_title,
        "chapter_id": episodes[0]["chapter_id"]
    }
)
video_data = video_resp.json()

print(f"URL Video: {video_data['video_url']}")
print(f"Durasi: {video_data['duration']} detik")

if video_data['next_episode']:
    print(f"Episode selanjutnya: #{video_data['next_episode']['episode']}")
```

JavaScript/Node.js

```javascript
const BASE_URL = 'https://reelshort-api.vercel.app/api/v1/reelshort';

async function getVideoUrl(keywords) {
  try {
    // Step 1: Search
    const searchRes = await fetch(`${BASE_URL}/search?keywords=${encodeURIComponent(keywords)}`);
    const searchData = await searchRes.json();
    
    if (!searchData.results.length) {
      throw new Error('Drama tidak ditemukan');
    }
    
    const { book_id, filtered_title } = searchData.results[0];
    
    // Step 2: Get Episodes
    const episodesRes = await fetch(
      `${BASE_URL}/episodes/${book_id}?filtered_title=${filtered_title}`
    );
    const episodesData = await episodesRes.json();
    
    // Step 3: Get Video (Episode 1)
    const { episode, chapter_id } = episodesData.episodes[0];
    const videoRes = await fetch(
      `${BASE_URL}/video/${book_id}/${episode}?filtered_title=${filtered_title}&chapter_id=${chapter_id}`
    );
    const videoData = await videoRes.json();
    
    return videoData.video_url;
  } catch (error) {
    console.error('Error:', error);
  }
}

// Usage
getVideoUrl('love').then(url => console.log(url));
```

cURL (One-liner)

```bash
# Chain all steps with jq (install jq first)
BOOK_ID=$(curl -s "https://reelshort-api.vercel.app/api/v1/reelshort/search?keywords=love" | jq -r '.results[0].book_id') && \
FILTERED_TITLE=$(curl -s "https://reelshort-api.vercel.app/api/v1/reelshort/search?keywords=love" | jq -r '.results[0].filtered_title') && \
CHAPTER_ID=$(curl -s "https://reelshort-api.vercel.app/api/v1/reelshort/episodes/${BOOK_ID}?filtered_title=${FILTERED_TITLE}" | jq -r '.episodes[0].chapter_id') && \
curl -s "https://reelshort-api.vercel.app/api/v1/reelshort/video/${BOOK_ID}/1?filtered_title=${FILTERED_TITLE}&chapter_id=${CHAPTER_ID}" | jq -r '.video_url'
```

📊 Response Codes

Code	Deskripsi	
```
200	Success	
400	Bad Request - Parameter tidak lengkap	
404	Not Found - Video tidak ditemukan	
500	Server Error	
504	Gateway Timeout - Request terlalu lama (Vercel limit)	
```

🏗️ Struktur Project

```
reelshort-api/
├── api/
│   └── index.py          # Entry point Vercel (Serverless Function)
├── vercel.json           # Konfigurasi Vercel
├── requirements.txt      # Dependencies Python
└── README.md             # Dokumentasi ini
```

🔧 Dependencies

- Flask - Web framework
- Flask-RESTX - Swagger/OpenAPI documentation
- Requests - HTTP library
- Werkzeug - WSGI utility

📝 Catatan Penting

1. Format Video: URL yang dikembalikan adalah format `.m3u8` (HLS streaming), bukan MP4 langsung
2. CORS: API sudah support CORS untuk akses dari browser
3. Rate Limit: Gunakan dengan bijak, jangan spam request
4. Token: API ini tidak memerlukan autentikasi/API key

🐛 Troubleshooting

Error 504 Gateway Timeout
- Terjadi karena Vercel timeout limit (10s)
- Solusi: Upgrade ke Vercel Pro (60s) atau deploy ke platform lain

Video URL Expired
- URL video dari ReelShort memiliki expiry time
- Solusi: Request ulang endpoint video untuk dapat URL fresh

Cold Start Lambat
- Normal untuk serverless, pertama kali akses akan lebih lambat
- Solusi: Gunakan Vercel Pro atau keep-warm service

📄 Lisensi

MIT License - Bebas digunakan untuk personal maupun komersial.

---

Dibuat dengan ❤️ untuk komunitas
