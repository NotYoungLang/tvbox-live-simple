# tvbox-live-simple

Filtered TVBox live source for MiTV-ASTP0 (Xiaomi TV, Android 9).

- `live_simple.m3u` - 198 channels, ads removed (timestamp placeholder + paid channel group), de-duplicated.
- `make_live_simple.py` - regenerate from Guovin/iptv-api gd branch.

TVBox 配置地址（直播源）:
`https://raw.githubusercontent.com/NotYoungLang/tvbox-live-simple/main/live_simple.m3u`

If direct raw is slow in China, use a gh-proxy prefix:
`https://gh-proxy.com/https://raw.githubusercontent.com/NotYoungLang/tvbox-live-simple/main/live_simple.m3u`
