const express = require("express");
const cors = require("cors");
const ytdl = require("ytdl-core");

const app = express();
const PORT = 5000;

app.use(cors());

app.get("/", (req, res) => {
  res.send("✅ YouTube Downloader Backend Running");
});

app.get("/download", async (req, res) => {
  const videoURL = req.query.url;
  if (!videoURL) {
    return res.status(400).json({ error: "❌ URL is required" });
  }

  try {
    // Get video info
    const info = await ytdl.getInfo(videoURL);
    const title = info.videoDetails.title.replace(/[^\w\s]/gi, "_");

    res.header("Content-Disposition", `attachment; filename="${title}.mp4"`);

    ytdl(videoURL, { format: "mp4", quality: "highest" }).pipe(res);
  } catch (err) {
    console.error("Download Error:", err.message);
    return res.status(500).json({ error: "⚠️ Failed to fetch video info" });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
