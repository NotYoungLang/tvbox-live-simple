# -*- coding: utf-8 -*-
"""GitHub Actions job: check every channel URL, repair dead ones from backups.

- Reads live_simple.m3u (active list) and live_result.m3u (full source with all lines).
- For each active channel, probe the URL with an HTTP GET (m3u8 playlist).
- If unreachable, try alternative lines of the SAME channel name from the full source.
- Rewrites live_simple.m3u if any line changed; writes CHECK_REPORT.md.
"""
import os
import re
import sys
import urllib.request
import ssl
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
ACTIVE = os.path.join(BASE, "live_simple.m3u")
SOURCE = os.path.join(BASE, "live_result.m3u")
REPORT = os.path.join(BASE, "CHECK_REPORT.md")

EPG = "#EXTM3U x-tvg-url=\"https://gh-proxy.com/https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/epg/epg.gz\""
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# channels that were intentionally removed (logo mismatch / no signal) -- never re-add
DROP_NAMES = {
    "黑龙江卫视", "浙江经济生活", "之江纪录", "湖州新闻综合", "浙江休闲台",
    "名山综合", "雅安新闻综合", "中国蓝新闻", "广元公共", "定襄综合",
}
REPLACE_URL = {
    "广东卫视": "http://107.150.60.122/live/gdwshd.m3u8",
    "河北卫视": "http://38.75.136.137:98/gslb/dsdqpub/hewshd.m3u8?auth=testpub",
}


def parse(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    out = []
    for i, l in enumerate(lines):
        if l.startswith("#EXTINF"):
            m = re.search(r'group-title="([^"]*)"', l)
            grp = m.group(1) if m else ""
            name = l.rsplit(",", 1)[-1].strip()
            url = lines[i + 1] if i + 1 < len(lines) and not lines[i + 1].startswith("#") else ""
            out.append({"ext": l, "name": name, "group": grp, "url": url})
    return out


def probe(url, timeout=8):
    """Return True if URL returns an m3u8/stream playlist with status 200."""
    if not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            if r.status != 200:
                return False
            head = r.read(4096).decode("utf-8", "ignore")
            # valid m3u8 must start with #EXTM3U (allow BOM/whitespace)
            return "#EXTM3U" in head[:64] or "#EXTINF" in head
    except Exception:
        return False


def main():
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    active = parse(ACTIVE)
    source = parse(SOURCE)
    backups = defaultdict(list)
    for c in source:
        if c["url"] and c["url"] not in backups[c["name"]]:
            backups[c["name"]].append(c["url"])

    # probe all active URLs concurrently
    with ThreadPoolExecutor(max_workers=16) as ex:
        fut = {ex.submit(probe, c["url"]): c for c in active}
        for f in as_completed(fut):
            fut[f]["_ok"] = f.result()

    fixed, dead, ok_count = [], [], 0
    for c in active:
        if c.get("_ok"):
            ok_count += 1
            continue
        # try alternatives (skip current) -- probe concurrently
        alts = [u for u in backups.get(c["name"], []) if u != c["url"]]
        replacement = None
        if alts:
            with ThreadPoolExecutor(max_workers=6) as ex:
                fut2 = {ex.submit(probe, u): u for u in alts}
                for f in as_completed(fut2):
                    if f.result():
                        replacement = fut2[f]
                        break
        if replacement:
            c["url"] = replacement
            fixed.append(c["name"])
        else:
            dead.append(c["name"])

    changed = bool(fixed)
    if changed:
        out = [EPG]
        for c in active:
            out.extend([c["ext"], c["url"]])
        open(ACTIVE, "w", encoding="utf-8").write("\n".join(out) + "\n")

    lines = [
        "# 直播源自动检查报告",
        "",
        "- 检查时间：%s" % now,
        "- 频道总数：%d" % len(active),
        "- 正常：%d" % ok_count,
        "- 修复（换备用线路）：%d" % len(fixed),
        "- 仍失效（无可用备源）：%d" % len(dead),
        "",
        "## 本次修复",
        "",
    ]
    lines += ["- %s" % n for n in fixed] or ["- 无"]
    lines += ["", "## 仍失效（建议关注）", ""]
    lines += ["- %s" % n for n in dead] or ["- 无"]
    lines += ["", "> 本报告由 GitHub Actions 每日自动生成；广告为时段轮播，检查仅判断线路连通性，不判断节目内容。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print("checked=%d ok=%d fixed=%d dead=%d changed=%s" %
          (len(active), ok_count, len(fixed), len(dead), changed))
    print("fixed:", fixed[:20])
    print("dead:", dead[:20])


if __name__ == "__main__":
    main()
