# FOODOJOの動画ごとに「foodojo.link/動画ID」のページを作る（インスタでサムネが出る・FOODOJOの動画だけ開ける）
# GitHub Actionsが15分ごとに自動で動かす。FOODOJO以外や古い動画を足したい時は ids.txt に1行1つURLを書く。
import glob, html, json, os, re, urllib.parse, urllib.request

CHANNELS = ['UCBFPVZG3M0O7EIjdOsUW_Cg']   # FOODOJO (miyu)
CHANNEL_IMAGE = 'https://yt3.googleusercontent.com/6RfbwRP4JDNfI8rQxYOFeVFCSf0MkROYD3sIXDyODpUhWa7fGDCs4lFvXH2u1WFK0iGHV_AwNw=s900-c-k-c0x00ffffff-no-rj'
ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (foodojo.link builder)'}


def get(url, method='GET'):
    req = urllib.request.Request(url, headers=UA, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def video_ids():
    ids = []
    for ch in CHANNELS:
        try:
            _, xml = get('https://www.youtube.com/feeds/videos.xml?channel_id=' + ch)
            ids += re.findall(r'<yt:videoId>([\w-]{11})</yt:videoId>', xml.decode('utf-8'))
        except Exception as e:
            print('feed error', ch, e)
    p = os.path.join(ROOT, 'ids.txt')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            m = re.search(r'(?:youtu\.be/|v=|/shorts/|/live/)([\w-]{11})', line) or re.fullmatch(r'([\w-]{11})', line)
            if m and not line.startswith('#'):
                ids.append(m.group(1))
    for f in glob.glob(os.path.join(ROOT, '*.html')):          # 前に作ったページも作り直す
        name = os.path.basename(f)[:-5]
        if re.fullmatch(r'[\w-]{11}', name):
            ids.append(name)
    return list(dict.fromkeys(ids))


def cached(v):
    f = os.path.join(ROOT, v + '.html')
    if not os.path.exists(f):
        return None
    s = open(f, encoding='utf-8').read()
    t = re.search(r'property="og:title" content="([^"]*)"', s)
    i = re.search(r'property="og:image" content="([^"]*)"', s)
    if t and i:
        return html.unescape(t.group(1)), i.group(1)
    return None


def info(v):
    c = cached(v)
    if c:
        return c
    title, image = 'FOODOJO ▶ YouTube', 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % v
    try:
        _, b = get('https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=' + v)
        title = json.loads(b).get('title') or title
    except Exception as e:
        print('oembed error', v, e)
    try:
        s, _ = get('https://i.ytimg.com/vi/%s/maxresdefault.jpg' % v, 'HEAD')
        if s == 200:
            image = 'https://i.ytimg.com/vi/%s/maxresdefault.jpg' % v
    except Exception:
        pass
    return title, image


# ---- アゴダなど外のサイトへの短いリンク（links.txt：短い名前 | URL | 表示する名前 | 動画ID(任意)）
LINK_TPL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="FOODOJO">
<meta property="og:title" content="{t}">
<meta property="og:description" content="タップすると{site}で開きます">
{img}<meta property="og:url" content="https://foodojo.link/{slug}">
<meta http-equiv="refresh" content="3;url={u}">
<style>
  body{{margin:0;font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;background:#111;color:#fff;
       min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center}}
  .box{{width:min(92vw,460px);padding:28px 20px}} h1{{font-size:20px}} p{{color:#bbb;font-size:14px}}
  .btn{{display:block;margin:18px 0;padding:18px;border-radius:14px;background:#ff0033;color:#fff;font-size:19px;font-weight:700;text-decoration:none}}
  .note{{position:fixed;bottom:8px;left:0;right:0;color:#555;font-size:10px}}
</style>
<script>
  var GA_ID = 'G-QDD5VCFLEY'; window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}}
  var s = document.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s); gtag('js', new Date()); gtag('config', GA_ID);
</script>
</head>
<body>
<div class="box"><h1>{t}</h1><p>{site}を開いています…</p><a class="btn" href="{u}">{site}で見る</a></div>
<div class="note">このページはGoogleアナリティクスでクリック数を数えています</div>
<script>
  var go = function () {{ location.replace({uj}); }}, done = false;
  gtag('event', 'open_link', {{ link: '{slug}', video: 'link:{slug}', dest: '{site}', transport_type: 'beacon', event_callback: function () {{ if (!done) {{ done = true; go(); }} }} }});
  setTimeout(function () {{ if (!done) {{ done = true; go(); }} }}, 1200);
</script>
</body>
</html>
"""

def build_links():
    p = os.path.join(ROOT, 'links.txt')
    if not os.path.exists(p): return
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = [x.strip() for x in line.split('|')]
        if len(parts) < 2 or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,40}', parts[0]) or len(parts[0]) == 11:
            print('skip link', line); continue
        slug, url = parts[0], parts[1]
        title = parts[2] if len(parts) > 2 and parts[2] else 'FOODOJO'
        vid = parts[3] if len(parts) > 3 else ''
        host = re.sub(r'^www\.', '', urllib.parse.urlparse(url).netloc)
        site = 'アゴダ' if 'agoda' in host else ('楽天トラベル' if 'rakuten' in host else ('Booking.com' if 'booking' in host else host))
        img = ''
        if re.fullmatch(r'[\w-]{11}', vid):
            img = '<meta property="og:image" content="https://i.ytimg.com/vi/%s/hqdefault.jpg">\n' % vid
        page = LINK_TPL.format(t=html.escape(title + '｜' + site + 'で見る', quote=True), site=html.escape(site), img=img,
                               slug=slug, u=html.escape(url, quote=True), uj=json.dumps(url))
        open(os.path.join(ROOT, slug + '.html'), 'w', encoding='utf-8').write(page)
        print('link', slug, '->', host)


def main():
    tpl = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(tpl)   # 404.htmlはいつもindex.htmlと同じ
    # インスタのプロフィール用：foodojo.link/youtube → FOODOJOのチャンネルを開く
    ch_og = ('<!--OG-->\n'
             '<meta property="og:type" content="website">\n'
             '<meta property="og:site_name" content="FOODOJO">\n'
             '<meta property="og:title" content="FOODOJO (miyu) - YouTube">\n'
             '<meta property="og:description" content="タップするとYouTubeアプリで開きます">\n'
             '<meta property="og:image" content="%s">\n'
             '<meta property="og:url" content="https://foodojo.link/youtube">\n'
             '<!--/OG-->') % CHANNEL_IMAGE
    ch = re.sub(r'<!--OG-->.*?<!--/OG-->', lambda m: ch_og, tpl, flags=re.S)
    ch = ch.replace('<title>FOODOJO ▶ YouTube</title>', '<title>FOODOJO (miyu) - YouTube</title>')
    open(os.path.join(ROOT, 'youtube.html'), 'w', encoding='utf-8').write(ch)
    build_links()
    for v in video_ids():
        title, image = info(v)
        t = html.escape(title, quote=True)
        og = ('<!--OG-->\n'
              '<meta property="og:type" content="video.other">\n'
              '<meta property="og:site_name" content="FOODOJO">\n'
              '<meta property="og:title" content="%s">\n'
              '<meta property="og:description" content="タップするとYouTubeアプリで開きます">\n'
              '<meta property="og:image" content="%s">\n'
              '<meta property="og:image:width" content="1280">\n'
              '<meta property="og:image:height" content="720">\n'
              '<meta property="og:url" content="https://foodojo.link/%s">\n'
              '<meta name="twitter:card" content="summary_large_image">\n'
              '<!--/OG-->') % (t, image, v)
        page = re.sub(r'<!--OG-->.*?<!--/OG-->', lambda m: og, tpl, flags=re.S)
        page = page.replace('<title>FOODOJO ▶ YouTube</title>', '<title>%s</title>' % t)
        page = page.replace("var VIDEO_ID = '';", "var VIDEO_ID = '%s';" % v)
        out = os.path.join(ROOT, v + '.html')
        old = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
        if page != old:
            open(out, 'w', encoding='utf-8').write(page)
            print('made', v, title)


if __name__ == '__main__':
    main()
