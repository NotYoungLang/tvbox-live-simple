# -*- coding: utf-8 -*-
"""Generate a filtered, de-duplicated m3u from Guovin iptv-api gd branch.

Removes the two ad-heavy groups (timestamp placeholder + paid channels),
de-duplicates by channel name (keeps first line), and writes a correct
gd-branch EPG header. Output: live_simple.m3u next to this script.
"""
import re
import urllib.request
import ssl

SRC = "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv4/result.m3u"
OUT = "live_simple.m3u"
RAW = "live_result.m3u"
EPG = "#EXTM3U x-tvg-url=\"https://gh-proxy.com/https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/epg/epg.gz\""
DROP_GROUPS = {"🕘️更新时间", "💰央视付费频道"}


def download():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        data = r.read().decode("utf-8", "ignore")
    with open(RAW, "w", encoding="utf-8") as f:
        f.write(data)
    return data


def group_of(ext):
    m = re.search(r'group-title="([^"]*)"', ext)
    return m.group(1) if m else ""


def name_of(ext):
    return ext.rsplit(",", 1)[-1].strip()


def main():
    try:
        data = download()
        print("downloaded", len(data), "chars")
    except Exception as e:
        print("download failed:", e, "- using", RAW)
        data = open(RAW, encoding="utf-8").read()

    lines = data.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            url = lines[i + 1] if i + 1 < len(lines) and not lines[i + 1].startswith("#") else ""
            blocks.append((lines[i], url))
            i += 2
        else:
            i += 1
    print("original entries:", len(blocks))

    kept = [(e, u) for e, u in blocks if group_of(e) not in DROP_GROUPS]
    seen = set()
    dedup = []
    for e, u in kept:
        n = name_of(e)
        if n in seen:
            continue
        seen.add(n)
        dedup.append((e, u))

    out = [EPG]
    for e, u in dedup:
        out.extend([e, u])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("filtered entries:", len(dedup), "->", OUT)


if __name__ == "__main__":
    main()
