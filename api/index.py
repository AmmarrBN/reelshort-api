from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields, reqparse
import requests
import re
import os

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

# Models
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

error_model = api.model('Error', {
    'error': fields.String(description='Pesan error')
})


class ReelShortAPI:
    """Kelas untuk berinteraksi dengan API ReelShort"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.reelshort.com/",
            "Origin": "https://www.reelshort.com"
        }
        self.base_url = "https://www.reelshort.com/_next/data/acf624d/id"

    def search(self, keywords):
        """Mencari drama/buku berdasarkan keyword"""
        encoded_keywords = keywords.replace(" ", "+")
        url = f"{self.base_url}/search.json?keywords={encoded_keywords}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

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
            print(f"Error search: {e}")
            return []

    def get_episodes(self, book_id, filtered_title):
        """Mendapatkan daftar episode dari sebuah buku"""
        url = f"{self.base_url}/movie/{filtered_title}-{book_id}.json?slug={filtered_title}-{book_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

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
            print(f"Error get episodes: {e}")
            return []

    def get_video_url(self, episode_num, filtered_title, book_id, chapter_id):
        """Mendapatkan URL video dari sebuah episode"""
        url = f"{self.base_url}/episodes/episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}.json?play_time=1&slug=episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            episode_data = data.get("pageProps", {}).get("data", {})

            return {
                "video_url": episode_data.get("video_url", ""),
                "serial_number": episode_data.get("serial_number", 0),
                "duration": episode_data.get("duration", 0)
            }
        except Exception as e:
            print(f"Error get video: {e}")
            return None

    def _filter_title(self, title):
        """Membersihkan judul untuk digunakan dalam URL"""
        filtered = title.lower()
        filtered = re.sub(r'[^a-z0-9]+', ' ', filtered)
        filtered = re.sub(r'\s+', ' ', filtered).strip()
        filtered = filtered.replace(' ', '-')
        return filtered


reelshort_client = ReelShortAPI()

# Parsers
search_parser = reqparse.RequestParser()
search_parser.add_argument('keywords', type=str, required=True, help='Kata kunci pencarian', location='args')

episodes_parser = reqparse.RequestParser()
episodes_parser.add_argument('filtered_title', type=str, required=True, help='Slug dari hasil search', location='args')

video_parser = reqparse.RequestParser()
video_parser.add_argument('filtered_title', type=str, required=True, help='Slug dari hasil search', location='args')
video_parser.add_argument('chapter_id', type=str, required=True, help='ID chapter dari hasil episodes', location='args')


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


# Handler untuk Vercel Serverless
def handler(request, **kwargs):
    """Handler function untuk Vercel Serverless"""
    with app.test_client() as client:
        # Build URL dengan query string
        url = request.path
        if request.query_string:
            url = f"{url}?{request.query_string.decode('utf-8')}"
        
        # Pilih method
        method = request.method
        headers = dict(request.headers)
        data = request.get_data() if request.data else None
        
        response = client.open(
            url,
            method=method,
            headers=headers,
            data=data
        )
        
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True)
        }


# Untuk development lokal
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
