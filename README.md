# TikTok DL

A simple command-line tool to download TikTok videos and photo slideshows without watermarks. Just paste in a URL and it handles the rest.

---

## Requirements

- Python 3.7 or newer
- `yt-dlp` (the script will install this automatically if it's missing)

That's genuinely it. No accounts, no API keys, nothing weird.

---

## How to use it

```bash
python tiktok_dl.py
```

You'll get a menu with a few options:

1. **Download a video** — paste in any TikTok video URL and it downloads it in the best available quality, no watermark
2. **Download photos** — for slideshow/photo posts, this grabs all the individual images and drops them in a `photos/` subfolder
3. **Change output folder** — by default files go to `~/TikTok Downloads/`, but you can point it anywhere
4. **Exit** — does what it says

---

## Where do files end up?

By default everything saves to:

```
~/TikTok Downloads/
```

Photo slideshows go into a `photos/` subfolder inside that. Filenames are formatted as `username_videoid.ext` so things don't clash if you download a bunch at once.

---

## URL formats that work

Pretty much any TikTok URL should work:

```
https://www.tiktok.com/@username/video/1234567890
https://vm.tiktok.com/XXXXXXX/   ← short links work too
```

---

## Troubleshooting

**"Download failed" error**
- Make sure the account is public — private accounts won't work
- Try copying the URL fresh from your browser rather than the share sheet, sometimes those add tracking params that break things

**Photos aren't downloading**
- If the post is actually a video (not a slideshow), use option 1 instead

**yt-dlp errors about format**
- Run `pip install -U yt-dlp` to update it — TikTok changes their stuff pretty often and yt-dlp patches keep up with it

---

## Notes

This is built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp) which does the heavy lifting. Only download content you have the right to download — respect creators.
