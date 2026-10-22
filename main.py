# -*- coding: utf-8 -*-
"""
Cướp Cờ Đáp Án AI - máy chủ game chiến thuật 1v1 .. 5v5 (Flask + Flask-SocketIO).

- Server là trọng tài: di chuyển, đạn, hạ gục, cờ, cắm cờ, chấm điểm đều do server quyết định.
- Bản đồ rộng kiểu MOBA: căn cứ 2 góc, 3 đường, sông chéo (đi chậm), rừng và bụi cỏ (núp, địch không thấy).
- Mỗi round 3 phút (10s đọc đề + 170s tranh cờ). Hết giờ mới chấm: cờ nằm ở căn cứ đội nào
  thì đội đó +100 nếu đúng, -50 nếu sai. Trong lúc chơi KHÔNG ai biết cờ nào đúng.
- Chủ phòng có thể tạm dừng cả trận. Có Cloudflare Tunnel (cloudflared) giống snake-AI.
- question.json KHÔNG được phục vụ ra web để học sinh không xem được đáp án.

Cấu hình: copy .env.example thành .env (cạnh file này). Chạy: python gunicorn.py (Gunicorn, khuyên dùng) hoặc python main.py (máy chủ dev)
"""
import io, os, re, sys, ssl, json, math, time, random, shutil, socket, hashlib, hmac, platform, tarfile
import threading, subprocess, urllib.request, traceback
from flask import Flask, send_from_directory, abort, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from socketio.exceptions import ConnectionRefusedError as RefuseConn
from werkzeug.serving import WSGIRequestHandler
try:  # long-polling: mặc định chỉ nhận 16 gói/lượt POST, client gửi input dày sẽ bị "Too many packets in payload"
    from engineio import payload as _eio_payload
    _eio_payload.Payload.max_decode_packets = 600
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))


def load_env():
    path = os.path.join(BASE, os.getenv("ENV_FILE", ".env"))
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


load_env()


def env_num(k, d):
    try:
        return type(d)(os.getenv(k, str(d)).strip())
    except ValueError:
        return d


def env_bool(k, d=False):
    return os.getenv(k, str(d)).strip().lower() in ("1", "true", "yes")


HOST = os.getenv("HOST", "0.0.0.0")
PORT = env_num("PORT", 8889)
# HTTPS trực tiếp (không qua Cloudflare Tunnel): chỉ bật khi có HTTPS_CERT hợp lệ
TLS_HOST = os.getenv("TLS_HOST", "0.0.0.0").strip() or "0.0.0.0"
TLS_PORT = env_num("TLS_PORT", 443)
HTTPS_CERT = os.getenv("HTTPS_CERT", "").strip()
HTTPS_KEY = os.getenv("HTTPS_KEY", "").strip()
TLS_REFRESH_H = env_num("TLS_REFRESH_HOURS", 12.0)  # tự tải lại chứng chỉ (hữu ích khi cert gia hạn)
TLS_DIR = os.path.join(BASE, ".tls")
QFILE = os.getenv("QUESTION_FILE", os.path.join(BASE, "question.json"))
ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*").strip()
ORIGINS = "*" if ORIGINS_RAW in ("", "*") else [o.strip().rstrip("/") for o in ORIGINS_RAW.split(",") if o.strip()]
ALLOWED_HOSTS = [h.strip().lower() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
ALLOW_ANY_HOST = not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS
TUNNEL_ENABLED = env_bool("TUNNEL", False)
TUNNEL_HOST = os.getenv("TUNNEL_HOST", "").strip()
TUNNEL_TOKEN = os.getenv("TUNNEL_TOKEN", "").strip()


def load_version():
    """Đọc version.json: chỉ client cùng "version" mới được kết nối."""
    path = os.path.join(BASE, os.getenv("VERSION_FILE", "version.json"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return str(d.get("versionName", "")).strip() or "v?", int(d.get("version", 0))
    except Exception as e:
        print("[!] Không đọc được version.json:", e)
        return "v0", 0


VERSION_NAME, VERSION = load_version()

READ_S, PLAY_S, RESULT_S = env_num("READ_SECONDS", 10), env_num("PLAY_SECONDS", 170), env_num("RESULT_SECONDS", 12)
HP, DOWN_S = env_num("HP", 3), env_num("DOWN_SECONDS", 5.0)
PTS_OK, PTS_BAD = env_num("POINTS_CORRECT", 100), env_num("POINTS_WRONG", -50)
PTS_KILL = env_num("POINTS_KILL", 20)  # điểm đội khi hạ một đối thủ
MAXLV = 5
REJOIN_S = env_num("REJOIN_SECONDS", 90)  # giữ chỗ cho người chơi mất kết nối giữa trận (giây); 0 = tắt
AFK_S = env_num("AFK_SECONDS", 60)  # đứng yên, không bấm gì quá chừng này giây giữa round thì bot chơi thay tạm thời (bấm lại là lấy lại quyền); 0 = tắt
MAX_SPECS = env_num("MAX_SPECTATORS", 30)
MM_WAIT_S = env_num("MATCH_FILL_SECONDS", 60)  # ghép trận tự động: chờ quá chừng này giây thì lấp chỗ thiếu bằng bot; 0 = tắt
T = 32; TW, TH = 80, 56; W, H = TW * T, TH * T     # bản đồ 80x56 ô
PR = 14; HZ = 20; DT = 1.0 / HZ
SPEED, CARRY_K, RIVER_K = 200.0, 0.7, 0.75
LASER_RANGE = 480.0                      # tầm ngắm/bắn của thần giữ cờ
GUARD_R, GUARD_SP = 22, 120.0            # bán kính, tốc độ thần giữ cờ (chậm hơn người chơi 200)
BSPEED, COOL = 600.0, 0.32
# Tầm bong bóng hiệu dụng lên thần giữ cờ = đạn bay + điểm xuất phát (PR+3) + bán kính trúng (GUARD_R+3)
# -> chọn BLIFE sao cho tầm đó đúng bằng LASER_RANGE: người chơi không thể bắn trúng thần từ ngoài tầm laze.
BLIFE = (LASER_RANGE - (14 + 3) - (GUARD_R + 3)) / BSPEED
SWORD_R, SWORD_COOL, SWORD_T = 58.0, 0.55, 0.25  # tầm / hồi chiêu / thời gian vung kiếm
SWORD_DMG = 2                  # kiếm: 2 sát thương / nhát (súng bóng nước: 1 / viên)
SHIELD_ARC, SHIELD_K = 1.15, 0.6  # khiên đỡ được trong ±1.15 rad (~66°) phía trước; đi chậm còn 60% khi giơ khiên
PLANT_S, STEAL_S, SEE_R = 2.0, 2.5, 170.0
UNPLANT_S = env_num("UNPLANT_SECONDS", 2.0)   # giữ F cạnh cờ nhà đã cắm chừng này giây thì nhổ được cờ lên
UNPLANT_MAX = env_num("UNPLANT_MAX", 2)       # số lần nhổ cờ tối đa của mỗi đội trong một round
UNPLANT_R = 70.0                              # phải đứng trong bán kính này quanh cờ để bắt đầu / tiếp tục nhổ

# ---------- tim hồi máu trên bản đồ, súng tên lửa, nâng cấp theo đội ----------
HEART_SPOTS_T = [(14, 30), (30, 50), (34, 12), (66, 26), (50, 6), (46, 44)]   # 6 tim (3 cặp đối xứng tâm)
HEART_RESPAWN = env_num("HEART_RESPAWN", 20.0)         # giây hồi lại sau khi có người nhặt
RK_SPOTS_T = [(7, 7), (73, 49), (7, 38), (73, 18)]      # 4 cây súng tên lửa rải 4 góc bản đồ (đối xứng tâm)
RK_RESPAWN = env_num("ROCKET_RESPAWN", 45.0)           # giây cây súng hiện lại sau khi bị nhặt
RK_AMMO, RK_SPEED, RK_TURN, RK_LIFE = 10, 340.0, 3.4, 3.2   # số đạn / tốc độ / tốc độ bẻ lái (rad/s) / thời gian bay
BOT_RK_FETCH = 1100.0                                    # bot hết đạn thì đi nhặt cây súng tên lửa nằm trong tầm này
RK_SEEK, RK_DMG, RK_SPLASH, RK_COOL = 460.0, 3, 62.0, 0.8   # tầm tìm mục tiêu / sát thương / bán kính nổ / hồi chiêu
UP_MAX = min(3, env_num("UPGRADE_MAX", 3))                     # số lần nâng cấp tối đa (mỗi round đội trả lời đúng +1)
GUN_DMG = [1, 2, 2, 3]                                 # sát thương súng bong bóng theo cấp nâng cấp của đội
SWORD_DMG_UP = [2, 3, 3, 4]                            # sát thương kiếm theo cấp nâng cấp
SHIELD_ARC_UP = 0.12                                   # khiên rộng thêm mỗi cấp (rad)

# ---------- bản đồ: đối xứng tâm (xoay 180 độ) ----------
def sym(r):
    x, y, w, h = r
    return (TW - x - w, TH - y - h, w, h)


def px(rs):
    return [(x * T, y * T, w * T, h * T) for x, y, w, h in rs]


_WA = [(10, 26, 3, 3), (16, 22, 3, 3), (13, 33, 3, 3), (21, 29, 3, 3), (22, 34, 2, 2), (9, 36, 2, 2),
       (28, 42, 3, 3), (36, 45, 3, 2), (44, 40, 3, 3), (50, 45, 3, 2), (34, 39, 2, 2), (56, 42, 3, 3), (64, 46, 2, 2),
       (8, 41, 4, 1), (12, 44, 1, 3), (12, 52, 1, 3)]
_BA = [(3, 30, 3, 3), (9, 18, 3, 3), (25, 36, 3, 2), (18, 44, 4, 2), (40, 49, 4, 2), (30, 31, 3, 2), (52, 38, 3, 3), (66, 50, 4, 2)]
WALLS = px(_WA + [sym(r) for r in _WA])
BUSHES = px(_BA + [sym(r) for r in _BA])
BASES = [(7 * T, 49 * T), (73 * T, 7 * T)]
BASE_R = 4 * T
LANES = [[(7, 49), (4, 42), (4, 5), (40, 4), (73, 7)], [(73, 7), (76, 14), (76, 51), (40, 52), (7, 49)],
         [(7, 49), (40, 28), (73, 7)]]
LANES = [[(x * T, y * T) for x, y in l] for l in LANES]
RIVER_K0, RIVER_HALF = 0.7, 3 * T
FLAG_SETS = {2: [(33, 35), (47, 21)], 3: [(33, 35), (47, 21), (40, 28)], 4: [(33, 35), (47, 21), (24, 24), (56, 32)]}
MAPINFO = {"W": W, "H": H, "aimLen": round(BSPEED * BLIFE + PR + 3),
           "bSpeed": BSPEED, "bLife": BLIFE, "cool": COOL, "swCool": SWORD_COOL, "swT": SWORD_T, "walls": WALLS, "bushes": BUSHES, "bases": BASES, "baseR": BASE_R, "lanes": LANES,
           "river": {"k": RIVER_K0, "half": RIVER_HALF}}

app = Flask(__name__)
sio = SocketIO(app, async_mode="threading", cors_allowed_origins=ORIGINS)
LOCK = threading.RLock()
ROOMS, SID_ROOM = {}, {}
TOK = {}  # sid -> token trình duyệt (để nhận ra học sinh khi vào lại)


def _strip_port(h):
    h = h.strip().lower()
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def host_allowed(host):
    if ALLOW_ANY_HOST:
        return True
    h = _strip_port(host).rstrip(".")
    for pat in ALLOWED_HOSTS:
        pat = _strip_port(pat).rstrip(".")
        if pat == h or (pat.startswith("*.") and h.endswith(pat[1:]) and len(h) > len(pat) - 1):
            return True
    return False


class HostGuard:
    def __init__(self, wsgi):
        self.wsgi = wsgi

    def __call__(self, environ, start_response):
        if not host_allowed(environ.get("HTTP_HOST", "")):
            body = b"Host not allowed"
            start_response("421 Misdirected Request", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
            return [body]
        return self.wsgi(environ, start_response)


if not ALLOW_ANY_HOST:
    app.wsgi_app = HostGuard(app.wsgi_app)


# ---------- câu hỏi ----------
FALLBACK = [
    {"question": "AI là viết tắt của cụm từ nào?", "correct": "Artificial Intelligence (Trí tuệ nhân tạo)",
     "wrong": ["Automatic Internet (Mạng tự động)", "Awesome Idea (Ý tưởng tuyệt vời)", "Animal Index (Chỉ số động vật)"],
     "explanation": "AI là Artificial Intelligence: trí tuệ nhân tạo."},
    {"question": "AI có thể trả lời sai không?", "correct": "Có, AI đôi khi trả lời sai",
     "wrong": ["Không, AI luôn đúng 100%", "Không, AI không bao giờ sai"],
     "explanation": "Hãy kiểm tra lại thông tin quan trọng."},
]
_QS, _DECK = [], []


def _s(v):
    return str(v).strip() if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ""


def load_questions():
    global _QS, _DECK
    items = []
    try:
        with open(QFILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for it in (data if isinstance(data, list) else data.get("questions", [])):
            q = _s(it.get("question", it.get("q"))); c = _s(it.get("correct", it.get("answer")))
            w = it.get("wrong", it.get("wrongs", it.get("incorrect", [])))
            w = [x for x in (_s(v) for v in (w if isinstance(w, list) else [w])) if x]
            if q and c and w:
                items.append({"question": q, "correct": c, "wrong": w, "explanation": _s(it.get("explanation", it.get("explain")))})
    except Exception as e:
        print("[!] Không đọc được question.json:", e)
    _QS, _DECK = items or FALLBACK, []
    print(f"[*] {len(_QS)} câu hỏi")


def next_question():
    global _DECK
    if not _DECK:
        _DECK = list(range(len(_QS))); random.shuffle(_DECK)
    q = _QS[_DECK.pop()]
    opts = [(q["correct"], True)] + [(t, False) for t in random.sample(q["wrong"], min(3, len(q["wrong"])))]
    random.shuffle(opts)
    return {"question": q["question"], "options": [o[0] for o in opts],
            "ok": [o[1] for o in opts].index(True), "explanation": q["explanation"]}


# ---------- mô hình ----------
def new_ai():
    return {"stuck_t": 0.0, "lx": 0.0, "ly": 0.0, "det": 0.0, "dd": (0.0, 0.0)}


class P:
    def __init__(s, sid, nick, pid):
        s.sid, s.nick, s.pid, s.team = sid, nick, pid, 0
        s.nopick = 0.0  # sau khi thả cờ, chưa nhặt lại được ngay
        s.ep = 0; s.tpos = 0.0  # ep: số lần máy chủ ép vị trí; tpos: lúc nhận vị trí client gần nhất
        s.g = 0; s.w = 0  # g: 0 nam/1 nữ; w: 0 súng bóng nước/1 kiếm nhựa
        s.bot = False; s.ai = new_ai()
        s.auto = False; s.proxy = False  # auto: người thật đang AFK nên bot chơi thay tạm; proxy: bot thay người đã rời trận
        s.act = time.time(); s.cw = 0  # act: lần cuối người chơi thật sự thao tác; cw: vũ khí client báo lần trước
        s.up = 0; s.rk = 0  # up: cấp nâng cấp của đội (đặt đầu mỗi round); rk: số đạn tên lửa đang có
        s.score = s.kills = s.deaths = 0  # thống kê cả trận: điểm cá nhân (hạ người/quái), số lần hạ, số lần bị hạ
        s.tok = ""; s.away = False; s.awayAt = 0.0  # tok: token trình duyệt; away: đang mất kết nối, chờ vào lại
        s.reset()

    def reset(s):
        s.x = s.y = 0.0; s.a = 0.0; s.down = 0.0; s.cool = 0.0
        s.lv = 1; s.exp = 0; s.mhp = HP + s.up; s.hp = s.mhp; s.rk = 0
        s.sw = 0.0; s.dx = s.dy = 0.0; s.fire = False; s.fl = False; s.sh = False; s.carry = -1; s.prog = 0.0; s.pf = -1
        s.kbt = 0.0; s.kvx = s.kvy = 0.0  # kbt: thời gian còn bị bật lùi
        s.un = -1  # chỉ số lá cờ nhà đang nhổ (-1 = không nhổ)


class Room:
    def __init__(s, code, name, pw, size, rounds, host, pve=False, eve=False):
        s.code, s.name, s.pw, s.size, s.rounds, s.host = code, name, pw, size, rounds, host
        s.pve = pve  # PvE: đội Đỏ (1) là bot do máy điều khiển
        s.eve = eve and not pve  # EvE (demo): cả hai đội đều là bot, mọi người trong phòng (kể cả chủ phòng) chỉ xem
        s.fill = False  # phòng ghép nhanh có lấp chỗ thiếu bằng bot (cả hai đội)
        s.players = {}; s.specs = {}; s.nextpid = 1; s.state = "lobby"; s.phase = "lobby"
        s.flags = []; s.bullets = []; s.q = None; s.round = 0; s.tl = 0.0; s.ev = []
        s.unp = [0, 0]; s.total = [0, 0]; s.up = [0, 0]; s.hearts = []; s.rkp = []; s.rockets = []; s.dead = False; s.abort = False; s.paused = False; s.beat = time.time()


def clean(v, n):
    return "".join(ch for ch in str(v or "") if ch.isprintable()).strip()[:n]


def num(v, lo, hi, df):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return df


def hpw(pw):
    return hashlib.sha256(pw.encode()).hexdigest() if pw else ""


def cap(r):
    """Số chỗ chơi tối đa của người thật: PvP = 2 đội, PvE = chỉ đội Xanh (đội Đỏ là máy), EvE = không có (cả hai đội là máy)."""
    if r.eve:
        return 0
    return r.size if r.pve else r.size * 2


def info(r):
    return {"code": r.code, "name": r.name, "size": r.size, "rounds": r.rounds, "pw": bool(r.pw), "state": r.state,
            "pve": r.pve, "eve": r.eve, "max": cap(r), "n": sum(1 for q in r.players.values() if not q.bot), "ns": len(r.specs),
            "host": (r.players.get(r.host) or r.specs.get(r.host) or P(0, "", 0)).pid,
            "teams": [[{"pid": p.pid, "nick": p.nick} for p in r.players.values() if p.team == t and not p.bot] for t in (0, 1)],
            "specs": [{"pid": p.pid, "nick": p.nick} for p in r.specs.values()]}


def rooms_list():
    return [{k: v for k, v in info(r).items() if k not in ("teams", "specs")} for r in ROOMS.values()]


def push(r):
    sio.emit("room", info(r), to=r.code)
    sio.emit("rooms", rooms_list())


def add_player(r, sid, nick, spec=False):
    p = P(sid, nick, r.nextpid); r.nextpid += 1
    if spec or r.eve:  # phòng EvE: ai vào cũng là khán giả
        p.team = -1; r.specs[sid] = p
    else:
        c = [sum(1 for q in r.players.values() if q.team == t) for t in (0, 1)]
        p.team = 0 if (r.pve or c[0] <= c[1]) else 1
        r.players[sid] = p
    SID_ROOM[sid] = r
    p.tok = TOK.get(sid, "")
    sio.server.enter_room(sid, r.code, namespace="/")  # không dùng join_room: nó cần request context, mà ghép trận chạy ở luồng nền
    return p


def drop(sid):
    unq(sid)
    r = SID_ROOM.pop(sid, None)
    if not r:
        return
    p = r.players.get(sid)
    r.specs.pop(sid, None)
    try:
        leave_room(r.code, sid=sid)
    except Exception:
        pass
    if p and r.state == "playing" and not r.dead and not r.abort and p.team in (0, 1) and not p.bot:
        to_bot(r, sid, p)  # đang giữa trận: nhân vật KHÔNG rời đi mà do bot điều khiển tiếp (cờ đang vác vẫn do bot mang)
    else:
        r.players.pop(sid, None)
        if p and 0 <= p.carry < len(r.flags):
            f = r.flags[p.carry]; f["c"] = None; f["x"], f["y"] = p.x, p.y
    humans = {k: q for k, q in r.players.items() if not q.bot}
    if not humans and not r.specs:
        r.dead = True; ROOMS.pop(r.code, None)
    else:
        if r.host == sid:
            r.host = next(iter(humans or r.specs)); r.paused = False
        if r.state == "playing" and (not any(q.team == 0 for q in r.players.values()) or not any(q.team == 1 for q in r.players.values())):
            r.abort = True
        push(r)
    sio.emit("rooms", rooms_list())


# ---------- sự kiện lobby ----------
@sio.on("connect")
def _connect(auth=None):
    cv = auth.get("version") if isinstance(auth, dict) else None
    if str(cv) != str(VERSION):
        raise RefuseConn({"code": "version", "server": VERSION_NAME, "version": VERSION})
    TOK[request.sid] = clean(auth.get("tok"), 40)
    emit("rooms", rooms_list())


@sio.on("disconnect")
def _disc():
    with LOCK:
        sid = request.sid
        r = SID_ROOM.get(sid); p = r.players.get(sid) if r else None
        TOK.pop(sid, None); CHAT_LAST.pop(sid, None)
        if p and not p.bot and p.tok and r.state == "playing" and REJOIN_S > 0 and not r.dead:
            # đang giữa trận: giữ chỗ REJOIN_S giây để học sinh vào lại (nhân vật đứng yên)
            p.away = True; p.awayAt = time.time(); p.dx = p.dy = 0.0; p.fire = p.fl = p.sh = False
            return
        drop(sid)


@sio.on("create")
def on_create(d):
    d = d or {}; sid = request.sid
    nick = clean(d.get("nick"), 14) or "Người chơi"
    name = clean(d.get("name"), 24) or "Phòng của " + nick
    with LOCK:
        drop(sid)
        code = str(random.randint(1000, 9999))
        while code in ROOMS:
            code = str(random.randint(1000, 9999))
        r = Room(code, name, hpw(clean(d.get("pw"), 20)), num(d.get("size"), 1, 5, 3), num(d.get("rounds"), 1, 5, 3), sid, bool(d.get("pve")), bool(d.get("eve")))
        ROOMS[code] = r
        p = add_player(r, sid, nick)
        emit("me", {"pid": p.pid}); push(r)


@sio.on("join")
def on_join(d):
    d = d or {}; sid = request.sid
    nick = clean(d.get("nick"), 14) or "Người chơi"
    with LOCK:
        r = ROOMS.get(str(d.get("code")))
        if not r:
            return emit("err", "Phòng không còn tồn tại.")
        if r.pw and not hmac.compare_digest(r.pw, hpw(clean(d.get("pw"), 20))):
            return emit("err", "Sai mật khẩu phòng.")
        if len(r.specs) >= MAX_SPECS and (r.state != "lobby" or sum(1 for q in r.players.values() if not q.bot) >= cap(r)):
            return emit("err", "Ghế khán giả đã đầy.")
        drop(sid)
        # phòng đang chơi hoặc đã đủ người: vào ghế khán giả
        spec = r.state != "lobby" or len(r.players) >= cap(r)
        p = add_player(r, sid, nick, spec)
        emit("me", {"pid": p.pid}); push(r)
        if r.state == "playing" and r.q:
            emit("rd", {"i": r.round, "n": r.rounds, "q": {"question": r.q["question"], "options": r.q["options"]},
                        "players": roster(r), "map": MAPINFO})


@sio.on("leave")
def on_leave():
    with LOCK:
        drop(request.sid)
    emit("left")


@sio.on("rejoin")
def on_rejoin(d):
    """Học sinh lỡ đóng trang / mất mạng giữa trận: nối lại đúng người chơi cũ (khớp token của trình duyệt)."""
    d = d or {}; sid = request.sid
    tok = TOK.get(sid, "")
    with LOCK:
        r = ROOMS.get(str(d.get("code")))
        old = None
        if r and tok and r.state == "playing" and sid not in r.players:
            old = next((k for k, q in r.players.items()
                        if not q.bot and q.tok and hmac.compare_digest(q.tok.encode(), tok.encode())), None)
        if old is None:
            return emit("rejoin_fail", "Không kết nối lại được: trận đã kết thúc hoặc đã hết thời gian chờ.")
        p = r.players.pop(old)
        SID_ROOM.pop(old, None)
        try:
            leave_room(r.code, sid=old)
        except Exception:
            pass
        if not p.away:
            sio.emit("kicked", to=old)  # kết nối cũ vẫn còn sống (tab khác): báo cho nó biết
        was_away = p.away
        p.sid, p.away = sid, False
        p.auto = False; p.act = time.time(); p.ai = new_ai()
        if was_away:
            r.ev.append(["nf", 5, p.pid, 0, -1])  # bảng tin: quay lại, tự điều khiển tiếp
        p.dx = p.dy = 0.0; p.fire = p.fl = p.sh = False
        p.ep += 1; p.tpos = time.time() + 2.0
        r.players[sid] = p; SID_ROOM[sid] = r
        join_room(r.code, sid=sid)
        if r.host == old:
            r.host = sid
        emit("rejoined"); emit("me", {"pid": p.pid}); push(r)
        if r.q:
            emit("rd", {"i": r.round, "n": r.rounds, "q": {"question": r.q["question"], "options": r.q["options"]},
                        "players": roster(r), "map": MAPINFO})


@sio.on("seat")
def on_seat(d):
    """Đổi chỗ ngồi trong phòng chờ: 0/1 = đội, 2 = ghế khán giả."""
    sid = request.sid
    with LOCK:
        r = SID_ROOM.get(sid)
        if not r or r.state != "lobby":
            return
        t = num(d, 0, 2, -1) if not isinstance(d, dict) else num(d.get("t"), 0, 2, -1)
        if t < 0:
            return
        p = r.players.get(sid) or r.specs.get(sid)
        if not p:
            return
        cur = 2 if sid in r.specs else p.team
        if t == cur:
            return
        if t == 2:
            if len(r.specs) >= MAX_SPECS:
                return emit("err", "Ghế khán giả đã đầy.")
            r.players.pop(sid, None); p.team = -1; r.specs[sid] = p
        else:
            if r.eve:
                return emit("err", "Phòng EvE: cả hai đội do máy điều khiển, bạn chỉ xem được.")
            if r.pve and t == 1:
                return emit("err", "Phòng PvE: đội Đỏ do máy điều khiển.")
            if sum(1 for q in r.players.values() if q.team == t) >= r.size:
                return emit("err", "Đội này đã đủ người.")
            r.specs.pop(sid, None); p.team = t; r.players[sid] = p
        push(r)


@sio.on("team")
def on_team():
    with LOCK:
        r = SID_ROOM.get(request.sid)
        if not r or r.state != "lobby":
            return
        p = r.players.get(request.sid)
        if not p:
            return
        if r.pve or r.eve:
            return emit("err", "Phòng PvE: đội Đỏ do máy điều khiển." if r.pve else "Phòng EvE: cả hai đội do máy điều khiển.")
        t = 1 - p.team
        if sum(1 for q in r.players.values() if q.team == t) >= r.size:
            return emit("err", "Đội kia đã đủ người.")
        p.team = t; push(r)


# ---------- ghép trận tự động ----------
MQ = {}  # cỡ trận (1..5) -> [(sid, nick), ...] theo thứ tự vào hàng chờ
MQT = {}  # sid -> lúc vào hàng chờ


def qnotify(size):
    lst = MQ.get(size, [])
    for sid, _ in lst:
        sio.emit("qs", {"size": size, "n": len(lst), "need": size * 2}, to=sid)


def unq(sid):
    MQT.pop(sid, None)
    for size, lst in MQ.items():
        if any(x[0] == sid for x in lst):
            lst[:] = [x for x in lst if x[0] != sid]
            qnotify(size)


def try_match(size, force=False):
    lst = MQ.setdefault(size, [])
    need = size * 2
    if len(lst) < need and not (force and lst):
        return
    grp = lst[:need]; del lst[:need]
    for sid, _ in grp:
        MQT.pop(sid, None)
    random.shuffle(grp)
    code = str(random.randint(1000, 9999))
    while code in ROOMS:
        code = str(random.randint(1000, 9999))
    r = Room(code, f"Ghép nhanh {size}v{size}", "", size, 3, grp[0][0])
    ROOMS[code] = r
    r.fill = len(grp) < need  # thiếu người: bot sẽ được thêm âm thầm khi trận bắt đầu
    for sid, nick in grp:
        p = add_player(r, sid, nick)  # add_player tự chia đều hai đội (xen kẽ)
        sio.emit("me", {"pid": p.pid}, to=sid)
    r.state = "playing"; r.abort = False; r.paused = False; r.beat = time.time()
    sio.start_background_task(run_match, r)
    push(r)
    qnotify(size)


@sio.on("queue")
def on_queue(d):
    d = d or {}; sid = request.sid
    size = num(d.get("size"), 1, 5, 2)
    nick = clean(d.get("nick"), 14) or "Người chơi"
    with LOCK:
        drop(sid)  # rời phòng/hàng chờ cũ
        MQ.setdefault(size, []).append((sid, nick))
        MQT[sid] = time.time()
        qnotify(size)
        try_match(size)


def mm_loop():
    """Người đầu hàng chờ đợi quá MM_WAIT_S giây mà chưa đủ người: bắt đầu trận với những người đang chờ, chỗ thiếu do bot lấp."""
    while True:
        sio.sleep(1)
        if MM_WAIT_S <= 0:
            continue
        try:
            with LOCK:
                now = time.time()
                for size in list(MQ):
                    lst = MQ[size]
                    if lst and now - MQT.get(lst[0][0], now) >= MM_WAIT_S:
                        try_match(size, force=True)
        except Exception:
            traceback.print_exc()


@sio.on("unqueue")
def on_unqueue():
    with LOCK:
        unq(request.sid)


@sio.on("start")
def on_start():
    with LOCK:
        r = SID_ROOM.get(request.sid)
        if not r or r.host != request.sid or r.state != "lobby":
            return
        if r.eve:
            pass  # EvE: không cần người chơi, máy tự lập cả hai đội khi trận bắt đầu
        elif r.pve:
            if not any(p.team == 0 for p in r.players.values()):
                return emit("err", "Cần ít nhất 1 người chơi ở đội Xanh.")
        elif not r.fill and (not any(p.team == 0 for p in r.players.values()) or not any(p.team == 1 for p in r.players.values())):
            return emit("err", "Mỗi đội cần ít nhất 1 người.")
        r.state = "playing"; r.abort = False; r.paused = False; r.beat = time.time()
        sio.start_background_task(run_match, r)
        push(r)


@sio.on("pause")
def on_pause():
    with LOCK:
        r = SID_ROOM.get(request.sid)
        if r and r.host == request.sid and r.state == "playing" and r.phase in ("read", "play"):
            r.paused = not r.paused


@sio.on("drop")
def on_drop():
    with LOCK:
        r = SID_ROOM.get(request.sid)
        p = r.players.get(request.sid) if r else None
        if p and p.carry >= 0 and p.down <= 0 and r.phase == "play" and not r.paused:
            r.ev.append(["nf", 3, p.pid, r.flags[p.carry]["letter"], -1])
            drop_flag(r, p)
            p.nopick = time.time() + 1.5
            r.ev.append(["p", round(p.x), round(p.y), p.team])
        elif p and p.carry < 0 and p.down <= 0 and p.kbt <= 0 and p.team in (0, 1) and r.phase == "play" and not r.paused \
                and r.unp[p.team] < UNPLANT_MAX:
            # không vác cờ mà bấm F cạnh lá cờ nhà đã cắm: bắt đầu nhổ cờ (phải đứng yên cạnh cờ đủ UNPLANT_S giây)
            k = next((k for k, f in enumerate(r.flags) if f["planted"] == p.team
                      and math.hypot(p.x - f["x"], p.y - f["y"]) < UNPLANT_R), -1)
            if k >= 0:
                p.un = k; p.prog = 0.0; p.pf = -1


# ---------- chat: kênh đội ("t") và kênh cả map ("a") ----------
CHAT_MAX, CHAT_GAP = 120, 0.6   # độ dài tối đa / giãn cách tối thiểu giữa 2 tin của một người (giây)
CHAT_LAST = {}


@sio.on("chat")
def on_chat(d):
    sid = request.sid
    if not isinstance(d, dict):
        return
    m = " ".join(clean(d.get("m"), CHAT_MAX).split())
    now = time.time()
    if not m or now - CHAT_LAST.get(sid, 0.0) < CHAT_GAP:
        return
    CHAT_LAST[sid] = now
    with LOCK:
        r = SID_ROOM.get(sid)
        p = (r.players.get(sid) or r.specs.get(sid)) if r else None
        if not p:
            return
        ch = "t" if d.get("ch") == "t" else "a"
        msg = {"pid": p.pid, "nick": p.nick, "team": p.team, "ch": ch, "m": m}
        if ch == "a":
            sio.emit("chat", msg, to=r.code)
        else:  # kênh đội: chỉ đồng đội (khán giả chat với nhau)
            group = r.specs.values() if p.team < 0 else r.players.values()
            for q in list(group):
                if q.team == p.team and not q.bot and not q.away:
                    _emit_safe("chat", msg, q.sid)


@sio.on("inp")
def on_inp(d):
    r = SID_ROOM.get(request.sid)
    if not r:
        return
    p = r.players.get(request.sid)
    if not p:
        return
    try:
        dx, dy, a = float(d["dx"]), float(d["dy"]), float(d["a"])
        n = math.hypot(dx, dy)
        if n > 1:
            dx, dy = dx / n, dy / n
        neww = d.get("w") if d.get("w") in (1, 2) else 0
        # thao tác thật: di chuyển, bắn/chém, giơ khiên hoặc đổi vũ khí (chỉ nhúc nhích chuột/ngắm thì chưa tính)
        if dx or dy or d.get("f") or d.get("sh") or neww != p.cw:
            p.act = time.time()
            if p.auto:
                set_auto(r, p, False)  # lấy lại quyền điều khiển từ bot
        p.cw = neww
        if p.auto:
            p.g = 1 if d.get("g") == 1 else 0
            return  # bot đang chơi thay: bỏ qua input/vị trí client cho tới khi người chơi thao tác lại
        p.dx, p.dy, p.a, p.fire = dx, dy, a, bool(d.get("f"))
        if p.fire and r.phase == "play" and p.down <= 0:
            p.fl = True  # chốt cú bấm ngắn: nhấn+thả giữa 2 tick vẫn tính 1 phát (khớp với đạn client đã hiện)
        p.g = 1 if d.get("g") == 1 else 0
        p.w = d.get("w") if d.get("w") in (1, 2) else 0
        p.sh = bool(d.get("sh")) and p.w == 1  # giữ khiên (chỉ khi cầm kiếm)
        # Client tự dự đoán vị trí (không giật khi ping cao); máy chủ chỉ kiểm tra có hợp lệ không
        if "x" in d and d.get("ep") == p.ep and p.down <= 0 and p.kbt <= 0 and r.phase == "play" and not r.paused:
            nx, ny, now = float(d["x"]), float(d["y"]), time.time()
            dt = min(max(now - p.tpos, 0.05), 2.0) if p.tpos else 0.15
            if math.hypot(nx - p.x, ny - p.y) <= SPEED * 1.3 * dt + 12 and not hit_wall(nx, ny, PR):
                p.x, p.y, p.tpos = nx, ny, now
            else:
                p.ep += 1; p.tpos = time.time() + 2.0  # quá nhanh hoặc xuyên tường: kéo client về vị trí máy chủ
    except Exception:
        pass


# ---------- bot (chế độ PvE) ----------
BOT_NAMES = ["Bé Na", "Tí Nị", "Cún Con", "Mít Ướt", "Sóc Nâu", "Bò Sữa", "Gấu Mập", "Thỏ Ngọc", "Mèo Mướp", "Vịt Bầu",
             "Chuột Nhắt", "Cáo Đỏ", "Kem Dâu", "Bánh Bao", "Xíu Mại", "Heo Hồng", "Nấm Lùn", "Sao Băng", "Mây Trắng", "Gió Núi",
             "Sấm Chớp", "Lửa Nhỏ", "Bin Bin", "Susu", "Tôm Hùm", "Cá Heo", "Ốc Sên", "Dế Mèn", "Bướm Vàng", "Ong Mật",
             "Rồng Con", "Hổ Báo", "Sói Xám", "Đại Bàng", "Khỉ Con", "Voi Con", "Ếch Xanh", "Cú Mèo", "Panda", "Tít Mít"]


def add_bots(r):
    """PvE: tạo số bot bằng số người chơi đội Xanh (tối thiểu 1) ở đội Đỏ, tên ngẫu nhiên không trùng."""
    humans = sum(1 for p in r.players.values() if p.team == 0 and not p.bot)
    taken = {p.nick for p in r.players.values()}
    pool = [n for n in BOT_NAMES if n not in taken]
    random.shuffle(pool)
    for _ in range(max(1, min(r.size, humans))):
        new_bot(r, 1, pool)


def new_bot(r, team, pool):
    p = P("bot%d" % r.nextpid, pool.pop() if pool else "Bot %d" % random.randint(10, 99), r.nextpid)
    r.nextpid += 1
    p.bot = True; p.team = team; p.g = random.randint(0, 1); p.w = 0
    p.ai = {"stuck_t": 0.0, "lx": 0.0, "ly": 0.0, "det": 0.0, "dd": (0.0, 0.0)}
    r.players[p.sid] = p


def fill_bots(r):
    """Ghép nhanh thiếu người: lấp đủ chỗ trống ở CẢ HAI đội bằng bot (không thông báo gì)."""
    taken = {p.nick for p in r.players.values()}
    pool = [n for n in BOT_NAMES if n not in taken]
    random.shuffle(pool)
    for t in (0, 1):
        for _ in range(r.size - sum(1 for p in r.players.values() if p.team == t)):
            new_bot(r, t, pool)


def botted(p):
    """Nhân vật đang do máy điều khiển: bot thật, người AFK (bot chơi thay tạm) hoặc người đang mất kết nối chờ vào lại."""
    return p.bot or p.auto or p.away


def set_auto(r, p, on):
    """Bật/tắt bot chơi thay tạm thời cho người chơi thật đang AFK."""
    if p.auto == on or p.bot:
        return
    p.auto = on; p.ai = new_ai(); p.dx = p.dy = 0.0; p.fire = p.fl = p.sh = False
    p.act = time.time()
    p.ep += 1; p.tpos = time.time()  # client chốt lại vị trí theo máy chủ
    r.ev.append(["nf", 4 if on else 5, p.pid, 0, -1])
    _emit_safe("auto", {"on": int(on)}, p.sid)


def to_bot(r, sid, p):
    """Người chơi rời trận giữa chừng: giữ nguyên nhân vật (máu, cờ, điểm, thống kê), giao cho bot điều khiển đến hết trận."""
    r.players.pop(sid, None)
    p.bot = True; p.proxy = True; p.auto = False; p.away = False; p.tok = ""
    p.sid = "bot%d" % p.pid
    p.ai = new_ai(); p.dx = p.dy = 0.0; p.fire = p.fl = p.sh = False; p.w = 0
    if not p.nick.endswith("🤖"):
        p.nick += " 🤖"
    r.players[p.sid] = p
    r.ev.append(["nf", 6, p.pid, 0, -1])


def remove_bots(r):
    for k in [k for k, q in r.players.items() if q.bot]:
        r.players.pop(k, None)


def clear_shot(x1, y1, x2, y2):
    """Đường thẳng từ (x1,y1) tới (x2,y2) không vướng tường (tên lửa chạm tường là nổ)."""
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) // 24))
    return not any(hit_wall(x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n, 3) for i in range(1, n))


def bot_ai(r, p):
    """Bot: nhặt cờ đúng -> mang về cắm; cờ đúng đã bị địch cắm thì cả đội kéo sang cướp (1 người cướp, số còn lại yểm trợ bắn);
    hộ tống đồng đội đang vác cờ; chạy tới bắn giúp đồng đội đang giao tranh; chặn địch xâm nhập căn cứ; chống kẹt tường.
    Vũ khí: nhặt súng tên lửa khi hết đạn và bắn người/golem/hiệp sĩ/thần giữ cờ; chém kiếm khi địch trong tầm cận chiến."""
    ai = p.ai
    bx, by = BASES[p.team]
    subst = p.proxy or p.auto or p.away  # bot thay người thật không tự đi nhặt cờ; chỉ cướp lá cờ đúng địch đã cắm, còn lại hỗ trợ đồng đội
    qq = getattr(r, "q", None)  # bot "biết" đáp án: chỉ đi lấy/cướp lá cờ đúng, và chỉ khi đội chưa có cờ
    ok = qq["ok"] if qq else -1
    if p.carry >= 0 and not subst and r.flags[p.carry]["letter"] != ok:  # lỡ nhặt phải cờ sai (đi ngang qua) thì thả ngay để đội còn nhặt cờ đúng
        r.ev.append(["nf", 3, p.pid, r.flags[p.carry]["letter"], -1])
        drop_flag(r, p)
        p.nopick = time.time() + 4.0
        r.ev.append(["p", round(p.x), round(p.y), p.team])
    foes = [q for q in r.players.values() if q.team != p.team and q.down <= 0]
    mates = [q for q in r.players.values() if q.team == p.team and q is not p and q.down <= 0]
    carriers = [q for q in foes if q.carry >= 0]
    kn_foes = [mo for mo in r.mons if mo["alive"] and mo["t"] == 4 and not friendly(mo, p.team)]  # hiệp sĩ canh căn cứ địch
    # ---- chọn mục tiêu bắn: người > hiệp sĩ địch (tầm 330) > quái trung lập (tầm 230) ----
    tgt, bd = None, 1e9
    for q in foes:
        d = math.hypot(q.x - p.x, q.y - p.y)
        if d < 420 and d - (150 if q.carry >= 0 else 0) < bd:
            tgt, bd = q, d - (150 if q.carry >= 0 else 0)
    shoot = None
    if tgt:
        shoot = (tgt.x, tgt.y)
    elif p.carry < 0:
        best = 1e9
        for mo in r.mons:
            if not mo["alive"] or mo["t"] == 3 or friendly(mo, p.team):
                continue
            d = math.hypot(mo["x"] - p.x, mo["y"] - p.y)
            if d < (330 if mo["t"] == 4 else 230) and d < best:
                shoot, best = (mo["x"], mo["y"]), d
    # ---- chọn nơi đến ----
    home, stop, siege = False, 8, False
    if p.carry >= 0:
        dest, home = (bx, by), True
    else:
        if team_has_flag(r, p.team):
            cands = []
        elif subst:  # không tự đi nhặt cờ dưới đất; chỉ cướp lá cờ ĐÁP ÁN ĐÚNG mà địch đã cắm, còn lại thì yểm trợ người khác
            cands = [f for f in r.flags if f["c"] is None and f["planted"] == 1 - p.team and f["letter"] == ok]
        else:
            cands = [f for f in r.flags if f["c"] is None and f["planted"] != p.team and f["letter"] == ok and f.get("ban", -1) != p.team]
        dest = None
        if carriers:  # địch đang vác cờ: đuổi theo cướp lại / hạ gục
            c = min(carriers, key=lambda q: math.hypot(q.x - p.x, q.y - p.y))
            dest, stop = (c.x, c.y), 140
        elif cands:
            f = min(cands, key=lambda f: math.hypot(f["x"] - p.x, f["y"] - p.y))
            dest = (f["x"], f["y"])
            if f["planted"] >= 0:  # cờ đúng đang được địch cắm ở căn cứ họ: tập hợp rồi công thành có đội hình
                allbots = [m for m in r.players.values() if m.team == p.team and ((m.bot and not m.proxy) or m.auto)]  # kể cả bot đang chờ hồi sinh
                crew = [m for m in allbots if m.down <= 0 and m.carry < 0]
                if p not in crew:
                    crew.append(p)
                ebx, eby = BASES[f["planted"]]
                a0 = math.atan2(by - eby, bx - ebx)
                stg = (ebx + math.cos(a0) * (BASE_R + 230), eby + math.sin(a0) * (BASE_R + 230))  # điểm tập kết: ngay ngoài vùng hiệp sĩ tự lao ra (BASE_R+170), vừa tầm bắn để nhử từng con ra
                now, kgo = time.time(), "go%d" % p.team
                active = now - f.get(kgo, -1e9) < 8.0  # đợt công thành đang diễn ra (còn ai đó áp sát cờ trong 8 giây qua)
                if not active:
                    near = [m for m in crew if math.hypot(m.x - stg[0], m.y - stg[1]) < 260]
                    ai["rally"] = ai.get("rally", 0.0) + DT
                    if (len(near) >= max(1, math.ceil(len(allbots) * 0.7)) and len(kn_foes) <= 1) or ai["rally"] >= 45.0 or p.prog > 0:
                        active = True; f[kgo] = now  # đủ quân và hiệp sĩ canh đã bị nhử ra hạ gần hết (hoặc chờ quá 45 giây) thì xông vào
                    else:
                        dest, stop = stg, 60
                if active:
                    ai["rally"] = 0.0
                    if any(math.hypot(m.x - f["x"], m.y - f["y"]) < 350 for m in crew):
                        f[kgo] = now
                    thief = min(crew, key=lambda m: (math.hypot(m.x - f["x"], m.y - f["y"]), m.pid))
                    siege = thief is p
                    if siege:  # người gần cờ nhất đi cướp; chờ đồng đội áp sát (tối đa ~6 giây) nếu cờ còn bị canh
                        others = [m for m in crew if m is not p]
                        danger = any(math.hypot(q.x - f["x"], q.y - f["y"]) < 300 for q in foes) or any(math.hypot(mo["x"] - f["x"], mo["y"] - f["y"]) < 300 for mo in kn_foes)
                        covered = any(math.hypot(m.x - p.x, m.y - p.y) < 260 for m in others)
                        if danger and others and not covered and ai.get("wait", 0.0) < 6.0:
                            ai["wait"] = ai.get("wait", 0.0) + DT
                            a = math.atan2(by - f["y"], bx - f["x"])
                            dest, stop = (f["x"] + math.cos(a) * 170, f["y"] + math.sin(a) * 170), 20
                        else:
                            stop = 8
                    else:  # yểm trợ: đứng vòng quanh lá cờ phía mình, bắn hiệp sĩ/địch canh cờ cho người cướp đứng yên
                        a = math.atan2(by - f["y"], bx - f["x"]) + ((p.pid % 5) - 2) * 0.55
                        dest, stop = (f["x"] + math.cos(a) * 100, f["y"] + math.sin(a) * 100), 25
        if dest is None:  # không có cờ để lấy/cướp: không đứng ngây ở căn cứ nữa
            dest, home = (bx, by), True  # mặc định: canh căn cứ
            carr = [m for m in mates if m.carry >= 0]
            intr = [f for f in foes if math.hypot(f.x - bx, f.y - by) < BASE_R + 300]
            fight = [f for f in foes if any(math.hypot(f.x - m.x, f.y - m.y) < 300 for m in mates)]  # đồng đội ở đâu cũng chạy tới hỗ trợ (kể cả bot thay người)
            if carr:  # hộ tống đồng đội đang vác cờ
                m = min(carr, key=lambda m: math.hypot(m.x - p.x, m.y - p.y))
                dest, home, stop = (m.x, m.y), False, 100
            elif intr:  # địch xâm nhập căn cứ: về chặn
                f = min(intr, key=lambda f: math.hypot(f.x - p.x, f.y - p.y))
                dest, home, stop = (f.x, f.y), False, 180
            elif fight:  # đồng đội đang đánh nhau: chạy tới bắn giúp
                f = min(fight, key=lambda f: math.hypot(f.x - p.x, f.y - p.y))
                dest, home, stop = (f.x, f.y), False, 200
    # ---- bot hết đạn thì đi nhặt súng tên lửa (tối đa 2 bot/AFK cùng đội đi nhặt một cây) ----
    swr = SWORD_R + 4 * (p.lv - 1)  # tầm kiếm hiện tại
    if p.carry < 0 and p.rk <= 0 and not siege and p.prog <= 0 and not carriers and not (tgt and bd < 220):
        bk, bs = 1e9, None
        for k in r.rkp:
            if k["t"] > 0:
                continue
            d0 = math.hypot(k["x"] - p.x, k["y"] - p.y)
            if d0 > BOT_RK_FETCH or d0 >= bk:
                continue
            if sum(1 for m in r.players.values() if m is not p and m.team == p.team and botted(m) and m.down <= 0 and m.rk <= 0
                   and math.hypot(m.x - k["x"], m.y - k["y"]) < d0) >= 2:
                continue
            bk, bs = d0, k
        if bs:
            dest, stop, home = (bs["x"], bs["y"]), 12, False
    # ---- địch sắp vào tầm kiếm: áp sát để chém (trừ khi đang vác cờ / cắm cờ / cướp cờ) ----
    if p.carry < 0 and not siege and p.prog <= 0 and tgt and math.hypot(tgt.x - p.x, tgt.y - p.y) < swr + 70:
        dest, stop, home = (tgt.x, tgt.y), swr * 0.5, False
    if not siege:
        ai["wait"] = 0.0  # chỉ giữ bộ đếm chờ khi đang làm người cướp cờ (hết 6 giây thì lao vào luôn, không quay lại chờ)
    lp = ai.get("lp")
    jump = lp is None or math.hypot(p.x - lp[0], p.y - lp[1]) > 250  # mới hồi sinh / bị bật xa: tính lại tuyến
    ai["lp"] = (p.x, p.y)
    d = math.hypot(dest[0] - p.x, dest[1] - p.y)
    ebx, eby = BASES[1 - p.team]
    if p.carry < 0 and d > 1000 and math.hypot(dest[0] - ebx, dest[1] - eby) < 750:
        # sang căn cứ địch: đi men theo rìa bản đồ (tránh Golem, quái và laze thần giữ cờ ở giữa) rồi mới áp sát
        lane = LANES[p.pid % 2]
        pts = lane if math.hypot(lane[0][0] - bx, lane[0][1] - by) < 10 else lane[::-1]
        if jump or "wp" not in ai:
            ai["wp"] = min(range(1, len(pts)), key=lambda i: math.hypot(pts[i][0] - p.x, pts[i][1] - p.y))
        wp = ai["wp"]
        while wp < len(pts) - 1 and math.hypot(pts[wp][0] - p.x, pts[wp][1] - p.y) < 160:
            wp += 1
        ai["wp"] = wp
        if math.hypot(pts[wp][0] - p.x, pts[wp][1] - p.y) > 160 and wp < len(pts) - 1:
            dest, stop, home = pts[wp], 8, False
            d = math.hypot(dest[0] - p.x, dest[1] - p.y)
    if home:
        stop = BASE_R * 0.4
    dx = dy = 0.0
    if d > stop:
        sx, sy = nav_steer(ai, p.x, p.y, dest[0], dest[1], time.time())  # A*: đi vòng tường thay vì húc thẳng
        sd = math.hypot(sx - p.x, sy - p.y) or 1.0
        dx, dy = (sx - p.x) / sd, (sy - p.y) / sd
    else:
        ai["path"] = None
    if dx or dy:  # né quái trung lập (Golem/slime/dơi/thần giữ cờ) thay vì đâm thẳng vào rồi chết giữa đường
        ax = ay = 0.0
        for mo in r.mons:
            if not mo["alive"] or mo["t"] == 4:
                continue
            R = (90, 90, 190, 200)[mo["t"]] + mo["r"]
            mdx, mdy = p.x - mo["x"], p.y - mo["y"]; md = math.hypot(mdx, mdy)
            if 1e-3 < md < R and math.hypot(dest[0] - mo["x"], dest[1] - mo["y"]) > R:  # đích nằm sát quái thì thôi (vd. cờ có thần giữ)
                w = (R - md) / R
                tx, ty = -mdy / md, mdx / md  # vector tiếp tuyến: đi vòng qua thay vì dừng trước mặt quái
                if tx * dx + ty * dy < 0:
                    tx, ty = -tx, -ty
                ax += (mdx / md) * w * 1.2 + tx * w * 1.4; ay += (mdy / md) * w * 1.2 + ty * w * 1.4
        if p.carry < 0 and not team_has_flag(r, p.team):
            for f in r.flags:  # cờ sai (hoặc bot không biết đáp án) nằm dưới đất: đi vòng, đừng chạm vào kẻo tự nhặt
                if f["c"] is None and f["planted"] == -1 and (subst or f["letter"] != ok):
                    mdx, mdy = p.x - f["x"], p.y - f["y"]; md = math.hypot(mdx, mdy)
                    if 1e-3 < md < 60 and math.hypot(dest[0] - f["x"], dest[1] - f["y"]) > 60:
                        w = (60 - md) / 60
                        tx, ty = -mdy / md, mdx / md
                        if tx * dx + ty * dy < 0:
                            tx, ty = -tx, -ty
                        ax += (mdx / md) * w * 1.2 + tx * w * 1.4; ay += (mdy / md) * w * 1.2 + ty * w * 1.4
        if ax or ay:
            dx, dy = dx + ax, dy + ay
            n = math.hypot(dx, dy) or 1.0
            dx, dy = dx / n, dy / n
    ai["stuck_t"] += DT
    if ai["stuck_t"] >= 0.6:
        if (dx or dy) and math.hypot(p.x - ai["lx"], p.y - ai["ly"]) < 20:
            s = random.choice((-1, 1)); ai["det"] = 0.8; ai["dd"] = (-dy * s, dx * s); ai["repath"] = True  # kẹt: đi lệch một chút và tính lại đường
        ai["lx"], ai["ly"], ai["stuck_t"] = p.x, p.y, 0.0
    if ai["det"] > 0:
        ai["det"] -= DT; dx, dy = ai["dd"]
    p.dx, p.dy = dx, dy
    p.sh = False
    # ---- chọn vũ khí: kiếm khi địch trong tầm cận chiến > tên lửa (có đạn, có đường bắn) > súng bong bóng ----
    melee, mb = None, 1e9
    for q in foes:
        dd = math.hypot(q.x - p.x, q.y - p.y)
        if dd < swr - 6 and dd < mb:
            melee, mb = (q.x, q.y), dd
    for mo in r.mons:
        if not mo["alive"] or mo["t"] == 3 or friendly(mo, p.team):
            continue
        dd = math.hypot(mo["x"] - p.x, mo["y"] - p.y)
        if dd < swr + mo["r"] - 6 and dd < mb:
            melee, mb = (mo["x"], mo["y"]), dd
    rk_t = None
    if p.rk > 0 and not melee:
        cb = 1e9
        for q in foes:  # người chơi (ưu tiên kẻ đang vác cờ)
            dd = math.hypot(q.x - p.x, q.y - p.y)
            sc = dd - (150 if q.carry >= 0 else 0)
            if 90 < dd < 420 and sc < cb and clear_shot(p.x, p.y, q.x, q.y):
                rk_t, cb = (q.x, q.y), sc
        for mo in r.mons:  # golem, hiệp sĩ địch, thần giữ cờ (chỉ khi canh lá cờ bot đang nhắm tới hoặc đã ở sát)
            if not mo["alive"] or friendly(mo, p.team) or mo["t"] not in (2, 3, 4):
                continue
            dd = math.hypot(mo["x"] - p.x, mo["y"] - p.y)
            if mo["t"] == 3 and not (dd < 300 or math.hypot(dest[0] - mo["ax"], dest[1] - mo["ay"]) < 400):
                continue
            sc = dd + 80
            if 90 < dd < 420 and sc < cb and clear_shot(p.x, p.y, mo["x"], mo["y"]):
                rk_t, cb = (mo["x"], mo["y"]), sc
    if melee:
        p.w = 1; p.a = math.atan2(melee[1] - p.y, melee[0] - p.x); p.fire = True
    elif rk_t:
        p.w = 2; p.a = math.atan2(rk_t[1] - p.y, rk_t[0] - p.x) + random.uniform(-0.05, 0.05); p.fire = True
    elif shoot:
        p.w = 0
        p.a = math.atan2(shoot[1] - p.y, shoot[0] - p.x) + random.uniform(-0.13, 0.13)
        p.fire = random.random() < 0.8
    else:
        p.w = 0; p.fire = False
        if dx or dy:
            p.a = math.atan2(dy, dx)


# ---------- vật lý ----------
def hit_wall(x, y, r):
    if x < r or y < r or x > W - r or y > H - r:
        return True
    for wx, wy, ww, wh in WALLS:
        cx = min(max(x, wx), wx + ww); cy = min(max(y, wy), wy + wh)
        if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
            return True
    return False


def in_river(x, y):
    return abs(RIVER_K0 * x - y) / math.hypot(RIVER_K0, 1) < RIVER_HALF


def in_bush(x, y):
    return any(bx <= x <= bx + bw and by <= y <= by + bh for bx, by, bw, bh in BUSHES)


def spawn(r, p):
    mates = sorted((q for q in r.players.values() if q.team == p.team), key=lambda q: q.pid)
    i = mates.index(p); n = len(mates)
    p.x = BASES[p.team][0]; p.y = BASES[p.team][1] + (i - (n - 1) / 2) * 1.3 * T
    p.ep += 1; p.tpos = time.time() + 2.0  # buộc client chốt lại vị trí theo máy chủ (2s không tự mô phỏng)


def drop_flag(r, p):
    if 0 <= p.carry < len(r.flags):
        f = r.flags[p.carry]; f["c"] = None; f["planted"] = -1; f["x"], f["y"] = p.x, p.y
    p.carry = -1; p.prog = 0.0; p.pf = -1


def take(r, p, k, f):
    was = f["planted"]  # >= 0: lá cờ đang cắm ở căn cứ của đội đó (bị cướp)
    p.carry = k; f["c"] = p; f["planted"] = -1; p.prog = 0.0; p.pf = -1
    r.ev.append(["p", round(p.x), round(p.y), p.team])
    r.ev.append(["nf", 1 if was >= 0 else 0, p.pid, f["letter"], was])


MON = {0: dict(hp=3, sp=70, r=14, dmg=1, pts=10, exp=(1, 2), heal=0.12, rt=25),    # slime
       1: dict(hp=2, sp=120, r=12, dmg=1, pts=15, exp=(1, 3), heal=0.12, rt=25),   # dơi
       2: dict(hp=14, sp=45, r=26, dmg=2, pts=60, exp=(5, 8), heal=1.0, rt=45),    # golem (trùm giữa bản đồ)
       3: dict(hp=25, sp=GUARD_SP, r=GUARD_R, dmg=2, pts=80, exp=(6, 9), heal=1.0, rt=45),  # thần giữ cờ: đi dạo quanh cờ, bắn laze, bị bắn thì đuổi
       4: dict(hp=6, sp=110, r=16, dmg=1, pts=25, exp=(3, 5), heal=0.3, rt=0)}  # hiệp sĩ canh căn cứ của một đội (chết là mất hẳn trong round, không hồi sinh)

KNIGHT_N, KNIGHT_RING = 5, 100.0                   # số hiệp sĩ mỗi đội, bán kính vòng tuần tra quanh căn cứ
KNIGHT_SEE = BASE_R + 170.0                        # địch vào trong tầm này (tính từ tâm căn cứ) thì hiệp sĩ lao ra chặn
KNIGHT_LEASH = BASE_R + 300.0                      # không đuổi quá xa căn cứ: vượt ngưỡng này là quay về vị trí gác
KNIGHT_ORBIT = 0.35                                # tốc độ đi vòng quanh căn cứ khi tuần tra (rad/giây)
KNIGHT_MELEE = PR + 16 + 30                        # xa hơn mức này (khỏi tầm cận chiến) thì hiệp sĩ bắn súng bong bóng
KNIGHT_GUN_RANGE, KNIGHT_GUN_CD = 360.0, 1.4       # tầm và hồi chiêu súng của hiệp sĩ (1 sát thương/viên)
KNIGHT_LOSE = 520.0                                # địch cách hiệp sĩ xa hơn mức này = chạy thoát -> về lại căn cứ


class _MonOwner:
    """Chủ đạn của quái/hiệp sĩ: không phải người chơi nên không có thống kê, hạ người thì tính là 'bởi quái vật'."""
    pid = -1


MON_OWNER = _MonOwner()


def friendly(mo, team):
    """Hiệp sĩ cùng đội với người bắn/chém thì không bị trúng đòn."""
    return mo.get("tm", -1) == team


def mon_pack(mo):
    return [mo["id"], mo["t"], round(mo["x"]), round(mo["y"]), mo["hp"], round(mo["ch"], 2), round(mo["la"], 2), round(mo["fl"], 2), round(mo["L"]), mo.get("tm", -1)]


def make_mons(r):
    """Đầu mỗi round: 4 slime + 4 dơi đặt đối xứng hai đội, 1 golem ở giữa, mỗi lá cờ có 1 thần giữ cờ bắn laze,
    mỗi đội có 5 hiệp sĩ tuần tra quanh căn cứ (không hồi sinh)."""
    r.mons, r.orbs, r.kp = [], [], [0, 0]
    def free(x, y, rad):
        return not hit_wall(x, y, rad + 6) and all(math.hypot(x - b[0], y - b[1]) > 450 for b in BASES)
    def add(t, x, y):
        c = MON[t]
        r.mons.append({"id": len(r.mons), "t": t, "x": x, "y": y, "hx": x, "hy": y, "hp": c["hp"], "mhp": c["hp"],
                       "r": c["r"], "cd": 0.0, "alive": True, "rt": 0.0, "ch": 0.0, "fl": 0.0, "lcd": 2.0, "la": 0.0, "L": 0.0,
                       "ax": x, "ay": y, "ag": None, "wt": 0.0, "ws": 0.0, "wx": x, "wy": y, "kbt": 0.0, "kvx": 0.0, "kvy": 0.0, "stun": 0.0,
                       "tm": -1, "pa": 0.0, "gcd": 0.0})
    for t in (0, 0, 1, 1):
        for _ in range(80):
            x, y = random.uniform(0.15, 0.85) * W, random.uniform(0.15, 0.85) * H
            if free(x, y, 14) and free(W - x, H - y, 14):
                add(t, x, y); add(t, W - x, H - y); break
    for _ in range(80):
        x, y = W / 2 + random.uniform(-160, 160), H / 2 + random.uniform(-160, 160)
        if free(x, y, 26):
            add(2, x, y); break
    for f in r.flags:  # mỗi lá cờ có một thần giữ cờ đứng cạnh
        for _ in range(40):
            a = random.uniform(0, 6.283); x, y = f["x"] + math.cos(a) * 85, f["y"] + math.sin(a) * 85
            if not hit_wall(x, y, 28):
                add(3, x, y)
                r.mons[-1]["ax"], r.mons[-1]["ay"] = f["x"], f["y"]  # mốc đi dạo = vị trí lá cờ
                break
    for team in (0, 1):  # hiệp sĩ canh căn cứ: xếp đều quanh căn cứ, góc xuất phát ngẫu nhiên
        bx, by = BASES[team]; a0 = random.uniform(0, 6.283)
        for k in range(KNIGHT_N):
            a = a0 + k * 6.283185 / KNIGHT_N
            x, y = bx + math.cos(a) * KNIGHT_RING, by + math.sin(a) * KNIGHT_RING
            add(4, x, y)
            r.mons[-1]["tm"] = team; r.mons[-1]["pa"] = a


def drop_orb(r, x, y, k, v=0):
    r.orbs.append({"x": x + random.uniform(-22, 22), "y": y + random.uniform(-22, 22), "k": k, "v": v, "ttl": 25.0})


def add_exp(r, p, v):
    if p.lv >= MAXLV:
        return
    p.exp += v
    while p.lv < MAXLV and p.exp >= p.lv * 6:
        p.exp -= p.lv * 6; p.lv += 1; p.mhp = HP + p.up + p.lv - 1; p.hp = p.mhp
        r.ev.append(["u", round(p.x), round(p.y), p.team])
    if p.lv >= MAXLV:
        p.exp = 0


def on_kill(r, victim, team):
    """Hạ một đối thủ: đội được cộng điểm, rớt ngẫu nhiên 1-2 cục EXP (và đôi khi một trái tim hồi máu)."""
    r.kp[team] += PTS_KILL
    for _ in range(random.randint(1, 2)):
        drop_orb(r, victim.x, victim.y, 0, random.randint(2, 4) + victim.lv - 1)
    if random.random() < 0.2:
        drop_orb(r, victim.x, victim.y, 1)


def team_has_flag(r, team):
    """Mỗi đội chỉ được mang về 1 lá cờ: đội đã cắm cờ ở căn cứ, hoặc đang có đồng đội vác cờ, thì không nhặt thêm cờ khác."""
    return any(f["planted"] == team or (f["c"] is not None and f["c"].team == team) for f in r.flags)


def defeat(r, victim, killer=None):
    """Một người bị hạ (hết máu): đóng băng, rớt cờ, ghi thống kê và thông báo. killer=None nghĩa là do quái vật/laze."""
    if victim.down > 0:
        return
    victim.down = DOWN_S; drop_flag(r, victim); victim.un = -1
    r.ev.append(["d", round(victim.x), round(victim.y), victim.team])
    victim.deaths += 1
    r.ev.append(["nk", victim.pid, killer.pid if killer is not None else -1])
    if killer is not None:
        killer.kills += 1; killer.score += PTS_KILL
        on_kill(r, victim, killer.team)


def shielding(p):
    return p.sh and p.w == 1 and p.down <= 0


def blocked(r, q, sx, sy):
    """Đòn đánh từ (sx, sy) vào q bị khiên chặn nếu q đang giơ khiên và nguồn nằm trong cung phía trước."""
    if not shielding(q):
        return False
    ang = abs((math.atan2(sy - q.y, sx - q.x) - q.a + math.pi) % (2 * math.pi) - math.pi)
    if ang > SHIELD_ARC + SHIELD_ARC_UP * q.up:
        return False
    r.ev.append(["k", round(q.x), round(q.y), q.team])
    return True


def hit_mon(r, mo, team, by=None, dmg=1):
    mo["hp"] -= dmg
    r.ev.append(["h", round(mo["x"]), round(mo["y"]), team])
    if mo["hp"] > 0:
        if mo["t"] in (3, 4) and by is not None:
            mo["ag"] = by  # bị đánh -> đuổi theo người đánh cho tới khi họ chạy thoát
        return
    c = MON[mo["t"]]
    mo["alive"] = False; mo["rt"] = c["rt"]
    r.kp[team] += c["pts"]
    if by is not None:
        by.score += c["pts"]
    for _ in range(random.randint(3, 4) if mo["t"] >= 2 else random.randint(1, 2)):
        drop_orb(r, mo["x"], mo["y"], 0, random.randint(*c["exp"]))
    if random.random() < c["heal"]:
        drop_orb(r, mo["x"], mo["y"], 1)
    r.ev.append(["d", round(mo["x"]), round(mo["y"]), team])


LASER_CHARGE, LASER_CD, LASER_DMG = 0.9, 2.6, 2
GUARD_WANDER, GUARD_LOSE, GUARD_LEASH = 120.0, 560.0, 650.0  # bán kính đi dạo / khoảng cách "chạy thoát" / dây xích tối đa quanh cờ


def laser_step(r, mo):
    """Thần giữ cờ: ngắm người gần nhất, nạp 0.9s (khoá hướng ở 0.35s cuối) rồi bắn tia laze xuyên người, dừng ở tường."""
    mo["fl"] = max(0.0, mo["fl"] - DT); mo["lcd"] -= DT
    tgt, bd = None, LASER_RANGE
    for p in r.players.values():
        d = math.hypot(p.x - mo["x"], p.y - mo["y"])
        if p.down <= 0 and d < bd:
            tgt, bd = p, d
    ch = mo["ch"]
    if ch <= 0 and tgt and mo["lcd"] <= 0:
        ch = LASER_CHARGE
    if ch > 0:
        if ch > 0.35 and tgt:
            mo["la"] = math.atan2(tgt.y - mo["y"], tgt.x - mo["x"])
        ca, sa = math.cos(mo["la"]), math.sin(mo["la"]); L = 0.0
        while L < 520 and not hit_wall(mo["x"] + ca * L, mo["y"] + sa * L, 3):
            L += 20
        mo["L"] = L; ch -= DT
        if ch <= 0:
            ch = 0.0; mo["fl"] = 0.3; mo["lcd"] = LASER_CD
            for p in r.players.values():
                dx, dy = p.x - mo["x"], p.y - mo["y"]
                if p.down <= 0 and 0 <= dx * ca + dy * sa <= L and abs(-dx * sa + dy * ca) < PR + 7:
                    if blocked(r, p, mo["x"], mo["y"]):
                        continue
                    p.hp -= LASER_DMG
                    r.ev.append(["h", round(p.x), round(p.y), p.team])
                    if p.hp <= 0:
                        defeat(r, p)
    mo["ch"] = ch


def mon_move(mo, tx, ty, sp, stop=4.0):
    d = math.hypot(tx - mo["x"], ty - mo["y"])
    if d <= stop:
        return
    a = math.atan2(ty - mo["y"], tx - mo["x"]); st = min(sp * DT, d)
    nx = mo["x"] + math.cos(a) * st
    if not hit_wall(nx, mo["y"], mo["r"]): mo["x"] = nx
    ny = mo["y"] + math.sin(a) * st
    if not hit_wall(mo["x"], ny, mo["r"]): mo["y"] = ny


def guard_step(r, mo, c):
    """Thần giữ cờ: bị bắn/chém thì đuổi người đó tới khi họ thoát (xa > GUARD_LOSE, ngã, hoặc kéo quá xa cờ);
    bình thường thì đi dạo ngẫu nhiên quanh lá cờ. Đứng yên khi đang nạp laze. Trả về (người gần nhất, khoảng cách) để đánh cận chiến."""
    tg = mo["ag"]
    if tg is not None:
        if (tg not in r.players.values() or tg.down > 0
                or math.hypot(tg.x - mo["x"], tg.y - mo["y"]) > GUARD_LOSE
                or math.hypot(tg.x - mo["ax"], tg.y - mo["ay"]) > GUARD_LEASH):
            mo["ag"] = tg = None  # người chơi đã thoát -> quay về đi dạo
    if mo["ch"] <= 0:  # đang nạp laze thì đứng yên để ngắm
        if tg is not None:
            mon_move(mo, tg.x, tg.y, c["sp"], stop=PR + mo["r"] - 2)
        elif math.hypot(mo["ax"] - mo["x"], mo["ay"] - mo["y"]) > GUARD_WANDER * 1.5:
            mon_move(mo, mo["ax"], mo["ay"], c["sp"] * 0.8)  # đi quá xa cờ (sau khi đuổi) -> về lại
        elif mo["wt"] > 0:
            mo["wt"] -= DT  # đang nghỉ
        elif math.hypot(mo["wx"] - mo["x"], mo["wy"] - mo["y"]) < 8 or mo["ws"] > 4.0:
            mo["wt"], mo["ws"] = random.uniform(1.0, 3.0), 0.0  # tới nơi (hoặc kẹt tường) -> nghỉ rồi chọn điểm mới
            for _ in range(12):
                a, d = random.uniform(0, 6.283), GUARD_WANDER * math.sqrt(random.random())
                x, y = mo["ax"] + math.cos(a) * d, mo["ay"] + math.sin(a) * d
                if not hit_wall(x, y, mo["r"] + 4):
                    mo["wx"], mo["wy"] = x, y; break
            else:
                mo["wx"], mo["wy"] = mo["x"], mo["y"]
        else:
            mo["ws"] += DT
            mon_move(mo, mo["wx"], mo["wy"], c["sp"] * 0.5)
    near, bd = None, 1e9
    for p in r.players.values():
        d = math.hypot(p.x - mo["x"], p.y - mo["y"])
        if p.down <= 0 and d < bd:
            near, bd = p, d
    return near, bd


def knight_step(r, mo, c):
    """Hiệp sĩ: đi vòng quanh căn cứ đội mình; địch lại gần căn cứ (hoặc bắn/chém nó) thì lao ra đánh cận chiến,
    đuổi tới khi địch ngã / chạy thoát / bị kéo quá xa căn cứ thì quay về vị trí gác. Trả về (mục tiêu, khoảng cách)."""
    bx, by = BASES[mo["tm"]]
    mo["gcd"] -= DT
    tg = mo["ag"]
    if tg is not None and (tg not in r.players.values() or tg.down > 0 or tg.team == mo["tm"]
                           or math.hypot(tg.x - bx, tg.y - by) > KNIGHT_LEASH
                           or math.hypot(tg.x - mo["x"], tg.y - mo["y"]) > KNIGHT_LOSE):
        mo["ag"] = tg = None
    if tg is None:
        bd = KNIGHT_SEE
        for p in r.players.values():
            d = math.hypot(p.x - bx, p.y - by)
            if p.team != mo["tm"] and p.down <= 0 and d < bd:
                tg, bd = p, d
    if tg is not None:
        mon_move(mo, tg.x, tg.y, c["sp"], stop=PR + mo["r"] - 2)
        d = math.hypot(tg.x - mo["x"], tg.y - mo["y"])
        if KNIGHT_MELEE < d <= KNIGHT_GUN_RANGE and mo["gcd"] <= 0:  # địch ngoài tầm cận chiến: vừa đuổi vừa bắn
            a = math.atan2(tg.y - mo["y"], tg.x - mo["x"]); ca, sa = math.cos(a), math.sin(a); L = 0.0
            while L < d and not hit_wall(mo["x"] + ca * L, mo["y"] + sa * L, 3):
                L += 16
            if L >= d:  # không bị tường chắn
                mo["gcd"] = KNIGHT_GUN_CD; a += random.uniform(-0.08, 0.08)
                r.bullets.append({"x": mo["x"] + math.cos(a) * (mo["r"] + 3), "y": mo["y"] + math.sin(a) * (mo["r"] + 3),
                                  "vx": math.cos(a) * BSPEED, "vy": math.sin(a) * BSPEED, "t": mo["tm"],
                                  "life": (KNIGHT_GUN_RANGE + 40) / BSPEED, "o": MON_OWNER, "mon": True})
                r.ev.append(["s", round(mo["x"]), round(mo["y"]), mo["tm"], -1])
        return tg, d
    mo["pa"] = (mo["pa"] + KNIGHT_ORBIT * DT) % 6.283185  # điểm gác trượt dần quanh căn cứ
    mon_move(mo, bx + math.cos(mo["pa"]) * KNIGHT_RING, by + math.sin(mo["pa"]) * KNIGHT_RING, c["sp"] * 0.8)
    return None, 1e9


def mon_step(r):
    for mo in r.mons:
        if not mo["alive"]:
            if mo["t"] == 4:
                continue  # hiệp sĩ chết là mất hẳn tới hết round (round sau make_mons tạo lại)
            mo["rt"] -= DT
            if mo["rt"] <= 0:
                mo.update(alive=True, hp=mo["mhp"], x=mo["hx"], y=mo["hy"], ch=0.0, fl=0.0, lcd=2.0,
                          ag=None, wt=0.0, ws=0.0, wx=mo["hx"], wy=mo["hy"], kbt=0.0, stun=0.0)
            continue
        c = MON[mo["t"]]; mo["cd"] -= DT
        if mo["stun"] > 0:  # bị kiếm đánh: choáng + trượt lùi, không hành động
            mo["stun"] -= DT; mo["fl"] = max(0.0, mo["fl"] - DT)
            if mo["kbt"] > 0:
                mo["kbt"] -= DT
                nx = mo["x"] + mo["kvx"] * DT
                if not hit_wall(nx, mo["y"], mo["r"]): mo["x"] = nx
                ny = mo["y"] + mo["kvy"] * DT
                if not hit_wall(mo["x"], ny, mo["r"]): mo["y"] = ny
            continue
        if mo["t"] == 3:
            laser_step(r, mo)
            tg, bd = guard_step(r, mo, c)
        elif mo["t"] == 4:
            tg, bd = knight_step(r, mo, c)
        else:
            tg, bd = None, 300.0
            for p in r.players.values():
                d = math.hypot(p.x - mo["x"], p.y - mo["y"])
                if p.down <= 0 and d < bd and math.hypot(p.x - mo["hx"], p.y - mo["hy"]) < 520:
                    tg, bd = p, d
            tx, ty = (tg.x, tg.y) if tg else (mo["hx"], mo["hy"])
            d = math.hypot(tx - mo["x"], ty - mo["y"])
            if d > 6:
                a = math.atan2(ty - mo["y"], tx - mo["x"]); sp = c["sp"] * (1.0 if tg else 0.8) * DT
                nx = mo["x"] + math.cos(a) * sp
                if not hit_wall(nx, mo["y"], mo["r"]): mo["x"] = nx
                ny = mo["y"] + math.sin(a) * sp
                if not hit_wall(mo["x"], ny, mo["r"]): mo["y"] = ny
        if tg and bd < PR + mo["r"] + 2 and mo["cd"] <= 0:
            mo["cd"] = 1.1
            if blocked(r, tg, mo["x"], mo["y"]):
                continue
            tg.hp -= c["dmg"]
            r.ev.append(["h", round(tg.x), round(tg.y), tg.team])
            if tg.hp <= 0:
                defeat(r, tg)


def orb_step(r):
    keep = []
    for o in r.orbs:
        o["ttl"] -= DT
        if o["ttl"] <= 0:
            continue
        got = next((p for p in r.players.values() if p.down <= 0 and math.hypot(p.x - o["x"], p.y - o["y"]) < 30
                    and (o["k"] == 0 or p.hp < p.mhp)), None)
        if got:
            if o["k"]: got.hp += 1
            else: add_exp(r, got, o["v"])
            r.ev.append(["o", round(got.x), round(got.y), got.team])
            continue
        keep.append(o)
    r.orbs = keep


KB_DIST, KB_T = 110.0, 0.22   # kiếm: đánh bật lùi người chơi 110px trong 0.22s (đồng thời ngắt hành động)
KB_MON = {0: 120.0, 1: 140.0, 2: 40.0, 3: 60.0, 4: 70.0}   # quãng bật lùi theo loại quái (golem nặng nên ít lùi)
KB_STUN = {0: 0.6, 1: 0.6, 2: 0.35, 3: 0.5, 4: 0.4}       # thời gian quái bị choáng (không đi, không đánh, không nạp laze)


def knock_player(r, q, src):
    """Kiếm trúng người chơi: bật lùi + ngắt hành động (vung kiếm, bắn, cắm/cướp cờ) trong KB_T giây."""
    d = math.hypot(q.x - src.x, q.y - src.y)
    a = math.atan2(q.y - src.y, q.x - src.x) if d > 1 else src.a
    q.kbt = KB_T; q.kvx = math.cos(a) * KB_DIST / KB_T; q.kvy = math.sin(a) * KB_DIST / KB_T
    q.sw = 0.0; q.fl = False; q.prog = 0.0; q.pf = -1; q.un = -1; q.cool = max(q.cool, 0.2)
    q.ep += 1  # client bỏ vị trí tự dự đoán, theo máy chủ trong lúc bị bật lùi


def knock_mon(mo, sx, sy):
    """Kiếm trúng quái: bật lùi + choáng; thần giữ cờ đang nạp laze bị ngắt ngay."""
    a = math.atan2(mo["y"] - sy, mo["x"] - sx)
    mo["kbt"] = KB_T; mo["kvx"] = math.cos(a) * KB_MON[mo["t"]] / KB_T; mo["kvy"] = math.sin(a) * KB_MON[mo["t"]] / KB_T
    mo["stun"] = KB_STUN[mo["t"]]; mo["cd"] = max(mo["cd"], 0.8)
    if mo["t"] == 3:
        mo["ch"] = 0.0; mo["lcd"] = max(mo["lcd"], 1.2)


# ---------- tìm đường cho bot (A* trên lưới ô, né tường) ----------
NAV_G = 8                      # ô mịn 8px: dùng để kiểm tra "đi thẳng được không" (đã nở thêm theo bán kính nhân vật)
NAV_C = 16                     # ô thô 16px (= 2x2 ô mịn): dùng cho A*
NAV_PAD = PR + 3               # nở tường thêm PR + 3px để bot không cạ góc tường
NAV_REPLAN = 0.8               # giây: tối thiểu giữa hai lần tính lại đường khi đích đứng yên
NAV_BUDGET = 1                 # số lần chạy A* tối đa mỗi tick (20Hz) trên toàn máy chủ, tránh giật khi nhiều bot cùng tính
_NAV = {}
_NAV_TICK = [0, 0]


def _nav_build():
    gw, gh = int(W // NAV_G), int(H // NAV_G)
    fb = bytearray(gw * gh)
    for j in range(gh):
        cy = (j + 0.5) * NAV_G
        for i in range(gw):
            cx = (i + 0.5) * NAV_G
            if cx < NAV_PAD or cy < NAV_PAD or cx > W - NAV_PAD or cy > H - NAV_PAD:
                fb[j * gw + i] = 1
    for wx, wy, ww, wh in WALLS:
        i0, i1 = max(0, int((wx - NAV_PAD) // NAV_G)), min(gw - 1, int((wx + ww + NAV_PAD) // NAV_G))
        j0, j1 = max(0, int((wy - NAV_PAD) // NAV_G)), min(gh - 1, int((wy + wh + NAV_PAD) // NAV_G))
        for j in range(j0, j1 + 1):
            cy = (j + 0.5) * NAV_G; ny = min(max(cy, wy), wy + wh)
            for i in range(i0, i1 + 1):
                cx = (i + 0.5) * NAV_G; nx = min(max(cx, wx), wx + ww)
                if (cx - nx) ** 2 + (cy - ny) ** 2 < NAV_PAD * NAV_PAD:
                    fb[j * gw + i] = 1
    k = NAV_C // NAV_G
    cw, ch = gw // k, gh // k
    cb = bytearray(cw * ch)
    for j in range(ch):
        for i in range(cw):
            if any(fb[(j * k + b) * gw + i * k + a] for b in range(k) for a in range(k)):
                cb[j * cw + i] = 1
    _NAV.update(gw=gw, gh=gh, fb=fb, cw=cw, ch=ch, cb=cb)


_nav_build()  # dựng lưới đường đi một lần lúc khởi động (~50ms) để không giật ở tick đầu tiên


def nav_los(x1, y1, x2, y2):
    """Đi thẳng từ (x1,y1) tới (x2,y2) mà không chạm tường (đã tính bán kính nhân vật)."""
    if not _NAV:
        _nav_build()
    fb, gw, gh = _NAV["fb"], _NAV["gw"], _NAV["gh"]
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) // (NAV_G * 0.75)))
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n; y = y1 + (y2 - y1) * i / n
        gi, gj = int(x // NAV_G), int(y // NAV_G)
        if gi < 0 or gj < 0 or gi >= gw or gj >= gh or fb[gj * gw + gi]:
            return False
    return True


def _nav_free_cell(cx, cy):
    """Ô thô trống gần (cx,cy) nhất (dò theo vòng) - dùng khi điểm đầu/đích nằm sát hoặc trong tường."""
    cw, ch, cb = _NAV["cw"], _NAV["ch"], _NAV["cb"]
    cx, cy = min(max(cx, 0), cw - 1), min(max(cy, 0), ch - 1)
    if not cb[cy * cw + cx]:
        return cx, cy
    for R in range(1, 40):
        best = None
        for j in range(max(0, cy - R), min(ch - 1, cy + R) + 1):
            for i in range(max(0, cx - R), min(cw - 1, cx + R) + 1):
                if max(abs(i - cx), abs(j - cy)) == R and not cb[j * cw + i]:
                    d = (i - cx) ** 2 + (j - cy) ** 2
                    if best is None or d < best[0]:
                        best = (d, i, j)
        if best:
            return best[1], best[2]
    return None


def nav_path(x1, y1, x2, y2):
    """A* 8 hướng trên lưới thô, không cắt góc tường. Trả về danh sách điểm (đã rút gọn bằng kiểm tra đường thẳng) hoặc None."""
    if not _NAV:
        _nav_build()
    import heapq
    cw, ch, cb = _NAV["cw"], _NAV["ch"], _NAV["cb"]
    s = _nav_free_cell(int(x1 // NAV_C), int(y1 // NAV_C))
    g = _nav_free_cell(int(x2 // NAV_C), int(y2 // NAV_C))
    if not s or not g:
        return None
    si, gi = s[1] * cw + s[0], g[1] * cw + g[0]
    gx, gy = g
    DIAG = 1.4142135
    best = {si: 0.0}
    came = {}
    heap = [(0.0, si)]
    done = set()
    found = False
    while heap:
        _, cur = heapq.heappop(heap)
        if cur in done:
            continue
        if cur == gi:
            found = True
            break
        done.add(cur)
        cx, cy = cur % cw, cur // cw
        gc = best[cur]
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cx + ox, cy + oy
            if nx < 0 or ny < 0 or nx >= cw or ny >= ch or cb[ny * cw + nx]:
                continue
            if ox and oy and (cb[cy * cw + nx] or cb[ny * cw + cx]):
                continue
            ni = ny * cw + nx
            ng = gc + (DIAG if ox and oy else 1.0)
            if ng < best.get(ni, 1e18):
                best[ni] = ng; came[ni] = cur
                dx, dy = abs(nx - gx), abs(ny - gy)
                heapq.heappush(heap, (ng + 1.25 * ((dx + dy) + (DIAG - 2.0) * min(dx, dy)), ni))  # heuristic nhân 1.25: nhanh hơn nhiều, đường dài hơn tối ưu rất ít
    if not found:
        return None
    pts = [(x2, y2)]
    cur = gi
    while cur != si:
        pts.append(((cur % cw + 0.5) * NAV_C, (cur // cw + 0.5) * NAV_C))
        cur = came[cur]
    pts.append(((si % cw + 0.5) * NAV_C, (si // cw + 0.5) * NAV_C))
    pts.reverse()  # [ô xuất phát, ..., ô đích, (x2,y2)]
    pts[-1] = (x2, y2) if nav_los(pts[-2][0], pts[-2][1], x2, y2) else pts[-2]
    out, i = [], 0  # rút gọn: từ mỗi điểm, nhảy tới điểm xa nhất còn đi thẳng tới được
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not nav_los(pts[i][0], pts[i][1], pts[j][0], pts[j][1]):
            j -= 1
        out.append(pts[j]); i = j
    return out


def nav_steer(ai, x, y, tx, ty, now):
    """Điểm bot nên hướng tới ngay lúc này: thẳng tới đích nếu đường thông, ngược lại bám theo đường A* (tính lại khi đích dời / bị kẹt)."""
    if nav_los(x, y, tx, ty):
        ai["path"] = None
        return tx, ty
    path = ai.get("path")
    goal = ai.get("pgoal")
    stale = (path is None or goal is None or math.hypot(goal[0] - tx, goal[1] - ty) > 90 or
             (now - ai.get("pt", 0.0) > NAV_REPLAN and not path) or now - ai.get("pt", 0.0) > 2.5 or ai.pop("repath", False))
    if stale and now - ai.get("pt", 0.0) > 0.25:
        tick = int(now * HZ)
        if _NAV_TICK[0] != tick:
            _NAV_TICK[0], _NAV_TICK[1] = tick, 0
        if _NAV_TICK[1] < NAV_BUDGET:
            _NAV_TICK[1] += 1
            path = nav_path(x, y, tx, ty)
            ai["path"], ai["pgoal"], ai["pt"], ai["pi"] = path, (tx, ty), now + (0.0 if path else 0.75), 0  # không ra đường thì chờ lâu hơn rồi mới thử lại
    path = ai.get("path")
    if not path:
        return tx, ty  # không tìm được đường (hoặc chưa tới lượt tính): đi thẳng, đã có cơ chế chống kẹt dự phòng
    i = ai.get("pi", 0)
    while i < len(path) - 1 and (math.hypot(path[i][0] - x, path[i][1] - y) < 14 or nav_los(x, y, path[i + 1][0], path[i + 1][1])):
        i += 1
    ai["pi"] = i
    return path[i]


def step(r, live):
    for p in r.players.values():
        if p.down > 0:
            p.act = time.time()  # đang bị đóng băng thì chưa tính AFK
            p.down -= DT; p.fl = False; p.kbt = 0.0
            if p.down <= 0:
                p.hp = p.mhp; p.down = 0; spawn(r, p)
            continue
        if not live:
            p.act = time.time()  # chưa vào giờ chơi thì chưa tính AFK
            continue
        if p.kbt > 0:  # đang bị kiếm đánh bật lùi: máy chủ tự di chuyển, bỏ qua mọi hành động
            nx = p.x + p.kvx * DT
            if not hit_wall(nx, p.y, PR): p.x = nx
            ny = p.y + p.kvy * DT
            if not hit_wall(p.x, ny, PR): p.y = ny
            p.kbt -= DT; p.fl = False; p.sw = 0.0
            if p.kbt <= 0:
                p.kbt = 0.0; p.ep += 1; p.tpos = time.time()
            continue
        if p.prog > 0:
            p.act = time.time()  # đang đứng cắm/cướp cờ (phải đứng yên) thì không phải AFK
        if AFK_S > 0 and not p.bot and not p.away and not p.auto and p.team in (0, 1) and time.time() - p.act > AFK_S:
            set_auto(r, p, True)
        if botted(p):
            bot_ai(r, p)
            if p.auto:
                p.ep += 1  # client luôn bám theo vị trí do máy chủ (bot) điều khiển
        if botted(p) or time.time() - p.tpos > 0.5:  # client không gửi vị trí (mất kết nối/đời cũ) thì máy chủ tự mô phỏng
            sp = SPEED * (1 + 0.04 * (p.lv - 1)) * (CARRY_K if p.carry >= 0 else 1) * (RIVER_K if in_river(p.x, p.y) else 1) * (SHIELD_K if shielding(p) else 1)
            nx = p.x + p.dx * sp * DT
            if not hit_wall(nx, p.y, PR): p.x = nx
            ny = p.y + p.dy * sp * DT
            if not hit_wall(p.x, ny, PR): p.y = ny
        p.cool -= DT
        p.sw -= DT
        fire = p.fire or p.fl; p.fl = False
        if fire and p.cool <= 0 and p.w == 1 and not shielding(p):
            p.cool, p.sw = SWORD_COOL, SWORD_T
            r.ev.append(["m", round(p.x), round(p.y), p.team, p.pid])
            for mo in r.mons:
                if mo["alive"] and not friendly(mo, p.team) and math.hypot(mo["x"] - p.x, mo["y"] - p.y) < SWORD_R + mo["r"] + 4 * (p.lv - 1):
                    ang = abs((math.atan2(mo["y"] - p.y, mo["x"] - p.x) - p.a + math.pi) % (2 * math.pi) - math.pi)
                    if ang < 1.05 or math.hypot(mo["x"] - p.x, mo["y"] - p.y) < PR + mo["r"] + 6:
                        hit_mon(r, mo, p.team, p, SWORD_DMG_UP[min(p.up, 3)])
                        if mo["alive"]:
                            knock_mon(mo, p.x, p.y)
            for q in r.players.values():
                if q.team == p.team or q.down > 0:
                    continue
                dd = math.hypot(q.x - p.x, q.y - p.y)
                if dd >= SWORD_R + 4 * (p.lv - 1):
                    continue
                ang = abs((math.atan2(q.y - p.y, q.x - p.x) - p.a + math.pi) % (2 * math.pi) - math.pi)
                if dd < PR + 6 or ang < 1.05:
                    if blocked(r, q, p.x, p.y):
                        continue
                    q.hp -= SWORD_DMG_UP[min(p.up, 3)]
                    r.ev.append(["h", round(q.x), round(q.y), q.team])
                    if q.hp <= 0:
                        defeat(r, q, p)
                    else:
                        knock_player(r, q, p)
        elif fire and p.cool <= 0 and p.w == 0:
            p.cool = COOL
            r.bullets.append({"x": p.x + math.cos(p.a) * (PR + 3), "y": p.y + math.sin(p.a) * (PR + 3),
                              "vx": math.cos(p.a) * BSPEED, "vy": math.sin(p.a) * BSPEED, "t": p.team, "life": BLIFE, "o": p, "dmg": GUN_DMG[min(p.up, 3)]})
            r.ev.append(["s", round(p.x), round(p.y), p.team, p.pid])
        elif fire and p.cool <= 0 and p.w == 2 and p.rk > 0:  # súng tên lửa: bắn 1 quả đuổi mục tiêu
            p.cool = RK_COOL; p.rk -= 1
            r.rockets.append({"x": p.x + math.cos(p.a) * (PR + 8), "y": p.y + math.sin(p.a) * (PR + 8), "a": p.a, "t": p.team,
                              "life": RK_LIFE, "o": p})
            r.ev.append(["rl", round(p.x), round(p.y), p.team, p.pid])
    if not live:
        return
    for p in r.players.values():
        if p.down > 0 or p.kbt > 0:
            continue
        if p.carry >= 0:
            bx, by = BASES[p.team]
            if math.hypot(p.x - bx, p.y - by) < BASE_R:
                p.prog += DT / PLANT_S
                if p.prog >= 1:
                    f = r.flags[p.carry]
                    used = {g["slot"] for g in r.flags if g["planted"] == p.team}
                    slot = next(i for i in range(4) if i not in used)
                    f["c"] = None; f["planted"] = p.team; f["slot"] = slot
                    f["x"] = bx + (1 if p.team == 0 else -1) * 1.5 * T; f["y"] = by + (slot - 1.5) * 1.1 * T
                    r.ev.append(["pl", round(f["x"]), round(f["y"]), p.team])
                    r.ev.append(["nf", 2, p.pid, f["letter"], p.team])
                    p.carry = -1; p.prog = 0.0
            else:
                p.prog = 0.0
            continue
        if p.un >= 0:  # đang nhổ lá cờ nhà đã cắm
            f = r.flags[p.un]
            if f["planted"] != p.team or r.unp[p.team] >= UNPLANT_MAX or math.hypot(p.x - f["x"], p.y - f["y"]) > UNPLANT_R:
                p.un = -1; p.prog = 0.0  # bỏ đi xa / cờ đã bị cướp: huỷ
            else:
                p.prog += DT / UNPLANT_S
                if p.prog >= 1:
                    # nhổ xong: cờ về vị trí gốc, đội này bị khoá không nhặt lại đúng lá đó trong round, phải săn lá cờ khác
                    f["planted"] = -1; f["c"] = None; f["x"], f["y"] = f["hx"], f["hy"]; f["ban"] = p.team
                    r.unp[p.team] += 1
                    r.ev.append(["nf", 7, p.pid, f["letter"], -1])
                    r.ev.append(["p", round(p.x), round(p.y), p.team])
                    p.un = -1; p.prog = 0.0
                continue
        tgt = -1
        has_flag = team_has_flag(r, p.team)  # đội đã có cờ (đã cắm hoặc đồng đội đang vác) thì không nhặt thêm
        for k, f in enumerate(r.flags):
            if not has_flag and f["c"] is None and f["planted"] != p.team and f.get("ban", -1) != p.team and time.time() >= p.nopick and math.hypot(p.x - f["x"], p.y - f["y"]) < 30:
                tgt = k; break
        if tgt < 0:
            p.prog = 0.0; p.pf = -1
        elif r.flags[tgt]["planted"] == -1:
            take(r, p, tgt, r.flags[tgt])
        else:
            if p.pf != tgt:
                p.pf = tgt; p.prog = 0.0
            p.prog += DT / STEAL_S
            if p.prog >= 1:
                take(r, p, tgt, r.flags[tgt])
    for f in r.flags:
        if f["c"] is not None:
            f["x"], f["y"] = f["c"].x, f["c"].y
    keep = []
    for b in r.bullets:
        b["x"] += b["vx"] * DT; b["y"] += b["vy"] * DT; b["life"] -= DT
        if b["life"] <= 0 or hit_wall(b["x"], b["y"], 2):
            continue
        hit = None
        for p in r.players.values():
            if p.team != b["t"] and p.down <= 0 and math.hypot(p.x - b["x"], p.y - b["y"]) < PR + 3:
                hit = p; break
        if not hit and not b.get("mon"):  # đạn của hiệp sĩ không trúng quái trung lập
            mh = next((mo for mo in r.mons if mo["alive"] and not friendly(mo, b["t"]) and math.hypot(mo["x"] - b["x"], mo["y"] - b["y"]) < mo["r"] + 3), None)
            if mh:
                hit_mon(r, mh, b["t"], b.get("o"), b.get("dmg", 1))
                continue
        if hit:
            if blocked(r, hit, b["x"], b["y"]):
                continue  # khiên chặn: đạn biến mất
            hit.hp -= b.get("dmg", 1)
            r.ev.append(["h", round(hit.x), round(hit.y), hit.team])
            if hit.hp <= 0:
                defeat(r, hit, None if b.get("mon") else b["o"])
            continue
        keep.append(b)
    r.bullets = keep
    if live:
        rocket_step(r); pickup_step(r)
        mon_step(r); orb_step(r)


def rocket_explode(r, rk):
    """Tên lửa nổ: mọi địch (người + quái không cùng đội) trong bán kính RK_SPLASH mất RK_DMG máu."""
    x, y, t, o = rk["x"], rk["y"], rk["t"], rk["o"]
    r.ev.append(["x", round(x), round(y), t])
    for q in list(r.players.values()):
        if q.team == t or q.down > 0 or math.hypot(q.x - x, q.y - y) > RK_SPLASH + PR:
            continue
        if blocked(r, q, x, y):
            continue
        q.hp -= RK_DMG
        r.ev.append(["h", round(q.x), round(q.y), q.team])
        if q.hp <= 0:
            defeat(r, q, o)
    for mo in r.mons:
        if mo["alive"] and not friendly(mo, t) and math.hypot(mo["x"] - x, mo["y"] - y) <= RK_SPLASH + mo["r"]:
            hit_mon(r, mo, t, o, RK_DMG)


def rocket_step(r):
    keep = []
    for rk in r.rockets:
        rk["life"] -= DT
        # tìm mục tiêu gần nhất trong tầm: người chơi địch (còn sống) hoặc quái không cùng đội
        tg, bd = None, RK_SEEK
        for q in r.players.values():
            if q.team != rk["t"] and q.down <= 0 and not in_bush(q.x, q.y):  # không dò được người đang núp bụi cỏ
                d = math.hypot(q.x - rk["x"], q.y - rk["y"])
                if d < bd:
                    tg, bd = (q.x, q.y, PR), d
        for mo in r.mons:
            if mo["alive"] and not friendly(mo, rk["t"]):
                d = math.hypot(mo["x"] - rk["x"], mo["y"] - rk["y"])
                if d < bd:
                    tg, bd = (mo["x"], mo["y"], mo["r"]), d
        if tg:
            da = (math.atan2(tg[1] - rk["y"], tg[0] - rk["x"]) - rk["a"] + math.pi) % (2 * math.pi) - math.pi
            rk["a"] += max(-RK_TURN * DT, min(RK_TURN * DT, da))
        rk["x"] += math.cos(rk["a"]) * RK_SPEED * DT; rk["y"] += math.sin(rk["a"]) * RK_SPEED * DT
        if hit_wall(rk["x"], rk["y"], 3):
            rocket_explode(r, rk); continue
        boom = any(q.team != rk["t"] and q.down <= 0 and math.hypot(q.x - rk["x"], q.y - rk["y"]) < PR + 6 for q in r.players.values()) \
            or any(mo["alive"] and not friendly(mo, rk["t"]) and math.hypot(mo["x"] - rk["x"], mo["y"] - rk["y"]) < mo["r"] + 6 for mo in r.mons)
        if boom:
            rocket_explode(r, rk); continue
        if rk["life"] > 0:
            keep.append(rk)
    r.rockets = keep


def pickup_step(r):
    """Tim hồi máu (6 chỗ cố định, hồi lại sau HEART_RESPAWN giây) và súng tên lửa (4 chỗ ở 4 góc, nhặt được 10 đạn)."""
    for h in r.hearts:
        if h["t"] > 0:
            h["t"] -= DT
            continue
        got = next((p for p in r.players.values() if p.down <= 0 and p.hp < p.mhp and math.hypot(p.x - h["x"], p.y - h["y"]) < 30), None)
        if got:
            got.hp = min(got.mhp, got.hp + 1); h["t"] = HEART_RESPAWN
            r.ev.append(["o", round(got.x), round(got.y), got.team])
    for k in r.rkp:
        if k["t"] > 0:
            k["t"] -= DT
            continue
        got = next((p for p in r.players.values() if (not p.bot or p.rk <= 3) and p.down <= 0 and p.rk < RK_AMMO and math.hypot(p.x - k["x"], p.y - k["y"]) < 32), None)
        if got:
            got.rk = RK_AMMO; k["t"] = RK_RESPAWN
            r.ev.append(["p", round(got.x), round(got.y), got.team])


def _emit_safe(ev, data, sid):
    try:
        sio.emit(ev, data, to=sid)
    except Exception:
        pass  # một client lỗi/đã đóng không được làm hỏng cả trận


def send_state(r):
    """Mỗi đội nhận một bản trạng thái riêng: địch đứng trong bụi cỏ (không có đồng đội ở gần) sẽ bị ẩn."""
    evs, r.ev = r.ev, []
    for t in (0, 1):
        team = [p for p in list(r.players.values()) if p.team == t and not p.bot and not p.away]
        if not team:
            continue
        seers = [p for p in team if p.down <= 0]
        vis = [p for p in list(r.players.values()) if p.team == t or not in_bush(p.x, p.y)
               or any(math.hypot(p.x - s.x, p.y - s.y) < SEE_R for s in seers)]
        ids = {p.pid for p in vis}
        st = {"ph": r.phase, "tl": round(r.tl, 1), "i": r.round, "tot": r.total, "pz": r.paused,
              "p": [[p.pid, p.team, round(p.x), round(p.y), round(p.a, 2), p.hp, round(p.down, 1), p.carry, round(p.prog, 2), p.g, p.w, round(max(p.sw, 0) / SWORD_T, 2), p.ep, p.lv, p.exp, p.mhp, int(shielding(p)), int(p.kbt > 0), p.up, p.rk] for p in vis],
              "f": [[round(f["x"]), round(f["y"]), f["c"].pid if f["c"] else 0, f["planted"]] if (not f["c"] or f["c"].pid in ids)
                    else [-1, -1, f["c"].pid, -1] for f in r.flags],
              "b": [[round(b["x"]), round(b["y"]), b["t"], b["o"].pid, b.get("dmg", 1)] for b in r.bullets], "ev": evs, "kp": r.kp, "un": r.unp, "um": UNPLANT_MAX,
              "rk": [[round(k["x"]), round(k["y"]), round(k["a"], 2), k["t"], k["o"].pid] for k in r.rockets],
              "hr": [[round(h["x"]), round(h["y"]), int(h["t"] <= 0)] for h in r.hearts],
              "rp": [[round(k["x"]), round(k["y"]), int(k["t"] <= 0)] for k in r.rkp],
              "mo": [mon_pack(mo) for mo in r.mons if mo["alive"]],
              "ob": [[round(o["x"]), round(o["y"]), o["k"]] for o in r.orbs],
              "ps": [[q.pid, q.score, q.kills, q.deaths] for q in list(r.players.values())]}
        for p in team:
            _emit_safe("st", st, p.sid)
    if r.specs:
        everyone = list(r.players.values())
        full = {"ph": r.phase, "tl": round(r.tl, 1), "i": r.round, "tot": r.total, "pz": r.paused, "sp": 1,
                "p": [[p.pid, p.team, round(p.x), round(p.y), round(p.a, 2), p.hp, round(p.down, 1), p.carry, round(p.prog, 2), p.g, p.w, round(max(p.sw, 0) / SWORD_T, 2), p.ep, p.lv, p.exp, p.mhp, int(shielding(p)), int(p.kbt > 0), p.up, p.rk] for p in everyone],
                "f": [[round(f["x"]), round(f["y"]), f["c"].pid if f["c"] else 0, f["planted"]] for f in r.flags],
                "b": [[round(b["x"]), round(b["y"]), b["t"], b["o"].pid, b.get("dmg", 1)] for b in r.bullets], "ev": evs, "kp": r.kp, "un": r.unp, "um": UNPLANT_MAX,
              "rk": [[round(k["x"]), round(k["y"]), round(k["a"], 2), k["t"], k["o"].pid] for k in r.rockets],
              "hr": [[round(h["x"]), round(h["y"]), int(h["t"] <= 0)] for h in r.hearts],
              "rp": [[round(k["x"]), round(k["y"]), int(k["t"] <= 0)] for k in r.rkp],
                "mo": [mon_pack(mo) for mo in r.mons if mo["alive"]],
                "ob": [[round(o["x"]), round(o["y"]), o["k"]] for o in r.orbs],
              "ps": [[q.pid, q.score, q.kills, q.deaths] for q in list(r.players.values())]}
        for p in list(r.specs.values()):
            _emit_safe("st", full, p.sid)


def roster(r):
    return [{"pid": p.pid, "nick": p.nick, "team": p.team} for p in r.players.values()]


def expire_away(r):
    """Người chơi mất kết nối quá REJOIN_S giây thì bị loại khỏi trận."""
    if REJOIN_S <= 0:
        return
    now = time.time()
    for k, q in list(r.players.items()):
        if q.away and now - q.awayAt > REJOIN_S:
            drop(k)


def wait(r, secs, live, phase):
    end = time.time() + secs; nxt = last = time.time()
    while True:
        if r.dead or r.abort:
            return False
        now = time.time()
        if r.paused:
            end += now - last; nxt = now
        last = now
        left = end - now
        if left <= 0:
            return True
        r.beat = time.time()
        try:
            with LOCK:
                r.phase = phase; r.tl = left
                expire_away(r)
                if r.paused:
                    for q in r.players.values():
                        q.act = time.time()
                if phase in ("read", "play"):
                    if not r.paused:
                        step(r, live)
                    send_state(r)
        except Exception:
            print("[!] Lỗi vòng lặp trận, phòng", r.code); traceback.print_exc()
        nxt += DT
        sio.sleep(max(0.0, nxt - time.time()))


def play_round(r, i):
    q = next_question(); n = len(q["options"])
    spots = FLAG_SETS[min(4, max(2, n))][:n]
    random.shuffle(spots)
    with LOCK:
        r.q, r.round, r.bullets, r.ev, r.paused = q, i, [], [], False
        r.rockets = []
        r.hearts = [{"x": a * T, "y": b * T, "t": 0.0} for a, b in HEART_SPOTS_T]
        r.rkp = [{"x": a * T, "y": b * T, "t": 0.0} for a, b in RK_SPOTS_T]
        r.flags = [{"x": spots[k][0] * T, "y": spots[k][1] * T, "c": None, "planted": -1, "slot": 0, "letter": k,
                    "hx": spots[k][0] * T, "hy": spots[k][1] * T, "ban": -1} for k in range(n)]
        r.unp = [0, 0]
        for p in r.players.values():
            p.up = r.up[p.team] if p.team in (0, 1) else 0
            p.reset(); spawn(r, p)
        make_mons(r)
        sio.emit("rd", {"i": i, "n": r.rounds, "q": {"question": q["question"], "options": q["options"]},
                        "players": roster(r), "map": MAPINFO, "up": list(r.up)}, to=r.code)
    if not wait(r, READ_S, False, "read"):
        return False
    if not wait(r, PLAY_S, True, "play"):
        return False
    with LOCK:
        planted = [[f["letter"], f["planted"]] for f in r.flags if f["planted"] >= 0]
        delta = [0, 0]
        for letter, t in planted:
            delta[t] += PTS_OK if letter == q["ok"] else PTS_BAD
        upg = [False, False]
        for letter, t in planted:
            if letter == q["ok"] and r.up[t] < UP_MAX:
                r.up[t] += 1; upg[t] = True  # đội cắm đúng cờ: round sau +1 máu tối đa, súng/kiếm mạnh hơn, khiên rộng hơn
        delta[0] += r.kp[0]; delta[1] += r.kp[1]  # điểm hạ quái và hạ đối thủ
        r.total = [r.total[0] + delta[0], r.total[1] + delta[1]]
        res = {"ok": q["ok"], "explanation": q["explanation"], "planted": planted, "delta": delta, "tot": r.total, "last": i == r.rounds - 1,
               "up": list(r.up), "upg": upg, "upmax": UP_MAX}
        r.bullets = []; r.rockets = []
    sio.emit("res", res, to=r.code)
    return wait(r, RESULT_S, False, "result")


def finish_match(r):
    """Kết thúc trận (kể cả khi luồng trận bị lỗi): đưa phòng về sảnh, loại người mất kết nối, báo client."""
    with LOCK:
        r.state = "lobby"; r.phase = "lobby"; r.flags = []; r.bullets = []; r.rockets = []; r.paused = False
        # thống kê cả trận (gồm cả bot) gửi kèm thông báo kết thúc để hiện bảng tổng kết + chúc mừng
        stats = [[q.pid, q.nick, q.team, q.score, q.kills, q.deaths] for q in r.players.values()]
        for k, q in list(r.players.items()):  # hết trận: người còn đang mất kết nối thì bị loại khỏi phòng
            if q.away:
                drop(k)
        remove_bots(r)
        r.up = [0, 0]
        for p in list(r.players.values()):
            p.up = 0; p.reset(); p.auto = False; p.act = time.time()
    if not r.dead:
        sio.emit("end", {"tot": r.total, "aborted": r.abort, "stats": stats}, to=r.code)
        r.abort = False
        with LOCK:
            push(r)


def run_match(r):
    try:
        _run_match(r)
    except Exception:
        print("[!] Lỗi trong trận, phòng", r.code); traceback.print_exc()
        r.abort = True
    finally:
        try:
            finish_match(r)
        except Exception:
            traceback.print_exc()


def janitor():
    """Dọn phòng treo: phòng không còn ai, hoặc phòng 'đang chơi' mà luồng trận đã chết / đứng quá lâu."""
    while True:
        sio.sleep(15)
        try:
            with LOCK:
                now = time.time()
                for r in list(ROOMS.values()):
                    expire_away(r)
                    humans = [q for q in r.players.values() if not q.bot]
                    if not humans and not r.specs:
                        r.dead = True; ROOMS.pop(r.code, None); print("[*] Dọn phòng trống", r.code)
                    elif r.state == "playing" and now - getattr(r, "beat", now) > 20:
                        print("[!] Phòng", r.code, "đứng im >20s, ép kết thúc trận"); r.abort = True
                        finish_match(r)
                sio.emit("rooms", rooms_list())
        except Exception:
            traceback.print_exc()


def _run_match(r):
    load_questions()
    r.total = [0, 0]; r.up = [0, 0]
    with LOCK:
        remove_bots(r)
        if r.pve:
            add_bots(r)
        elif r.eve or r.fill:  # EvE: lập đủ size bot cho CẢ HAI đội (không có người chơi thật)
            fill_bots(r)
        for q in r.players.values():
            q.score = q.kills = q.deaths = 0; q.up = 0
        sio.emit("room", info(r), to=r.code)
    for i in range(r.rounds):
        if not play_round(r, i):
            break


# ---------- Cloudflare Tunnel (giống snake-AI) ----------
_cloudflared_proc = None
_cloudflared_url = None


def _cloudflared_asset():
    sysname = platform.system().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64",
            "armv7l": "arm", "armv6l": "arm", "i386": "386", "i686": "386"}.get(platform.machine().lower(), "amd64")
    if sysname == "linux":
        return f"cloudflared-linux-{arch}", False
    if sysname == "windows":
        return f"cloudflared-windows-{'386' if arch == '386' else 'amd64'}.exe", False
    if sysname == "darwin":
        return f"cloudflared-darwin-{'arm64' if arch == 'arm64' else 'amd64'}.tgz", True
    return None, False


def download_cloudflared(dest_dir):
    asset, is_tgz = _cloudflared_asset()
    if not asset:
        return None
    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{asset}"
    local_path = os.path.join(dest_dir, "cloudflared.exe" if os.name == "nt" else "cloudflared")
    print(f"[*] Đang tải cloudflared: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        blob = resp.read()
    if len(blob) < 1_000_000:
        raise RuntimeError(f"File tải về quá nhỏ ({len(blob)} byte), có thể bị chặn mạng")
    if is_tgz:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            member = next(m for m in tf.getmembers() if m.name.endswith("cloudflared"))
            with open(local_path, "wb") as out:
                out.write(tf.extractfile(member).read())
    else:
        with open(local_path, "wb") as out:
            out.write(blob)
    if os.name != "nt":
        os.chmod(local_path, 0o755)
    return local_path


def _cloudflared_ok(path):
    try:
        return subprocess.run([path, "--version"], capture_output=True, timeout=20).returncode == 0
    except Exception:
        return False


def ensure_cloudflared_binary():
    found = shutil.which("cloudflared")
    if found and _cloudflared_ok(found):
        return found
    local_path = os.path.join(BASE, "cloudflared.exe" if os.name == "nt" else "cloudflared")
    if os.path.exists(local_path):
        if _cloudflared_ok(local_path):
            return local_path
        print("[!] cloudflared bị hỏng, đang xoá và tải lại...")
        try:
            os.remove(local_path)
        except OSError as e:
            print(f"[!] Không xoá được {local_path}: {e}")
            return None
    try:
        path = download_cloudflared(BASE)
        if path and _cloudflared_ok(path):
            return path
        print("[!] File cloudflared tải về không chạy được.")
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"[!] Không thể tự động tải cloudflared: {e}")
    return None


def launch_cloudflared(bin_path):
    if TUNNEL_TOKEN and TUNNEL_HOST:
        cfg = os.path.join(BASE, "flag_cloudflared.yml")   # tên riêng, không đè config.yml của snake-AI
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(f"tunnel: {TUNNEL_TOKEN}\n\nprotocol: http2\ningress:\n  - hostname: {TUNNEL_HOST}\n"
                    f"    service: http://{HOST}:{PORT}\n  - service: http_status:404\n")
        cmd = [bin_path, "tunnel", "--no-autoupdate", "--config", cfg, "run", "--token", TUNNEL_TOKEN]
    else:
        if TUNNEL_TOKEN or TUNNEL_HOST:
            print("[!] Thiếu TUNNEL_TOKEN hoặc TUNNEL_HOST - dùng domain tạm trycloudflare.com.")
        cmd = [bin_path, "tunnel", "--no-autoupdate", "--url", f"http://{HOST}:{PORT}"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")


def monitor_cloudflared(proc):
    global _cloudflared_url
    ansi = re.compile(r"\x1b\[[0-9;]*[mK]")
    try:
        with proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                clean_line = ansi.sub("", line).strip()
                if not clean_line:
                    continue
                print(f"[CLOUDFLARED] {clean_line}")
                if TUNNEL_TOKEN and TUNNEL_HOST:
                    if _cloudflared_url is None and re.search(r"[Rr]egistered tunnel connection", clean_line):
                        _cloudflared_url = TUNNEL_HOST
                        print("\n" + "=" * 60 + f"\n Cướp Cờ đang chạy tại: https://{TUNNEL_HOST}\n" + "=" * 60 + "\n")
                    continue
                m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", clean_line)
                if m and m.group(0) != _cloudflared_url:
                    _cloudflared_url = m.group(0)
                    print("\n" + "=" * 60 + f"\n Cướp Cờ đang chạy tại: {_cloudflared_url}\n" + "=" * 60 + "\n")
    except Exception:
        pass


def start_tunnel_and_watchdog():
    global _cloudflared_proc
    bin_path = ensure_cloudflared_binary()
    if not bin_path:
        print("[!] TUNNEL=true nhưng không tìm được/tải được cloudflared. Bỏ qua tunnel.")
        return
    _cloudflared_proc = launch_cloudflared(bin_path)
    threading.Thread(target=monitor_cloudflared, args=(_cloudflared_proc,), daemon=True).start()
    while True:
        time.sleep(1)
        if _cloudflared_proc.poll() is not None:
            print("[!] cloudflared dừng đột ngột, đang khởi động lại...")
            time.sleep(2)
            _cloudflared_proc = launch_cloudflared(bin_path)
            threading.Thread(target=monitor_cloudflared, args=(_cloudflared_proc,), daemon=True).start()


def stop_tunnel():
    if _cloudflared_proc is not None:
        try:
            _cloudflared_proc.terminate()
        except Exception:
            pass


class NoDelayHandler(WSGIRequestHandler):
    def setup(self):
        super().setup()
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("10.255.255.255", 1))
            return sk.getsockname()[0]
    except Exception:
        return None


# ---------- HTTPS trực tiếp ----------
def _parse_src(v):
    """'url;<link>' | 'file;<đường dẫn>' | 'none'/trống -> (loại, giá trị) hoặc None."""
    v = (v or "").strip()
    if not v or v.lower() == "none":
        return None
    kind, _, val = v.partition(";")
    kind, val = kind.strip().lower(), val.strip()
    if kind in ("url", "file") and val:
        return kind, val
    print(f"[!] Giá trị '{v}' không hợp lệ. Dùng: url;<link> | file;<đường dẫn> | none")
    return None


def _sibling_key(cert_src):
    """HTTPS_KEY trống + HTTPS_CERT kết thúc bằng fullchain.pem -> lấy privkey.pem cùng thư mục."""
    kind, val = cert_src
    if val.lower().endswith("fullchain.pem"):
        return kind, val[:-len("fullchain.pem")] + "privkey.pem"
    return None


def _fetch_pem(src):
    kind, val = src
    if kind == "file":
        path = val if os.path.isabs(val) else os.path.join(BASE, val)
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(val, headers={"User-Agent": "flag-server"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _write_bin(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def _sync_tls(ctx, cert_src, key_src, first=False):
    """Tải/đọc cert + key, kiểm tra hợp lệ rồi nạp vào ctx. Trả True nếu có thay đổi."""
    cb, kb = _fetch_pem(cert_src), _fetch_pem(key_src)
    os.makedirs(TLS_DIR, exist_ok=True)
    cp, kp = os.path.join(TLS_DIR, "fullchain.pem"), os.path.join(TLS_DIR, "privkey.pem")
    try:
        with open(cp, "rb") as f1, open(kp, "rb") as f2:
            old = (f1.read(), f2.read())
    except OSError:
        old = None
    if not first and old == (cb, kb):
        return False
    cn, kn = cp + ".new", kp + ".new"
    _write_bin(cn, cb, 0o644); _write_bin(kn, kb, 0o600)
    try:
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cn, kn)  # cert/key sai hoặc không khớp -> lỗi tại đây
    except Exception:
        for p in (cn, kn):
            try: os.remove(p)
            except OSError: pass
        raise
    os.replace(cn, cp); os.replace(kn, kp)
    ctx.load_cert_chain(cp, kp)
    return True


def _tls_refresher(ctx, cert_src, key_src):
    while True:
        time.sleep(max(0.1, TLS_REFRESH_H) * 3600)
        try:
            if _sync_tls(ctx, cert_src, key_src):
                print("[*] Đã nạp lại chứng chỉ HTTPS mới.")
        except Exception as e:
            print(f"[!] Không làm mới được chứng chỉ HTTPS (giữ cert cũ): {e}")


def start_https():
    cert_src = _parse_src(HTTPS_CERT)
    if not cert_src:
        print("[*] HTTPS_CERT trống/none - không bật HTTPS trực tiếp.")
        return
    key_src = _parse_src(HTTPS_KEY) or _sibling_key(cert_src)
    if not key_src:
        print("[!] Thiếu HTTPS_KEY (và HTTPS_CERT không kết thúc bằng fullchain.pem để tự suy ra privkey.pem) - không bật HTTPS.")
        return
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        _sync_tls(ctx, cert_src, key_src, first=True)
    except Exception as e:
        print(f"[!] Không nạp được chứng chỉ HTTPS: {e}")
        return
    from werkzeug.serving import make_server
    try:
        srv = make_server(TLS_HOST, TLS_PORT, app, threaded=True, ssl_context=ctx, request_handler=NoDelayHandler)
    except OSError as e:
        print(f"[!] Không mở được HTTPS tại {TLS_HOST}:{TLS_PORT}: {e} (cổng < 1024 trên Linux/macOS cần quyền root, hoặc cổng đang bị chiếm)")
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if cert_src[0] == "url" or key_src[0] == "url" or TLS_REFRESH_H > 0:
        threading.Thread(target=_tls_refresher, args=(ctx, cert_src, key_src), daemon=True).start()
    print(f"[*] HTTPS đang chạy tại {TLS_HOST}:{TLS_PORT} (chỉ truy cập được bằng đúng tên miền của chứng chỉ, không phải IP).")


# ---------- phục vụ web ----------
@app.route("/")
def index():
    return send_from_directory(BASE, "flag.html")


@app.route("/<path:f>")
def static_files(f):
    if f in ("socket_io_min.js", "flag.html", "manifest.json", "version.json", "favicon.ico", "favicon-32.png", "icon-192.png", "icon-512.png"):   # question.json cố tình KHÔNG được trả ra
        return send_from_directory(BASE, f)
    if f.startswith("img/") and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")):   # ảnh giao diện (nền sảnh...) nằm trong thư mục img/
        return send_from_directory(os.path.join(BASE, "img"), f[4:], max_age=86400)
    abort(404)


_boot = {"master": False, "worker": False}


def startup_worker():
    """Việc cần làm trong tiến trình chạy game (nơi giữ ROOMS/trận đấu): nạp câu hỏi, in địa chỉ, mở HTTPS trực tiếp."""
    if _boot["worker"]:
        return
    _boot["worker"] = True
    load_questions()
    sio.start_background_task(janitor)
    sio.start_background_task(mm_loop)
    print(f"[*] Phiên bản game: {VERSION_NAME} (version {VERSION}) - chỉ client cùng version được kết nối")
    print(f"[*] Bản đồ {TW}x{TH} ô, {HZ} lần/giây. CORS: {ORIGINS if ORIGINS == '*' else ', '.join(ORIGINS)}")
    print(f"[*] Mở http://{'127.0.0.1' if HOST in ('0.0.0.0', '::') else HOST}:{PORT}/")
    if HOST in ("0.0.0.0", "::") and lan_ip():
        print(f"[*] Máy khác cùng Wi-Fi/LAN mở: http://{lan_ip()}:{PORT}/")
    elif HOST not in ("0.0.0.0", "::"):
        print("[*] (Muốn máy khác trong LAN vào được: đặt HOST=0.0.0.0 trong .env)")
    start_https()


def startup_master():
    """Chỉ chạy một lần (tiến trình cha của Gunicorn, hoặc tiến trình chính khi chạy python main.py): bật Cloudflare Tunnel."""
    if _boot["master"]:
        return
    _boot["master"] = True
    if TUNNEL_ENABLED:
        threading.Thread(target=start_tunnel_and_watchdog, daemon=True).start()
    else:
        print("[*] TUNNEL=false - không chạy cloudflared, chỉ phục vụ nội bộ.")


def run_dev():
    """Chạy bằng máy chủ phát triển của Werkzeug (python main.py). Dùng khi không có Gunicorn (vd. Windows)."""
    startup_worker()
    startup_master()
    try:
        sio.run(app, host=HOST, port=PORT, debug=False, allow_unsafe_werkzeug=True, request_handler=NoDelayHandler)
    except KeyboardInterrupt:
        print("\n[*] Đang thoát...")
        stop_tunnel(); os._exit(0)
    finally:
        stop_tunnel()


if __name__ == "__main__":
    run_dev()