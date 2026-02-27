from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields, reqparse
import requests
import re
import json
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Konfigurasi Swagger API
api = Api(
    app,
    version='1.0',
    title='ReelShort API',
    description='API untuk mengakses konten ReelShort - Platform Nonton Drama China',
    doc='/docs',
    prefix='/api/v1',
    mask=False
)

ns = api.namespace('reelshort', description='Operasi ReelShort')

# ============== MODELS ==============
search_result_model = api.model('SearchResult', {
    'book_id': fields.String(description='ID unik buku/drama (simpan untuk step 2)', required=True),
    'book_title': fields.String(description='Judul drama'),
    'filtered_title': fields.String(description='Slug untuk URL (simpan untuk step 2)'),
    'book_pic': fields.String(description='URL poster'),
    'chapter_count': fields.Integer(description='Total episode')
})

search_response_model = api.model('SearchResponse', {
    'results': fields.List(fields.Nested(search_result_model))
})

episode_model = api.model('Episode', {
    'episode': fields.Integer(description='Nomor episode'),
    'chapter_id': fields.String(description='ID chapter untuk video (simpan untuk step 3)')
})

episodes_response_model = api.model('EpisodesResponse', {
    'episodes': fields.List(fields.Nested(episode_model))
})

video_data_model = api.model('VideoData', {
    'video_url': fields.String(description='URL video langsung'),
    'episode': fields.Integer(description='Nomor episode'),
    'duration': fields.Integer(description='Durasi detik'),
    'next_episode': fields.Nested(episode_model, allow_null=True, description='Episode berikutnya')
})

# Bookshelf models (FULL - no limits)
chapter_info_model = api.model('ChapterInfo', {
    'chapter_id': fields.String(description='ID chapter'),
    'chapter_name': fields.String(description='Nama chapter'),
    'like_count': fields.Integer(description='Jumlah likes'),
    'publish_at': fields.String(description='Tanggal publish'),
    'create_time': fields.String(description='Tanggal dibuat')
})

# UPDATED: Replaced t_book_id with book_id (from search), added filtered_title
book_info_full_model = api.model('BookInfoFull', {
    'book_title': fields.String(description='Judul buku'),
    'filtered_title': fields.String(description='Slug untuk URL (hasil filter dari book_title)'),
    'book_pic': fields.String(description='URL poster'),
    'special_desc': fields.String(description='Deskripsi spesial'),
    'chapter_count': fields.Integer(description='Total chapter'),
    'book_id': fields.String(description='ID buku (dari hasil /search menggunakan filtered_title)'),
    'chapter_base': fields.List(fields.Nested(chapter_info_model), description='Semua chapter (FULL)')
})

bookshelf_full_model = api.model('BookshelfFull', {
    'bookshelf_name': fields.String(description='Nama bookshelf'),
    'books': fields.List(fields.Nested(book_info_full_model), description='Semua buku (FULL - no limit)')
})

error_model = api.model('Error', {
    'error': fields.String(description='Pesan error'),
    'details': fields.String(description='Detail error')
})


# ============== REELSHORT API CLASS ==============
class ReelShortAPI:
    """Kelas untuk berinteraksi dengan API ReelShort"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Referer": "https://www.reelshort.com/",
            "Origin": "https://www.reelshort.com"
        }
        self.base_url = None
        self.build_id = None
        self._update_build_id()

    def _update_build_id(self):
        """Get latest build ID from ReelShort homepage"""
        try:
            home_url = "https://www.reelshort.com/id"
            logger.info(f"Fetching build ID from {home_url}")
            response = requests.get(home_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Look for buildId in the HTML
            build_id_match = re.search(r'"buildId":"([^"]+)"', response.text)
            if build_id_match:
                self.build_id = build_id_match.group(1)
                self.base_url = f"https://www.reelshort.com/_next/data/{self.build_id}/id"
                logger.info(f"Successfully updated build ID: {self.build_id}")
            else:
                # Try alternative pattern
                build_id_match = re.search(r'/id/_next/data/([^/]+)/', response.text)
                if build_id_match:
                    self.build_id = build_id_match.group(1)
                    self.base_url = f"https://www.reelshort.com/_next/data/{self.build_id}/id"
                    logger.info(f"Updated build ID (alt pattern): {self.build_id}")
                else:
                    raise Exception("Build ID pattern not found in HTML")
                    
        except Exception as e:
            logger.error(f"Error getting build ID: {e}")
            # Fallback to hardcoded build ID (may need manual update)
            self.build_id = "acf624d"
            self.base_url = f"https://www.reelshort.com/_next/data/{self.build_id}/id"
            logger.warning(f"Using fallback build ID: {self.build_id}")

    def _make_request(self, url):
        """Make request with auto-retry on build ID expiration"""
        try:
            logger.debug(f"Making request to: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            
            # If we get HTML instead of JSON, build ID might be expired
            if 'text/html' in response.headers.get('Content-Type', ''):
                logger.warning("Received HTML instead of JSON, build ID may be expired")
                self._update_build_id()
                # Retry with new build ID
                url = url.replace(f"/_next/data/{self.build_id}/id", f"/_next/data/{self.build_id}/id")
                response = requests.get(url, headers=self.headers, timeout=15)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise

    def search(self, keywords):
        """Mencari drama/buku berdasarkan keyword"""
        encoded_keywords = keywords.replace(" ", "+")
        url = f"{self.base_url}/search.json?keywords={encoded_keywords}"

        try:
            data = self._make_request(url)
            books = data.get("pageProps", {}).get("books", [])
            results = []

            for book in books:
                filtered_title = self._filter_title(book.get("book_title", ""))
                results.append({
                    "book_id": book.get("_id"),
                    "book_title": book.get("book_title"),
                    "filtered_title": filtered_title,
                    "book_pic": book.get("book_pic"),
                    "chapter_count": book.get("chapter_count", 0)
                })
            return results
        except Exception as e:
            logger.error(f"Error search: {e}")
            return []

    def get_episodes(self, book_id, filtered_title):
        """Mendapatkan daftar episode dari sebuah buku"""
        url = f"{self.base_url}/movie/{filtered_title}-{book_id}.json?slug={filtered_title}-{book_id}"

        try:
            data = self._make_request(url)
            book_data = data.get("pageProps", {}).get("data", {})
            episodes = book_data.get("online_base", [])

            results = []
            for ep in episodes:
                results.append({
                    "episode": ep.get("serial_number"),
                    "chapter_id": ep.get("chapter_id")
                })
            return results
        except Exception as e:
            logger.error(f"Error get episodes: {e}")
            return []

    def get_video_url(self, episode_num, filtered_title, book_id, chapter_id):
        """Mendapatkan URL video dari sebuah episode"""
        url = f"{self.base_url}/episodes/episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}.json?play_time=1&slug=episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}"

        try:
            data = self._make_request(url)
            episode_data = data.get("pageProps", {}).get("data", {})

            return {
                "video_url": episode_data.get("video_url", ""),
                "serial_number": episode_data.get("serial_number", 0),
                "duration": episode_data.get("duration", 0)
            }
        except Exception as e:
            logger.error(f"Error get video: {e}")
            return None

    def _get_raw_bookshelves(self):
        """Get raw bookshelf data from ReelShort"""
        target_url = f"https://www.reelshort.com/_next/data/{self.build_id}/id.json"
        logger.info(f"Fetching bookshelves from: {target_url}")
        
        try:
            data = self._make_request(target_url)
            
            # Debug: print structure
            page_props = data.get("pageProps", {})
            fallback = page_props.get("fallback", {})
            hall_info = fallback.get("/api/video/hall/info", {})
            book_shelf_list = hall_info.get("bookShelfList", [])
            
            logger.info(f"Found {len(book_shelf_list)} bookshelves")
            for shelf in book_shelf_list:
                logger.debug(f" - {shelf.get('bookshelf_name')}")
            
            return book_shelf_list
            
        except Exception as e:
            logger.error(f"Error fetching bookshelves: {e}")
            return None

    def _get_book_id_from_search(self, filtered_title):
        """Get book_id from search results using filtered_title"""
        try:
            # Search menggunakan filtered_title sebagai keyword
            search_results = self.search(filtered_title)
            
            # Cari hasil yang filtered_title-nya cocok
            for result in search_results:
                if result.get('filtered_title') == filtered_title:
                    return result.get('book_id')
            
            # Jika tidak cocok persis, coba cocokkan dengan book_title
            for result in search_results:
                if self._filter_title(result.get('book_title', '')) == filtered_title:
                    return result.get('book_id')
            
            logger.warning(f"Book ID not found for filtered_title: {filtered_title}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting book_id from search: {e}")
            return None

    def _parse_shelf_data(self, shelf):
        """Parse shelf data into structured format (FULL - no limits)"""
        shelf_name = shelf.get("bookshelf_name")
        books = shelf.get("books", [])
        
        logger.info(f"Parsing shelf '{shelf_name}' with {len(books)} books")
        
        shelf_data = {
            "bookshelf_name": shelf_name,
            "books": []
        }
        
        for book in books:
            book_title = book.get("book_title", "")
            # Generate filtered_title dari book_title
            filtered_title = self._filter_title(book_title)
            
            # Dapatkan book_id dari hasil search menggunakan filtered_title
            book_id = self._get_book_id_from_search(filtered_title)
            
            book_info = {
                "book_title": book_title,
                "filtered_title": filtered_title,
                "book_pic": book.get("book_pic"),
                "special_desc": book.get("special_desc"),
                "chapter_count": book.get("chapter_count"),
                "book_id": book_id,  # Dari hasil /search, None jika tidak ditemukan
                "chapter_base": []
            }
            
            chapter_base = book.get("chapter_base", [])
            # FULL - no limit, take all chapters
            for chapter in chapter_base:
                chapter_info = {
                    "chapter_id": chapter.get("chapter_id"),
                    "chapter_name": chapter.get("chapter_name"),
                    "like_count": chapter.get("like_count"),
                    "publish_at": chapter.get("publish_at"),
                    "create_time": chapter.get("create_time")
                }
                book_info["chapter_base"].append(chapter_info)
            
            shelf_data["books"].append(book_info)
        
        return shelf_data

    def get_drama_dub(self):
        """Get 'Drama dengan dub' bookshelf - FULL DATA"""
        book_shelf_list = self._get_raw_bookshelves()
        if book_shelf_list is None:
            return None, "Failed to fetch bookshelf data"
        
        for shelf in book_shelf_list:
            if shelf.get("bookshelf_name") == "Drama dengan Dub🎧":
                return self._parse_shelf_data(shelf), None
        
        # List available shelves for debugging
        available = [s.get("bookshelf_name") for s in book_shelf_list]
        return None, f"'Drama dengan dub' not found. Available: {available}"

    def get_new_release(self):
        """Get 'Rilis Baru' bookshelf - FULL DATA"""
        book_shelf_list = self._get_raw_bookshelves()
        if book_shelf_list is None:
            return None, "Failed to fetch bookshelf data"
        
        for shelf in book_shelf_list:
            if shelf.get("bookshelf_name") == "Rilis Baru💥":
                return self._parse_shelf_data(shelf), None
        
        available = [s.get("bookshelf_name") for s in book_shelf_list]
        return None, f"'Rilis Baru' not found. Available: {available}"

    def get_recommended(self):
        """Get 'Lebih Direkomendasikan' bookshelf - FULL DATA"""
        book_shelf_list = self._get_raw_bookshelves()
        if book_shelf_list is None:
            return None, "Failed to fetch bookshelf data"
        
        for shelf in book_shelf_list:
            if shelf.get("bookshelf_name") == "Lebih Direkomendasikan 🔍":
                return self._parse_shelf_data(shelf), None
        
        available = [s.get("bookshelf_name") for s in book_shelf_list]
        return None, f"'Lebih Direkomendasikan' not found. Available: {available}"

    def _filter_title(self, title):
        """Membersihkan judul untuk digunakan dalam URL"""
        filtered = title.lower()
        filtered = re.sub(r'[^a-z0-9]+', ' ', filtered)
        filtered = re.sub(r'\s+', ' ', filtered).strip()
        filtered = filtered.replace(' ', '-')
        return filtered


reelshort_client = ReelShortAPI()

# ============== PARSERS ==============
search_parser = reqparse.RequestParser()
search_parser.add_argument('keywords', type=str, required=True, help='Kata kunci pencarian', location='args')

episodes_parser = reqparse.RequestParser()
episodes_parser.add_argument('filtered_title', type=str, required=True, help='Slug dari hasil search', location='args')

video_parser = reqparse.RequestParser()
video_parser.add_argument('filtered_title', type=str, required=True, help='Slug dari hasil search', location='args')
video_parser.add_argument('chapter_id', type=str, required=True, help='ID chapter dari hasil episodes', location='args')


# ============== ROUTES ==============

# STEP 1: SEARCH
@ns.route('/search')
class SearchResource(Resource):
    """STEP 1: Cari drama - Mulai dari sini"""

    @ns.doc(
        'search_books',
        description='STEP 1: Cari drama berdasarkan kata kunci. Simpan book_id dan filtered_title untuk step 2.'
    )
    @ns.expect(search_parser)
    @ns.marshal_with(search_response_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    def get(self):
        """STEP 1: Cari drama berdasarkan kata kunci"""
        args = search_parser.parse_args()
        keywords = args['keywords']

        if not keywords:
            api.abort(400, 'Keywords required')

        results = reelshort_client.search(keywords)
        return {'results': results}


# STEP 2: EPISODES
@ns.route('/episodes/<string:book_id>')
@ns.param('book_id', 'Dari field book_id hasil search (step 1)')
class EpisodesResource(Resource):
    """STEP 2: Dapatkan daftar episode - Gunakan book_id dari step 1"""

    @ns.doc(
        'get_episodes',
        description='STEP 2: Dapatkan daftar episode. Gunakan book_id dan filtered_title dari step 1. Simpan episode dan chapter_id untuk step 3.'
    )
    @ns.expect(episodes_parser)
    @ns.marshal_with(episodes_response_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    def get(self, book_id):
        """STEP 2: Dapatkan daftar episode"""
        args = episodes_parser.parse_args()
        filtered_title = args['filtered_title']

        if not filtered_title:
            api.abort(400, 'filtered_title required')

        episodes = reelshort_client.get_episodes(book_id, filtered_title)
        return {'episodes': episodes}


# STEP 3: VIDEO
@ns.route('/video/<string:book_id>/<int:episode_num>')
@ns.param('book_id', 'Dari field book_id hasil search (step 1)')
@ns.param('episode_num', 'Dari field episode hasil episodes (step 2)')
class VideoResource(Resource):
    """STEP 3: Dapatkan URL video - Gunakan semua data dari step 1 & 2"""

    @ns.doc(
        'get_video',
        description='STEP 3: Dapatkan URL video. Gunakan book_id (step 1), filtered_title (step 1), episode_num (step 2), dan chapter_id (step 2).'
    )
    @ns.expect(video_parser)
    @ns.marshal_with(video_data_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(404, 'Video Not Found', error_model)
    def get(self, book_id, episode_num):
        """STEP 3: Dapatkan URL video episode"""
        args = video_parser.parse_args()
        filtered_title = args['filtered_title']
        chapter_id = args['chapter_id']

        if not filtered_title or not chapter_id:
            api.abort(400, 'filtered_title and chapter_id required')

        video_data = reelshort_client.get_video_url(
            episode_num, filtered_title, book_id, chapter_id
        )

        if not video_data or not video_data.get('video_url'):
            api.abort(404, 'Video not found')

        episodes_list = reelshort_client.get_episodes(book_id, filtered_title)
        next_episode = None

        for i, ep in enumerate(episodes_list):
            if ep['episode'] == episode_num and i + 1 < len(episodes_list):
                next_episode = {
                    'episode': episodes_list[i + 1]['episode'],
                    'chapter_id': episodes_list[i + 1]['chapter_id']
                }
                break

        return {
            'video_url': video_data['video_url'],
            'episode': video_data['serial_number'],
            'duration': video_data['duration'],
            'next_episode': next_episode
        }


# ============== NEW: SEPARATE BOOKSHELF ENDPOINTS (FULL DATA) ==============

@ns.route('/dramadub')
class DramaDubResource(Resource):
    """Get 'Drama dengan dub' bookshelf - FULL UNLIMITED DATA"""

    @ns.doc(
        'get_drama_dub',
        description='Mendapatkan semua data dari bookshelf "Drama dengan dub".'
    )
    @ns.marshal_with(bookshelf_full_model)
    @ns.response(200, 'Success')
    @ns.response(404, 'Bookshelf Not Found', error_model)
    @ns.response(500, 'Server Error', error_model)
    def get(self):
        """Get Drama dengan dub - FULL DATA"""
        result, error = reelshort_client.get_drama_dub()
        
        if error:
            if "Failed to fetch" in error:
                api.abort(500, error)
            else:
                api.abort(404, error)
        
        return result


@ns.route('/newrelease')
class NewReleaseResource(Resource):
    """Get 'Rilis Baru' bookshelf - FULL UNLIMITED DATA"""

    @ns.doc(
        'get_new_release',
        description='Mendapatkan semua data dari bookshelf "Rilis Baru".'
    )
    @ns.marshal_with(bookshelf_full_model)
    @ns.response(200, 'Success')
    @ns.response(404, 'Bookshelf Not Found', error_model)
    @ns.response(500, 'Server Error', error_model)
    def get(self):
        """Get Rilis Baru - FULL DATA"""
        result, error = reelshort_client.get_new_release()
        
        if error:
            if "Failed to fetch" in error:
                api.abort(500, error)
            else:
                api.abort(404, error)
        
        return result


@ns.route('/recommend')
class RecommendResource(Resource):
    """Get 'Lebih Direkomendasikan' bookshelf - FULL UNLIMITED DATA"""

    @ns.doc(
        'get_recommended',
        description='Mendapatkan semua data dari bookshelf "Lebih Direkomendasikan".'
    )
    @ns.marshal_with(bookshelf_full_model)
    @ns.response(200, 'Success')
    @ns.response(404, 'Bookshelf Not Found', error_model)
    @ns.response(500, 'Server Error', error_model)
    def get(self):
        """Get Lebih Direkomendasikan - FULL DATA"""
        result, error = reelshort_client.get_recommended()
        
        if error:
            if "Failed to fetch" in error:
                api.abort(500, error)
            else:
                api.abort(404, error)
        
        return result


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
