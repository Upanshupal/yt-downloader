# app.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
import uuid
import traceback

app = Flask(__name__)
CORS(app)  # allow frontend to call this API

# Configuration
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Normalize and clean YouTube URL (handle youtu.be and shorts)
def fix_youtube_url(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    # remove trailing parameters like ?feature=shared (we only need id)
    # handle youtu.be/ID
    m = re.search(r"youtu\.be\/([^?&/\s]+)", url)
    if m:
        vid = m.group(1)
        return f"https://www.youtube.com/watch?v={vid}"
    # handle shorts
    m2 = re.search(r"shorts\/([^?&/\s]+)", url)
    if m2:
        vid = m2.group(1)
        return f"https://www.youtube.com/watch?v={vid}"
    return url

# Basic validation for youtube url
def is_valid_youtube_url(url: str) -> bool:
    if not url:
        return False
    # after fixing we expect a watch?v=VIDEOID or youtube.com/... or youtu.be link turned into watch?v=
    pattern = re.compile(r"^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/")
    return bool(pattern.search(url))

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/videoinfo", methods=["GET"])
def get_video_info():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    url = fix_youtube_url(url)
    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        ydl_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # build formats list (include useful info)
            formats = []
            for f in info.get("formats", []):
                # show formats that have either resolution or are audio only
                fmt = {
                    "format_id": f.get("format_id") or f.get("format"),
                    "ext": f.get("ext"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                    "height": f.get("height"),
                    "width": f.get("width"),
                    "format_note": f.get("format_note"),
                    "abr": f.get("abr"),  # audio bitrate
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                }
                # include formats that look usable (either audio or video)
                if fmt["ext"] and (fmt["filesize"] or fmt["height"] or fmt["abr"]):
                    formats.append(fmt)

            # sort formats by height (desc) then by audio bitrate
            def sort_key(x):
                h = x.get("height") or 0
                abr = x.get("abr") or 0
                return (h, abr)

            formats.sort(key=sort_key, reverse=True)

            result = {
                "id": info.get("id"),
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "formats": formats,
            }
            return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to fetch video info: {str(e)}"}), 500

@app.route("/api/download", methods=["GET"])
def download_video():
    url = request.args.get("url", "").strip()
    format_id = request.args.get("format_id", "best").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    url = fix_youtube_url(url)
    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL"}), 400

    unique = uuid.uuid4().hex
    out_template = os.path.join(DOWNLOAD_FOLDER, unique + ".%(ext)s")

    ydl_opts = {
        "format": format_id,
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        # 'noplaylist': True,  # optional: prevent playlist downloads
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # prepare filename used by ytdl
            filepath = ydl.prepare_filename(info)
            # filepath should exist now
            if not os.path.exists(filepath):
                # sometimes yt-dlp writes separate files for bestvideo+bestaudio; try to find file
                # fallback: search downloads folder for files starting with unique
                candidates = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(unique)]
                if candidates:
                    filepath = os.path.join(DOWNLOAD_FOLDER, candidates[0])
                else:
                    return jsonify({"error": "Downloaded file not found"}), 500

            # create a safe download name (original title + extension)
            title_safe = info.get("title", unique).strip().replace("/", "_").replace("\\", "_")
            ext = os.path.splitext(filepath)[1].lstrip(".") or (info.get("ext") or "mp4")

            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{title_safe}.{ext}",
                mimetype="video/mp4",
            )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Download failed: {str(e)}"}), 500
    finally:
        # remove the downloaded file(s) matching unique id (best-effort cleanup)
        try:
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(unique):
                    try:
                        os.remove(os.path.join(DOWNLOAD_FOLDER, f))
                    except:
                        pass
        except:
            pass

if __name__ == "__main__":
    # run on the same port you're using (you had 10159 earlier)
    app.run(host="127.0.0.1", port=10159, debug=True)
