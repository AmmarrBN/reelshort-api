from flask import Flask
from flask_restx import Api, Resource, fields, reqparse
import requests
import re

app = Flask(__name__)

# =============================
# SWAGGER CONFIG
# =============================
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


# =============================
# MODELS
# =============================
search_result_model = api.model('SearchResult', {
    'book_id': fields.String(required=True),
    'book_title': fields.String,
    'filtered_title': fields.String,
    'book_pic': fields.String,
    'chapter_count': fields.Integer
})

search_response_model = api.model('SearchResponse', {
    'results': fields.List(fields.Nested(search_result_model))
})

episode_model = api.model('Episode', {
    'episode': fields.Integer,
    'chapter_id': fields.String
})

episodes_response_model = api.model('EpisodesResponse', {
    'episodes': fields.List(fields.Nested(episode_model))
})

video_data_model = api.model('VideoData', {
    'video_url': fields.String,
    'episode': fields.Integer,
    'duration': fields.Integer,
    'next_episode': fields.Nested(episode_model, allow_null=True)
})

error_model = api.model('Error', {
    'error': fields.String
})


# =============================
# REELSHORT CLIENT
# =============================
class ReelShortAPI:

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.reelshort.com/",
            "Origin": "https://www.reelshort.com"
        }
        self.base_url = "https://www.reelshort.com/_next/data/acf624d/id"

    def search(self, keywords):
        encoded = keywords.replace(" ", "+")
        url = f"{self.base_url}/search.json?keywords={encoded}"

        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()

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
            print("Search error:", e)
            return []

    def get_episodes(self, book_id, filtered_title):
        url = f"{self.base_url}/movie/{filtered_title}-{book_id}.json?slug={filtered_title}-{book_id}"

        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()

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
            print("Episodes error:", e)
            return []

    def get_video_url(self, episode_num, filtered_title, book_id, chapter_id):
        url = f"{self.base_url}/episodes/episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}.json?play_time=1&slug=episode-{episode_num}-{filtered_title}-{book_id}-{chapter_id}"

        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()

            episode_data = data.get("pageProps", {}).get("data", {})

            return {
                "video_url": episode_data.get("video_url", ""),
                "serial_number": episode_data.get("serial_number", 0),
                "duration": episode_data.get("duration", 0)
            }
        except Exception as e:
            print("Video error:", e)
            return None

    def _filter_title(self, title):
        filtered = title.lower()
        filtered = re.sub(r'[^a-z0-9]+', ' ', filtered)
        filtered = re.sub(r'\s+', ' ', filtered).strip()
        return filtered.replace(" ", "-")


reelshort_client = ReelShortAPI()


# =============================
# PARSERS
# =============================
search_parser = reqparse.RequestParser()
search_parser.add_argument('keywords', type=str, required=True, location='args')

episodes_parser = reqparse.RequestParser()
episodes_parser.add_argument('filtered_title', type=str, required=True, location='args')

video_parser = reqparse.RequestParser()
video_parser.add_argument('filtered_title', type=str, required=True, location='args')
video_parser.add_argument('chapter_id', type=str, required=True, location='args')


# =============================
# ROUTES
# =============================

@ns.route('/search')
class SearchResource(Resource):

    @ns.expect(search_parser)
    @ns.marshal_with(search_response_model)
    def get(self):
        args = search_parser.parse_args()
        results = reelshort_client.search(args['keywords'])
        return {'results': results}


@ns.route('/episodes/<string:book_id>')
class EpisodesResource(Resource):

    @ns.expect(episodes_parser)
    @ns.marshal_with(episodes_response_model)
    def get(self, book_id):
        args = episodes_parser.parse_args()
        episodes = reelshort_client.get_episodes(book_id, args['filtered_title'])
        return {'episodes': episodes}


@ns.route('/video/<string:book_id>/<int:episode_num>')
class VideoResource(Resource):

    @ns.expect(video_parser)
    @ns.marshal_with(video_data_model)
    def get(self, book_id, episode_num):
        args = video_parser.parse_args()

        video_data = reelshort_client.get_video_url(
            episode_num,
            args['filtered_title'],
            book_id,
            args['chapter_id']
        )

        if not video_data or not video_data.get("video_url"):
            api.abort(404, "Video not found")

        episodes_list = reelshort_client.get_episodes(book_id, args['filtered_title'])
        next_episode = None

        for i, ep in enumerate(episodes_list):
            if ep['episode'] == episode_num and i + 1 < len(episodes_list):
                next_episode = episodes_list[i + 1]
                break

        return {
            'video_url': video_data['video_url'],
            'episode': video_data['serial_number'],
            'duration': video_data['duration'],
            'next_episode': next_episode
        }


# =============================
# WAJIB UNTUK VERCEL
# =============================
app = app


if __name__ == '__main__':
    app.run(debug=True)
