# FOODOJOの動画ごとに「foodojo.link/動画ID」のページを作る（インスタなどでサムネが出るように）
# GitHub Actionsが1時間ごとに自動で動かす。手で足したい動画は ids.txt に1行1つ書く。
import html, json, os, re, urllib.request

CHANNELS = ['UCBFPVZG3M0O7EIjdOsUW_Cg']   # FOODOJO (miyu)
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
            m = re.search(r'(?:youtu\.be/|v=|/shorts/|/live/)?([\w-]{11})', line.strip())
            if m and not line.strip().startswith('#'):
                ids.append(m.group(1))
    return list(dict.fromkeys(ids))


def info(v):
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


def main():
    tpl = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(tpl)   # 404.htmlはいつもindex.htmlと同じ
    for v in video_ids():
        out = os.path.join(ROOT, v + '.html')
        if os.path.exists(out) and 'og:image' in open(out, encoding='utf-8').read():
            continue
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
        open(out, 'w', encoding='utf-8').write(page)
        print('made', v, title)


if __name__ == '__main__':
    main()
