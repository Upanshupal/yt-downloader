from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "✅ Backend is running!"

@app.route("/download", methods=["GET"])
def download_video():
    url = request.args.get("url")
    quality = request.args.get("quality", "720p")

    if not url:
        return jsonify({"error": "Missing video URL"}), 400

    ydl_opts = {
        "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]",
        "noplaylist": True,
        "quiet": True,
        "outtmpl": "%(title)s.%(ext)s"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title"),
                "url": info.get("webpage_url"),
                "formats": [
                    {"format_id": f["format_id"], "resolution": f.get("height")}
                    for f in info.get("formats", []) if f.get("height")
                ]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
