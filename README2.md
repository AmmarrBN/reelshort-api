# ReelShort API

API untuk mengakses konten ReelShort - Platform Nonton Drama China. API ini menyediakan endpoint untuk mencari drama, mendapatkan daftar episode, mengambil URL video, dan mengakses bookshelf kategori.
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Fitur

- 🔍 **Search Drama** - Cari drama berdasarkan kata kunci
- 📋 **List Episodes** - Dapatkan daftar episode dari drama
- 🎬 **Get Video URL** - Ambil URL video langsung ke episode
- 📚 **Bookshelf Categories** - Akses drama berdasarkan kategori (Dub, New Release, Recommended)
- 📖 **Swagger UI** - Dokumentasi API interaktif
- 🔄 **Auto Next Episode** - Dapatkan info episode berikutnya otomatis

## Instalasi

```bash
# Clone repository
git clone https://github.com/username/reelshort-api.git
cd reelshort-api

# Install dependencies
pip install flask flask-restx requests

# Jalankan server
python reelshort.py
```

Server akan berjalan di `http://localhost:5000`

## Dokumentasi API

Akses Swagger UI: `http://localhost:5000/docs`

## Alur Penggunaan

API ini menggunakan 3 step berurutan:

### Step 1: Search Drama
```http
GET /api/v1/reelshort/search?keywords=love
```

**Response:**
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

> Simpan `book_id` dan `filtered_title` untuk step 2

### Step 2: Get Episodes
```http
GET /api/v1/reelshort/episodes/{book_id}?filtered_title=love-story-drama
```

**Response:**
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

> Simpan `episode` dan `chapter_id` untuk step 3

### Step 3: Get Video URL
```http
GET /api/v1/reelshort/video/{book_id}/{episode_num}?filtered_title=love-story-drama&chapter_id=chapter_001
```

**Response:**
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

> Convert Dulu dari .m3u8 jadi .mp4

## Bookshelf Endpoints (New)

Endpoint untuk mengakses drama berdasarkan kategori. Setiap buku sudah include `filtered_title` dan `book_id` yang bisa langsung digunakan untuk Step 2 dan Step 3.

### Get Drama dengan Dub
```http
GET /api/v1/reelshort/dramadub
```

**Response:**
```json
{
  "bookshelf_name": "Drama dengan Dub🎧",
  "books": [
    {
      "book_title": "Drama Title",
      "filtered_title": "drama-title",
      "book_pic": "https://...",
      "special_desc": "Description",
      "chapter_count": 50,
      "book_id": "65a1b2c3d4e5f6g7h8i9j0k1",
      "chapter_base": [
        {
          "chapter_id": "chapter_001",
          "chapter_name": "Episode 1",
          "like_count": 1000,
          "publish_at": "2024-01-01",
          "create_time": "2024-01-01"
        }
      ]
    }
  ]
}
```

### Get Rilis Baru
```http
GET /api/v1/reelshort/newrelease
```

**Response:** Sama format dengan `/dramadub`

### Get Lebih Direkomendasikan
```http
GET /api/v1/reelshort/recommend
```

**Response:** Sama format dengan `/dramadub`

### Alur Penggunaan Bookshelf

```bash
# 1. Ambil daftar drama dari bookshelf
curl "http://localhost:5000/api/v1/reelshort/dramadub"

# 2. Gunakan book_id dan filtered_title langsung ke /episodes
curl "http://localhost:5000/api/v1/reelshort/episodes/BOOK_ID?filtered_title=FILTERED_TITLE"

# 3. Get video URL
curl "http://localhost:5000/api/v1/reelshort/video/BOOK_ID/1?filtered_title=FILTERED_TITLE&chapter_id=CHAPTER_ID"
```

## Endpoints

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/v1/reelshort/search` | Cari drama |
| GET | `/api/v1/reelshort/episodes/{book_id}` | Dapatkan daftar episode |
| GET | `/api/v1/reelshort/video/{book_id}/{episode_num}` | Dapatkan URL video |
| GET | `/api/v1/reelshort/dramadub` | Drama dengan dubbing |
| GET | `/api/v1/reelshort/newrelease` | Rilis terbaru |
| GET | `/api/v1/reelshort/recommend` | Lebih direkomendasikan |

## Parameters

### Search
| Parameter | Type | Required | Deskripsi |
|-----------|------|----------|-----------|
| keywords | string | Yes | Kata kunci pencarian |

### Episodes
| Parameter | Type | Required | Deskripsi |
|-----------|------|----------|-----------|
| book_id | path | Yes | ID dari hasil search atau bookshelf |
| filtered_title | query | Yes | Slug dari hasil search atau bookshelf |

### Video
| Parameter | Type | Required | Deskripsi |
|-----------|------|----------|-----------|
| book_id | path | Yes | ID dari hasil search atau bookshelf |
| episode_num | path | Yes | Nomor episode |
| filtered_title | query | Yes | Slug dari hasil search atau bookshelf |
| chapter_id | query | Yes | ID chapter dari episodes |

### Bookshelf
| Parameter | Type | Required | Deskripsi |
|-----------|------|----------|-----------|
| - | - | - | Tidak memerlukan parameter |

## Contoh Penggunaan dengan cURL

```bash
# Step 1: Search
curl "http://localhost:5000/api/v1/reelshort/search?keywords=love"

# Step 2: Get Episodes (ganti BOOK_ID dan FILTERED_TITLE)
curl "http://localhost:5000/api/v1/reelshort/episodes/BOOK_ID?filtered_title=FILTERED_TITLE"

# Step 3: Get Video (ganti parameter sesuai hasil sebelumnya)
curl "http://localhost:5000/api/v1/reelshort/video/BOOK_ID/1?filtered_title=FILTERED_TITLE&chapter_id=CHAPTER_ID"

# Atau gunakan Bookshelf (lebih mudah - sudah ada book_id dan filtered_title)
curl "http://localhost:5000/api/v1/reelshort/dramadub"
```

## Contoh Penggunaan dengan Python

```python
import requests

BASE_URL = "http://localhost:5000/api/v1/reelshort"

# === METODE 1: VIA SEARCH ===
# Step 1: Search
search_resp = requests.get(f"{BASE_URL}/search", params={"keywords": "love"})
book = search_resp.json()["results"][0]
book_id = book["book_id"]
filtered_title = book["filtered_title"]

# Step 2: Get Episodes
episodes_resp = requests.get(
    f"{BASE_URL}/episodes/{book_id}",
    params={"filtered_title": filtered_title}
)
episodes = episodes_resp.json()["episodes"]

# Step 3: Get Video URL
video_resp = requests.get(
    f"{BASE_URL}/video/{book_id}/{episodes[0]['episode']}",
    params={
        "filtered_title": filtered_title,
        "chapter_id": episodes[0]["chapter_id"]
    }
)
video_url = video_resp.json()["video_url"]
print(f"Video URL: {video_url}")


# === METODE 2: VIA BOOKSHELF (Lebih Mudah) ===
# Ambil dari bookshelf, langsung dapat book_id dan filtered_title
shelf_resp = requests.get(f"{BASE_URL}/dramadub")
book = shelf_resp.json()["books"][0]

book_id = book["book_id"]              # Langsung ada
filtered_title = book["filtered_title"] # Langsung ada
chapter_id = book["chapter_base"][0]["chapter_id"]  # Dari chapter_base

# Langsung ke Step 2 atau Step 3
video_resp = requests.get(
    f"{BASE_URL}/video/{book_id}/1",
    params={
        "filtered_title": filtered_title,
        "chapter_id": chapter_id
    }
)
print(f"Video URL: {video_resp.json()['video_url']}")
```

## Response Codes

| Code | Deskripsi |
|------|-----------|
| 200 | Success |
| 400 | Bad Request - Parameter tidak lengkap |
| 404 | Not Found - Video atau bookshelf tidak ditemukan |
| 500 | Server Error |

## Struktur Project

```
.
├── reelshort.py     # Main API file
├── README.md        # Dokumentasi ini
└── requirements.txt # Dependencies
```

## Dependencies

- Flask
- Flask-RESTX
- Requests

Install semua:
```bash
pip install flask flask-restx requests
```

## Catatan Penting

- **Bookshelf Data**: Endpoint `/dramadub`, `/newrelease`, dan `/recommend` mengembalikan **FULL RESPONSE DARI REELSHORT**
- **Book ID**: Di bookshelf, `book_id` diperoleh otomatis dari hasil internal search menggunakan `filtered_title`
- **Rate Limiting**: Jika menggunakan bookshelf, API melakukan multiple search requests di background. Hindari pemanggilan berlebihan.
- **Video Format**: URL video berformat `.m3u8` (HLS streaming), perlu dikonversi ke `.mp4` jika ingin download

## Lisensi

MIT License

---

Dibuat dengan ❤️ untuk komunitas
