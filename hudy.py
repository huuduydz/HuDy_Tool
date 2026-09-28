import os, time, subprocess, re, sys, builtins, sqlite3, tempfile, threading, json, base64, io, random, hashlib
from collections import deque
import urllib.request, urllib.error
from datetime import datetime
import xml.etree.ElementTree as ET

# =====================================================================
# ANTI-CRASH & FIX TERMINAL
# =====================================================================
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

_original_print = builtins.print
def safe_print(*args, **kwargs):
    if 'end' not in kwargs:
        kwargs['end'] = '\r\n'
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or 'utf-8'
        safe_args = [
            str(a).encode(enc, errors='replace').decode(enc)
            for a in args
        ]
        _original_print(*safe_args, **kwargs)
builtins.print = safe_print

try:
    import termios
    OLD_TTY = termios.tcgetattr(sys.stdin.fileno())
except:
    OLD_TTY = None

def fix_tty():
    # Chỉ fix TTY từ main thread - tránh bg thread corrupt terminal
    if threading.current_thread() is not threading.main_thread():
        return
    try:
        if OLD_TTY:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, OLD_TTY)
        else:
            os.system("stty sane 2>/dev/null")
    except:
        pass
    # Tắt bracketed paste mode để tránh lỗi gõ phím ra ^[1
    try:
        sys.stdout.write('\033[?2004l')
        sys.stdout.flush()
    except:
        pass

def safe_input(prompt=''):
    """Input wrapper: fix TTY trước, sau đó lọc escape sequence ra khỏi kết quả."""
    fix_tty()
    try:
        val = input(prompt)
    except EOFError:
        fix_tty()
        return ''
    # Lọc bỏ escape sequence dạng ^[ (ESC) và ^[[...~ (bracketed paste markers)
    val = re.sub(r'\x1b\[\?2004[hl]', '', val)  # bracketed paste on/off
    val = re.sub(r'\x1b\[200~|\x1b\[201~', '', val)  # paste start/end markers
    val = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', val)  # các escape sequence khác
    val = re.sub(r'\x1b.', '', val)  # ESC + ký tự bất kỳ còn sót
    return val.strip()

def safe_root(cmd, timeout=15):
    """Chạy lệnh root với timeout - luôn đảm bảo chạy dưới quyền su."""
    cmd_str = cmd.strip()
    if not cmd_str.startswith("su ") and not cmd_str.startswith("su\t") and not cmd_str.startswith("su -c"):
        cmd_exec = f"su -c '{cmd_str}'"
    else:
        cmd_exec = cmd_str
    try:
        subprocess.run(
            cmd_exec, shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        pass
    except:
        pass
    # KHÔNG gọi fix_tty() từ background thread - tránh corrupt terminal

def _run_root_capture(command, timeout=15):
    """Chạy một lệnh root không qua shell lồng nhau và giữ lại mã lỗi thật."""
    try:
        result = subprocess.run(
            ["su", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout sau {timeout}s"
    except Exception as exc:
        return -1, "", str(exc)


system_logs = []

def add_log(msg):
    global system_logs
    import time
    t_str = time.strftime("%H:%M:%S")
    formatted = f"[{t_str}] {msg}"
    system_logs.append(formatted)
    if len(system_logs) > 50:
        system_logs.pop(0)

def clear_screen():
    fix_tty()
    # Dùng clear system command thay vì ANSI escape sequence
    # Để tránh tạo tab mới hoặc scroll lạ trên terminal Android/Cloud Phone
    try:
        os.system('clear 2>/dev/null || cls 2>/dev/null')
    except:
        sys.stdout.write('\033[2J\033[H\r')
        sys.stdout.flush()

# =====================================================================
# MÀU SẮC & THEME CYBERPUNK NEON
# =====================================================================
BOLD = '\033[1m'
DIM = '\033[2m'
ITALIC = '\033[3m'
UNDERLINE = '\033[4m'
C = '\033[96m'        # Cyan sáng
G = '\033[92m'        # Green sáng
Y = '\033[93m'        # Yellow sáng
R = '\033[91m'        # Red sáng
M = '\033[95m'        # Magenta sáng
WHITE = W = '\033[97m'        # White sáng
RESET = '\033[0m'     # Reset màu

# Bảng màu mở rộng Modern Cyberpunk Sunset Gradient (256-color mượt mà trên Termux)
CYAN_NEON = '\033[38;5;51m'
PURPLE_NEON = '\033[38;5;141m'
PINK_NEON = '\033[38;5;205m'
GOLD_NEON = '\033[38;5;220m'
GREEN_MINT = '\033[38;5;48m'
BLUE_ICE = '\033[38;5;39m'
GRAY_DARK = '\033[38;5;240m'
GRAY_LIGHT = '\033[38;5;250m'

# Bảng màu chuyển sắc HuDy Gradient & High-End Dashboard
C_CYAN_GLOW   = '\033[38;5;51m'   # Electric Cyan Glow
C_CYAN_DEEP   = '\033[38;5;45m'   # Deep Ice Blue
C_VIOLET      = '\033[38;5;141m'  # Neon Amethyst
C_MAGENTA     = '\033[38;5;177m'  # Orchid Magenta
C_HOT_PINK    = '\033[38;5;206m'  # Hot Pink
C_SUNSET_ROSE = '\033[38;5;213m'  # Sunset Rose
C_GOLD        = '\033[38;5;220m'  # Neon Gold
C_MINT        = '\033[38;5;48m'   # Cyber Mint
C_ICE         = '\033[38;5;39m'   # Sky Ice
C_GRAY_DARK   = '\033[38;5;240m'
C_GRAY_LIGHT  = '\033[38;5;250m'

# =====================================================================
# BIẾN TOÀN CỤC
# =====================================================================
selected_packages = []
target_place_id = "4520749081"
COOKIE_LOGIN_REVISION = "2026-09-28 (Ultra Robust Dual-Engine Cookie Injector)"
COOKIE_LOGIN_APP_LOAD_WAIT = 6
kill_all_time = 0
json_path_cache = {}          # {pkg: {acc_name: (path, last_mtime)}}
heartbeat_last_check = {}     # {pkg: {acc_name: last_check_time}}
CLAIMED_NAMES = set()

# Tùy chọn giao diện
CHECK_EXECUTOR_METHOD = "Disable"
CHANGE_ACCOUNTS = "Disable"
CHANGE_ACCOUNTS_CUSTOM = "Disable"
CHECK_UI_TIME = 180
AUTO_BLOCK = "Disable"
AUTO_RESTORE_DELTA_KEY = "Disable"
AUTO_CHECK_ACC_HEALTH = "Enable"
MANDATORY_COOKIE_CHECK_INTERVAL = 60  # Bắt buộc check Cookie mỗi 60s kể cả khi Lua gửi heartbeat
CHECK_ACC_TIME_BLOCKED = 60           # Chu kỳ check lại khi acc bị dính Captcha/Not-Approved (giây)
CHECK_ACC_TIME_NORMAL = 180           # Chu kỳ check định kỳ khi acc đang farm bình thường (giây)
OMOCAPTCHA_KEY = ""

# HuDy WebKey authorization for Tool Rejoin. The key is checked once at launch;
# the server stores only its SHA-256 hash in Cloudflare D1.
HUDY_WEBKEY_BASE = "https://hudyy.com"
HUDY_REJOIN_VERSION = "3.5"
HUDY_REJOIN_ACCOUNT = ""

# =====================================================================
# CẤU HÌNH SCRIPT AUTO INJECT (BẠN CÓ THỂ THAY ĐỔI LINK SCRIPT DƯỚI ĐÂY)
# =====================================================================
# Script được chọn ở mục 2 sẽ tự động inject vào thư mục autoexec của executor (Delta/Fluxus...)
AUTO_INJECT_SCRIPTS = {
    "1": {
        "name": "Hop Fin_Tail",
        "url": "https://raw.githubusercontent.com/huuduydz/AutoSam_TpHome/refs/heads/main/hihi",  # <-- [1] THAY LINK SCRIPT HOP FIN_TAIL TẠI ĐÂY
        "desc": "Script Hop Server Fin_Tail"
    },
    "2": {
        "name": "Hop_Tear",
        "url": "https://raw.githubusercontent.com/huuduydz/AutoSam_TpHome/refs/heads/main/Tear",  # <-- [2] THAY LINK SCRIPT HOP_TEAR TẠI ĐÂY
        "desc": "Script Hop Server Tear"
    },
    "3": {
        "name": "Main_KingLegacy",
        "url": "https://raw.githubusercontent.com/huuduydz/AutoSam_TpHome/refs/heads/main/king_legacy.lua",  # <-- [3] THAY LINK SCRIPT MAIN_KINGLEGACY TẠI ĐÂY
        "desc": "Script Main KingLegacy Farm"
    },
}
SELECTED_SCRIPT_KEY = "1"  # Mặc định chọn script số 1: Hop Fin_Tail
CUSTOM_SCRIPT_URL = ""  # URL hoặc code Lua tùy chỉnh
CUSTOM_SCRIPT_IS_CODE = False  # True nếu CUSTOM_SCRIPT_URL là code Lua trực tiếp
AUTO_SOLVE_CAPTCHA_V2 = "Enable"  # Mặc định BẬT auto solve captchav2
JOIN_SERVER_MODE = "Disable"      # Mặc định TẮT mode join server
JOIN_SERVER_LINK = ""             # Link Private / VIP server tùy chỉnh
# =====================================================================
# CẤU HÌNH ĐƯỜNG DẪN /STORAGE/EMULATED/0/DOWNLOAD (ANDROID & TERMUX)
# =====================================================================
def get_download_dirs():
    """Danh sách các thư mục Download tìm kiếm theo thứ tự ưu tiên."""
    dirs = []
    # 1. Ưu tiên tuyệt đối thư mục Download chính của Android
    for d in ["/storage/emulated/0/Download", "/sdcard/Download"]:
        if os.path.exists(d) and os.path.isdir(d):
            if d not in dirs:
                dirs.append(d)
    # 2. Termux storage symlink
    try:
        t_dl = os.path.expanduser("~/storage/downloads")
        if os.path.exists(t_dl) and os.path.isdir(t_dl) and t_dl not in dirs:
            dirs.append(t_dl)
        t_sh = os.path.expanduser("~/storage/shared/Download")
        if os.path.exists(t_sh) and os.path.isdir(t_sh) and t_sh not in dirs:
            dirs.append(t_sh)
    except:
        pass
    # 3. Chuẩn Android fallback (ngay cả khi chưa mount storage)
    for std_p in ["/storage/emulated/0/Download", "/sdcard/Download"]:
        if std_p not in dirs:
            dirs.append(std_p)
    # 4. Thư mục script hiện tại và cwd
    try:
        s_dir = os.path.dirname(os.path.abspath(__file__))
        if s_dir not in dirs:
            dirs.append(s_dir)
    except:
        pass
    cwd = os.getcwd()
    if cwd not in dirs:
        dirs.append(cwd)
    return dirs

def is_android_env():
    """Kiểm tra thiết bị có phải môi trường Android / Termux không."""
    return os.path.exists("/storage/emulated/0") or os.path.exists("/sdcard") or os.path.exists("/data/data/com.termux")

def get_primary_download_dir():
    """Trả về thư mục Download chính ưu tiên /storage/emulated/0/Download."""
    for d in ["/storage/emulated/0/Download", "/sdcard/Download"]:
        if os.path.exists(d) and os.path.isdir(d):
            return d
    try:
        t_dl = os.path.expanduser("~/storage/downloads")
        if os.path.exists(t_dl) and os.path.isdir(t_dl):
            return t_dl
    except:
        pass
    if os.path.exists("/storage/emulated/0"):
        return "/storage/emulated/0/Download"
    return os.path.dirname(os.path.abspath(__file__))

def get_rejoin_device_fingerprint():
    parts = []
    for command in ["settings get secure android_id", "getprop ro.serialno", "getprop ro.product.model"]:
        code, stdout, _ = _run_root_capture(command, timeout=4)
        if code == 0 and stdout and stdout.lower() not in ("null", "unknown"):
            parts.append(stdout.strip())
    return "|".join(part for part in parts if part) or "hudy-rejoin-device"

def rejoin_api_request(path, payload, timeout=15):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        HUDY_WEBKEY_BASE.rstrip("/") + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"HuDy-Rejoin/{HUDY_REJOIN_VERSION}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8", errors="replace"))
            return data if isinstance(data, dict) else {"ok": False, "error": f"HTTP_{exc.code}"}
        except Exception:
            return {"ok": False, "error": f"HTTP_{exc.code}"}
    except Exception as exc:
        return {"ok": False, "error": f"NETWORK_ERROR: {str(exc)[:80]}"}

def verify_rejoin_access(token):
    global HUDY_REJOIN_ACCOUNT
    clean_token = str(token or "").strip()
    if not clean_token:
        return False, "MISSING_KEY"
    payload = {
        "token": clean_token,
        "fingerprint": get_rejoin_device_fingerprint(),
        "deviceName": os.environ.get("HOSTNAME") or "Android Tool Rejoin",
        "version": HUDY_REJOIN_VERSION,
    }
    result = rejoin_api_request("/api/rejoin/verify", payload)
    if not result.get("ok"):
        HUDY_REJOIN_ACCOUNT = ""
        return False, result.get("error", "ACCESS_DENIED")
    HUDY_REJOIN_ACCOUNT = str(result.get("account") or "")
    return True, "OK"

def require_rejoin_key():
    for attempt in range(3):
        clear_screen()
        print_banner()
        print(f"{C}--- HUDY TOOL REJOIN ACCESS ---{RESET}")
        print(f"{Y}Nhập key được quản trị viên cung cấp để mở tool.{RESET}")
        key = safe_input(f"{M}Rejoin key: {RESET}").strip()
        ok, reason = verify_rejoin_access(key)
        if ok:
            print(f"{G}[✓] Xác thực thành công: {HUDY_REJOIN_ACCOUNT}{RESET}")
            time.sleep(1)
            return True
        remaining = 2 - attempt
        print(f"{R}[✗] Key bị từ chối: {reason}{RESET}")
        if remaining:
            print(f"{Y}Còn {remaining} lần thử.{RESET}")
            time.sleep(2)
    return False

def write_file_safe(file_path, content):
    """Ghi file an toàn trên Mobile Android, tự fallback qua root su + chmod 777 nếu bị giới hạn quyền."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            os.chmod(file_path, 0o777)
        except:
            pass
        return True
    except Exception:
        try:
            safe_root(f"mkdir -p \"$(dirname \"{file_path}\")\"", timeout=5)
            b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
            cmd = f"echo '{b64_content}' | base64 -d > '{file_path}' && chmod 777 '{file_path}'"
            code, _, _ = _run_root_capture(cmd, timeout=5)
            return code == 0
        except:
            return False

def init_download_workspace():
    """
    Tự động khởi tạo đầy đủ các file cần thiết trên Mobile tại /storage/emulated/0/Download:
      1. hudy.py (bản sao script để dễ mở trong MT Manager / ZArchiver / chạy lại)
      2. cookie.txt (file mẫu dán cookie Roblox)
      3. svv.txt (file mẫu dán link VIP Server)
      4. hudy_config.json (file cấu hình hệ thống)
    """
    if not is_android_env():
        return

    primary_dir = "/storage/emulated/0/Download"
    try:
        os.makedirs(primary_dir, exist_ok=True)
    except:
        pass
    safe_root(f"mkdir -p '{primary_dir}' && chmod 777 '{primary_dir}'", timeout=5)

    # 1. Tự sao chép hudy.py vào Download trên mobile nếu chạy từ thư mục khác
    try:
        cur_file = os.path.abspath(__file__)
        target_hudy = os.path.join(primary_dir, "hudy.py")
        if os.path.abspath(target_hudy) != cur_file:
            try:
                with open(cur_file, "r", encoding="utf-8", errors="ignore") as f_in:
                    src_code = f_in.read()
                write_file_safe(target_hudy, src_code)
                safe_root(f"chmod 777 '{target_hudy}'", timeout=5)
            except:
                safe_root(f"cp '{cur_file}' '{target_hudy}' && chmod 777 '{target_hudy}'", timeout=5)
    except:
        pass

    # 2. Tạo sẵn cookie.txt nếu chưa có
    target_cookie = os.path.join(primary_dir, "cookie.txt")
    if not os.path.exists(target_cookie):
        cookie_template = (
            "# =====================================================================\n"
            "# DANH SACH COOKIE ROBLOX (.ROBLOSECURITY)\n"
            "# Dan Cookie vao ben duoi (Moi account 1 dong).\n"
            "# Tool se tu dong doc va nap vao cac app Roblox clone.\n"
            "# =====================================================================\n"
        )
        write_file_safe(target_cookie, cookie_template)
        safe_root(f"chmod 777 '{target_cookie}'", timeout=5)

    # 3. Tạo sẵn svv.txt nếu chưa có
    target_svv = os.path.join(primary_dir, "svv.txt")
    if not os.path.exists(target_svv):
        svv_template = (
            "# =====================================================================\n"
            "# LINK SERVER VIP / PRIVATE SERVER ROBLOX (SVV)\n"
            "# Dan link server rieng hoac link share vao ben duoi:\n"
            "# Vi du: https://www.roblox.com/games/4520749081?privateServerLinkCode=...\n"
            "# Hoac: https://roblox.com/share?code=...&type=Server\n"
            "# =====================================================================\n"
        )
        write_file_safe(target_svv, svv_template)
        safe_root(f"chmod 777 '{target_svv}'", timeout=5)

    # 4. Tạo sẵn hudy_config.json nếu chưa có
    target_cfg = os.path.join(primary_dir, "hudy_config.json")
    if not os.path.exists(target_cfg):
        save_settings()
        safe_root(f"chmod 777 '{target_cfg}'", timeout=5)

def find_file_in_download(filenames):
    """Tìm file trong các đường dẫn Download (trả về path đầu tiên tìm thấy hoặc None)."""
    if isinstance(filenames, str):
        filenames = [filenames]
    search_dirs = get_download_dirs()
    for d in search_dirs:
        for fname in filenames:
            p = os.path.join(d, fname)
            if os.path.exists(p) and os.path.isfile(p):
                return p
    return None

def get_download_save_path(filename):
    """Lấy đường dẫn lưu file vào thư mục Download chuẩn."""
    primary = get_primary_download_dir()
    try:
        os.makedirs(primary, exist_ok=True)
    except:
        pass
    return os.path.join(primary, filename)

def _normalize_roblosecurity_cookie(cookie):
    """Trả về riêng giá trị .ROBLOSECURITY, không kèm tên/header Cookie hay ngoặc kép."""
    if not cookie:
        return ""
    cookie = str(cookie).strip().replace('\r', '').replace('\n', '').strip('\'"')
    match = re.search(r'(?:^|[;\s])\.ROBLOSECURITY\s*=\s*([^;]+)', cookie, re.IGNORECASE)
    if match:
        cookie = match.group(1).strip().strip('\'"')
    return cookie

def load_cookies_from_download():
    """Đọc danh sách cookie Roblox từ file cookie.txt / cookies.txt trong Download."""
    candidates = ["cookie.txt", "cookies.txt", "cookie", "cookies"]
    fpath = find_file_in_download(candidates)
    if not fpath:
        return [], None
    cookies = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().strip('"').strip("'")
                if not line or line.startswith(('#', '//', '--')):
                    continue
                clean_c = _normalize_roblosecurity_cookie(line)
                if clean_c and clean_c not in cookies:
                    cookies.append(clean_c)
    except:
        pass
    return cookies, fpath

def save_cookie_to_download(cookie, append=True):
    """Lưu cookie vào /storage/emulated/0/Download/cookie.txt."""
    clean_c = _normalize_roblosecurity_cookie(cookie)
    if not clean_c:
        return None
    save_path = get_download_save_path("cookie.txt")
    try:
        existing = []
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    l = line.strip()
                    if l and not l.startswith(('#', '//', '--')):
                        existing.append(l)
        if clean_c not in existing:
            if append:
                existing.append(clean_c)
            else:
                existing = [clean_c]
        content = "\n".join(existing) + "\n"
        if write_file_safe(save_path, content):
            return save_path
    except:
        return None

def load_svv_link_from_file():
    """Đọc link VIP / Private Server từ file svv / svv.txt / server.txt tại Download."""
    candidates = ["svv.txt", "svv", "server.txt", "vip.txt", "link.txt", "sv.txt"]
    fpath = find_file_in_download(candidates)
    if not fpath:
        return "", None
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip().strip('"').strip("'")
                if line and not line.startswith(('#', '//', '--')):
                    return line, fpath
    except:
        pass
    return "", fpath

def save_svv_link_to_file(link):
    """Lưu link VIP / Private Server vào file svv.txt tại Download."""
    save_path = get_download_save_path("svv.txt")
    if write_file_safe(save_path, link.strip() + "\n"):
        return save_path
    return None

def get_config_file_path():
    """Tìm file config trong Download hoặc thư mục script."""
    found = find_file_in_download(["hudy_config.json", "config.json"])
    if found:
        return found
    return get_download_save_path("hudy_config.json")

CONFIG_FILE = get_config_file_path()

def load_settings():
    global target_place_id, kill_all_time, CHECK_ACC_TIME_BLOCKED, SELECTED_SCRIPT_KEY, CUSTOM_SCRIPT_URL, CUSTOM_SCRIPT_IS_CODE
    global AUTO_SOLVE_CAPTCHA_V2, JOIN_SERVER_MODE, JOIN_SERVER_LINK, CONFIG_FILE
    try:
        cfg_path = get_config_file_path()
        if cfg_path and os.path.exists(cfg_path):
            CONFIG_FILE = cfg_path
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                target_place_id = str(data.get("target_place_id", target_place_id))
                kill_all_time = int(data.get("kill_all_time", kill_all_time))
                CHECK_ACC_TIME_BLOCKED = int(data.get("check_acc_time_blocked", CHECK_ACC_TIME_BLOCKED))
                SELECTED_SCRIPT_KEY = str(data.get("selected_script_key", "1"))
                if not SELECTED_SCRIPT_KEY or (SELECTED_SCRIPT_KEY not in AUTO_INJECT_SCRIPTS and SELECTED_SCRIPT_KEY not in ["custom", "0"]):
                    SELECTED_SCRIPT_KEY = "1"
                CUSTOM_SCRIPT_URL = str(data.get("custom_script_url", CUSTOM_SCRIPT_URL))
                CUSTOM_SCRIPT_IS_CODE = bool(data.get("custom_script_is_code", False))
                AUTO_SOLVE_CAPTCHA_V2 = str(data.get("auto_solve_captcha_v2", "Enable"))
                if AUTO_SOLVE_CAPTCHA_V2 not in ["Enable", "Disable"]:
                    AUTO_SOLVE_CAPTCHA_V2 = "Enable"
                JOIN_SERVER_MODE = str(data.get("join_server_mode", "Disable"))
                if JOIN_SERVER_MODE not in ["Enable", "Disable"]:
                    JOIN_SERVER_MODE = "Disable"
                JOIN_SERVER_LINK = str(data.get("join_server_link", ""))
        else:
            SELECTED_SCRIPT_KEY = "1"
            AUTO_SOLVE_CAPTCHA_V2 = "Enable"
            JOIN_SERVER_MODE = "Disable"
            JOIN_SERVER_LINK = ""
        # Tự động nạp link VIP server từ file svv.txt trong Download nếu có
        svv_link, _ = load_svv_link_from_file()
        if svv_link:
            JOIN_SERVER_LINK = svv_link
    except:
        SELECTED_SCRIPT_KEY = "1"
        AUTO_SOLVE_CAPTCHA_V2 = "Enable"
        JOIN_SERVER_MODE = "Disable"

def save_settings():
    try:
        data = {
            "target_place_id": target_place_id,
            "kill_all_time": kill_all_time,
            "check_acc_time_blocked": CHECK_ACC_TIME_BLOCKED,
            "selected_script_key": SELECTED_SCRIPT_KEY,
            "custom_script_url": CUSTOM_SCRIPT_URL,
            "custom_script_is_code": CUSTOM_SCRIPT_IS_CODE,
            "auto_solve_captcha_v2": AUTO_SOLVE_CAPTCHA_V2,
            "join_server_mode": JOIN_SERVER_MODE,
            "join_server_link": JOIN_SERVER_LINK,
        }
        content = json.dumps(data, indent=4, ensure_ascii=False)
        primary_cfg = get_download_save_path("hudy_config.json")
        write_file_safe(primary_cfg, content)
        script_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hudy_config.json")
        if script_cfg != primary_cfg:
            write_file_safe(script_cfg, content)
    except:
        pass

load_settings()
init_download_workspace()

def load_omocaptcha_key():
    global OMOCAPTCHA_KEY
    candidates = [
        get_download_save_path("omocaptcha_key.txt"),
        get_download_save_path("license.txt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "omocaptcha_key.txt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "license.txt"),
        "/storage/emulated/0/Download/omocaptcha_key.txt",
        "/storage/emulated/0/Download/license.txt",
        "/sdcard/Download/omocaptcha_key.txt",
        "/sdcard/omocaptcha_key.txt"
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            OMOCAPTCHA_KEY = line
                            return OMOCAPTCHA_KEY
            except:
                pass
    return OMOCAPTCHA_KEY

def save_omocaptcha_key(new_key):
    global OMOCAPTCHA_KEY
    OMOCAPTCHA_KEY = new_key.strip()
    saved = False
    for target in [get_download_save_path("omocaptcha_key.txt"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "omocaptcha_key.txt")]:
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(OMOCAPTCHA_KEY)
            saved = True
        except:
            pass
    return saved

# Nạp key ngay khi khởi động
load_omocaptcha_key()

# Delta key: số giờ trước khi coi key là hết hạn và cần lấy mới
KEY_EXPIRE_HOURS = 23
_last_key_trigger = {}   # {pkg: timestamp} – khi nào lần cuối trigger Get Key
BACON_API_KEY = ""

last_restart_time = {}
last_any_restart_time = 0            # Thời điểm bất kỳ pkg nào restart gần nhất
shared_lock = threading.Lock()       # bảo vệ CLAIMED_NAMES giữa các thread
pkg_restart_locks = {}               # {pkg: Lock} - mỗi pkg 1 lock riêng
global_restart_semaphore = threading.Semaphore(1)  # Chỉ serialize bước boot
file_to_pkg_binding = {}             # {file_path: pkg} - ghi nhớ file json nào thuộc pkg nào

# =====================================================================
# LẤY CPU & RAM
# =====================================================================
def get_cpu_usage():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
            parts = line.split()
            if len(parts) >= 5:
                total = sum(int(x) for x in parts[1:])
                idle = int(parts[4])
                return f"{((total - idle) / total * 100):.2f}%"
    except:
        return "N/A"

def get_memory_usage():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        total = free = 0
        for line in lines:
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                free = int(line.split()[1])
        if total > 0:
            used = total - free
            return f"{(used / total * 100):.1f}%"
    except:
        return "N/A"

# =====================================================================
# GIAO DIỆN BANNER & DASHBOARD LIVE
# =====================================================================
def parse_server_link(link, fallback_place_id="4520749081"):
    """Phân tích link Roblox Private Server / VIP Server / Share Link."""
    link = link.strip()
    if not link:
        return fallback_place_id, ""
    if link.startswith("roblox://"):
        return None, link
    m_pid = re.search(r'/games/(\d+)', link) or re.search(r'placeId=(\d+)', link)
    pid = m_pid.group(1) if m_pid else (fallback_place_id or "4520749081")
    m_code = re.search(r'privateServerLinkCode=([a-zA-Z0-9_\-]+)', link) or re.search(r'linkCode=([a-zA-Z0-9_\-]+)', link)
    if m_code:
        code = m_code.group(1)
        deeplink = f"roblox://experiences/start?placeId={pid}&linkCode={code}"
        return pid, deeplink
    m_share = re.search(r'code=([a-zA-Z0-9_\-]+)', link)
    if "share" in link and m_share:
        return pid, link
    if re.match(r'^[a-zA-Z0-9_\-]{20,}$', link):
        deeplink = f"roblox://experiences/start?placeId={pid}&linkCode={link}"
        return pid, deeplink
    return pid, link

def build_roblox_launch_uri(pkg=None, auth_ticket=None):
    """Tạo URI/Deeplink để khởi chạy Roblox vào game thường hoặc Private/VIP server."""
    global JOIN_SERVER_MODE, JOIN_SERVER_LINK, target_place_id
    if JOIN_SERVER_MODE == "Enable":
        cur_link = JOIN_SERVER_LINK.strip()
        if not cur_link:
            svv_l, _ = load_svv_link_from_file()
            if svv_l:
                cur_link = svv_l
        if cur_link:
            pid, uri = parse_server_link(cur_link, target_place_id)
            if auth_ticket:
                if "roblox://" in uri:
                    sep = "&" if "?" in uri else "?"
                    uri = f"{uri}{sep}authTicket={auth_ticket}"
            return uri
    if target_place_id:
        uri = f"roblox://experiences/start?placeId={target_place_id}"
        if auth_ticket:
            uri += f"&authTicket={auth_ticket}"
        return uri
    return ""

import shutil

def get_terminal_width():
    """Tự động phát hiện độ rộng terminal, mở rộng đầy khung hình cho cả Màn hình Đứng và Ngang."""
    try:
        cols, _ = shutil.get_terminal_size(fallback=(72, 24))
        # Cho phép mở rộng đầy đủ theo độ rộng màn hình (tối đa 160 ký tự trên màn hình ngang)
        return max(54, min(cols - 1, 160))
    except:
        return 68

def visible_len(s):
    """Tính độ dài hiển thị thực tế của chuỗi, bỏ qua các mã màu ANSI."""
    return len(re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', str(s)))

def fit_ansi(s, width):
    """Căn lề chuỗi có chứa mã màu ANSI với độ rộng width chính xác tuyệt đối."""
    vlen = visible_len(s)
    if vlen > width:
        clean = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', str(s))
        return clean[:max(0, width - 3)] + "..."
    return str(s) + (" " * (width - vlen))

def print_banner():
    term_w = get_terminal_width()
    inner_w = term_w - 2

    # Logo HuDy 6 tầng chuyển sắc Cyberpunk Sunset Neon Gradient cực đẹp
    T1 = '\033[38;5;51m'   # Tầng 1: Diamond Cyan (Xanh ngọc sáng chói)
    T2 = '\033[38;5;45m'   # Tầng 2: Deep Ice Blue (Xanh băng sâu lắng)
    T3 = '\033[38;5;141m'  # Tầng 3: Neon Amethyst (Tím thạch anh rực rỡ)
    T4 = '\033[38;5;177m'  # Tầng 4: Orchid Magenta (Hồng ánh tím quý phái)
    T5 = '\033[38;5;206m'  # Tầng 5: Hot Neon Pink (Hồng neon đậm đà)
    T6 = '\033[38;5;220m'  # Tầng 6: Sunset Neon Gold (Vàng hoàng hôn rực rỡ)

    logo_6 = [
        f"{T1}  ██╗  ██╗  ██╗   ██╗  ██████╗   ██╗   ██╗{RESET}",
        f"{T2}  ██║  ██║  ██║   ██║  ██╔══██╗  ╚██╗ ██╔╝{RESET}",
        f"{T3}  ███████║  ██║   ██║  ██║  ██║   ╚████╔╝ {RESET}",
        f"{T4}  ██╔══██║  ██║   ██║  ██║  ██║    ╚██╔╝  {RESET}",
        f"{T5}  ██║  ██║  ╚██████╔╝  ██████╔╝     ██║   {RESET}",
        f"{T6}  ╚═╝  ╚═╝   ╚═════╝   ╚═════╝      ╚═╝   {RESET}"
    ]

    if term_w >= 85:
        # Chế độ xoay ngang (Landscape): Khung thẻ Cyber Card 6 tầng đối xứng 1-1 với Logo
        inner_badge_w = min(54, term_w - 44 - 4)
        
        b_l1 = f" {BOLD}{T1}HUDY REJOIN AUTOMATION{RESET}  {T5}[PRO V3.5]{RESET}"
        b_l2 = f" {C_GRAY_LIGHT}Tác Giả:{RESET} {C_MINT}HuDy{RESET}   │ {C_GRAY_LIGHT}Anti-Hang:{RESET} {C_MINT}BẬT 24/7{RESET}"
        b_l3 = f" {C_GRAY_LIGHT}Chế Độ:{RESET}  {C_ICE}Multi-Acc{RESET} │ {C_GRAY_LIGHT}CaptchaV2:{RESET} {T6}Đa Ngôn Ngữ{RESET}"

        side_badge = [
            f"{T2}╭" + "─" * (inner_badge_w) + f"╮{RESET}",
            f"{T2}│{RESET}" + fit_ansi(b_l1, inner_badge_w) + f"{T2}│{RESET}",
            f"{T3}├" + "─" * (inner_badge_w) + f"┤{RESET}",
            f"{T4}│{RESET}" + fit_ansi(b_l2, inner_badge_w) + f"{T4}│{RESET}",
            f"{T5}│{RESET}" + fit_ansi(b_l3, inner_badge_w) + f"{T5}│{RESET}",
            f"{T6}╰" + "─" * (inner_badge_w) + f"╯{RESET}"
        ]
        print()
        for i in range(6):
            print(f"{logo_6[i]}    {side_badge[i]}")
    else:
        # Chế độ đứng (Portrait): 6 tầng nhãn thông tin xếp gọn gàng bên phải
        badge_lines = [
            f" {BOLD}{T1}HUDY REJOIN [V3.5]{RESET}",
            f" {T3}Core High-Speed{RESET}",
            f" {C_MINT}Tác Giả: HuDy ●{RESET}",
            f" {T4}Anti-Hang: BẬT{RESET}",
            f" {T5}Auto-Bypass: 24/7{RESET}",
            f" {T6}Captcha V2: Đa Ngôn Ngữ{RESET}",
        ]
        print()
        for i in range(6):
            print(f"{logo_6[i]}  {badge_lines[i]}")

    # Thanh Sub-bar bên dưới Logo
    if inner_w >= 85:
        sub = f" {BOLD}{WHITE}HuDy Automation Core{RESET} {C_GRAY_DARK}•{RESET} {C_MINT}Anti-Hang{RESET} {C_GRAY_DARK}•{RESET} {T6}Auto-Bypass{RESET} {C_GRAY_DARK}•{RESET} {T1}Auto-Inject{RESET} {C_GRAY_DARK}•{RESET} {T3}Multi-Lang CaptchaV2{RESET} {C_GRAY_DARK}•{RESET} {T5}VIP Server{RESET}"
    elif inner_w >= 68:
        sub = f" {BOLD}{WHITE}HuDy Automation Core{RESET} {C_GRAY_DARK}•{RESET} {C_MINT}Anti-Hang{RESET} {C_GRAY_DARK}•{RESET} {T6}Auto-Bypass{RESET} {C_GRAY_DARK}•{RESET} {T1}Auto-Inject{RESET} {C_GRAY_DARK}•{RESET} {T3}CaptchaV2{RESET}"
    else:
        sub = f" {BOLD}{WHITE}HuDy Core{RESET} {C_GRAY_DARK}•{RESET} {C_MINT}Anti-Hang{RESET} {C_GRAY_DARK}•{RESET} {T6}Bypass{RESET} {C_GRAY_DARK}•{RESET} {T1}Auto-Inject{RESET}"

    print(f"{T2}╭{'─' * inner_w}╮{RESET}")
    print(f"{T2}│{RESET}{fit_ansi(sub, inner_w)}{T2}│{RESET}")
    print(f"{T2}╰{'─' * inner_w}╯{RESET}")


def print_dashboard(states):
    clear_screen()
    print_banner()
    term_w = get_terminal_width()
    inner_w = term_w - 2

    cpu_str = get_cpu_usage()
    ram_str = get_memory_usage()
    cur_sc_name = AUTO_INJECT_SCRIPTS.get(SELECTED_SCRIPT_KEY, {}).get("name", "Custom" if SELECTED_SCRIPT_KEY == "custom" else "Tắt")
    pid_display = target_place_id if target_place_id else "Sảnh (0)"
    restart_display = f"{kill_all_time}m" if kill_all_time > 0 else "Tắt"
    v2_display = "Bật" if AUTO_SOLVE_CAPTCHA_V2 == "Enable" else "Tắt"
    join_display = "Bật (VIP)" if JOIN_SERVER_MODE == "Enable" else "Tắt"
    v2_col = C_MINT if v2_display == 'Bật' else R
    join_col = C_VIOLET if join_display != 'Tắt' else C_GRAY_LIGHT

    # 1. Khung Thông Số Hệ Thống & Cấu Hình (Căn lề lưới đối xứng hoàn hảo 100%)
    title_box = " ⚙️ THÔNG SỐ HỆ THỐNG & CẤU HÌNH "
    dashes_top = max(2, inner_w - visible_len(title_box) - 1)
    print(f"{C_CYAN_DEEP}╭─{title_box}{'─' * dashes_top}╮{RESET}")

    if inner_w >= 75:
        # Bố trí 4 cột đều nhau tuyệt đối trên màn hình ngang
        w_c1 = (inner_w - 7) // 4
        w_c2 = (inner_w - 7) // 4
        w_c3 = (inner_w - 7) // 4
        w_c4 = inner_w - 7 - (w_c1 + w_c2 + w_c3)

        c1_1 = f" CPU: {C_MINT}{cpu_str}{RESET}"
        c1_2 = f" RAM: {C_ICE}{ram_str}{RESET}"
        c1_3 = f" Place: {C_GOLD}{pid_display}{RESET}"
        c1_4 = f" CaptV2: {v2_col}{v2_display}{RESET}"

        c2_1 = f" Restart: {Y}{restart_display}{RESET}"
        c2_2 = f" Cookie: {C_MINT}{CHECK_ACC_TIME_BLOCKED}s{RESET}"
        c2_3 = f" JoinSv: {join_col}{join_display}{RESET}"
        c2_4 = f" Script: {C_HOT_PINK}{cur_sc_name}{RESET}"

        row1 = f" {fit_ansi(c1_1, w_c1 - 1)}│ {fit_ansi(c1_2, w_c2 - 1)}│ {fit_ansi(c1_3, w_c3 - 1)}│ {fit_ansi(c1_4, w_c4 - 1)}"
        row2 = f" {fit_ansi(c2_1, w_c1 - 1)}│ {fit_ansi(c2_2, w_c2 - 1)}│ {fit_ansi(c2_3, w_c3 - 1)}│ {fit_ansi(c2_4, w_c4 - 1)}"

        print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(row1, inner_w)}{C_CYAN_DEEP}│{RESET}")
        print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(row2, inner_w)}{C_CYAN_DEEP}│{RESET}")
    else:
        # Bố trí 2 cột đều nhau trên màn hình đứng hẹp
        w_c1 = (inner_w - 3) // 2
        w_c2 = inner_w - 3 - w_c1

        row1 = f" {fit_ansi(f'CPU: {C_MINT}{cpu_str}{RESET}', w_c1 - 1)}│ {fit_ansi(f'RAM: {C_ICE}{ram_str}{RESET}', w_c2 - 1)}"
        row2 = f" {fit_ansi(f'Place: {C_GOLD}{pid_display}{RESET}', w_c1 - 1)}│ {fit_ansi(f'CaptV2: {v2_col}{v2_display}{RESET}', w_c2 - 1)}"
        row3 = f" {fit_ansi(f'Restart: {Y}{restart_display}{RESET}', w_c1 - 1)}│ {fit_ansi(f'Cookie: {C_MINT}{CHECK_ACC_TIME_BLOCKED}s{RESET}', w_c2 - 1)}"
        row4 = f" {fit_ansi(f'JoinSv: {join_col}{join_display}{RESET}', w_c1 - 1)}│ {fit_ansi(f'Script: {C_HOT_PINK}{cur_sc_name}{RESET}', w_c2 - 1)}"
        for r in [row1, row2, row3, row4]:
            print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(r, inner_w)}{C_CYAN_DEEP}│{RESET}")

    print(f"{C_CYAN_DEEP}╰{'─' * inner_w}╯{RESET}")

    # 2. Khung Tiến Trình Tài Khoản (Tính toán cột chính xác tuyệt đối theo độ rộng màn hình)
    pkg_cnt = len(selected_packages)
    acc_title = f" 🎮 TIẾN TRÌNH TÀI KHOẢN ({pkg_cnt} Package) "
    dashes_acc = max(2, inner_w - visible_len(acc_title) - 1)
    print(f"{C_CYAN_DEEP}╭─{acc_title}{'─' * dashes_acc}╮{RESET}")

    if inner_w >= 85:
        w_pkg = int(inner_w * 0.35)
        w_user = int(inner_w * 0.22)
        w_status = inner_w - w_pkg - w_user - 8
    elif inner_w >= 70:
        w_pkg = int(inner_w * 0.35)
        w_user = int(inner_w * 0.22)
        w_status = inner_w - w_pkg - w_user - 8
    else:
        w_pkg = 20
        w_user = 13
        w_status = max(14, inner_w - w_pkg - w_user - 8)

    hdr_str = f" {BOLD}{'Package':<{w_pkg}} │ {'Username':<{w_user}} │ {'Trạng Thái':<{w_status}}{RESET} "
    print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(hdr_str, inner_w)}{C_CYAN_DEEP}│{RESET}")
    print(f"{C_CYAN_DEEP}├{'─' * (w_pkg + 2)}┼{'─' * (w_user + 2)}┼{'─' * (w_status + 2)}┤{RESET}")
    for item in selected_packages:
        pkg = item['pkg']
        s_pkg = pkg if len(pkg) <= w_pkg else pkg[:max(1, w_pkg - 3)] + "..."
        s_name = states[pkg]['display_name']
        if len(s_name) > w_user: s_name = s_name[:max(1, w_user - 3)] + "..."
        txt = states[pkg]['text']
        if len(txt) > w_status: txt = txt[:max(1, w_status - 3)] + "..."
        col = states[pkg]['color']
        row_str = f" {s_pkg:<{w_pkg}} │ {WHITE}{s_name:<{w_user}}{RESET} │ {col}{txt:<{w_status}}{RESET} "
        print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(row_str, inner_w)}{C_CYAN_DEEP}│{RESET}")
    print(f"{C_CYAN_DEEP}╰{'─' * (w_pkg + 2)}┴{'─' * (w_user + 2)}┴{'─' * (w_status + 2)}╯{RESET}")

    print(f" {C_MINT}●{RESET} {BOLD}Đang chạy Live Dashboard...{RESET} {C_GRAY_LIGHT}(Bấm Ctrl+C để về Menu){RESET}")

    # 3. Khung Nhật Ký Hệ Thống Gần Đây
    if system_logs:
        log_title = " NHẬT KÝ HỆ THỐNG GẦN ĐÂY "
        dashes_log = max(2, inner_w - visible_len(log_title) - 1)
        print(f"{C_CYAN_DEEP}╭─{log_title}{'─' * dashes_log}╮{RESET}")
        for log in system_logs[-8:]:
            print(f"{C_CYAN_DEEP}│{RESET}{fit_ansi(' ' + log, inner_w)}{C_CYAN_DEEP}│{RESET}")
        print(f"{C_CYAN_DEEP}╰{'─' * inner_w}╯{RESET}")

# =====================================================================
# CÀI ĐẶT & AUTO INJECT SCRIPT
# =====================================================================
def select_auto_inject_script_menu():
    global SELECTED_SCRIPT_KEY, CUSTOM_SCRIPT_URL, CUSTOM_SCRIPT_IS_CODE
    clear_screen()
    print_banner()
    term_w = get_terminal_width()
    inner_w = term_w - 2

    sc_title = " CHỌN SCRIPT AUTO INJECT "
    dashes_sc = max(2, inner_w - visible_len(sc_title) - 1)
    print(f"{CYAN_NEON}╭─{sc_title}{'─' * dashes_sc}╮{RESET}")
    print(f"{CYAN_NEON}│{RESET}{fit_ansi('   ' + GRAY_LIGHT + 'Script sẽ tự nạp vào thư mục autoexec của executor' + RESET, inner_w)}{CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}├{'─' * inner_w}┤{RESET}")
    
    for key, info in AUTO_INJECT_SCRIPTS.items():
        def_lbl = " / Mặc định" if key == "1" else ""
        is_cur = f" {GREEN_MINT}[✓ Đang chọn{def_lbl}]{RESET}" if SELECTED_SCRIPT_KEY == key else ""
        l1 = f"  {BOLD}{C}[{key}]{RESET} {GOLD_NEON}{info['name']:<18}{RESET}{is_cur}"
        l2 = f"      {GRAY_LIGHT}↳ {info['url'][:max(15, inner_w - 12)]}...{RESET}"
        print(f"{CYAN_NEON}│{RESET}{fit_ansi(l1, inner_w)}{CYAN_NEON}│{RESET}")
        print(f"{CYAN_NEON}│{RESET}{fit_ansi(l2, inner_w)}{CYAN_NEON}│{RESET}")
    
    # Hiển thị trạng thái custom
    custom_cur = ""
    if SELECTED_SCRIPT_KEY == "custom":
        custom_type = "[Code Lua]" if CUSTOM_SCRIPT_IS_CODE else "[URL]"
        custom_cur = f" {GREEN_MINT}[✓ Đang chọn {custom_type}]{RESET}"
    l_c1 = f"  {BOLD}{C}[4]{RESET} {PURPLE_NEON}Tự Nhập Script/URL Tùy Chỉnh (Custom){RESET}{custom_cur}"
    l_c2 = f"      {GRAY_LIGHT}↳ Nhập raw URL hoặc dán thẳng code Lua{RESET}"
    print(f"{CYAN_NEON}│{RESET}{fit_ansi(l_c1, inner_w)}{CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}│{RESET}{fit_ansi(l_c2, inner_w)}{CYAN_NEON}│{RESET}")
    disabled_cur = f" {R}[✓ Đang tắt]{RESET}" if SELECTED_SCRIPT_KEY == "0" else ""
    l_d1 = f"  {BOLD}{C}[0]{RESET} {R}Tắt Auto Inject Script Thêm{RESET}{disabled_cur}"
    print(f"{CYAN_NEON}│{RESET}{fit_ansi(l_d1, inner_w)}{CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}╰{'─' * inner_w}╯{RESET}")
    
    fix_tty()
    sel = safe_input(f"\n{BOLD}{CYAN_NEON}HuDy Script{RESET} {PINK_NEON}❯{RESET} Chọn [0-4] (Enter giữ nguyên): ").strip()
    if sel in AUTO_INJECT_SCRIPTS:
        SELECTED_SCRIPT_KEY = sel
        print(f"\n{G}[✓] Đã chọn Script: {AUTO_INJECT_SCRIPTS[sel]['name']}!{RESET}")
        save_settings()
        inject_user_script()
        time.sleep(1.5)
    elif sel == '4':
        fix_tty()
        print(f"{CYAN_NEON}╭──────────────── NHẬP CUSTOM SCRIPT ────────────────╮{RESET}")
        print(f"{CYAN_NEON}│{RESET} {Y}Bạn có thể nhập:{RESET}")
        print(f"{CYAN_NEON}│{RESET}   {G}• Raw URL{RESET}   : https://raw.githubusercontent.com/...")
        print(f"{CYAN_NEON}│{RESET}   {G}• Code Lua{RESET}  : Dán thẳng code (bắt đầu bằng -- hoặc local...)")
        print(f"{CYAN_NEON}│{RESET} {GRAY_LIGHT}Nhập xong, gõ dòng trống (Enter rỗng) để kết thúc.{RESET}")
        print(f"{CYAN_NEON}╰────────────────────────────────────────────────────╯{RESET}")
        
        lines = []
        print(f"{M}> Nhập nội dung (Enter 2 lần để kết thúc):{RESET}")
        empty_count = 0
        while True:
            try:
                line = input("  ")
            except (EOFError, KeyboardInterrupt):
                break
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
        
        content = "\n".join(lines).strip()
        if content:
            CUSTOM_SCRIPT_URL = content
            # Phát hiện là URL hay code Lua
            if content.startswith("http://") or content.startswith("https://"):
                CUSTOM_SCRIPT_IS_CODE = False
                print(f"\n{G}[✓] Đã lưu Custom Script URL!{RESET}")
            else:
                CUSTOM_SCRIPT_IS_CODE = True
                line_count = len(content.splitlines())
                print(f"\n{G}[✓] Đã lưu Code Lua trực tiếp ({line_count} dòng)!{RESET}")
            SELECTED_SCRIPT_KEY = "custom"
            save_settings()
            inject_user_script()
            time.sleep(1.5)
        else:
            print(f"\n{Y}[*] Đã hủy, giữ nguyên cài đặt cũ.{RESET}")
            time.sleep(1)
    elif sel == '0':
        SELECTED_SCRIPT_KEY = "0"
        print(f"\n{Y}[*] Đã tắt tính năng Auto Inject script thêm.{RESET}")
        save_settings()
        inject_user_script()
        time.sleep(1.5)

def settings_menu():
    global target_place_id, kill_all_time, CHECK_ACC_TIME_BLOCKED, AUTO_SOLVE_CAPTCHA_V2, JOIN_SERVER_MODE, JOIN_SERVER_LINK
    while True:
        clear_screen()
        print_banner()
        if SELECTED_SCRIPT_KEY in AUTO_INJECT_SCRIPTS:
            def_tag = " (Mặc định)" if SELECTED_SCRIPT_KEY == "1" else ""
            cur_script_name = f"{GREEN_MINT}{AUTO_INJECT_SCRIPTS[SELECTED_SCRIPT_KEY]['name']}{def_tag}{RESET}"
        elif SELECTED_SCRIPT_KEY == "custom":
            if CUSTOM_SCRIPT_IS_CODE:
                line_cnt = len(CUSTOM_SCRIPT_URL.splitlines()) if CUSTOM_SCRIPT_URL else 0
                cur_script_name = f"{BLUE_ICE}Custom Code ({line_cnt} dòng Lua){RESET}"
            else:
                cur_script_name = f"{BLUE_ICE}Custom URL ({CUSTOM_SCRIPT_URL[:20]}...){RESET}"
        else:
            cur_script_name = f"{R}Tắt (Không inject thêm script){RESET}"
            
        cur_pid = target_place_id if target_place_id else "Vào sảnh chính (0)"
        cur_restart = f"{kill_all_time} phút" if kill_all_time > 0 else "Tắt (0)"
        v2_status_lbl = f"{GREEN_MINT}Bật (Mặc định tự giải Nhấn & Giữ đa ngôn ngữ){RESET}" if AUTO_SOLVE_CAPTCHA_V2 == "Enable" else f"{R}Tắt (Không tự động giải){RESET}"
        if JOIN_SERVER_MODE == "Enable" and JOIN_SERVER_LINK:
            join_link_disp = JOIN_SERVER_LINK[:32] + "..." if len(JOIN_SERVER_LINK) > 35 else JOIN_SERVER_LINK
            join_status_lbl = f"{PURPLE_NEON}Bật (Link: {join_link_disp}){RESET}"
        else:
            join_status_lbl = f"{GRAY_LIGHT}Tắt (Vào server thường qua Place ID){RESET}"
        
        term_w = get_terminal_width()
        inner_w = term_w - 2

        set_title = " ⚙️ CÀI ĐẶT HỆ THỐNG "
        dashes_set = max(2, inner_w - visible_len(set_title) - 1)
        print(f"{CYAN_NEON}╭─{set_title}{'─' * dashes_set}╮{RESET}")
        
        line_s1 = f"  1. Place ID (Game ID):       {GOLD_NEON}{cur_pid}{RESET}"
        line_s2 = f"  2. Script Auto Inject:       {cur_script_name}"
        line_s3 = f"  3. Auto Restart:             {Y}{cur_restart}{RESET}"
        line_s4 = f"  4. Chu Kỳ Re-Check Acc Kẹt:  {G}{CHECK_ACC_TIME_BLOCKED}s{RESET}"
        line_s5 = f"  5. Auto Solve Captcha V2:    {v2_status_lbl}"
        line_s6 = f"  6. Mode Join Server (VIP):   {join_status_lbl}"
        line_s7 = f"  7. Thư Mục Lưu Trữ:          {GOLD_NEON}{get_primary_download_dir()}{RESET}"
        for sl in [line_s1, line_s2, line_s3, line_s4, line_s5, line_s6, line_s7]:
            print(f"{CYAN_NEON}│{RESET}{fit_ansi(sl, inner_w)}{CYAN_NEON}│{RESET}")
        print(f"{CYAN_NEON}├{'─' * inner_w}┤{RESET}")
        
        opt_v2_tag = f"{GREEN_MINT}[BẬT]{RESET}" if AUTO_SOLVE_CAPTCHA_V2 == "Enable" else f"{R}[TẮT]{RESET}"
        opt_join_tag = f"{PURPLE_NEON}[BẬT]{RESET}" if JOIN_SERVER_MODE == "Enable" else f"{GRAY_LIGHT}[TẮT]{RESET}"
        
        m_opts = [
            f"  {BOLD}{C}[1]{RESET} Đổi Place ID (Game ID)",
            f"  {BOLD}{C}[2]{RESET} Chọn Script Auto Inject (Fin_Tail, Tear, King, Custom)",
            f"  {BOLD}{C}[3]{RESET} Cài Đặt Thời Gian Auto Restart (phút)",
            f"  {BOLD}{C}[4]{RESET} Cài Đặt Chu Kỳ Re-check Acc Dính Captcha",
            f"  {BOLD}{C}[5]{RESET} Bật / Tắt Auto Solve Captcha V2         {opt_v2_tag}",
            f"  {BOLD}{C}[6]{RESET} Cài Đặt Mode Join Server (VIP / Private)   {opt_join_tag}",
            f"  {BOLD}{C}[7]{RESET} Cấu Hình Nhanh Tất Cả (Wizard Setup)",
            f"  {BOLD}{R}[8]{RESET} ↩Quay Lại Menu Chính"
        ]
        for mo in m_opts:
            print(f"{CYAN_NEON}│{RESET}{fit_ansi(mo, inner_w)}{CYAN_NEON}│{RESET}")
        print(f"{CYAN_NEON}╰{'─' * inner_w}╯{RESET}")
        
        fix_tty()
        c = safe_input(f"\n{BOLD}{CYAN_NEON}HuDy Settings{RESET} {PINK_NEON}❯{RESET} ").strip()
        if c == '1':
            fix_tty()
            p_id_raw = safe_input(f"{M}Nhập Place ID [Mặc định 4520749081, nhập 0 để vào sảnh]: {RESET}").strip()
            if p_id_raw == "":
                target_place_id = "4520749081"
                print(f"{Y}[*] Place ID mặc định: {target_place_id}{RESET}")
            elif p_id_raw == "0":
                target_place_id = ""
                print(f"{Y}[*] Đã xóa Place ID, app mở vào sảnh chính.{RESET}")
            else:
                nums = re.findall(r'\d+', p_id_raw)
                if nums:
                    target_place_id = nums[0]
                    print(f"{G}[+] Đã lưu Place ID: {target_place_id}{RESET}")
                else:
                    print(f"{R}[!] ID không hợp lệ.{RESET}")
            save_settings()
            time.sleep(1.5)
        elif c == '2':
            select_auto_inject_script_menu()
        elif c == '3':
            fix_tty()
            k_time_raw = safe_input(f"{M}Nhập thời gian Auto Restart (phút, 0 để tắt): {RESET}").strip()
            if k_time_raw != "":
                nums = re.findall(r'\d+', k_time_raw)
                if nums:
                    kill_all_time = int(nums[0])
                    if kill_all_time > 0:
                        print(f"{G}[+] Auto Restart mỗi {kill_all_time} phút.{RESET}")
                    else:
                        print(f"{Y}[*] Đã tắt Auto Restart.{RESET}")
                    save_settings()
                else:
                    print(f"{R}[!] Số phút không hợp lệ.{RESET}")
            time.sleep(1.5)
        elif c == '4':
            fix_tty()
            k_acc_raw = safe_input(f"{M}Thời gian re-check khi Acc dính Captcha/Not-Approved (giây, Enter giữ {CHECK_ACC_TIME_BLOCKED}s): {RESET}").strip()
            if k_acc_raw != "":
                nums = re.findall(r'\d+', k_acc_raw)
                if nums and int(nums[0]) >= 10:
                    CHECK_ACC_TIME_BLOCKED = int(nums[0])
                    print(f"{G}[+] Đã lưu chu kỳ re-check Acc kẹt: {CHECK_ACC_TIME_BLOCKED}s{RESET}")
                    save_settings()
            time.sleep(1.5)
        elif c == '5':
            fix_tty()
            if AUTO_SOLVE_CAPTCHA_V2 == "Enable":
                AUTO_SOLVE_CAPTCHA_V2 = "Disable"
                print(f"\n{Y}[*] Đã TẮT tính năng Auto Solve Captcha V2.{RESET}")
            else:
                AUTO_SOLVE_CAPTCHA_V2 = "Enable"
                print(f"\n{G}[✓] Đã BẬT Auto Solve Captcha V2 (Tự động nhận diện và nhấn giữ đa ngôn ngữ)!{RESET}")
            save_settings()
            time.sleep(1.5)
        elif c == '6':
            fix_tty()
            svv_link_found, svv_file_found = load_svv_link_from_file()
            print(f"{CYAN_NEON}╭───────────────── CÀI ĐẶT MODE JOIN SERVER ─────────────────╮{RESET}")
            print(f"{CYAN_NEON}│{RESET} {Y}Hỗ trợ link / deeplink / mã link code và file svv.txt:{RESET}")
            print(f"{CYAN_NEON}│{RESET}   {G}• Link Private Server{RESET}: https://www.roblox.com/games/...?privateServerLinkCode=...")
            print(f"{CYAN_NEON}│{RESET}   {G}• Share Link{RESET}         : https://roblox.com/share?code=...&type=Server")
            print(f"{CYAN_NEON}│{RESET}   {G}• Deeplink{RESET}           : roblox://experiences/start?placeId=...&linkCode=...")
            print(f"{CYAN_NEON}│{RESET}   {G}• File svv trong Download{RESET}: {GOLD_NEON}{get_download_save_path('svv.txt')}{RESET}")
            print(f"{CYAN_NEON}╰─────────────────────────────────────────────────────────────╯{RESET}")
            cur_txt = JOIN_SERVER_LINK if JOIN_SERVER_LINK else "Chưa có"
            print(f"Trạng thái hiện tại: {PURPLE_NEON}{JOIN_SERVER_MODE}{RESET} | Link: {G}{cur_txt}{RESET}")
            
            if svv_link_found and svv_file_found:
                disp_f = svv_link_found[:35] + "..." if len(svv_link_found) > 38 else svv_link_found
                print(f"\n{GREEN_MINT}[✓] Đã tìm thấy file svv: {GOLD_NEON}{svv_file_found}{RESET}")
                print(f"    Link trong file: {C}{disp_f}{RESET}")
                print(f"  [{C}1{RESET}] {BOLD}{G}Sử dụng link từ file svv.txt{RESET} {DIM}(Nhấn Enter chọn ngay){RESET}")
                print(f"  [{C}2{RESET}] {W}Nhập / Dán Link mới bằng tay{RESET}")
                print(f"  [{C}0{RESET}] {R}Tắt Mode Join Server (Vào server thường){RESET}")
                fix_tty()
                sub_c = safe_input(f"\n{M}Chọn [1/2/0, mặc định 1]: {RESET}").strip()
                if sub_c in ['', '1']:
                    link_input = svv_link_found
                elif sub_c in ['0', 'off', 'tat', 'tắt']:
                    link_input = '0'
                else:
                    link_input = safe_input(f"{M}Nhập Link Server mới: {RESET}").strip()
            else:
                link_input = safe_input(f"\n{M}Nhập Link Server mới (Nhập '0' hoặc 'off' để TẮT, Enter giữ nguyên): {RESET}").strip()

            if link_input.lower() in ['0', 'off', 'tat', 'tắt']:
                JOIN_SERVER_MODE = "Disable"
                print(f"\n{Y}[*] Đã TẮT Mode Join Server (Chuyển sang join thường theo Place ID).{RESET}")
                save_settings()
            elif link_input:
                JOIN_SERVER_LINK = link_input
                JOIN_SERVER_MODE = "Enable"
                pid_extracted, _ = parse_server_link(link_input, target_place_id)
                if pid_extracted and pid_extracted != target_place_id:
                    target_place_id = pid_extracted
                    print(f"{G}[+] Đã tự động đồng bộ Place ID từ link: {target_place_id}{RESET}")
                saved_f = save_svv_link_to_file(link_input)
                if saved_f:
                    print(f"{G}[✓] Đã lưu link vào file: {GOLD_NEON}{saved_f}{RESET}")
                print(f"{G}[✓] Đã BẬT Mode Join Server và lưu cấu hình thành công!{RESET}")
                save_settings()
            else:
                if JOIN_SERVER_LINK:
                    JOIN_SERVER_MODE = "Enable" if JOIN_SERVER_MODE == "Disable" else JOIN_SERVER_MODE
                    print(f"{G}[✓] Giữ nguyên link cũ. Trạng thái: {JOIN_SERVER_MODE}{RESET}")
                    save_settings()
            time.sleep(1.8)
        elif c == '7':
            fix_tty()
            p_id_raw = safe_input(f"{M}1. Nhập Place ID (Enter giữ {target_place_id}): {RESET}").strip()
            if p_id_raw == "0":
                target_place_id = ""
            elif p_id_raw != "":
                nums = re.findall(r'\d+', p_id_raw)
                if nums: target_place_id = nums[0]
                
            select_auto_inject_script_menu()
            
            fix_tty()
            k_time_raw = safe_input(f"{M}3. Nhập thời gian Auto Restart (phút, Enter giữ {kill_all_time}m): {RESET}").strip()
            if k_time_raw != "":
                nums = re.findall(r'\d+', k_time_raw)
                if nums: kill_all_time = int(nums[0])
                
            fix_tty()
            k_acc_raw = safe_input(f"{M}4. Chu kỳ re-check Acc kẹt Captcha (giây, Enter giữ {CHECK_ACC_TIME_BLOCKED}s): {RESET}").strip()
            if k_acc_raw != "":
                nums = re.findall(r'\d+', k_acc_raw)
                if nums and int(nums[0]) >= 10: CHECK_ACC_TIME_BLOCKED = int(nums[0])
                
            fix_tty()
            v2_in = safe_input(f"{M}5. Bật Auto Solve Captcha V2? (Y/n, Enter giữ {AUTO_SOLVE_CAPTCHA_V2}): {RESET}").strip().lower()
            if v2_in in ['n', 'no', '0', 'tat']:
                AUTO_SOLVE_CAPTCHA_V2 = "Disable"
            elif v2_in in ['y', 'yes', '1', 'bat']:
                AUTO_SOLVE_CAPTCHA_V2 = "Enable"
                
            fix_tty()
            js_in = safe_input(f"{M}6. Link VIP Server (Enter để giữ {JOIN_SERVER_LINK or 'Trống/Tắt'}, gõ 'off' để tắt): {RESET}").strip()
            if js_in.lower() in ['off', '0', 'tat']:
                JOIN_SERVER_MODE = "Disable"
            elif js_in:
                JOIN_SERVER_LINK = js_in
                JOIN_SERVER_MODE = "Enable"
                pid_extracted, _ = parse_server_link(js_in, target_place_id)
                if pid_extracted: target_place_id = pid_extracted

            save_settings()
            print(f"\n{G}[✓] Đã lưu cấu hình cài đặt thành công!{RESET}")
            time.sleep(1.5)
        elif c == '8':
            break

def scan_packages():
    packages = []
    try:
        output = subprocess.check_output("pm list packages -3", shell=True, text=True, stderr=subprocess.DEVNULL)
    except:
        try:
            output = subprocess.check_output("su -c 'pm list packages -3'", shell=True, text=True, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        except:
            output = ""
    fix_tty()
    for line in output.splitlines():
        if "package:" in line:
            packages.append(line.replace("package:", "").strip())
    return list(set(packages))

def is_vip_package(pkg):
    """Kiểm tra package có đầu/tên VIP (ví dụ vip..., com.vip..., com.roblox.vip...)."""
    if not pkg:
        return False
    p = pkg.lower()
    if p.startswith("vip"):
        return True
    parts = p.split(".")
    if any(part.startswith("vip") for part in parts):
        return True
    if "vip" in p and "roblox" in p:
        return True
    return False

def auto_select_vip_packages():
    """Tự động chọn tất cả package có đầu VIP làm mặc định."""
    global selected_packages
    try:
        packages = scan_packages()
        vip_pkgs = [p for p in packages if is_vip_package(p)]
        if vip_pkgs:
            vip_pkgs = sorted(list(set(vip_pkgs)))
            selected_packages = [{"pkg": p, "name": ""} for p in vip_pkgs]
            return len(selected_packages)
    except:
        pass
    return 0

def select_package_menu():
    global selected_packages
    packages = scan_packages()
    if not packages:
        print(f"{R}[!] Không tìm thấy app nào trên thiết bị!{RESET}")
        time.sleep(2)
        return
    clear_screen()
    print_banner()
    print(f"{CYAN_NEON}╭────────────────── QUẢN LÝ PACKAGE ROBLOX ──────────────────╮{RESET}")
    print(f"{CYAN_NEON}│{RESET} {GRAY_LIGHT}Mặc định hệ thống tự động chọn tất cả package có đầu 'vip'   {RESET}{CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}├───────────────────────────────────────────────────────────────┤{RESET}")
    current_selected_pkgs = {item['pkg'] for item in selected_packages}
    for i, pkg in enumerate(packages, 1):
        mark = f" {GREEN_MINT}[✓ Đang chọn]{RESET}" if pkg in current_selected_pkgs else ""
        vip_tag = f" {GOLD_NEON}[VIP]{RESET}" if is_vip_package(pkg) else ""
        print(f"{CYAN_NEON}│{RESET}  {BOLD}{C}[{i}]{RESET} {pkg}{vip_tag}{mark}")
    
    print(f"{CYAN_NEON}├───────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{CYAN_NEON}│{RESET}  • Bấm {BOLD}[Enter]{RESET} : Giữ nguyên danh sách hiện tại ({len(selected_packages)} Package)       {CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}│{RESET}  • Gõ {BOLD}'vip'{RESET}   : Tự động quét lại toàn bộ package có đầu VIP       {CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}│{RESET}  • Nhập số    : Tùy chỉnh chọn theo số thứ tự (VD: 1 3 5)         {CYAN_NEON}│{RESET}")
    print(f"{CYAN_NEON}╰───────────────────────────────────────────────────────────────╯{RESET}")
    try:
        fix_tty()
        choice_str = safe_input(f"\n{BOLD}{CYAN_NEON}HuDy Package{RESET} {PINK_NEON}❯{RESET} ").strip()
        if not choice_str:
            print(f"\n{G}[✓] Giữ nguyên danh sách ({len(selected_packages)} package).{RESET}")
            time.sleep(1.2)
            return
        if choice_str.lower() == 'vip':
            cnt = auto_select_vip_packages()
            print(f"\n{G}[✓] Đã tự động chọn {cnt} package VIP!{RESET}")
            time.sleep(1.2)
            return
        choices = [int(x) for x in re.findall(r'\d+', choice_str)]
        if choices:
            new_sel = []
            for choice in sorted(set(choices)):
                if 1 <= choice <= len(packages):
                    pkg_name = packages[choice - 1]
                    fix_tty()
                    acc_name = safe_input(f"\n{C}[?] Tên In-game cho {Y}{pkg_name}{C} (bỏ trống để auto): {RESET}").strip()
                    new_sel.append({"pkg": pkg_name, "name": acc_name})
            if new_sel:
                selected_packages = new_sel
                print(f"\n{G}[+] Đã lưu {len(selected_packages)} package tùy chỉnh.{RESET}")
                time.sleep(1.2)
    except:
        pass

# =====================================================================
# INJECT SCRIPT UNIVERSAL (REJOIN & HEARTBEAT)
# =====================================================================
def inject_universal_lua():
    lua_code = """
loadstring(game:HttpGet("https://raw.githubusercontent.com/huuduydz/AutoSam_TpHome/refs/heads/main/bypassloading.lua"))()
local Players = game:GetService("Players")
local GuiService = game:GetService("GuiService")
local DisconnectErrors = Enum.ConnectionError.DisconnectErrors.Value
local PlaceLaunchOtherError = Enum.ConnectionError.PlacelaunchOtherError.Value
repeat task.wait() until game:IsLoaded() and Players.LocalPlayer
local LocalPlayer = Players.LocalPlayer
local fileName = "rj_" .. LocalPlayer.Name .. "_checkhudyhub.json"
local sWF = true
task.spawn(function()
    while sWF do
        task.wait(3)
        pcall(function()
            local errorCode = GuiService:GetErrorCode().Value
            if errorCode == 1 or errorCode == 773 or errorCode == 772 or errorCode == 769 or (errorCode >= DisconnectErrors and errorCode < PlaceLaunchOtherError) then
                sWF = false
            end
        end)
        if sWF then
            local pidOk, pid = pcall(function() return game.PlaceId end)
            local humOk, hum = pcall(function() return LocalPlayer.Character.Humanoid end)
            if not (pidOk and pid == 0 and not (humOk and hum)) then
                pcall(function()
                    -- Ghi Unix timestamp số nguyên (không dùng string date) để Python đọc chính xác
                    writefile(fileName, string.format('{"playerName":"%s","timestamp":%d}', LocalPlayer.Name, math.floor(workspace:GetServerTimeNow())))
                end)
            end
        end
    end
end)"""
    safe_root("su -c 'find /sdcard/ -maxdepth 4 -type f -name \"*checkhudyhub.lua\" -delete 2>/dev/null'")
    temp_lua = "/sdcard/Download/universal_checkhudyhub.lua"
    try:
        with open(temp_lua, "w", encoding="utf-8") as f:
            f.write(lua_code)
    except Exception:
        safe_root(f"su -c 'cat << \\'EOF\\' > {temp_lua}\n{lua_code}\nEOF'")
    root_cmd = f"""su -c "for dir in \\$(find /sdcard/ -maxdepth 3 -type d -iname '*autoexec*' 2>/dev/null); do cp {temp_lua} \\"\\$dir/universal_checkhudyhub.lua\\" && chmod 777 \\"\\$dir/universal_checkhudyhub.lua\\"; done; rm {temp_lua}" """
    safe_root(root_cmd)

# =====================================================================
# INJECT USER SCRIPT (FILE RIÊNG: user_autoinject.lua)
# =====================================================================
def inject_user_script():
    global SELECTED_SCRIPT_KEY, CUSTOM_SCRIPT_URL, CUSTOM_SCRIPT_IS_CODE, AUTO_INJECT_SCRIPTS

    script_name = ""
    script_content_raw = ""
    is_direct_code = False

    if SELECTED_SCRIPT_KEY in AUTO_INJECT_SCRIPTS:
        script_name = AUTO_INJECT_SCRIPTS[SELECTED_SCRIPT_KEY]["name"]
        script_content_raw = AUTO_INJECT_SCRIPTS[SELECTED_SCRIPT_KEY]["url"].strip()
        is_direct_code = False
    elif SELECTED_SCRIPT_KEY == "custom" and CUSTOM_SCRIPT_URL:
        script_name = "Custom Script"
        script_content_raw = CUSTOM_SCRIPT_URL.strip()
        is_direct_code = CUSTOM_SCRIPT_IS_CODE

    if not script_content_raw or SELECTED_SCRIPT_KEY == "0":
        print(f"{Y}[*] Không inject user script (Tắt hoặc chưa có nội dung).{RESET}")
        return

    print(f"{G}[+] Đang inject: {C}{script_name}{RESET}...")

    if is_direct_code:
        indented = "\n".join("        " + ln for ln in script_content_raw.splitlines())
        lua_code = f"""-- [HuDy Custom Code: {script_name}]
task.spawn(function()
    repeat task.wait() until game:IsLoaded() and game:GetService("Players").LocalPlayer
    task.wait(2)
    pcall(function()
{indented}
    end)
end)"""
    else:
        lua_code = f"""-- [HuDy Auto Inject: {script_name}]
task.spawn(function()
    repeat task.wait() until game:IsLoaded() and game:GetService("Players").LocalPlayer
    task.wait(2)
    pcall(function()
        loadstring(game:HttpGet("{script_content_raw}", true))()
    end)
end)"""

    safe_root("su -c 'find /sdcard/ -maxdepth 5 -type f -name \"*user_autoinject.lua\" -delete 2>/dev/null'")
    temp_lua = "/sdcard/Download/user_autoinject.lua"
    try:
        with open(temp_lua, "w", encoding="utf-8") as f:
            f.write(lua_code)
    except Exception:
        pass

    root_cmd = f"""su -c "for dir in \\$(find /sdcard/ -maxdepth 3 -type d -iname '*autoexec*' 2>/dev/null); do cp {temp_lua} \\"\\$dir/user_autoinject.lua\\" && chmod 777 \\"\\$dir/user_autoinject.lua\\"; done; rm {temp_lua}" """
    safe_root(root_cmd)
    inject_type = "Code trực tiếp" if is_direct_code else "URL"
    print(f"{G}[✓] Đã inject '{script_name}' ({inject_type}) -> user_autoinject.lua!{RESET}")

# =====================================================================
# HEARTBEAT & ACCOUNT DISCOVERY (ĐÃ SỬA TÌM ĐÚNG FILE)
# =====================================================================
def extract_username_from_filename(filename):
    """Lấy tên ingame từ tên file kiểu rj_TEN_checkhudyhub.json hoặc r_j_TEN_checkhudyhub.json..."""
    base = os.path.basename(filename)
    # Xóa đuôi _checkhudyhub.json
    if base.endswith('_checkhudyhub.json'):
        base = base[:-len('_checkhudyhub.json')]
    else:
        # Không đúng định dạng, thử tách phần trước đuôi .json
        base = os.path.splitext(base)[0]
    # Tách bởi dấu gạch dưới, lấy phần tử cuối cùng (sau khi đã bỏ hậu tố) làm tên
    # Với rj_TEN -> parts = ['rj', 'TEN'] -> lấy parts[-1]
    # Với r_j_TEN -> parts = ['r', 'j', 'TEN'] -> lấy parts[-1]
    parts = base.split('_')
    if len(parts) >= 2:
        return parts[-1]  # Phần cuối là tên
    return base  # fallback

def get_all_heartbeat_files_fast(pkg=None):
    """Tìm file heartbeat bằng su find - giống hudy_2.py đã hoạt động."""
    search_dirs = [
        "/sdcard/Android/media",
        "/sdcard/Android/data",
        "/sdcard/Delta",
        "/storage/emulated/0/Delta",
        "/sdcard/DeltaQT",
        "/storage/emulated/0/DeltaQT",
        "/sdcard/ModWorkspace",
    ]
    if pkg:
        search_dirs = [
            f"/sdcard/Android/media/{pkg}",
            f"/sdcard/Android/data/{pkg}",
            "/sdcard/Delta",
            "/storage/emulated/0/Delta",
            "/sdcard/DeltaQT",
            "/storage/emulated/0/DeltaQT",
        ]
    results = []
    for d in search_dirs:
        try:
            cmd = f"su -c 'find {d} -iname \"*_checkhudyhub.json\" -type f 2>/dev/null'"
            out = subprocess.check_output(cmd, shell=True, text=True, timeout=5,
                                           stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).strip()
            for line in out.splitlines():
                line = line.strip()
                if line and '_checkhudyhub.json' in line:
                    results.append(line)
        except:
            pass
    return list(set(results))

def get_heartbeat_files_for_pkg(pkg):
    return get_all_heartbeat_files_fast(pkg)


def _get_file_mtime_root(filepath):
    try:
        import subprocess
        cmd = f"su -c 'stat -c %Y \"{filepath}\"' 2>/dev/null"
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=2).strip()
        if out.isdigit():
            return float(out)
    except:
        pass
    try:
        import subprocess
        # Backup dùng su -mm (Mount Master) để xuyên Namespace nếu Magisk hỗ trợ
        cmd = f"su -mm -c 'stat -c %Y \"{filepath}\"' 2>/dev/null"
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=2).strip()
        if out.isdigit():
            return float(out)
    except:
        pass
    return 0

def _get_file_mtime(filepath):
    """Lấy mtime - thử getmtime trước, fallback su stat cho file cần root."""
    try:
        return os.path.getmtime(filepath)
    except:
        pass
    try:
        out = subprocess.check_output(
            f"su -c 'stat -c %Y \"{filepath}\" 2>/dev/null'",
            shell=True, text=True, timeout=3,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).strip()
        if out.isdigit():
            return float(out)
    except:
        pass
    return -1

import json as _json_mod

def _read_json_timestamp(filepath):
    """Đọc nội dung JSON, trả về Unix timestamp. -1 nếu lỗi.
    Hỗ trợ format mới {timestamp:N} và format cũ {time:string}."""
    raw = None
    # Ưu tiên đọc trực tiếp (Delta ở /storage/emulated/0/ không cần root)
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            raw = fh.read().strip()
    except:
        pass
    # Fallback: đọc qua su -c cat (file trong /sdcard/Android/ cần root)
    if not raw:
        try:
            raw = subprocess.check_output(
                f"su -c 'cat \"{filepath}\" 2>/dev/null'",
                shell=True, text=True, timeout=3,
                stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).strip()
        except:
            pass
    if not raw:
        return -1
    try:
        data = _json_mod.loads(raw)
        if 'timestamp' in data:
            return float(data['timestamp'])
        if 'time' in data:
            # Format cũ: "2024-05-01T12:00:00Z" → parse thành epoch
            from datetime import datetime, timezone
            dt = datetime.strptime(data['time'], '%Y-%m-%dT%H:%M:%SZ')
            return dt.replace(tzinfo=timezone.utc).timestamp()
    except:
        pass
    return -1

def get_heartbeat(acc_name, pkg):
    """Trả về mtime của file heartbeat - giống hudy_2.py đã hoạt động."""
    global json_path_cache, heartbeat_last_check, file_to_pkg_binding
    now = time.time()
    if pkg not in json_path_cache:
        json_path_cache[pkg] = {}
        heartbeat_last_check[pkg] = {}
    cache = json_path_cache[pkg]
    last_check = heartbeat_last_check[pkg]

    if acc_name in cache:
        cached_path, cached_mtime = cache[acc_name]
        if os.path.exists(cached_path):
            if now - last_check.get(acc_name, 0) < 15:
                return cached_mtime
            mtime = _get_file_mtime(cached_path)
            if mtime > 0:
                cache[acc_name] = (cached_path, mtime)
                last_check[acc_name] = now
                with shared_lock:
                    file_to_pkg_binding[cached_path] = pkg
                return mtime
        del cache[acc_name]

    all_files = get_all_heartbeat_files_fast(pkg)
    best_mtime = 0
    best_file = None
    for f in all_files:
        name_in_file = extract_username_from_filename(f)
        if name_in_file == acc_name:
            mtime = _get_file_mtime(f)
            if mtime > best_mtime:
                best_mtime = mtime
                best_file = f
    if best_file and best_mtime > 0:
        cache[acc_name] = (best_file, best_mtime)
        last_check[acc_name] = now
        with shared_lock:
            file_to_pkg_binding[best_file] = pkg
        return best_mtime
    return -1

def discover_unbound_account(pkg, states):
    """Tìm acc chưa được claim. Dùng mtime giống hudy_2.py (đã hoạt động)."""
    global CLAIMED_NAMES, file_to_pkg_binding

    active_names_other_pkgs = {
        s['bound_name'] for p, s in states.items()
        if p != pkg and s.get('bound_name')
    }
    with shared_lock:
        blocked_files = {fp for fp, fp_pkg in file_to_pkg_binding.items() if fp_pkg != pkg}

    all_files = get_all_heartbeat_files_fast(pkg)
    candidates = []
    now = time.time()
    for f in all_files:
        if f in blocked_files:
            continue
        mtime = _get_file_mtime(f)
        if mtime > 0 and now - mtime < 300:
            name = extract_username_from_filename(f)
            if name:
                candidates.append((name, mtime, f))
    candidates.sort(key=lambda x: x[1], reverse=True)

    with shared_lock:
        for name, mtime, fpath in candidates:
            if name not in CLAIMED_NAMES and name not in active_names_other_pkgs:
                CLAIMED_NAMES.add(name)
                file_to_pkg_binding[fpath] = pkg
                return name
    return None

# =====================================================================
# BOOT & RESTART
# =====================================================================
_boot_threads = {}   # {pkg: Thread} — track boot threads

def _pgrep_pkg(pkg):
    """
    Lấy danh sách PID của package một cách nhanh chóng, chính xác, chống va chạm clone:
    1. Thử qua pidof (nhanh nhất, ~5ms)
    2. Thử qua ps -A -o PID,NAME / ps -ef (chính xác từng process name, không va chạm clone)
    3. Thử qua pgrep -x / pgrep -f
    """
    pids = set()

    # 1. Thử pidof (nhanh và chuẩn Android)
    try:
        out = subprocess.check_output(
            f"su -c 'pidof {pkg} 2>/dev/null'",
            shell=True, text=True, timeout=2,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for token in out.strip().split():
            if token.isdigit():
                pids.add(token)
    except:
        pass

    if pids:
        return list(pids)

    # 2. Thử ps -A / ps -ef (chống va chạm clone bằng so khớp exact name)
    try:
        out = subprocess.check_output(
            "su -c 'ps -A -o PID,NAME 2>/dev/null || ps -ef 2>/dev/null || ps 2>/dev/null'",
            shell=True, text=True, timeout=3,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                cand_pid = None
                cand_name = None
                if parts[0].isdigit():
                    cand_pid = parts[0]
                    cand_name = parts[-1]
                elif len(parts) >= 8 and parts[1].isdigit():
                    cand_pid = parts[1]
                    cand_name = parts[-1]
                
                if cand_pid and cand_name:
                    if cand_name == pkg or cand_name.startswith(pkg + ':'):
                        pids.add(cand_pid)
    except:
        pass

    if pids:
        return list(pids)

    # 3. Thử pgrep
    try:
        out = subprocess.check_output(
            f"su -c 'pgrep -x {pkg} 2>/dev/null || pgrep -f {pkg} 2>/dev/null'",
            shell=True, text=True, timeout=2,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for token in out.strip().split():
            if token.isdigit():
                pids.add(token)
    except:
        pass

    return list(pids)

def is_app_running(pkg):
    """
    Kiểm tra app có đang chạy hay không — hỗ trợ cả Toàn màn hình lẫn Cửa sổ nổi (Floating / Freeform / Multi-window / Split-screen).
    Đa tầng:
    1. Process PID qua _pgrep_pkg (pidof, ps -A, pgrep)
    2. Dumpsys Activity Processes (ProcessRecord của Android ActivityManager)
    3. Dumpsys Window (Nhận diện cửa sổ nổi / freeform window đang active trên màn hình)
    4. Dumpsys Activity Activities (Activity stack trong chế độ đa nhiệm / pop-up)
    5. Heartbeat file mới cập nhật (< 90s)
    """
    # 1. Process PID (nhanh nhất)
    if bool(_pgrep_pkg(pkg)):
        return True

    # 2. ActivityManager Process Record
    try:
        p_out = subprocess.check_output(
            f"su -c 'dumpsys activity p {pkg} 2>/dev/null'",
            shell=True, text=True, timeout=2,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if "ProcessRecord" in p_out and (" " + pkg in p_out or ":" + pkg in p_out or "/" + pkg in p_out):
            return True
    except:
        pass

    # 3. WindowManager: Nhận diện Cửa Sổ Nổi (Floating Window / Freeform / Pop-up view)
    try:
        w_out = subprocess.check_output(
            "su -c 'dumpsys window windows 2>/dev/null || dumpsys window displays 2>/dev/null'",
            shell=True, text=True, timeout=3,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        pattern = re.compile(r'\b' + re.escape(pkg) + r'\b')
        if pattern.search(w_out):
            return True
    except:
        pass

    # 4. Activity stack đa nhiệm
    try:
        act_out = subprocess.check_output(
            "su -c 'dumpsys activity activities 2>/dev/null'",
            shell=True, text=True, timeout=3,
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        pattern = re.compile(r'\b' + re.escape(pkg) + r'\b')
        if pattern.search(act_out):
            return True
    except:
        pass

    # 5. Heartbeat file còn mới (< 90s)
    try:
        all_hb = get_all_heartbeat_files_fast(pkg)
        now = time.time()
        for f in all_hb:
            mt = _get_file_mtime(f)
            if mt > 0 and (now - mt < 90):
                return True
    except:
        pass

    return False

def _is_pkg_active(pkg):
    """Kiểm tra pkg đang hoạt động (đồng bộ hoàn toàn với is_app_running)."""
    return is_app_running(pkg)

def is_pkg_in_foreground(pkg):
    """Kiểm tra package có đang ở Foreground (cửa sổ nổi bật nhất trên màn hình) hay không."""
    if not pkg:
        return False
    try:
        cmd = "su -c 'dumpsys window 2>/dev/null | grep -E \"mCurrentFocus|mFocusedApp\"'"
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=2, stderr=subprocess.DEVNULL)
        if pkg in out:
            return True
        cmd2 = "su -c 'dumpsys activity activities 2>/dev/null | grep -E \"mResumedActivity|topResumedActivity\"'"
        out2 = subprocess.check_output(cmd2, shell=True, text=True, timeout=2, stderr=subprocess.DEVNULL)
        if pkg in out2:
            return True
    except:
        pass
    return False

def _kill_pkg(pkg):
    """Kill process của pkg — kill -9 PID trước, fallback am force-stop."""
    pids = _pgrep_pkg(pkg)
    if pids:
        pid_str = ' '.join(pids)
        safe_root(f"su -c 'kill -9 {pid_str} 2>/dev/null'")
    
    # Aggressive kill via ps
    try:
        ps_cmd = f"su -c 'ps -ef 2>/dev/null || ps 2>/dev/null'"
        out = subprocess.check_output(ps_cmd, shell=True, text=True, timeout=5, stderr=subprocess.DEVNULL)
        pids_to_kill = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 8:
                pid = parts[1]
                name = parts[-1]
                if name == pkg or name.startswith(pkg + ':'):
                    if pid.isdigit() and pid not in pids:
                        pids_to_kill.append(pid)
        if pids_to_kill:
            pid_str2 = ' '.join(pids_to_kill)
            safe_root(f"su -c 'kill -9 {pid_str2} 2>/dev/null'")
    except:
        pass

    safe_root(f"su -c 'am force-stop {pkg}'")
    time.sleep(1)

def boot_pkg_with_verify(pkg, max_retries=3):
    """Boot pkg với tối đa 3 lần thử mượt mà, chống xung đột process và chống văng app."""
    for attempt in range(1, max_retries + 1):
        # A) Dọn process cũ hoàn toàn
        safe_root(f"su -c 'am force-stop {pkg}'")
        time.sleep(1.5)

        # B) Launch đúng package bằng cờ FLAG_ACTIVITY_NEW_TASK (0x10000000)
        launch_uri = build_roblox_launch_uri(pkg)
        if launch_uri:
            safe_root(
                f"su -c 'am start -p {pkg} -f 0x10000000 -a android.intent.action.VIEW "
                f"-d \"{launch_uri}\" 2>/dev/null'"
            )
        else:
            safe_root(f"su -c 'monkey -p {pkg} -c android.intent.category.LAUNCHER 1 2>/dev/null'")

        # C) Poll nhẹ nhàng: 8 lần * 2.5s = 20s
        for _ in range(8):
            time.sleep(2.5)
            if _is_pkg_active(pkg):
                return True

        if attempt < max_retries:
            time.sleep(2)

    # Last resort
    safe_root(f"su -c 'am force-stop {pkg}'")
    time.sleep(1.5)
    safe_root(f"su -c 'monkey -p {pkg} -c android.intent.category.LAUNCHER 1 2>/dev/null'")
    return False

def launch_roblox_to_game(pkg):
    """Bắn package vào game hoặc VIP Server mượt mà, chống lặp lệnh và chống văng app."""
    global target_place_id
    uri = build_roblox_launch_uri(pkg)
    if not uri:
        pid = target_place_id if (target_place_id and str(target_place_id).strip().isdigit()) else "4520749081"
        uri = f"roblox://experiences/start?placeId={pid}"

    # Dùng cờ chuẩn FLAG_ACTIVITY_NEW_TASK (0x10000000) thay vì MULTIPLE_TASK để tránh tạo đa task gây crash
    cmd = f"su -c 'am start -p {pkg} -f 0x10000000 -a android.intent.action.VIEW -d \"{uri}\" 2>/dev/null'"
    safe_root(cmd)

    # Chờ app khởi tạo (poll tối đa 10s, kiểm tra mỗi 2s - không spam monkey đè lên)
    for _ in range(5):
        time.sleep(2)
        if is_app_running(pkg):
            return True

    # Fallback chỉ khi sau 10s app hoàn toàn chưa chạy
    safe_root(f"su -c 'monkey -p {pkg} -c android.intent.category.LAUNCHER 1 2>/dev/null'")
    time.sleep(3)
    safe_root(cmd)
    return is_app_running(pkg)

def _boot_worker(pkg, states):
    """Background thread: boot pkg không block monitor thread."""
    boot_acquired = global_restart_semaphore.acquire(timeout=60)
    try:
        boot_pkg_with_verify(pkg)
    except Exception:
        pass
    finally:
        if boot_acquired:
            global_restart_semaphore.release()
        _boot_threads.pop(pkg, None)

def force_restart_app(pkg, states, current_time, reason, color):
    global last_restart_time, last_any_restart_time, file_to_pkg_binding
    if pkg in last_restart_time and current_time - last_restart_time[pkg] < 180:
        return

    states[pkg]['text'] = reason
    states[pkg]['color'] = color
    last_restart_time[pkg] = current_time
    last_any_restart_time = current_time

    # ── B1: Kill ngay (ngược lại với semaphore → không block pkg khác) ───
    _kill_pkg(pkg)

    # ── Dọn file heartbeat + cache RAM ──────────────────────────
    bound_name = states[pkg].get('bound_name')
    if bound_name:
        safe_root(
            f"su -c 'rm -f "
            f"/sdcard/Android/media/{pkg}/workspace/*_{bound_name}_checkhudyhub.json "
            f"/sdcard/Android/data/{pkg}/workspace/*_{bound_name}_checkhudyhub.json "
            f"/sdcard/Android/media/{pkg}/*_{bound_name}_checkhudyhub.json "
            f"/sdcard/Android/data/{pkg}/*_{bound_name}_checkhudyhub.json "
            f"/sdcard/Delta/*_{bound_name}_checkhudyhub.json "
            f"2>/dev/null'"
        )
        json_path_cache.pop(pkg, None)
        heartbeat_last_check.pop(pkg, None)
        with shared_lock:
            CLAIMED_NAMES.discard(bound_name)
            stale_fps = [fp for fp, fp_pkg in file_to_pkg_binding.items() if fp_pkg == pkg]
            for fp in stale_fps:
                del file_to_pkg_binding[fp]

    # ── Reset state ──────────────────────────────────────────
    states[pkg]['rejoin_time'] = current_time
    states[pkg]['warmup_until'] = current_time + 60
    states[pkg]['bound_name'] = None
    states[pkg]['display_name'] = 'Chờ Auto-Bind...'
    states[pkg]['heartbeat_misses'] = 0

    # ── B2: Boot trong background thread — monitor thread không bị block ────
    existing = _boot_threads.get(pkg)
    if existing and existing.is_alive():
        return  # Đang boot rồi, không spawn thêm
    t = threading.Thread(
        target=_boot_worker, args=(pkg, states),
        daemon=True, name=f"boot_{pkg[-8:]}"
    )
    _boot_threads[pkg] = t
    t.start()

# =====================================================================
# COOKIE INJECTION & AUTO LOGIN VIA AUTH TICKET DEEPLINK
# =====================================================================

def get_pkg_uid_gid(pkg):
    """Lấy chính xác Linux UID và GID của app để phân quyền tránh bị Android/Chromium reset database."""
    code, ownership, _ = _run_root_capture(f"stat -c '%u %g' '/data/data/{pkg}'", timeout=3)
    if code == 0:
        parts = ownership.split()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            return parts[0], parts[1]
    return "10000", "10000"

def _normalize_roblosecurity_cookie(cookie):
    """Trả về riêng giá trị .ROBLOSECURITY, không kèm tên/header Cookie hay ngoặc kép."""
    if not cookie:
        return ""
    cookie = str(cookie).strip().replace('\r', '').replace('\n', '').strip('\'"')
    match = re.search(r'(?:^|[;\s])\.ROBLOSECURITY\s*=\s*([^;]+)', cookie, re.IGNORECASE)
    if match:
        cookie = match.group(1).strip().strip('\'"')
    return cookie

def _run_root_capture(command, timeout=15):
    """Chạy một lệnh root không qua shell lồng nhau và giữ lại mã lỗi thật."""
    try:
        result = subprocess.run(
            ["su", "-c", command],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout sau {timeout}s"
    except Exception as exc:
        return -1, "", str(exc)

def get_auth_ticket(cookie):
    """
    Tạo Auth Ticket từ Roblox API server thông qua Cookie .ROBLOSECURITY.
    Auth Ticket giúp ứng dụng Android tự động kích hoạt Đăng Nhập tức thì.
    """
    cookie = _normalize_roblosecurity_cookie(cookie)
    if not cookie:
        return None, "Cookie rỗng"

    base_headers = {
        "Cookie": f".ROBLOSECURITY={cookie}",
        "Content-Type": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    # B1: Lấy X-CSRF-TOKEN từ auth.roblox.com (hoặc các endpoint auth chính)
    csrf_token = None
    csrf_candidates = [
        ("https://auth.roblox.com/v1/authentication-ticket/", base_headers),
        ("https://auth.roblox.com/v2/login", base_headers),
        ("https://auth.roblox.com/v1/logout", base_headers),
        ("https://apis.roblox.com/auth-token-service/v1/login/enterCode", {"Content-Type": "application/json", "User-Agent": base_headers["User-Agent"]})
    ]
    for url, hdrs in csrf_candidates:
        try:
            req_c = urllib.request.Request(url, data=b"{}", headers=hdrs, method="POST")
            with urllib.request.urlopen(req_c, timeout=6) as resp_c:
                csrf_token = resp_c.headers.get("x-csrf-token") or resp_c.headers.get("X-CSRF-TOKEN")
        except urllib.error.HTTPError as e:
            csrf_token = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
        except Exception:
            pass
        if csrf_token:
            break

    if not csrf_token:
        return None, "Không lấy được X-CSRF-Token từ server Roblox"

    # B2: Gửi request sinh Auth Ticket (thử qua 3 bộ headers: Browser chuẩn, Client native, Negotiation flag)
    req_configs = [
        # Kiểu 1: Trình duyệt chuẩn (Chrome / Android WebView)
        dict(base_headers, **{"x-csrf-token": csrf_token}),
        # Kiểu 2: Roblox native client
        {
            "Cookie": f".ROBLOSECURITY={cookie}",
            "Content-Type": "application/json",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com",
            "User-Agent": "Roblox/WinInet",
            "x-csrf-token": csrf_token
        },
        # Kiểu 3: Có kèm negotiation flag
        {
            "Cookie": f".ROBLOSECURITY={cookie}",
            "Content-Type": "application/json",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com",
            "User-Agent": "Roblox/WinInet",
            "RBXAuthenticationNegotiation": "1",
            "x-csrf-token": csrf_token
        }
    ]

    last_err = "Không tạo được Auth Ticket"
    for hdrs in req_configs:
        try:
            req2 = urllib.request.Request("https://auth.roblox.com/v1/authentication-ticket/", data=b"{}", headers=hdrs, method="POST")
            with urllib.request.urlopen(req2, timeout=8) as resp2:
                ticket = resp2.headers.get("rbx-authentication-ticket") or resp2.headers.get("RBX-Authentication-Ticket")
                if ticket:
                    return ticket, "Thành công"
                try:
                    data = json.loads(resp2.read().decode('utf-8'))
                    t = data.get("authTicket")
                    if t: return t, "Thành công"
                except:
                    pass
        except urllib.error.HTTPError as e:
            ticket = e.headers.get("rbx-authentication-ticket") or e.headers.get("RBX-Authentication-Ticket")
            if ticket:
                return ticket, "Thành công"
            last_err = f"HTTP {e.code}"
        except Exception as e:
            last_err = str(e)

    return None, last_err

def inject_cookie_webview(pkg, cookie):
    """
    Tiêm Cookie vào tất cả các file SQLite Cookies của WebView theo chuẩn Chromium:
    - top_frame_site_key = '' cho unpartitioned first-party cookies (chuẩn Chromium CHIPS).
    - top_frame_site_key = 'https://roblox.com' bản copy partitioned để tương thích mọi phiên bản.
    - samesite = 0 (UNSPECIFIED) tránh lỗi enum âm bị Chromium drop row.
    - Phủ rộng các domain (.roblox.com, roblox.com, www.roblox.com, api.roblox.com, auth.roblox.com, web.roblox.com).
    - Bổ sung cả tên '.ROBLOSECURITY' và 'ROBLOSECURITY'.
    - Đồng bộ sang cả app_webview/Default/Cookies và app_webview/Default/Network/Cookies.
    - Xóa sạch file WAL/SHM/journal tránh xung đột ghi đè.
    - Phân quyền chính xác UID:GID, chmod 660 và chcon/restorecon SELinux.
    """
    cookie = _normalize_roblosecurity_cookie(cookie)
    if not cookie:
        return False

    uid, gid = get_pkg_uid_gid(pkg)

    # Đảm bảo các thư mục webview cơ bản tồn tại
    for d in [
        f"/data/data/{pkg}/app_webview/Default/Network",
        f"/data/data/{pkg}/app_webview/Default",
        f"/data/data/{pkg}/app_webview",
        f"/data/data/{pkg}/databases"
    ]:
        _run_root_capture(f"mkdir -p '{d}' && chown {uid}:{gid} '{d}' && chmod 771 '{d}' 2>/dev/null", timeout=3)

    # Tìm tất cả cơ sở dữ liệu cookies trong package
    dbs = []
    default_paths = [
        f"/data/data/{pkg}/app_webview/Default/Network/Cookies",
        f"/data/data/{pkg}/app_webview/Default/Cookies",
        f"/data/data/{pkg}/app_webview/Cookies",
        f"/data/data/{pkg}/databases/webviewCookiesChromium.db",
        f"/data/data/{pkg}/databases/webview.db",
        f"/data/data/{pkg}/databases/Cookies",
        f"/data/data/{pkg}/app_chrome/Default/Network/Cookies",
        f"/data/data/{pkg}/app_chrome/Default/Cookies",
        f"/data/data/{pkg}/app_chrome/Cookies"
    ]
    for p in default_paths:
        if p not in dbs:
            try:
                _, chk, _ = _run_root_capture(f"test -f '{p}' && echo exists", timeout=2)
                if "exists" in chk:
                    dbs.append(p)
            except:
                pass

    try:
        code, out, _ = _run_root_capture(
            f"find '/data/data/{pkg}/' -type f \( -name 'Cookies' -o -name '*cookie*' \) 2>/dev/null",
            timeout=5
        )
        if code == 0 and out:
            for line in out.splitlines():
                p = line.strip()
                if p and p not in dbs and not p.endswith(('-journal', '-wal', '-shm')):
                    dbs.append(p)
    except:
        pass

    tmp_dir = os.path.join(tempfile.gettempdir(), 'hudy_cookie_tmp')
    try: os.makedirs(tmp_dir, exist_ok=True)
    except: tmp_dir = tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)

    # Nếu hoàn toàn chưa có file DB nào (app mới cài chưa mở lần nào), tự khởi tạo DB SQLite chuẩn
    if not dbs:
        fallback_db = f"/data/data/{pkg}/app_webview/Default/Network/Cookies"
        local_init = os.path.join(tmp_dir, "init_cookies.db")
        if os.path.exists(local_init):
            try: os.remove(local_init)
            except: pass
        try:
            init_conn = sqlite3.connect(local_init)
            init_c = init_conn.cursor()
            init_c.execute('''
                CREATE TABLE IF NOT EXISTS cookies(
                    creation_utc INTEGER NOT NULL,
                    host_key TEXT NOT NULL,
                    top_frame_site_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    encrypted_value BLOB NOT NULL,
                    path TEXT NOT NULL,
                    expires_utc INTEGER NOT NULL,
                    is_secure INTEGER NOT NULL,
                    is_httponly INTEGER NOT NULL,
                    last_access_utc INTEGER NOT NULL,
                    has_expires INTEGER NOT NULL,
                    is_persistent INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    samesite INTEGER NOT NULL,
                    source_scheme INTEGER NOT NULL,
                    source_port INTEGER NOT NULL,
                    is_same_party INTEGER NOT NULL,
                    last_update_utc INTEGER NOT NULL,
                    source_type INTEGER NOT NULL,
                    has_cross_site_ancestor INTEGER NOT NULL,
                    PRIMARY KEY (host_key, top_frame_site_key, name, path, source_scheme, source_port)
                )
            ''')
            init_c.execute('''CREATE TABLE IF NOT EXISTS meta(key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, value LONGVARCHAR)''')
            init_c.execute("INSERT OR REPLACE INTO meta VALUES('version', '21')")
            init_c.execute("INSERT OR REPLACE INTO meta VALUES('last_compatible_version', '18')")
            init_conn.commit()
            init_conn.close()

            _run_root_capture(f"cp '{local_init}' '{fallback_db}' && chown {uid}:{gid} '{fallback_db}' && chmod 660 '{fallback_db}'", timeout=5)
            dbs.append(fallback_db)
            try: os.remove(local_init)
            except: pass
        except Exception:
            pass

    if not dbs:
        return False

    # Tính toán Chromium Epoch 1601 UTC (Microseconds kể từ 1601-01-01)
    epoch_offset = 11644473600
    now_1601 = (int(time.time()) + epoch_offset) * 1000000
    exp_1601 = (int(time.time()) + 10 * 365 * 86400 + epoch_offset) * 1000000

    hosts = ['.roblox.com', 'roblox.com', 'www.roblox.com', '.www.roblox.com', 'api.roblox.com', '.api.roblox.com', 'auth.roblox.com', '.auth.roblox.com', 'web.roblox.com', '.web.roblox.com']
    cookie_names = ['.ROBLOSECURITY', 'ROBLOSECURITY']
    site_keys = ['', 'https://roblox.com']

    success_count = 0
    primary_synced_db = None

    for idx, webview_db in enumerate(dbs, 1):
        local_db = os.path.join(tmp_dir, f"inj_db_{idx}.db")
        copy_code, _, _ = _run_root_capture(
            f"cp '{webview_db}' '{local_db}' && chmod 666 '{local_db}'"
        )
        if copy_code != 0 or not os.path.exists(local_db):
            continue

        try:
            conn = sqlite3.connect(local_db)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
            if not c.fetchone():
                conn.close()
                try: os.remove(local_db)
                except: pass
                continue

            c.execute("PRAGMA table_info(cookies)")
            column_info = c.fetchall()
            columns = [col[1] for col in column_info]

            # Xóa các cookie Roblox cũ để tránh xung đột key
            c.execute("DELETE FROM cookies WHERE name IN ('.ROBLOSECURITY', 'ROBLOSECURITY', 'RobloxSecurityToken')")

            counter = 0
            for hk in hosts:
                for cname in cookie_names:
                    for sk in site_keys:
                        counter += 1
                        row_time = now_1601 + counter
                        data = {
                            'creation_utc': row_time,
                            'top_frame_site_key': sk,
                            'host_key': hk,
                            'name': cname,
                            'value': cookie,
                            'encrypted_value': b'',
                            'path': '/',
                            'expires_utc': exp_1601,
                            'is_secure': 1,
                            'is_httponly': 1,
                            'last_access_utc': row_time,
                            'last_update_utc': row_time,
                            'has_expires': 1,
                            'is_persistent': 1,
                            'priority': 1,
                            'samesite': 0,
                            'source_scheme': 2,
                            'source_port': 443,
                            'source_type': 0,
                            'has_cross_site_ancestor': 0,
                            'is_same_party': 0
                        }

                        # Bổ sung giá trị trung tính cho cột NOT NULL không có DEFAULT
                        for _, col_name, col_type, not_null, default_value, _ in column_info:
                            if col_name in data or not not_null or default_value is not None:
                                continue
                            type_upper = (col_type or '').upper()
                            if 'BLOB' in type_upper:
                                data[col_name] = b''
                            elif any(t in type_upper for t in ('INT', 'REAL', 'NUM')):
                                data[col_name] = 0
                            else:
                                data[col_name] = ''

                        valid_cols = [k for k in data if k in columns]
                        vals = [data[k] for k in valid_cols]
                        placeholders = ','.join(['?' for _ in valid_cols])

                        sql = f"INSERT INTO cookies ({','.join(valid_cols)}) VALUES ({placeholders})"
                        c.execute(sql, vals)

            conn.commit()
            conn.close()

            # Ghi đè vào app + dọn sạch file WAL/journal + gán quyền uid:gid chuẩn & SELinux context
            fix_cmd = (
                f"cp \"{local_db}\" \"{webview_db}\" && "
                f"rm -f \"{webview_db}-wal\" \"{webview_db}-shm\" \"{webview_db}-journal\" 2>/dev/null && "
                f"chown {uid}:{gid} \"{webview_db}\" && "
                f"chmod 660 \"{webview_db}\" && "
                f"(chcon -R --reference='/data/data/{pkg}' \"{webview_db}\" 2>/dev/null || restorecon -F \"{webview_db}\" 2>/dev/null || true)"
            )
            write_code, _, _ = _run_root_capture(fix_cmd)
            if write_code == 0:
                success_count += 1
                if not primary_synced_db:
                    primary_synced_db = local_db
            if primary_synced_db != local_db:
                try: os.remove(local_db)
                except: pass
        except Exception as e:
            try: conn.close()
            except: pass
            try: os.remove(local_db)
            except: pass

    # Đồng bộ hóa chéo sang cả các đường dẫn Chromium WebView khác (Default/Cookies và Network/Cookies)
    if primary_synced_db and os.path.exists(primary_synced_db):
        sync_targets = [
            f"/data/data/{pkg}/app_webview/Default/Network/Cookies",
            f"/data/data/{pkg}/app_webview/Default/Cookies",
            f"/data/data/{pkg}/app_webview/Cookies"
        ]
        for st in sync_targets:
            parent = os.path.dirname(st)
            _run_root_capture(
                f"mkdir -p '{parent}' && chown {uid}:{gid} '{parent}' && "
                f"cp \"{primary_synced_db}\" \"{st}\" && "
                f"rm -f \"{st}-wal\" \"{st}-shm\" \"{st}-journal\" 2>/dev/null && "
                f"chown {uid}:{gid} \"{st}\" && chmod 660 \"{st}\" && "
                f"(chcon -R --reference='/data/data/{pkg}' \"{st}\" 2>/dev/null || restorecon -F \"{st}\" 2>/dev/null || true)",
                timeout=5
            )
        try: os.remove(primary_synced_db)
        except: pass

    return success_count > 0

def inject_cookie_safe_xml(pkg, cookie, user_name=None, user_id=None):
    """
    Tiêm trực tiếp Cookie vào SharedPreferences của Roblox và Delta Lite:
    1. Cốt lõi kiến trúc: Ghi trực tiếp vào 'WebViewCookieHandlerNativeStorage.xml'
       (Hệ thống NativeCookieStorage fl.e của Roblox đọc file này và tự động
        đồng bộ Cookie sang WebView CookieManager và OkHttp Engine khi mở App).
    2. Ghi đè flag '__migrated_from_webview_v3__' = true để kích hoạt chế độ nạp trực tiếp.
    3. Cập nhật 'webView_backup.xml', '{pkg}_preferences.xml', 'com.roblox.client_preferences.xml'.
    4. Cập nhật tất cả các file XML khác có thẻ <map> trong shared_prefs.
    """
    cookie = _normalize_roblosecurity_cookie(cookie)
    if not cookie:
        return False

    shared_prefs_dir = f"/data/data/{pkg}/shared_prefs"
    uid, gid = get_pkg_uid_gid(pkg)

    # Đảm bảo thư mục shared_prefs tồn tại
    _run_root_capture(f"mkdir -p '{shared_prefs_dir}' && chown {uid}:{gid} '{shared_prefs_dir}' && chmod 771 '{shared_prefs_dir}' 2>/dev/null", timeout=3)

    code, files_str, _ = _run_root_capture(f"ls '{shared_prefs_dir}'/*.xml 2>/dev/null", timeout=5)
    xml_files = []
    if code == 0 and files_str:
        xml_files = [f.strip() for f in files_str.splitlines() if f.strip() and f.strip().endswith('.xml')]

    # Các file SharedPreferences thiết yếu theo phân tích mã nguồn Roblox NativeCookieStorage (fl.e & ni.s)
    essential_files = [
        f"{shared_prefs_dir}/WebViewCookieHandlerNativeStorage.xml",
        f"{shared_prefs_dir}/webView_backup.xml",
        f"{shared_prefs_dir}/{pkg}_preferences.xml",
        f"{shared_prefs_dir}/com.roblox.client_preferences.xml",
        f"{shared_prefs_dir}/AppPreferences.xml"
    ]
    for ef in essential_files:
        if ef not in xml_files:
            xml_files.append(ef)

    tmp_dir = os.path.join(tempfile.gettempdir(), 'hudy_cookie_tmp')
    try: os.makedirs(tmp_dir, exist_ok=True)
    except: tmp_dir = tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)

    updates = {
        'ROBLOSECURITY': cookie,
        '.ROBLOSECURITY': cookie,
        'RobloxSecurityToken': cookie
    }
    if user_name:
        updates.update({
            'Username': str(user_name),
            'RobloxUsername': str(user_name),
            'RBX_USERNAME': str(user_name)
        })
    if user_id:
        updates.update({
            'UserId': str(user_id),
            'RobloxUserId': str(user_id),
            'RBX_USER_ID': str(user_id)
        })

    success_count = 0
    for xml_path in xml_files:
        read_code, raw, _ = _run_root_capture(f"cat '{xml_path}' 2>/dev/null", timeout=4)
        root_el = None
        if read_code == 0 and raw and '<map>' in raw:
            try:
                root_el = ET.fromstring(raw)
            except:
                root_el = None

        if root_el is None:
            root_el = ET.Element('map')

        fname = os.path.basename(xml_path)

        # 1. WebViewCookieHandlerNativeStorage.xml - Hệ thống lưu trữ Native Cookie của Roblox (fl.e)
        if fname == "WebViewCookieHandlerNativeStorage.xml":
            # Đảm bảo flag __migrated_from_webview_v3__ = true
            for n in [x for x in list(root_el) if x.get('name') == '__migrated_from_webview_v3__']:
                root_el.remove(n)
            ET.SubElement(root_el, 'boolean', name='__migrated_from_webview_v3__', value='true')

            # Gán trực tiếp .ROBLOSECURITY và ROBLOSECURITY
            for k in ['.ROBLOSECURITY', 'ROBLOSECURITY']:
                for n in [x for x in list(root_el) if x.get('name') == k]:
                    root_el.remove(n)
                el = ET.SubElement(root_el, 'string', name=k)
                el.text = cookie

        # 2. webView_backup.xml - ShellCookieHandler backup (ni.s)
        elif fname == "webView_backup.xml":
            for k in ['roblox.com', 'roblox.com-2']:
                for n in [x for x in list(root_el) if x.get('name') == k]:
                    root_el.remove(n)
                el = ET.SubElement(root_el, 'string', name=k)
                el.text = cookie

        # 3. Các file Preferences thông thường
        else:
            for key, value in updates.items():
                for n in [x for x in list(root_el) if x.get('name') == key]:
                    root_el.remove(n)
                el = ET.SubElement(root_el, 'string', name=key)
                el.text = value

        xml_output = '<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n' + ET.tostring(root_el, encoding='unicode')
        fd, temp_file = tempfile.mkstemp(suffix='.xml', prefix='cookie_', dir=tmp_dir)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(xml_output)

        fix_xml_cmd = (
            f"cp '{temp_file}' '{xml_path}' && "
            f"chown {uid}:{gid} '{xml_path}' && "
            f"chmod 660 '{xml_path}' && "
            f"(chcon -R --reference='/data/data/{pkg}' \"{xml_path}\" 2>/dev/null || restorecon -F \"{xml_path}\" 2>/dev/null || true)"
        )
        write_code, _, _ = _run_root_capture(fix_xml_cmd)
        try: os.remove(temp_file)
        except: pass
        if write_code == 0:
            success_count += 1

    return success_count > 0

def roblox_quick_login(cookie, code):
    """
    Sử dụng Cookie Roblox để phê duyệt phiên đăng nhập nhanh (Quick Login / Cross-Device Login) cho App.
    Gọi các API chính thức của Roblox:
    - POST https://apis.roblox.com/auth-token-service/v1/login/enterCode
    - POST https://apis.roblox.com/auth-token-service/v1/login/validateCode
    Trả về: (success: bool, message: str, info_dict: dict|None)
    """
    cookie = _normalize_roblosecurity_cookie(cookie)
    if not cookie:
        return False, "Cookie rỗng hoặc không hợp lệ!", None

    code = str(code).strip().upper().replace(" ", "").replace("-", "")
    if len(code) != 6 or not code.isalnum():
        return False, f"Mã Quick Login '{code}' không hợp lệ (phải đúng 6 chữ số/chữ cái)!", None

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/my/account#!/quick-login"
    }
    csrf_token = None
    try:
        req0 = urllib.request.Request(
            "https://apis.roblox.com/auth-token-service/v1/login/enterCode",
            data=b"{}",
            headers=headers,
            method="POST"
        )
        urllib.request.urlopen(req0, timeout=6)
    except urllib.error.HTTPError as e:
        csrf_token = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
    except Exception:
        pass

    if not csrf_token:
        try:
            req_fb = urllib.request.Request(
                "https://auth.roblox.com/v1/logout",
                data=b"{}",
                headers={**headers, "Cookie": f".ROBLOSECURITY={cookie}"},
                method="POST"
            )
            urllib.request.urlopen(req_fb, timeout=6)
        except urllib.error.HTTPError as e:
            csrf_token = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
        except Exception:
            pass

    if not csrf_token:
        return False, "Không lấy được X-CSRF-TOKEN từ máy chủ Roblox!", None

    headers["x-csrf-token"] = csrf_token
    headers["Cookie"] = f".ROBLOSECURITY={cookie}"
    payload = json.dumps({"code": code}).encode("utf-8")

    device_info = {}
    try:
        req_enter = urllib.request.Request(
            "https://apis.roblox.com/auth-token-service/v1/login/enterCode",
            data=payload,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req_enter, timeout=10) as resp_enter:
            raw_enter = resp_enter.read().decode('utf-8', errors='ignore')
            try:
                device_info = json.loads(raw_enter) if raw_enter else {}
            except Exception:
                device_info = {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        try:
            err_json = json.loads(body)
            err_msg = err_json.get("errors", [{}])[0].get("message", body)
            err_code = err_json.get("errors", [{}])[0].get("code", e.code)
            if err_code == 9002 or "not authenticated" in err_msg.lower():
                return False, f"Cookie hết hạn hoặc không hợp lệ ({err_msg})", None
            if "invalid" in err_msg.lower() or "not found" in err_msg.lower():
                return False, f"Mã '{code}' không tồn tại hoặc đã hết hạn (chỉ có hiệu lực trong 5 phút)", None
            return False, f"Lỗi enterCode (HTTP {e.code}): {err_msg}", None
        except Exception:
            return False, f"Lỗi enterCode (HTTP {e.code}): {body[:150]}", None
    except Exception as e:
        return False, f"Lỗi kết nối enterCode: {str(e)}", None

    try:
        req_val = urllib.request.Request(
            "https://apis.roblox.com/auth-token-service/v1/login/validateCode",
            data=payload,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req_val, timeout=10) as resp_val:
            if resp_val.code in (200, 204):
                return True, "Cấp phép thành công! App Roblox trên thiết bị sẽ tự động đăng nhập ngay.", device_info
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        try:
            err_json = json.loads(body)
            err_msg = err_json.get("errors", [{}])[0].get("message", body)
            return False, f"Lỗi validateCode (HTTP {e.code}): {err_msg}", device_info
        except Exception:
            return False, f"Lỗi validateCode (HTTP {e.code}): {body[:150]}", device_info
    except Exception as e:
        return False, f"Lỗi kết nối validateCode: {str(e)}", device_info

    return False, "Không nhận được phản hồi hợp lệ từ máy chủ Roblox.", device_info


def detect_quick_login_code_from_screen():
    """Quét màn hình thiết bị (thông qua uiautomator dump) để tìm mã Quick Login 6 ký tự."""
    try:
        dump_path = "/data/local/tmp/quick_login_dump.xml"
        _run_root_capture(f"uiautomator dump '{dump_path}' 2>/dev/null", timeout=6)
        code, xml_content, _ = _run_root_capture(f"cat '{dump_path}' 2>/dev/null", timeout=4)
        _run_root_capture(f"rm -f '{dump_path}' 2>/dev/null", timeout=2)
        if code != 0 or not xml_content:
            return None
        matches = re.findall(r'text="([A-Za-z0-9\s]{6,12})"', xml_content)
        ignore_words = {"CANCEL", "SUBMIT", "ROBLOX", "LOGOUT", "SEARCH", "BUTTON", "PLAYER", "LOGIN", "SIGNIN", "VERIFY"}
        for m in matches:
            clean_m = m.replace(" ", "").strip().upper()
            if len(clean_m) == 6 and clean_m.isalnum() and not clean_m.isdigit():
                if clean_m not in ignore_words:
                    return clean_m
    except Exception:
        pass
    return None


def clone_package_session(src_pkg, dst_pkg):
    """
    Sao chép dữ liệu phiên đăng nhập (shared_prefs, databases, files) từ src_pkg sang dst_pkg.
    Tự động cập nhật UID:GID của dst_pkg và fix SELinux context.
    """
    if src_pkg == dst_pkg:
        return False, "Package nguồn và đích không được trùng nhau!"

    src_code, _, _ = _run_root_capture(f"test -d '/data/data/{src_pkg}' && echo exists", timeout=3)
    if src_code != 0:
        return False, f"Không tìm thấy thư mục dữ liệu của package nguồn '{src_pkg}'!"

    dst_uid, dst_gid = get_pkg_uid_gid(dst_pkg)
    if dst_uid == 0 and dst_gid == 0:
        return False, f"Chưa xác định được UID/GID của '{dst_pkg}'. Vui lòng mở app '{dst_pkg}' ít nhất một lần!"

    _run_root_capture(f"am force-stop '{dst_pkg}'", timeout=8)
    time.sleep(1)

    targets = ['shared_prefs', 'databases', 'files']
    copied = 0
    for folder in targets:
        src_folder = f"/data/data/{src_pkg}/{folder}"
        dst_folder = f"/data/data/{dst_pkg}/{folder}"
        chk_code, _, _ = _run_root_capture(f"test -d '{src_folder}' && echo exists", timeout=3)
        if chk_code == 0:
            _run_root_capture(f"rm -rf '{dst_folder}'", timeout=5)
            cp_code, _, _ = _run_root_capture(f"cp -a '{src_folder}' '{dst_folder}'", timeout=10)
            if cp_code == 0:
                copied += 1

    _run_root_capture(f"rm -rf '/data/data/{dst_pkg}/cache/'* '/data/data/{dst_pkg}/code_cache/'*", timeout=5)

    chown_cmd = (
        f"chown -R {dst_uid}:{dst_gid} '/data/data/{dst_pkg}' && "
        f"chmod -R 771 '/data/data/{dst_pkg}' && "
        f"(restorecon -R '/data/data/{dst_pkg}' 2>/dev/null || true)"
    )
    ch_code, _, ch_err = _run_root_capture(chown_cmd, timeout=10)
    if ch_code != 0:
        return False, f"Lỗi phân quyền UID:GID: {ch_err[:100]}"

    if copied > 0:
        return True, f"Đã nhân bản thành công {copied} thư mục dữ liệu sang '{dst_pkg}'!"
    return False, f"Không tìm thấy dữ liệu phiên hợp lệ trong '{src_pkg}' để sao chép."


def login_via_cookie():
    global selected_packages, target_place_id

    # 1. Kiểm tra quyền ROOT
    root_code, root_out, root_err = _run_root_capture("id", timeout=5)
    if root_code != 0 or "uid=0" not in root_out:
        print(f"{R}[!] Lỗi kiểm tra quyền ROOT. Vui lòng cấp quyền SU trong Magisk/KernelSU!{RESET}")
        if root_err:
            print(f"{Y}    Chi tiết: {root_err[:120]}{RESET}")
        time.sleep(3)
        return

    # 2. Kiểm tra danh sách package - Tự động quét nếu chưa chọn ở mục [1]
    if not selected_packages:
        print(f"\n{Y}[*] Bạn chưa chọn package ở mục [1]. Đang quét package Roblox trên máy...{RESET}")
        scanned = scan_packages()
        if not scanned:
            scanned = ["com.roblox.client"]

        if len(scanned) == 1:
            pkg_name = scanned[0]
            selected_packages = [{"pkg": pkg_name, "name": "Player"}]
            print(f"{G}[✓] Tự động chọn package Roblox duy nhất: {C}{pkg_name}{RESET}")
            time.sleep(1)
        else:
            print(f"\n{C}Tìm thấy {len(scanned)} package Roblox trên máy:{RESET}")
            for i, p in enumerate(scanned, 1):
                print(f"  [{C}{i}{RESET}] {W}{p}{RESET}")
            print(f"  [{C}A{RESET}] {G}Chọn tất cả ({len(scanned)} package){RESET}")
            fix_tty()
            sel = safe_input(f"\n{M}Chọn package để nạp [1-{len(scanned)} / A]: {RESET}").strip()
            if sel.upper() == 'A':
                selected_packages = [{"pkg": p, "name": f"Acc_{i}"} for i, p in enumerate(scanned, 1)]
            elif sel.isdigit() and 1 <= int(sel) <= len(scanned):
                selected_packages = [{"pkg": scanned[int(sel) - 1], "name": "Player"}]
            else:
                selected_packages = [{"pkg": scanned[0], "name": "Player"}]
            print(f"{G}[✓] Đã chọn: {', '.join(p['pkg'] for p in selected_packages)}{RESET}")
            time.sleep(1)

    clear_screen()
    print_banner()
    print(f"{C}=== ĐĂNG NHẬP ROBLOX VÀO APP BẰNG COOKIE (NẠP TRỰC TIẾP) ==={RESET}")
    print(f"{C}Bản vá mục 4: {COOKIE_LOGIN_REVISION}{RESET}")
    print(f"Các package đang chọn ({len(selected_packages)}): {W}{', '.join(p['pkg'] for p in selected_packages)}{RESET}")
    print("-" * 65)
    print(f"{Y}[i] Chỉ cần dán Cookie .ROBLOSECURITY (không cần thao tác mã 6 số).{RESET}")
    print(f"{Y}[i] Tool sẽ tự động nạp Cookie vào SQLite DB, XML và kích hoạt vào App ngay!{RESET}")
    print("-" * 65)

    cookies_in_file, c_fpath = load_cookies_from_download()
    raw_cookie = ""
    multi_cookie_map = {}

    if cookies_in_file and c_fpath:
        print(f"\n{GREEN_MINT}╭──────────────── TÌM THẤY FILE COOKIE TRONG DOWNLOAD ───────────────╮{RESET}")
        print(f"{GREEN_MINT}│{RESET} {G}[✓] File:{RESET} {GOLD_NEON}{c_fpath}{RESET}")
        print(f"{GREEN_MINT}│{RESET} {G}[✓] Số lượng Cookie tìm thấy:{RESET} {C}{len(cookies_in_file)} cookie{RESET}")
        print(f"{GREEN_MINT}╰─────────────────────────────────────────────────────────────────────╯{RESET}")
        print(f"  [{C}1{RESET}] {BOLD}{G}Nạp tự động từ file cookie.txt{RESET} {DIM}(Nhấn Enter để chọn ngay){RESET}")
        print(f"  [{C}2{RESET}] {W}Nhập / Dán Cookie thủ công bằng tay{RESET}")
        fix_tty()
        opt = safe_input(f"\n{M}Lựa chọn [1/2, mặc định 1]: {RESET}").strip()
        if opt in ['', '1']:
            if len(cookies_in_file) == 1:
                raw_cookie = cookies_in_file[0]
                print(f"{G}[✓] Đã chọn cookie từ file {os.path.basename(c_fpath)}{RESET}")
            else:
                print(f"\n{C}Danh sách {len(cookies_in_file)} cookie trong file:{RESET}")
                for i, ck in enumerate(cookies_in_file, 1):
                    masked = ck[:18] + "..." + ck[-10:] if len(ck) > 28 else ck
                    print(f"  [{C}{i}{RESET}] Cookie #{i}: {W}{masked}{RESET}")
                if len(selected_packages) > 1 and len(cookies_in_file) >= len(selected_packages):
                    print(f"  [{C}A{RESET}] {BOLD}{G}Tự động phân bổ lần lượt từng cookie cho {len(selected_packages)} package{RESET}")
                fix_tty()
                c_sel = safe_input(f"\n{M}Chọn cookie [1-{len(cookies_in_file)} / Enter lấy #1]: {RESET}").strip()
                if c_sel.upper() == 'A' and len(selected_packages) > 1:
                    for i_p, p_item in enumerate(selected_packages):
                        p_pkg = p_item['pkg'] if isinstance(p_item, dict) else p_item
                        multi_cookie_map[p_pkg] = cookies_in_file[i_p % len(cookies_in_file)]
                    raw_cookie = cookies_in_file[0]
                elif c_sel.isdigit() and 1 <= int(c_sel) <= len(cookies_in_file):
                    raw_cookie = cookies_in_file[int(c_sel) - 1]
                else:
                    raw_cookie = cookies_in_file[0]
        else:
            fix_tty()
            raw_cookie = safe_input(f"\n{M}Nhập Cookie Roblox (_|WARNING...): {RESET}")
    else:
        fix_tty()
        raw_cookie = safe_input(f"\n{M}Nhập Cookie Roblox (_|WARNING...): {RESET}")

    cookie = _normalize_roblosecurity_cookie(raw_cookie)
    if not cookie and not multi_cookie_map:
        print(f"{Y}[*] Đã hủy.{RESET}")
        time.sleep(1.5)
        return

    # Nếu người dùng nhập thủ công (chưa có trong file), hỏi có muốn lưu vào Download/cookie.txt không
    if not cookies_in_file and cookie:
        fix_tty()
        ask_save = safe_input(f"\n{M}Lưu cookie này vào Download/cookie.txt để dùng lần sau? (Y/n): {RESET}").strip().lower()
        if ask_save in ['', 'y', 'yes', 'co', 'có']:
            saved_c = save_cookie_to_download(cookie)
            if saved_c:
                print(f"{G}[✓] Đã lưu cookie vào: {GOLD_NEON}{saved_c}{RESET}")

    print(f"\n{Y}[*] Đang xác thực thông tin Cookie qua Roblox API...{RESET}")
    acc_info = check_roblox_account_status(cookie)
    status = acc_info.get('status')
    u_name = acc_info.get('username') or "Player"
    u_id = acc_info.get('user_id')

    if status == 'EXPIRED':
        print(f"{R}[✗] Cookie đã hết hạn hoặc không hợp lệ (HTTP 401)!{RESET}")
        print(f"{Y}[i] Vui lòng kiểm tra lại cookie đã copy từ trình duyệt.{RESET}")
        fix_tty()
        safe_input(f"\n{Y}Bấm Enter để quay lại Menu...{RESET}")
        return
    elif status == 'NOT_APPROVED':
        print(f"{Y}[!] Cảnh báo: Tài khoản đang bị kẹt Not-Approved / Kiểm Duyệt.{RESET}")
        print(f"{Y}    Vẫn tiếp tục nạp vào app...{RESET}")
    elif status == 'CAPTCHA_CHECKPOINT':
        print(f"{Y}[!] Cảnh báo: Tài khoản đang yêu cầu giải Captcha / Checkpoint.{RESET}")
        print(f"{Y}    Vẫn tiếp tục nạp vào app để bạn giải captcha trong app...{RESET}")
    else:
        print(f"{G}[✓] Cookie SỐNG! Tài khoản: {C}{u_name}{G} (ID: {u_id or 'N/A'}){RESET}")

    # Tiến hành nạp Cookie và mở app
    for idx, item in enumerate(selected_packages, 1):
        pkg = item['pkg'] if isinstance(item, dict) else item
        cur_cookie = multi_cookie_map.get(pkg, cookie)
        print(f"\n{C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"{Y}[{idx}/{len(selected_packages)}] Đang nạp Cookie vào: {W}{pkg}{RESET}")

        # 1. Force-stop app
        print(f"{Y}  ├─ [*] Đang dừng app {pkg}...{RESET}")
        _run_root_capture(f"am force-stop '{pkg}'", timeout=10)
        time.sleep(1)

        # 2. Xóa cache phiên cũ
        print(f"{Y}  ├─ [*] Dọn dẹp cache phiên cũ...{RESET}")
        _run_root_capture(f"rm -rf '/data/data/{pkg}/cache/'* '/data/data/{pkg}/code_cache/'*", timeout=10)

        # 3. Tiêm WebView SQLite DB
        print(f"{Y}  ├─ [*] Đang tiêm Cookie vào Chromium WebView SQLite DB...{RESET}")
        ok_wv = inject_cookie_webview(pkg, cur_cookie)
        if not ok_wv:
            # Nếu chưa có DB (app mới cài chưa từng mở), mở 3s bằng monkey rồi dừng để hệ thống tạo DB
            print(f"{Y}  ├─ [*] Chưa có SQLite DB, đang khởi tạo app 3s...{RESET}")
            _run_root_capture(f"monkey -p '{pkg}' -c android.intent.category.LAUNCHER 1", timeout=5)
            time.sleep(3)
            _run_root_capture(f"am force-stop '{pkg}'", timeout=10)
            time.sleep(1)
            ok_wv = inject_cookie_webview(pkg, cur_cookie)

        if ok_wv:
            print(f"{G}  ├─ [✓] WebView SQLite DB: Tiêm thành công!{RESET}")
        else:
            print(f"{Y}  ├─ [!] Không tìm thấy DB WebView, chuyển sang SharedPreferences XML.{RESET}")

        # 4. Tiêm SharedPreferences XML
        print(f"{Y}  ├─ [*] Đang cập nhật SharedPreferences XML...{RESET}")
        ok_xml = inject_cookie_safe_xml(pkg, cur_cookie, user_name=u_name, user_id=u_id)
        if ok_xml:
            print(f"{G}  ├─ [✓] SharedPrefs XML: Cập nhật tài khoản thành công!{RESET}")
        else:
            print(f"{Y}  ├─ [i] Bỏ qua bước XML (app chưa tạo file XML hoặc không tìm thấy).{RESET}")

        # 5. Tạo Auth Ticket từ Roblox Server
        print(f"{Y}  ├─ [*] Đang tạo Roblox Auth Ticket...{RESET}")
        ticket, t_msg = get_auth_ticket(cur_cookie)

        # 6. Khởi chạy ứng dụng (dùng FLAG_ACTIVITY_NEW_TASK 0x14000000)
        print(f"{Y}  └─ [*] Đang khởi động ứng dụng...{RESET}")
        launched = False
        if ticket:
            print(f"{G}     [✓] Tạo Auth Ticket thành công: {ticket[:18]}...{RESET}")
            # Kích hoạt Intent đăng nhập chính thức bằng roblox://navigation
            nav_deeplink = f"roblox://navigation?authTicket={ticket}"
            code, out, _ = _run_root_capture(f"am start -p {pkg} -f 0x14000000 -a android.intent.action.VIEW -d \"{nav_deeplink}\"", timeout=10)
            if code == 0 and "Error:" not in out:
                print(f"{G}     [✓] Đã kích hoạt Đăng Nhập qua Auth Ticket Deeplink (roblox://navigation)!{RESET}")
                launched = True
            else:
                # Thử các scheme & activity chính thức từ APK (roblox, robloxmobile, robloxglobal)
                alt_intents = [
                    f"am start -p {pkg} -f 0x14000000 -a android.intent.action.VIEW -d \"roblox://navigation/home?authTicket={ticket}\"",
                    f"am start -p {pkg} -f 0x14000000 -a android.intent.action.VIEW -d \"robloxmobile://navigation?authTicket={ticket}\"",
                    f"am start -p {pkg} -f 0x14000000 -a android.intent.action.VIEW -d \"robloxglobal://navigation?authTicket={ticket}\"",
                    f"am start -n {pkg}/com.roblox.client.startup.ActivitySplash -f 0x14000000 --es authTicket \"{ticket}\""
                ]
                for alt_cmd in alt_intents:
                    c_alt, out_alt, _ = _run_root_capture(alt_cmd, timeout=8)
                    if c_alt == 0 and "Error:" not in out_alt:
                        print(f"{G}     [✓] Đã gửi Auth Ticket qua Intent thay thế!{RESET}")
                        launched = True
                        break
        else:
            print(f"{Y}     [!] Không tạo được Auth Ticket ({t_msg}). Khởi chạy bằng Launcher với Cookie đã nạp...{RESET}")

        if not launched:
            # Mở App qua Launcher chính thức của APK (com.roblox.client.startup.ActivitySplash / LauncherAliasMain)
            launcher_cmds = [
                f"am start -n {pkg}/com.roblox.client.startup.ActivitySplash -f 0x14000000",
                f"am start -n {pkg}/com.roblox.client.startup.LauncherAliasMain -f 0x14000000",
                f"am start -n {pkg}/com.roblox.client.ActivityNativeMain -f 0x14000000",
                f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg} -f 0x14000000",
                f"monkey -p '{pkg}' -c android.intent.category.LAUNCHER 1"
            ]
            for l_cmd in launcher_cmds:
                code, out, _ = _run_root_capture(l_cmd, timeout=10)
                if code == 0 and "Error:" not in out:
                    print(f"{G}     [✓] Đã khởi động App qua Launcher thành công!{RESET}")
                    launched = True
                    break

            if not launched:
                print(f"{R}     [✗] Không thể mở app: {pkg}{RESET}")

        print(f"{Y}     [*] Chờ {COOKIE_LOGIN_APP_LOAD_WAIT}s để app tải xong...{RESET}")
        time.sleep(COOKIE_LOGIN_APP_LOAD_WAIT)

    print(f"\n{G}╔═══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{G}║             [✓] ĐÃ NẠP COOKIE VÀ MỞ APP THÀNH CÔNG!       ║{RESET}")
    print(f"{G}╚═══════════════════════════════════════════════════════════╝{RESET}")
    print(f"  • Tài khoản: {C}{u_name}{RESET} (ID: {u_id or 'N/A'})")
    print(f"  • Hãy nhìn vào màn hình điện thoại để kiểm tra tài khoản trong app.{RESET}")
    print(f"{C}====================================================={RESET}")
    fix_tty()
    print(f"\n{Y}Bấm Enter để quay lại Menu...{RESET}")
    try: input()
    except: pass

def login_via_cookie_legacy(target_pkgs, cookie, u_name=None, u_id=None):
    """Giữ lại alias để tương thích ngược."""
    global selected_packages
    old_sel = selected_packages
    try:
        selected_packages = target_pkgs
        login_via_cookie()
    finally:
        selected_packages = old_sel

# =====================================================================
def extract_roblox_cookie(pkg):
    """
    Trích xuất cookie .ROBLOSECURITY MỚI NHẤT từ app Roblox trên thiết bị Android (cần Root).
    1. Quét tìm tất cả DB SQLite Cookies (Network/Cookies, Default/Cookies, Cookies).
       - Sao chép cả file WAL (-wal) và SHM (-shm) để đọc dữ liệu phiên vừa đăng nhập trong app.
       - Sắp xếp ORDER BY last_access_utc DESC, creation_utc DESC để lấy Cookie mới nhất.
    2. Quét SharedPreferences XML theo thứ tự file được sửa đổi mới nhất (mtime DESC).
    """
    tmp_dir = os.path.join(tempfile.gettempdir(), 'hudy_cookie_tmp')
    try:
        os.makedirs(tmp_dir, exist_ok=True)
    except:
        tmp_dir = tempfile.gettempdir()

    # 1. Quét tìm tất cả DB SQLite Cookies theo thứ tự ưu tiên
    db_candidates = [
        f"/data/data/{pkg}/app_webview/Default/Network/Cookies",
        f"/data/data/{pkg}/app_webview/Default/Cookies",
        f"/data/data/{pkg}/app_webview/Cookies",
        f"/data/data/{pkg}/databases/webviewCookiesChromium.db",
        f"/data/data/{pkg}/databases/webview.db",
    ]
    try:
        code, out, _ = _run_root_capture(
            f"find '/data/data/{pkg}/' \\( -name 'Cookies' -o -iname '*cookie*.db' \\) -type f 2>/dev/null",
            timeout=3
        )
        if code == 0 and out:
            for line in out.splitlines():
                p = line.strip()
                if p and p not in db_candidates:
                    db_candidates.append(p)
    except:
        pass

    for db_path in db_candidates:
        try:
            check = subprocess.check_output(
                f"su -c 'test -f \"{db_path}\" && echo exists'",
                shell=True, text=True, timeout=3
            ).strip()
            if "exists" not in check:
                continue

            local_db = os.path.join(tmp_dir, f"ext_{pkg.split('.')[-1]}.db")
            # Quan trọng: chép kèm WAL và SHM nếu có để không bỏ sót giao dịch vừa đăng nhập
            cp_cmd = (
                f"cp \"{db_path}\" \"{local_db}\" 2>/dev/null && "
                f"(cp \"{db_path}-wal\" \"{local_db}-wal\" 2>/dev/null || true) && "
                f"(cp \"{db_path}-shm\" \"{local_db}-shm\" 2>/dev/null || true) && "
                f"chmod 666 \"{local_db}\"* 2>/dev/null || true"
            )
            subprocess.run(f"su -c '{cp_cmd}'", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

            if os.path.exists(local_db):
                conn = sqlite3.connect(local_db)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
                if not c.fetchone():
                    conn.close()
                    try: os.remove(local_db)
                    except: pass
                    continue

                c.execute("PRAGMA table_info(cookies)")
                cols = [col[1] for col in c.fetchall()]
                order_by = ""
                if "last_access_utc" in cols and "creation_utc" in cols:
                    order_by = "ORDER BY last_access_utc DESC, creation_utc DESC"
                elif "creation_utc" in cols:
                    order_by = "ORDER BY creation_utc DESC"
                elif "last_access_utc" in cols:
                    order_by = "ORDER BY last_access_utc DESC"

                c.execute(f"SELECT value FROM cookies WHERE name='.ROBLOSECURITY' AND host_key LIKE '%roblox.com%' {order_by} LIMIT 1")
                row = c.fetchone()
                conn.close()
                for f_del in [local_db, f"{local_db}-wal", f"{local_db}-shm"]:
                    try:
                        if os.path.exists(f_del): os.remove(f_del)
                    except: pass

                if row and row[0] and str(row[0]).startswith("_|WARNING"):
                    return row[0].strip()
        except:
            pass

    # 2. Quét SharedPreferences XML (sắp xếp file sửa đổi mới nhất lên đầu để lấy đúng acc vừa lưu)
    try:
        xml_files_raw = subprocess.check_output(
            f"su -c 'ls -t \"/data/data/{pkg}/shared_prefs/\"*.xml 2>/dev/null'",
            shell=True, text=True, timeout=4
        ).strip()
        if xml_files_raw:
            for xml_file in xml_files_raw.splitlines():
                xml_file = xml_file.strip()
                if not xml_file:
                    continue
                match = subprocess.check_output(
                    f"su -c 'grep -hoE \"_\\|WARNING:[^<\"]+\" \"{xml_file}\" 2>/dev/null'",
                    shell=True, text=True, timeout=3
                ).strip()
                if match:
                    for line in match.splitlines():
                        if line.startswith("_|WARNING"):
                            return line.strip()
    except:
        pass

    return None

def check_roblox_account_status(cookie):
    """
    Kiểm tra chi tiết trạng thái tài khoản Roblox bằng Cookie:
    - 'OK': Hoạt động bình thường (không dính Captcha/Lock)
    - 'NOT_APPROVED': Kẹt màn hình phê duyệt Not-Approved / Cảnh báo điều khoản
    - 'CAPTCHA_CHECKPOINT': Yêu cầu xác minh Captcha Arkose / Checkpoint
    - 'EXPIRED': Cookie hết hạn hoặc không hợp lệ (401)
    - 'ERROR': Lỗi mạng hoặc không thể kết nối
    """
    if not cookie or not isinstance(cookie, str):
        return {
            "status": "NO_COOKIE",
            "badge": "Không Có Cookie",
            "color": R,
            "message": "Không tìm thấy cookie trong app hoặc chưa đăng nhập."
        }

    cookie = cookie.strip()
    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie.split("=", 1)[1].strip()
    cookie_header = f".ROBLOSECURITY={cookie}"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    user_id = None
    username = None
    display_name = None

    # 1. API Xác thực chính: users.roblox.com
    try:
        req = urllib.request.Request(
            "https://users.roblox.com/v1/users/authenticated",
            headers={"Cookie": cookie_header, "User-Agent": ua}
        )
        with urllib.request.urlopen(req, timeout=6) as res:
            raw = res.read().decode('utf-8', errors='ignore')
            data = json.loads(raw)
            user_id = data.get("id")
            username = data.get("name")
            display_name = data.get("displayName")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore').lower()
        if e.code == 401:
            return {
                "status": "EXPIRED",
                "badge": "Cookie Hết Hạn / Die (401)",
                "color": R,
                "user_id": None,
                "username": None,
                "message": "Cookie không hợp lệ hoặc đã bị đăng xuất trên hệ thống."
            }
        elif "moderated" in err_body:
            return {
                "status": "NOT_APPROVED",
                "badge": "Kẹt Not-Approved / Kiểm Duyệt",
                "color": R,
                "user_id": None,
                "username": None,
                "message": "Tài khoản đang bị kiểm duyệt (User is moderated)!"
            }
    except Exception:
        pass

    # 2. Kiểm tra điều hướng trang chủ roblox.com/home
    try:
        req_home = urllib.request.Request(
            "https://www.roblox.com/home",
            headers={"Cookie": cookie_header, "User-Agent": ua}
        )
        with urllib.request.urlopen(req_home, timeout=6) as res:
            final_url = res.geturl().lower()
            html_body = res.read().decode('utf-8', errors='ignore').lower()

            if "not-approved" in final_url or "not-approved" in html_body:
                return {
                    "status": "NOT_APPROVED",
                    "badge": "Kẹt Trang Not-Approved / Cần Duyệt",
                    "color": R,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "url": res.geturl(),
                    "message": "Tài khoản đang bị kẹt tại trang Not-Approved (cần vào web chấp thuận cảnh báo hoặc giải captcha)!"
                }
            elif any(k in html_body for k in ["nhấn giữ nút", "nhấn và giữ", "press and hold", "press & hold"]):
                ref_m = re.search(r'(?:id tham chiếu|reference id)[:\s]*([a-f0-9\-]+)', html_body, re.I)
                ref_id = ref_m.group(1) if ref_m else "N/A"
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": "Dính Captcha 'Nhấn và Giữ' (Bảo Mật)",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "challenge_type": "PRESS_AND_HOLD",
                    "challenge_id": ref_id,
                    "url": res.geturl(),
                    "message": f"Tài khoản bị chặn bởi màn hình Bảo Mật 'Nhấn và Giữ' (ID tham chiếu: {ref_id})!"
                }
            elif any(k in final_url for k in ["/checkpoint", "/challenge", "/two-step", "arkoselabs.com"]) or \
                 any(k in html_body for k in ["api.arkoselabs.com", "funcaptcha.com", "id=\"challenge-container\"", "id=\"two-step-verification\""]):
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": "Dính Captcha / Checkpoint Xác Minh",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "url": res.geturl(),
                    "message": "Tài khoản bị yêu cầu giải Captcha FunCaptcha/Arkose hoặc xác minh 2 bước!"
                }
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "").lower()
        if "not-approved" in loc:
            return {
                "status": "NOT_APPROVED",
                "badge": "Kẹt Trang Not-Approved / Cần Duyệt",
                "color": R,
                "user_id": user_id,
                "username": username or "N/A",
                "url": e.headers.get("Location"),
                "message": "Tài khoản bị chuyển hướng vào trang Not-Approved!"
            }
        elif any(k in loc for k in ["checkpoint", "challenge", "two-step"]):
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha / Checkpoint Xác Minh",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "url": e.headers.get("Location"),
                "message": "Tài khoản bị chuyển hướng yêu cầu giải Captcha / Checkpoint!"
            }
    except Exception:
        pass

    # 3. Lấy X-CSRF-TOKEN từ Auth / Join API
    csrf_token = None
    req_csrf = urllib.request.Request(
        "https://auth.roblox.com/v1/authentication-ticket/",
        data=b"{}",
        headers={
            "Cookie": cookie_header,
            "Content-Type": "application/json",
            "User-Agent": ua,
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_csrf, timeout=6) as resp_c:
            csrf_token = resp_c.headers.get("x-csrf-token") or resp_c.headers.get("X-CSRF-TOKEN")
    except urllib.error.HTTPError as e:
        csrf_token = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
        chal_type = (e.headers.get("rblx-challenge-type") or "").lower()
        chal_id = e.headers.get("rblx-challenge-id") or ""
        chal_meta = e.headers.get("rblx-challenge-metadata") or ""
        raw_body = e.read().decode('utf-8', errors='ignore')
        err_body = raw_body.lower()

        if "moderated" in err_body:
            return {
                "status": "NOT_APPROVED",
                "badge": "Kẹt Not-Approved / Kiểm Duyệt",
                "color": R,
                "user_id": user_id,
                "username": username or "N/A",
                "message": "Tài khoản đang bị kiểm duyệt (User is moderated)!"
            }
        is_press_and_hold = (
            any(k in err_body for k in ["nhấn giữ nút", "nhấn và giữ", "press and hold", "press & hold", "người thật", "human", "reference id", "id tham chiếu"]) or
            any(k in chal_type for k in ["security", "generic", "proof-of-work", "press", "hold"])
        )
        if is_press_and_hold:
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha 'Nhấn và Giữ' (Bảo Mật)",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "PRESS_AND_HOLD",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'security'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn (Auth Ticket 403) và yêu cầu vượt qua màn hình Bảo Mật 'Nhấn và Giữ' (ID tham chiếu: {chal_id or 'N/A'})!"
            }
        elif "captchav2" in chal_type or ("captchav2" in chal_meta.lower() if chal_meta else False):
            meta_json = {}
            if chal_meta:
                try:
                    meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                except:
                    pass
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha V2 Vào Game",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "CAPTCHAV2",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "meta_data": meta_json,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captchav2'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn xác thực (Auth Ticket 403, challenge_type=captchav2) và yêu cầu giải Captcha V2 (ID: {chal_id or 'N/A'})!"
            }
        elif "captcha" in chal_type or "arkose" in chal_type or "captcha" in err_body or "challenge is required" in err_body:
            meta_json = {}
            if chal_meta:
                try:
                    meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                except:
                    pass
            hybrid_challenge_url = ""
            if chal_id:
                ch_params = {
                    "generic-challenge-type": "captcha",
                    "app-type": "browser",
                    "generic-challenge-id": chal_id,
                    "challenge-metadata-json": chal_meta or "",
                    "challenge-type": "generic",
                    "dark-mode": "false"
                }
                hybrid_challenge_url = "https://www.roblox.com/challenge/cdn/hybrid?" + urllib.parse.urlencode(ch_params)
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha V1 (Arkose FunCaptcha)",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "CAPTCHA_V1",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "challenge_url": hybrid_challenge_url,
                "meta_data": meta_json,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captcha'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn xác thực (Auth Ticket 403, challenge_type={chal_type or 'captcha'}) và yêu cầu giải Captcha V1 (Arkose FunCaptcha, ID: {chal_id or 'N/A'})!"
            }
        elif chal_id or chal_type or chal_meta:
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": f"Dính Checkpoint Bảo Mật ({chal_type or 'Challenge'})",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": chal_type or "CHALLENGE",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn xác thực (Auth Ticket 403) và kích hoạt Thử Thách Bảo Mật (ID tham chiếu: {chal_id or 'N/A'})!"
            }
    except Exception:
        pass

    if not csrf_token:
        try:
            req_l = urllib.request.Request(
                "https://auth.roblox.com/v1/logout",
                data=b"{}",
                headers={"Cookie": cookie_header, "Content-Type": "application/json", "User-Agent": ua},
                method="POST"
            )
            with urllib.request.urlopen(req_l, timeout=6) as resp_l:
                csrf_token = resp_l.headers.get("x-csrf-token") or resp_l.headers.get("X-CSRF-TOKEN")
        except urllib.error.HTTPError as e:
            csrf_token = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
        except:
            pass

    # 4. KIỂM TRA ĐẶC TRỊ: POST https://gamejoin.roblox.com/v1/join-game (Bắt chuẩn 100% Game Join Captcha)
    pid = 4520749081
    try:
        if target_place_id and str(target_place_id).strip().isdigit():
            pid = int(target_place_id)
    except:
        pass

    join_headers = {
        "Cookie": cookie_header,
        "Content-Type": "application/json",
        "User-Agent": ua,
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/"
    }
    if csrf_token:
        join_headers["x-csrf-token"] = csrf_token
        join_headers["X-CSRF-TOKEN"] = csrf_token

    payload = json.dumps({"placeId": pid}).encode('utf-8')
    req_join = urllib.request.Request(
        "https://gamejoin.roblox.com/v1/join-game",
        data=payload,
        headers=join_headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_join, timeout=6) as res_j:
            # 200 OK -> game-join thành công, tài khoản sạch hoàn toàn!
            pass
    except urllib.error.HTTPError as e:
        chal_type = (e.headers.get("rblx-challenge-type") or "").lower()
        chal_id = e.headers.get("rblx-challenge-id") or ""
        chal_meta = e.headers.get("rblx-challenge-metadata") or ""
        raw_body = e.read().decode('utf-8', errors='ignore')
        err_body = raw_body.lower()

        # Nếu 403 do cần token mới thì thử lại 1 lần với token mới
        if e.code == 403 and (e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")) and not chal_type:
            new_csrf = e.headers.get("x-csrf-token") or e.headers.get("X-CSRF-TOKEN")
            join_headers["x-csrf-token"] = new_csrf
            join_headers["X-CSRF-TOKEN"] = new_csrf
            req_retry = urllib.request.Request(
                "https://gamejoin.roblox.com/v1/join-game",
                data=payload,
                headers=join_headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req_retry, timeout=6) as res_r:
                    pass
            except urllib.error.HTTPError as e2:
                chal_type = (e2.headers.get("rblx-challenge-type") or "").lower()
                chal_id = e2.headers.get("rblx-challenge-id") or ""
                chal_meta = e2.headers.get("rblx-challenge-metadata") or ""
                raw_body = e2.read().decode('utf-8', errors='ignore')
                err_body = raw_body.lower()

        if "moderated" in err_body:
            return {
                "status": "NOT_APPROVED",
                "badge": "Kẹt Not-Approved / Kiểm Duyệt",
                "color": R,
                "user_id": user_id,
                "username": username or "N/A",
                "message": "Tài khoản đang bị kiểm duyệt (User is moderated)!"
            }
        is_press_and_hold = (
            any(k in err_body for k in ["nhấn giữ nút", "nhấn và giữ", "press and hold", "press & hold", "người thật", "human", "reference id", "id tham chiếu"]) or
            any(k in chal_type for k in ["security", "generic", "proof-of-work", "press", "hold"])
        )
        if is_press_and_hold:
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha 'Nhấn và Giữ' (Bảo Mật)",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "PRESS_AND_HOLD",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'security'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn vào game (join-game 403) yêu cầu vượt qua màn hình Bảo Mật 'Nhấn và Giữ' (ID tham chiếu: {chal_id or 'N/A'})!"
            }
        elif "twostepverification" in chal_type or "two-step" in err_body:
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Yêu Cầu Xác Minh 2FA",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "TWO_STEP_VERIFICATION",
                "challenge_id": chal_id,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type}, body={raw_body.strip()[:150]}",
                "message": "Roblox yêu cầu xác minh 2 bước trước khi vào game!"
            }
        elif "captchav2" in chal_type or ("captchav2" in chal_meta.lower() if chal_meta else False):
            meta_json = {}
            if chal_meta:
                try:
                    meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                except:
                    pass
            action_type = meta_json.get("actionType", "JoinGame") if isinstance(meta_json, dict) else "JoinGame"
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha V2 Vào Game",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "CAPTCHAV2",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "meta_data": meta_json,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captchav2'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn vào game (join-game HTTP 403, challenge_type=captchav2) và yêu cầu giải Captcha V2 (Action: {action_type}, ID: {chal_id or 'N/A'})!"
            }
        elif "captcha" in chal_type or "arkose" in chal_type or "captcha" in err_body or "funcaptcha" in err_body or "challenge is required" in err_body:
            meta_json = {}
            if chal_meta:
                try:
                    meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                except:
                    pass
            action_type = meta_json.get("actionType", "JoinGame") if isinstance(meta_json, dict) else "JoinGame"
            hybrid_challenge_url = ""
            if chal_id:
                ch_params = {
                    "generic-challenge-type": "captcha",
                    "app-type": "browser",
                    "generic-challenge-id": chal_id,
                    "challenge-metadata-json": chal_meta or "",
                    "challenge-type": "generic",
                    "dark-mode": "false"
                }
                hybrid_challenge_url = "https://www.roblox.com/challenge/cdn/hybrid?" + urllib.parse.urlencode(ch_params)
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": "Dính Captcha V1 (Arkose FunCaptcha)",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": "CAPTCHA_V1",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "challenge_url": hybrid_challenge_url,
                "meta_data": meta_json,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captcha'}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn vào game (join-game HTTP 403, challenge_type={chal_type or 'captcha'}) và yêu cầu giải Captcha V1 (Arkose FunCaptcha, Action: {action_type}, ID: {chal_id or 'N/A'})!"
            }
        elif chal_id or chal_type or chal_meta:
            return {
                "status": "CAPTCHA_CHECKPOINT",
                "badge": f"Dính Checkpoint Bảo Mật ({chal_type or 'Challenge'})",
                "color": Y,
                "user_id": user_id,
                "username": username or "N/A",
                "challenge_type": chal_type or "CHALLENGE",
                "challenge_id": chal_id,
                "challenge_meta": chal_meta,
                "raw_response": f"HTTP {e.code}, challenge_type={chal_type}, body={raw_body.strip()[:150]}",
                "message": f"Roblox chặn vào game (join-game 403) và kích hoạt Thử Thách Bảo Mật (ID tham chiếu: {chal_id or 'N/A'})!"
            }
    except Exception:
        pass

    # 5. Kiểm tra dự phòng qua POST https://auth.roblox.com/v1/authentication-ticket/
    if csrf_token:
        try:
            req_ticket = urllib.request.Request(
                "https://auth.roblox.com/v1/authentication-ticket/",
                data=b"{}",
                headers=join_headers,
                method="POST"
            )
            with urllib.request.urlopen(req_ticket, timeout=6) as res_t:
                pass
        except urllib.error.HTTPError as e:
            chal_type = (e.headers.get("rblx-challenge-type") or "").lower()
            chal_id = e.headers.get("rblx-challenge-id") or ""
            chal_meta = e.headers.get("rblx-challenge-metadata") or ""
            raw_body = e.read().decode('utf-8', errors='ignore')
            err_body = raw_body.lower()

            if "moderated" in err_body:
                return {
                    "status": "NOT_APPROVED",
                    "badge": "Kẹt Not-Approved / Kiểm Duyệt",
                    "color": R,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "message": "Tài khoản đang bị kiểm duyệt (User is moderated)!"
                }
            is_press_and_hold = (
                any(k in err_body for k in ["nhấn giữ nút", "nhấn và giữ", "press and hold", "press & hold", "người thật", "human", "reference id", "id tham chiếu"]) or
                any(k in chal_type for k in ["security", "generic", "proof-of-work", "press", "hold"])
            )
            if is_press_and_hold:
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": "Dính Captcha 'Nhấn và Giữ' (Bảo Mật)",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "challenge_type": "PRESS_AND_HOLD",
                    "challenge_id": chal_id,
                    "challenge_meta": chal_meta,
                    "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'security'}, body={raw_body.strip()[:150]}",
                    "message": f"Roblox chặn sinh Ticket và yêu cầu vượt qua màn hình Bảo Mật 'Nhấn và Giữ' (ID tham chiếu: {chal_id or 'N/A'})!"
                }
            elif "captchav2" in chal_type or ("captchav2" in chal_meta.lower() if chal_meta else False):
                meta_json = {}
                if chal_meta:
                    try:
                        meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                    except:
                        pass
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": "Dính Captcha V2 Vào Game",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "challenge_type": "CAPTCHAV2",
                    "challenge_id": chal_id,
                    "challenge_meta": chal_meta,
                    "meta_data": meta_json,
                    "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captchav2'}, body={raw_body.strip()[:150]}",
                    "message": f"Roblox chặn sinh Ticket vào game (challenge_type=captchav2) và yêu cầu giải Captcha V2 (ID: {chal_id or 'N/A'})!"
                }
            elif "captcha" in chal_type or "arkose" in chal_type or "captcha" in err_body or "challenge is required" in err_body:
                meta_json = {}
                if chal_meta:
                    try:
                        meta_json = json.loads(base64.b64decode(chal_meta).decode('utf-8', errors='ignore'))
                    except:
                        pass
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": "Dính Captcha V1 (Arkose FunCaptcha)",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "challenge_type": "CAPTCHA_V1",
                    "challenge_id": chal_id,
                    "challenge_meta": chal_meta,
                    "meta_data": meta_json,
                    "raw_response": f"HTTP {e.code}, challenge_type={chal_type or 'captcha'}, body={raw_body.strip()[:150]}",
                    "message": f"Roblox chặn sinh Ticket vào game (challenge_type={chal_type or 'captcha'}) và yêu cầu giải Captcha V1 (Arkose FunCaptcha, ID: {chal_id or 'N/A'})!"
                }
            elif chal_id or chal_type or chal_meta:
                return {
                    "status": "CAPTCHA_CHECKPOINT",
                    "badge": f"Dính Checkpoint Bảo Mật ({chal_type or 'Challenge'})",
                    "color": Y,
                    "user_id": user_id,
                    "username": username or "N/A",
                    "challenge_type": chal_type or "CHALLENGE",
                    "challenge_id": chal_id,
                    "challenge_meta": chal_meta,
                    "raw_response": f"HTTP {e.code}, challenge_type={chal_type}, body={raw_body.strip()[:150]}",
                    "message": f"Roblox chặn sinh Ticket và kích hoạt Thử Thách Bảo Mật (ID tham chiếu: {chal_id or 'N/A'})!"
                }
        except Exception:
            pass

    if user_id:
        return {
            "status": "OK",
            "badge": "Bình Thường (Tài khoản Sạch)",
            "color": G,
            "user_id": user_id,
            "username": username,
            "display_name": display_name,
            "message": f"Tài khoản [{username}] hoàn toàn sạch, join game tốt, không bị Captcha hay Not-Approved!"
        }

    return {
        "status": "UNKNOWN",
        "badge": "Không Thể Kiểm Tra",
        "color": Y,
        "user_id": None,
        "username": None,
        "message": "Không thể kết nối đến máy chủ Roblox hoặc mạng bị chặn."
    }

def safe_uiautomator_dump(timeout=5):
    """
    Dump giao diện Android an toàn, có timeout nghiêm ngặt và tự dọn tiến trình uiautomator rác nếu bị treo.
    Trả về (True, xml_string) hoặc (False, "").
    """
    dump_file = f"/data/local/tmp/dump_cap_{os.getpid()}.xml"
    _run_root_capture(f"rm -f '{dump_file}' 2>/dev/null", timeout=2)
    code, _, err = _run_root_capture(f"uiautomator dump '{dump_file}' 2>/dev/null", timeout=timeout)
    if code != 0 or "timeout" in str(err).lower():
        # Dọn dẹp triệt để tiến trình uiautomator rác nếu bị nghẽn hệ thống tránh treo máy
        _run_root_capture("killall -9 uiautomator 2>/dev/null || pkill -9 uiautomator 2>/dev/null", timeout=2)
        return False, ""

    code_cat, xml_str, _ = _run_root_capture(f"cat '{dump_file}' 2>/dev/null", timeout=3)
    _run_root_capture(f"rm -f '{dump_file}' 2>/dev/null", timeout=2)
    if code_cat == 0 and xml_str:
        return True, xml_str
    return False, ""

# Danh sách từ khóa Đa Ngôn Ngữ cho Captcha V2 (Nhấn và Giữ / Press and Hold / Security Challenge)
V2_HOLD_KEYWORDS = [
    # Tiếng Việt
    "nhấn và giữ", "nhấn giữ nút", "nhấn giữ", "chạm và giữ", "giữ nút",
    # Tiếng Anh
    "press and hold", "press & hold", "touch and hold", "tap and hold", "hold button",
    # Tiếng Tây Ban Nha (Spanish)
    "mantén presionado", "mantener presionado", "presione y mantenga", "toca y mantén",
    # Tiếng Bồ Đào Nha (Portuguese)
    "pressione e segure", "toque e segure", "mantenha pressionado",
    # Tiếng Pháp (French)
    "appuyez et maintenez", "maintenez enfoncé", "touchez et maintenez",
    # Tiếng Đức (German)
    "gedrückt halten", "drücken und halten", "berühren und halten",
    # Tiếng Nga (Russian)
    "нажмите и удерживайте", "нажмите и держите", "удерживайте",
    # Tiếng Indonesia / Malaysia
    "tekan dan tahan", "sentuh dan tahan",
    # Tiếng Thổ Nhĩ Kỳ (Turkish)
    "basılı tutun", "dokunun ve basılı tutun",
    # Tiếng Ý (Italian)
    "tieni premuto", "premi e tieni premuto",
    # Tiếng Ba Lan (Polish)
    "naciśnij i przytrzymaj", "dotknij i przytrzymaj",
    # Tiếng Nhật (Japanese)
    "長押し", "長押しして確認",
    # Tiếng Hàn (Korean)
    "길게 누르기", "길게 눌러", "길게 눌러 확인",
    # Tiếng Trung (Giản thể & Phồn thể)
    "按住", "按住以确认", "按住以確認", "长按", "長按",
    # Tiếng Thái (Thai)
    "กดค้างไว้", "แตะค้างไว้",
    # Tiếng Ả Rập (Arabic)
    "اضغط مع الاستمرار",
    # Tiếng Hindi
    "दबाकर रखें"
]

V2_CHALLENGE_HEADERS = [
    # Tiếng Việt
    "xác nhận bạn là người thật", "chứng minh bạn là người thật", "bảo mật", "thử thách bảo mật",
    # Tiếng Anh
    "security challenge", "confirm you are human", "confirm that you are human", "prove you are human",
    # Tiếng Tây Ban Nha
    "desafío de seguridad", "confirma que eres humano", "confirmar que eres humano",
    # Tiếng Bồ Đào Nha
    "desafio de segurança", "confirme que você é humano", "confirme que é humano",
    # Tiếng Pháp
    "défi de sécurité", "confirmez que vous êtes un humain",
    # Tiếng Đức
    "sicherheitsüberprüfung", "bestätigen sie, dass sie ein mensch sind",
    # Tiếng Nga
    "проверка безопасности", "подтвердите, что вы человек",
    # Tiếng Indonesia
    "tantangan keamanan", "konfirmasi bahwa anda là manusia", "konfirmasi bahwa anda adalah manusia",
    # Tiếng Thổ Nhĩ Kỳ
    "güvenlik sorgusu", "güvenlik doğrulaması", "insan olduğunuzu doğrulayın",
    # Tiếng Ý
    "sfida di sicurezza", "conferma che sei umano",
    # Tiếng Ba Lan
    "weryfikacja zabezpieczeń", "potwierdź, że jesteś człowiekiem",
    # Tiếng Nhật
    "セキュリティ認証", "人間であることを確認",
    # Tiếng Hàn
    "보안 챌린지", "사람임을 확인",
    # Tiếng Trung
    "安全验证", "安全驗證", "确认你是真人", "確認你是真人",
    # Tiếng Thái
    "การทดสอบความปลอดภัย", "ยืนยันว่าคุณเป็นมนุษย์",
    # Tiếng Ả Rập
    "تحدي الأمان", "تأكيد أنك إنسان"
]

def detect_in_app_captcha(pkg=None, auto_solve_v2=False, attempt=1):
    """
    Quét màn hình Android hỗ trợ ĐA NGÔN NGỮ (bằng uiautomator dump an toàn, chống treo máy):
    - Nhận diện Captcha V1 (Arkose FunCaptcha, vòng xoay, ghép hình, challenge dialog/webview)
    - Nhận diện Captcha V2 ('Nhấn và Giữ' / 'Security Challenge') với MỌI ngôn ngữ (Anh, Việt, TBN, BĐN, Pháp, Đức, Nga, Nhật, Hàn, Trung, Thái...)
    
    Trả về dict:
      detected: bool
      type: 'CAPTCHA_V1' | 'CAPTCHAV2' | None
      badge: str
      ref_id: str
      btn_coords: (cx, cy) nếu có nút V2
      solved: bool (nếu auto_solve_v2=True)
    """
    try:
        ok, xml_str = safe_uiautomator_dump(timeout=5)
        if not ok or not xml_str:
            return {"detected": False, "type": None}

        xml_lower = xml_str.lower()

        # 1. KIỂM TRA CAPTCHA V1 (Arkose FunCaptcha / Challenge Puzzle)
        keywords_v1 = [
            "rotate", "match the", "pick the", "xoay hình", "chọn hình", "mũi tên",
            "xác thực hình ảnh", "funcaptcha", "arkoselabs", "api.arkoselabs.com",
            "solve this puzzle", "vui lòng giải", "please solve this challenge",
            "challenge-container", "roblox.com/challenge", "thử thách bảo mật",
            "xác minh bạn là người", "chứng minh bạn không phải là rô-bốt",
            "prove you're human", "challenge-frame"
        ]
        is_v1 = any(k in xml_lower for k in keywords_v1)

        # 2. KIỂM TRA CAPTCHA V2 ĐA NGÔN NGỮ (Nhấn và Giữ / Press and Hold / Security Challenge)
        has_hold_action = any(k in xml_lower for k in V2_HOLD_KEYWORDS)
        has_challenge_hdr = any(k in xml_lower for k in V2_CHALLENGE_HEADERS)
        
        # Nhận diện Reference ID (Đa ngôn ngữ & UUID chuẩn)
        ref_patterns = [
            r'(?:id tham chiếu|reference id|id de referencia|id de référence|referenz-id|id di riferimento|referans kimliği|id referensi|참조 id|参照 id|参考 id|參考 id|รหัสอ้างอิง|ref id)[:\s]*([a-f0-9\-]+)',
            r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        ]
        ref_id = "N/A"
        for pat in ref_patterns:
            ref_m = re.search(pat, xml_str, re.I)
            if ref_m:
                ref_id = ref_m.group(1)
                break

        has_ref_id = (ref_id != "N/A")
        
        # Điều kiện phát hiện V2:
        # - Hoặc có từ khóa hành động Nhấn Giữ (bất kỳ ngôn ngữ nào)
        # - Hoặc có tiêu đề bảo mật + (có ref_id HOẶC từ khóa người thật)
        # - Hoặc có ref_id + (challenge / security / arkose)
        is_v2 = (
            has_hold_action or
            (has_challenge_hdr and (has_ref_id or "human" in xml_lower or "người thật" in xml_lower or "humano" in xml_lower)) or
            (has_ref_id and any(k in xml_lower for k in ["challenge", "bảo mật", "security", "arkose", "roblox"]))
        )

        if is_v2:
            btn_coords = None
            try:
                root = ET.fromstring(xml_str)
                candidates = []
                w_scr, h_scr = get_screen_resolution()
                
                for node in root.iter('node'):
                    text = (node.get('text') or '').strip()
                    desc = (node.get('content-desc') or '').strip()
                    cls = (node.get('class') or '').strip()
                    bounds = node.get('bounds') or ''
                    m_b = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if not m_b:
                        continue
                    x1, y1, x2, y2 = map(int, m_b.groups())
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    bw = x2 - x1
                    bh = y2 - y1
                    combined = f"{text} {desc}".lower().strip()

                    # Bỏ qua các text mô tả hướng dẫn/tiêu đề dài (> 40 chars)
                    if len(combined) > 40 and any(k in combined for k in ["xác nhận", "confirm", "human", "người thật", "tham chiếu", "reference"]):
                        continue

                    score = 0
                    # 1. Khớp chính xác từ khóa Nhấn Giữ đa ngôn ngữ:
                    if any(k in combined for k in V2_HOLD_KEYWORDS):
                        score += 100
                        if "button" in cls.lower() or node.get('clickable') == 'true':
                            score += 30
                    # 2. Clickable Button nằm ở vùng trung tâm (khu vực nút bấm chuẩn)
                    elif ("button" in cls.lower() or node.get('clickable') == 'true') and bh >= 35 and bw >= 80:
                        y_ratio = cy / max(1, h_scr)
                        x_ratio = cx / max(1, w_scr)
                        if 0.35 <= y_ratio <= 0.75 and 0.25 <= x_ratio <= 0.75:
                            score += 60
                            if 100 <= bw <= 700 and 40 <= bh <= 200:
                                score += 20
                        else:
                            score += 15

                    if score > 0:
                        candidates.append((score, cx, cy))

                if candidates:
                    candidates.sort(key=lambda c: c[0], reverse=True)
                    btn_coords = (candidates[0][1], candidates[0][2])
            except Exception:
                pass

            # Fallback 1: Regex quét bounds trực tiếp từ từ khóa đa ngôn ngữ
            if not btn_coords:
                for kw in ["nhấn và giữ", "nhấn giữ", "press and hold", "press & hold", "touch and hold", "mantén presionado", "pressione e segure", "appuyez et maintenez", "gedrückt halten", "нажмите и удерживайте", "tekan dan tahan", "basılı tutun", "長押し", "길게 누르기", "按住", "กดค้างไว้"]:
                    kw_esc = re.escape(kw)
                    pat1 = rf'(?:text|content-desc)="[^"]*{kw_esc}[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                    m = re.search(pat1, xml_str, re.I)
                    if not m:
                        pat2 = rf'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*(?:text|content-desc)="[^"]*{kw_esc}[^"]*"'
                        m = re.search(pat2, xml_str, re.I)
                    if m:
                        x1, y1, x2, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                        btn_coords = ((x1 + x2) // 2, (y1 + y2) // 2)
                        break

            # Fallback 2: Tính toán tọa độ theo tỷ lệ màn hình (tối ưu cho cả ngang và dọc)
            if not btn_coords or attempt > 1:
                w, h = get_screen_resolution()
                is_landscape = (w >= h)
                if attempt == 1:
                    btn_coords = (w // 2, int(h * 0.52)) if is_landscape else (w // 2, int(h * 0.45))
                elif attempt == 2:
                    btn_coords = (w // 2, int(h * 0.62)) if is_landscape else (w // 2, int(h * 0.55))
                else:
                    btn_coords = (w // 2, int(h * 0.38)) if is_landscape else (w // 2, int(h * 0.35))

            solved = False
            if auto_solve_v2 and btn_coords:
                cx, cy = btn_coords
                add_log(f"[{pkg[-12:] if pkg else 'BẢO MẬT'}] {Y}Phát hiện 'Nhấn và Giữ' (Ref: {ref_id[:8]}.., Lần {attempt})! Đang giữ nút ({cx}, {cy}) 16s...{RESET}")
                safe_root(f"su -c 'input tap {cx} {cy}'", timeout=3)
                time.sleep(0.3)
                safe_root(f"su -c 'input swipe {cx} {cy} {cx} {cy} 16000'", timeout=20)
                time.sleep(2.5)

                ok_chk, chk_xml = safe_uiautomator_dump(timeout=5)
                if ok_chk and chk_xml:
                    chk_lower = chk_xml.lower()
                    still_has = any(k in chk_lower for k in V2_HOLD_KEYWORDS) or any(k in chk_lower for k in V2_CHALLENGE_HEADERS)
                    if not still_has:
                        solved = True
                        add_log(f"[{pkg[-12:] if pkg else 'BẢO MẬT'}] {G}[✓] Đã giữ 16s thành công vượt qua màn hình 'Nhấn và Giữ'!{RESET}")
                else:
                    # Màn hình UI đã đóng/chuyển tab -> Giải thành công
                    solved = True
                    add_log(f"[{pkg[-12:] if pkg else 'BẢO MẬT'}] {G}[✓] Màn hình bảo mật đã tắt!{RESET}")

            return {
                "detected": True,
                "type": "CAPTCHAV2",
                "badge": "Dính Captcha 'Nhấn và Giữ' (Bảo Mật)",
                "ref_id": ref_id,
                "btn_coords": btn_coords,
                "solved": solved
            }

        elif is_v1:
            return {
                "detected": True,
                "type": "CAPTCHA_V1",
                "badge": "Dính Captcha V1 (Arkose FunCaptcha) Trong App",
                "ref_id": ref_id,
                "solved": False
            }

        return {"detected": False, "type": None}
    except Exception:
        return {"detected": False, "type": None}

def solve_captchav2_in_app(pkg, states=None):
    """
    Quy trình tự động giải Captcha V2 ('Nhấn và Giữ' / 'Press and Hold') đa ngôn ngữ:
    1. Khởi động app Roblox một cách mượt mà (không văng, không lặp).
    2. Chờ 10s ban đầu cho splash screen load xong.
    3. Polling liên tục tới 30s để chờ màn hình 'Nhấn và Giữ' (Security Challenge) hiển thị đầy đủ.
    4. Khi màn hình xuất hiện, tự động quét tìm nút và giữ 16 giây.
    5. Kiểm tra lại và xác nhận bằng API cookie để đảm bảo acc đã sạch 100%.
    """
    if not pkg:
        return False

    add_log(f"[{pkg[-12:]}] {Y}[AUTO CAPTCHA V2] Đang mở app và chờ màn hình 'Nhấn và Giữ' xuất hiện...{RESET}")
    launch_roblox_to_game(pkg)
    time.sleep(10)

    # Polling tìm màn hình Captcha V2 trong tối đa 30s (10 chu kỳ * 3s)
    v2_detected = False
    for poll_step in range(1, 11):
        if not is_app_running(pkg):
            launch_roblox_to_game(pkg)
            time.sleep(4)

        cap_res = detect_in_app_captcha(pkg, auto_solve_v2=False)
        if cap_res.get("detected") and cap_res.get("type") == "CAPTCHAV2":
            v2_detected = True
            add_log(f"[{pkg[-12:]}] {G}[CAPTCHA V2] Đã phát hiện màn hình 'Nhấn và Giữ' (sau {10 + poll_step*3}s)! Bắt đầu giải...{RESET}")
            break
        elif cap_res.get("detected") and cap_res.get("type") == "CAPTCHA_V1":
            add_log(f"[{pkg[-12:]}] {R}[CAPTCHA V1] Phát hiện câu đố Arkose (không thể tự giải), tắt app chờ...{RESET}")
            _kill_pkg(pkg)
            return False
            
        time.sleep(3)

    if not v2_detected:
        cookie = extract_roblox_cookie(pkg)
        if cookie:
            try:
                res = check_roblox_account_status(cookie)
                if res.get('status') == 'OK':
                    add_log(f"[{pkg[-12:]}] {G}[✓ CAPTCHA V2] Kiểm tra API: Acc đã sạch hoàn toàn!{RESET}")
                    if states and pkg in states:
                        states[pkg]['is_blocked'] = False
                        states[pkg]['captcha_type'] = None
                        states[pkg]['block_reason'] = ''
                        states[pkg]['text'] = 'Acc Sạch -> Rejoin'
                        states[pkg]['color'] = G
                    return True
            except:
                pass
        add_log(f"[{pkg[-12:]}] {Y}[CAPTCHA V2] Hết 30s chưa thấy nút hiển thị, tạm tắt app chờ chu kỳ sau ({CHECK_ACC_TIME_BLOCKED}s)...{RESET}")
        _kill_pkg(pkg)
        return False

    # Khi đã phát hiện màn hình Captcha V2, thử nhấn giữ 16s tối đa 3 lần
    for attempt in range(1, 4):
        solve_res = detect_in_app_captcha(pkg, auto_solve_v2=True, attempt=attempt)
        if solve_res.get("solved"):
            add_log(f"[{pkg[-12:]}] {G}[✓ CAPTCHA V2] Đã giữ nút 16s thành công lần {attempt}! Acc đã sạch.{RESET}")
            if states and pkg in states:
                states[pkg]['is_blocked'] = False
                states[pkg]['captcha_type'] = None
                states[pkg]['block_reason'] = ''
                states[pkg]['text'] = 'Đã Giải V2 -> Vào Game'
                states[pkg]['color'] = G
            return True
        else:
            add_log(f"[{pkg[-12:]}] {Y}[!] Giữ nút lần {attempt} chưa vượt qua, đang thử lại với tọa độ mới...{RESET}")
            time.sleep(3)

    add_log(f"[{pkg[-12:]}] {R}[CAPTCHA V2] Đã thử giữ nút 3 lần chưa thành công. Tắt app chờ chu kỳ sau ({CHECK_ACC_TIME_BLOCKED}s)...{RESET}")
    _kill_pkg(pkg)
    return False

# Giữ tương thích ngược với code cũ gọi detect_press_and_hold_screen
detect_press_and_hold_screen = detect_in_app_captcha

def print_account_check_result(label, cookie, res):
    mask_c = (cookie[:18] + "..." + cookie[-10:]) if (cookie and len(cookie) > 30) else (cookie or "<Trống>")
    print(f"\n{C}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{Y}ĐỐI TƯỢNG:{RESET}  {W}{label}{RESET}")
    print(f"{Y}COOKIE:{RESET}    {mask_c}")
    if res.get('username'):
        print(f"{Y}ACC NAME:{RESET}  {G}{res['username']}{RESET} (ID: {res.get('user_id', 'N/A')})")
    col = res.get('color', Y)
    print(f"{Y}KẾT QUẢ:{RESET}   {col}[{res.get('badge', 'N/A')}]{RESET}")
    print(f"{Y}CHI TIẾT:{RESET}  {res.get('message', '')}")
    if res.get('challenge_id'):
        print(f"{Y}ID THAM CHIẾU (CHALLENGE ID):{RESET} {C}{res['challenge_id']}{RESET}")
    if res.get('challenge_type'):
        print(f"{Y}LOẠI THỬ THÁCH:{RESET}               {C}{res['challenge_type']}{RESET}")
    if res.get('raw_response'):
        print(f"{Y}TÍN HIỆU DEBUG:{RESET}               {M}[DBG] {res['raw_response']}{RESET}")
    if res.get('meta_data'):
        try:
            print(f"{Y}CHALLENGE METADATA:{RESET}           {W}{json.dumps(res['meta_data'], ensure_ascii=False)}{RESET}")
        except:
            pass
    if res.get('url'):
        print(f"{Y}URL KẸT:{RESET}   {C}{res['url']}{RESET}")

def handle_not_approved_in_app(pkg=None):
    """Tự động kiểm tra và bấm nút Đồng ý / Tôi hiểu / Reactivate trực tiếp trong app Roblox."""
    time.sleep(2.0)
    ok, xml_str = safe_uiautomator_dump(timeout=5)
    if not ok or not xml_str:
        return False

    xml_lower = xml_str.lower()
    btn_keywords = ["tôi hiểu", "i understand", "tôi đồng ý", "i agree", "reactivate", "kích hoạt lại", "đồng ý", "tiếp tục", "continue", "chấp nhận", "accept", "ok"]
    try:
        root = ET.fromstring(xml_str)
        for node in root.iter('node'):
            t = (node.get('text') or node.get('content-desc') or '').strip().lower()
            if any(k in t for k in btn_keywords):
                bounds = node.get('bounds') or ''
                m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    add_log(f"[{pkg[-12:] if pkg else 'IN-APP'}] {G}[NOT-APPROVED] Tự động bấm nút '{t}' tại ({cx}, {cy}) để kích hoạt lại acc!{RESET}")
                    safe_root(f"su -c 'input tap {cx} {cy}'")
                    time.sleep(2)
                    return True
    except:
        pass
    return False

def check_and_handle_account_health(pkg, states, current_time, force=False):
    """
    Kiểm tra trạng thái tài khoản qua Cookie trong app Roblox:
    - Nếu acc bị dính lỗi (NOT_APPROVED, CAPTCHA_CHECKPOINT, EXPIRED):
        + Cập nhật state: is_blocked=True, text, color, block_reason
        + Ghi add_log chi tiết cảnh báo
        + Dừng process app để không tốn tài nguyên và tuyệt đối KHÔNG vào game
        + Trả về True (bị block)
    - Nếu acc bình thường (OK hoặc không tìm thấy cookie / lỗi mạng tạm thời):
        + Cập nhật state: is_blocked=False
        + Trả về False (cho phép chạy / vào game bình thường)
    """
    global AUTO_CHECK_ACC_HEALTH
    if AUTO_CHECK_ACC_HEALTH != "Enable":
        return False

    state = states.get(pkg)
    if not state:
        return False

    # BẢO VỆ (chỉ áp dụng khi KHÔNG force):
    if not force:
        if state.get('in_game'):
            return False
        bound = state.get('bound_name')
        if bound:
            hb = get_heartbeat(bound, pkg)
            if hb != -1 and (current_time - hb <= 120):
                state['in_game'] = True
                return False

    cookie = extract_roblox_cookie(pkg)
    if not cookie:
        cookie = state.get('cached_cookie')
    else:
        # Nếu phát hiện cookie mới khác cookie cũ trong cache -> người dùng vừa đăng nhập acc mới
        if state.get('cached_cookie') and state['cached_cookie'] != cookie:
            add_log(f"[{pkg[-12:]}] {G}[ĐỔI ACC] Phát hiện tài khoản mới! Đang đồng bộ...{RESET}")
            state['is_blocked'] = False
            state['block_reason'] = ''
            state['bound_name'] = None
            state['display_name'] = 'Đang đồng bộ...'

    state['last_acc_check'] = current_time
    if not cookie:
        return False
    state['cached_cookie'] = cookie

    try:
        res = check_roblox_account_status(cookie)
    except Exception:
        return False

    status = res.get('status')
    state['account_status'] = status

    # Luôn cập nhật tên hiển thị mới nhất theo kết quả trả về từ API
    if res.get('username'):
        state['bound_name'] = res['username']
        state['display_name'] = res['username']

    if status == 'NOT_APPROVED':
        state['is_blocked'] = True
        state['in_game'] = False
        badge = res.get('badge', 'Kẹt Not-Approved / Cần Duyệt')
        state['block_reason'] = badge
        state['text'] = "Kẹt Not-Approved"
        state['color'] = R
        msg_detail = res.get('message', '')
        add_log(f"[{pkg[-12:]}] {R}[CẢNH BÁO COOKIE] {badge}: {msg_detail}{RESET}")
        _kill_pkg(pkg)
        time.sleep(1)
        launch_roblox_to_game(pkg)
        handle_not_approved_in_app(pkg)
        return True
    elif status == 'EXPIRED':
        state['is_blocked'] = True
        state['in_game'] = False
        badge = res.get('badge', 'Cookie Die (401)')
        state['block_reason'] = badge
        state['text'] = "Cookie Die (401)"
        state['color'] = R
        msg_detail = res.get('message', '')
        add_log(f"[{pkg[-12:]}] {R}[CẢNH BÁO COOKIE] {badge}: {msg_detail}{RESET}")
        _kill_pkg(pkg)
        return True
    elif status == 'CAPTCHA_CHECKPOINT':
        badge = res.get('badge', 'Dính Captcha')
        chal_type = res.get('challenge_type', '')
        msg_detail = res.get('message', '')

        state['in_game'] = False
        state['is_blocked'] = True
        state['block_reason'] = badge
        # TẮT NGAY TIẾN TRÌNH APP: TUYỆT ĐỐI KHÔNG VÀO GAME KHI DÍNH CAPTCHA!
        if is_app_running(pkg):
            _kill_pkg(pkg)

        if chal_type in ['CAPTCHA_V1', 'ARKOSE_CAPTCHA'] or "V1" in badge or "Arkose" in badge:
            state['captcha_type'] = 'CAPTCHA_V1'
            state['text'] = "Chờ Cookie Sạch (V1)"
            state['color'] = Y
            add_log(f"[{pkg[-12:]}] {Y}[CẢNH BÁO COOKIE] {badge}: {msg_detail}{RESET}")
            add_log(f"[{pkg[-12:]}] {Y}[CAPTCHA V1] Không vào game! Đã tắt app, chờ đến khi Cookie sạch lại sẽ tự Rejoin...{RESET}")
            return True
        else:
            state['captcha_type'] = 'CAPTCHAV2'
            add_log(f"[{pkg[-12:]}] {Y}[CẢNH BÁO COOKIE] {badge}: {msg_detail}{RESET}")
            if AUTO_SOLVE_CAPTCHA_V2 == "Enable":
                state['text'] = "Tự Giải Captcha V2..."
                state['color'] = Y
                add_log(f"[{pkg[-12:]}] {G}[CAPTCHA V2] Đang tự động giải Captcha V2 (Nhấn và Giữ đa ngôn ngữ)...{RESET}")
                ok_v2 = solve_captchav2_in_app(pkg, states)
                if ok_v2:
                    state['is_blocked'] = False
                    state['block_reason'] = ''
                    state['text'] = "Đã Giải V2 -> Rejoin"
                    state['color'] = G
                    return False  # Đã giải xong, cho phép tiếp tục vào game!
                else:
                    state['is_blocked'] = True
                    state['text'] = "Dính Captcha V2 (Chờ)"
                    state['color'] = Y
                    return True
            else:
                state['is_blocked'] = True
                state['text'] = "Dính Captcha V2 (Chờ)"
                state['color'] = Y
                add_log(f"[{pkg[-12:]}] {Y}[CAPTCHA V2] Auto Solve đang Tắt, tạm dừng chờ kiểm tra lại...{RESET}")
                return True
    elif status == 'OK':
        if state.get('is_blocked'):
            state['is_blocked'] = False
            state['block_reason'] = ''
            u_name = res.get('username') or state.get('bound_name') or 'Acc'
            add_log(f"[{pkg[-12:]}] {G}[ACC SẠCH] Acc {u_name} ĐÃ BÌNH THƯỜNG! Đang Rejoin vào game...{RESET}")
            with pkg_restart_locks[pkg]:
                force_restart_app(pkg, states, current_time, "Acc Sạch -> Rejoin", G)
            return False
        return False

    return False

def account_captcha_check_menu():
    global selected_packages
    while True:
        clear_screen()
        print_banner()
        print(f"{C}=== KIỂM TRA TRẠNG THÁI ACC / CAPTCHA / NOT-APPROVED (TEST) ==={RESET}")
        print(f"[{C}1{RESET}] Kiểm tra các Package ĐANG ĐƯỢC CHỌN (trong Mục [1])")
        print(f"[{C}2{RESET}] Quét TẤT CẢ Package Roblox trên máy và kiểm tra từng Acc")
        print(f"[{C}3{RESET}] Nhập trực tiếp chuỗi Cookie để test ngay")
        print(f"[{C}4{RESET}] Quét MÀN HÌNH App Roblox phát hiện Captcha V1 / V2 (Chống treo máy)")
        print(f"[{C}5{RESET}] Cấu hình / Nhập OMOCaptcha API Key (Key: {G}{mask_secret(OMOCAPTCHA_KEY)}{RESET})")
        print(f"[{C}6{RESET}] Quay lại Menu chính")
        fix_tty()
        c = safe_input(f"\n{M}Chọn [1-6]: {RESET}").strip()
        if c == '1':
            if not selected_packages:
                print(f"\n{R}[!] Chưa chọn package nào ở Mục [1]!{RESET}")
                time.sleep(2)
                continue
            print(f"\n{Y}[*] Đang trích xuất cookie và kiểm tra {len(selected_packages)} package...{RESET}")
            for idx, item in enumerate(selected_packages, 1):
                pkg = item['pkg']
                cookie = extract_roblox_cookie(pkg)
                if not cookie:
                    res = {"status": "NO_COOKIE", "badge": "Không Tìm Thấy Cookie", "color": R, "message": "App chưa đăng nhập tài khoản hoặc không tìm thấy database cookie."}
                else:
                    res = check_roblox_account_status(cookie)
                print_account_check_result(f"Package #{idx}: {pkg}", cookie, res)
            fix_tty()
            print(f"\n{Y}Bấm Enter để tiếp tục...{RESET}")
            try: input()
            except: pass
        elif c == '2':
            all_pkgs = scan_packages()
            roblox_pkgs = [p for p in all_pkgs if any(k in p.lower() for k in ["roblox", "delta", "hydrogen", "arceus", "fluxus"])] or all_pkgs
            print(f"\n{Y}[*] Tìm thấy {len(roblox_pkgs)} package. Đang kiểm tra từng app...{RESET}")
            for idx, pkg in enumerate(roblox_pkgs, 1):
                cookie = extract_roblox_cookie(pkg)
                if not cookie:
                    res = {"status": "NO_COOKIE", "badge": "Không Tìm Thấy Cookie", "color": R, "message": "App chưa có phiên đăng nhập."}
                else:
                    res = check_roblox_account_status(cookie)
                print_account_check_result(f"[{idx}/{len(roblox_pkgs)}] {pkg}", cookie, res)
            fix_tty()
            print(f"\n{Y}Bấm Enter để tiếp tục...{RESET}")
            try: input()
            except: pass
        elif c == '3':
            fix_tty()
            cookies_in_file, f_path = load_cookies_from_download()
            raw_c = ""
            if cookies_in_file and f_path:
                print(f"\n{GREEN_MINT}[✓] Tìm thấy {len(cookies_in_file)} cookie trong file: {GOLD_NEON}{f_path}{RESET}")
                print(f"  [{C}1{RESET}] {BOLD}{G}Kiểm tra TẤT CẢ ({len(cookies_in_file)}) Cookie từ file cookie.txt{RESET} {DIM}(Nhấn Enter chọn ngay){RESET}")
                print(f"  [{C}2{RESET}] {W}Nhập / Dán Cookie thủ công bằng tay{RESET}")
                fix_tty()
                sub_opt = safe_input(f"\n{M}Chọn [1/2, mặc định 1]: {RESET}").strip()
                if sub_opt in ['', '1']:
                    print(f"\n{Y}[*] Đang gửi yêu cầu kiểm tra trạng thái {len(cookies_in_file)} Cookie tới Roblox API...{RESET}")
                    for idx_c, ck in enumerate(cookies_in_file, 1):
                        res = check_roblox_account_status(ck)
                        print_account_check_result(f"Cookie #{idx_c}/{len(cookies_in_file)} từ {os.path.basename(f_path)}", ck, res)
                    fix_tty()
                    print(f"\n{Y}Bấm Enter để tiếp tục...{RESET}")
                    try: input()
                    except: pass
                    continue
                else:
                    raw_c = safe_input(f"\n{M}Nhập Cookie Roblox (_|WARNING...): {RESET}").strip()
            else:
                raw_c = safe_input(f"\n{M}Nhập Cookie Roblox (_|WARNING...): {RESET}").strip()

            if not raw_c:
                print(f"{Y}[*] Đã hủy.{RESET}")
                time.sleep(1.5)
                continue
            print(f"\n{Y}[*] Đang gửi yêu cầu kiểm tra trạng thái tới Roblox API...{RESET}")
            res = check_roblox_account_status(raw_c)
            print_account_check_result("Kiểm tra Cookie thủ công", raw_c, res)
            fix_tty()
            print(f"\n{Y}Bấm Enter để tiếp tục...{RESET}")
            try: input()
            except: pass
        elif c == '4':
            print(f"\n{Y}[*] Đang quét màn hình thiết bị tìm popup Captcha V1 / V2 (Chống treo)...{RESET}")
            res = detect_in_app_captcha()
            if res.get("detected"):
                c_t = res.get("type")
                if c_t == "CAPTCHA_V1":
                    print(f"\n{R}╔═══════════════════════════════════════════════════════════╗{RESET}")
                    print(f"{R}║   [!] PHÁT HIỆN CAPTCHA V1 (ARKOSE PUZZLE) TRÊN APP!      ║{RESET}")
                    print(f"{R}╚═══════════════════════════════════════════════════════════╝{RESET}")
                    print(f"  • Loại:          {W}Arkose FunCaptcha (Vòng xoay/ghép hình){RESET}")
                    print(f"  • Trạng thái:    {Y}Không nên vào game lúc này để tránh kẹt.{RESET}")
                    print(f"  • Cơ chế:        {G}Tool sẽ tự động tắt app và chờ cookie sạch lại rồi tự Rejoin.{RESET}")
                elif c_t == "CAPTCHAV2":
                    print(f"\n{G}╔═══════════════════════════════════════════════════════════╗{RESET}")
                    print(f"{G}║   [✓] PHÁT HIỆN POPUP BẢO MẬT: 'NHẤN VÀ GIỮ' TRÊN APP!    ║{RESET}")
                    print(f"{G}╚═══════════════════════════════════════════════════════════╝{RESET}")
                    print(f"  • Tiêu đề:       {C}Bảo Mật (Security Challenge / Captcha V2){RESET}")
                    print(f"  • Yêu cầu:       {W}Nhấn giữ nút để xác nhận bạn là người thật.{RESET}")
                    print(f"  • ID tham chiếu: {C}{res.get('ref_id', 'N/A')}{RESET}")
                    if res.get("btn_coords"):
                        print(f"  • Tọa độ nút:    Pixel {res['btn_coords']}")
                        fix_tty()
                        test_hold = safe_input(f"\n{M}Bạn có muốn tự động nhấn giữ 16s thử nghiệm không? (y/N): {RESET}").strip().lower()
                        if test_hold == 'y':
                            cx, cy = res["btn_coords"]
                            print(f"{Y}[*] Đang giữ nút tại ({cx}, {cy}) 16s...{RESET}")
                            safe_root(f"su -c 'input tap {cx} {cy}'", timeout=3)
                            time.sleep(0.3)
                            safe_root(f"su -c 'input swipe {cx} {cy} {cx} {cy} 16000'", timeout=20)
                            time.sleep(2.5)
                            re_chk = detect_in_app_captcha()
                            if not re_chk.get("detected"):
                                print(f"{G}[✓] ĐÃ VƯỢT QUA 'NHẤN VÀ GIỮ' THÀNH CÔNG!{RESET}")
                            else:
                                print(f"{Y}[!] Vẫn còn trên màn hình sau khi giữ.{RESET}")
            else:
                print(f"\n{C}[i] Màn hình hiện tại không có popup Captcha V1 hay V2.{RESET}")
            fix_tty()
            print(f"\n{Y}Bấm Enter để tiếp tục...{RESET}")
            try: input()
            except: pass
        elif c == '5':
            print(f"\n{C}=== CẤU HÌNH OMOCAPTCHA API KEY ==={RESET}")
            print(f"Key hiện tại: {G}{mask_secret(OMOCAPTCHA_KEY)}{RESET}")
            new_k = safe_input(f"{M}Nhập OMOCaptcha Client Key mới (Enter để giữ nguyên): {RESET}").strip()
            if new_k:
                if save_omocaptcha_key(new_k):
                    print(f"{G}[✓] Đã lưu OMOCaptcha Key thành công vào omocaptcha_key.txt!{RESET}")
                else:
                    print(f"{R}[!] Lỗi lưu file omocaptcha_key.txt!{RESET}")
            time.sleep(1.5)
        elif c == '6':
            break

# =====================================================================
# AUTO REJOIN (TỐI ƯU + ĐỌC ĐÚNG FILE)
# =====================================================================
# =====================================================================
# MONITOR THREAD - Mỗi package chạy 1 thread riêng
# =====================================================================

def monitor_package(pkg, states, last_ok_ping, stop_event):
    """Thread độc lập cho từng package - không ảnh hưởng tab khác."""
    global kill_all_time, last_restart_time, CLAIMED_NAMES, CHECK_ACC_TIME_BLOCKED, CHECK_ACC_TIME_NORMAL, AUTO_CHECK_ACC_HEALTH
    while not stop_event.is_set():
        try:
            current_time = time.time()
            state = states[pkg]
            # session_start_time: thời điểm start lần đầu, KHÔNG reset khi rejoin
            # rejoin_time: chỉ dùng để tính warmup
            session_uptime = current_time - state['session_start_time']
            uptime_seconds = current_time - state['rejoin_time']

            # === MANDATORY PERIODIC COOKIE CHECK (MỖI 60S LUÔN CHECK BẤT KỂ LUA CÓ GỬI HEARTBEAT) ===
            last_mandatory_chk = state.get('last_mandatory_cookie_check', 0)
            if (current_time - last_mandatory_chk >= MANDATORY_COOKIE_CHECK_INTERVAL) and (AUTO_CHECK_ACC_HEALTH == "Enable"):
                state['last_mandatory_cookie_check'] = current_time
                chk_res = check_and_handle_account_health(pkg, states, current_time, force=True)
                if chk_res:
                    stop_event.wait(3)
                    continue

            # === KIỂM TRA TRẠNG THÁI ACC ĐANG BỊ KẸT (NOT_APPROVED / CAPTCHA V1 / V2 / EXPIRED) ===
            if state.get('is_blocked'):
                # Acc đang bị dính: TUYỆT ĐỐI KHÔNG VÀO GAME! Đảm bảo app tắt để không tốn tài nguyên
                if is_app_running(pkg):
                    _kill_pkg(pkg)

                last_check = state.get('last_acc_check', 0)
                recheck_interval = CHECK_ACC_TIME_BLOCKED
                time_passed = current_time - last_check
                time_left = max(0, int(recheck_interval - time_passed))

                short_reason = state.get('block_reason', 'Kẹt Acc')
                if "v1" in short_reason.lower() or "arkose" in short_reason.lower() or state.get('captcha_type') == 'CAPTCHA_V1':
                    lbl = "Chờ Cookie Sạch (V1)"
                elif "captchav2" in short_reason.lower() or "nhấn và giữ" in short_reason.lower() or "nhấn&giữ" in short_reason.lower():
                    lbl = "Dính Nhấn&Giữ"
                elif "not-approved" in short_reason.lower():
                    lbl = "Kẹt Not-Approved"
                elif "401" in short_reason or "hết hạn" in short_reason.lower():
                    lbl = "Cookie Die (401)"
                else:
                    lbl = short_reason[:18]

                state['text'] = f"{lbl} ({time_left}s)"
                state['color'] = R if ("not-approved" in short_reason.lower() or "401" in short_reason) else Y

                # Đến chu kỳ kiểm tra lại xem acc đã sạch chưa
                if time_passed >= recheck_interval:
                    # Nếu dính Captcha V2 và Auto Solve đang BẬT: tự động thử giải lại trong app
                    if state.get('captcha_type') == 'CAPTCHAV2' and AUTO_SOLVE_CAPTCHA_V2 == "Enable":
                        add_log(f"[{pkg[-12:]}] {Y}[CAPTCHA V2] Đến chu kỳ re-check, đang tự động giải lại Captcha V2...{RESET}")
                        ok_solved = solve_captchav2_in_app(pkg, states)
                        state['last_acc_check'] = current_time
                        if ok_solved:
                            state['is_blocked'] = False
                            state['block_reason'] = ''
                            state['warmup_until'] = current_time + 45
                            continue

                    cookie = extract_roblox_cookie(pkg) or state.get('cached_cookie')
                    state['last_acc_check'] = current_time
                    if cookie:
                        state['cached_cookie'] = cookie
                        try:
                            res = check_roblox_account_status(cookie)
                        except Exception:
                            res = {"status": "ERROR"}

                        if res.get('username'):
                            state['bound_name'] = res['username']
                            state['display_name'] = res['username']

                        if res.get('status') == 'OK':
                            # Acc đã sạch hoàn toàn! Tiến hành Rejoin vào game
                            state['is_blocked'] = False
                            state['block_reason'] = ''
                            state['account_status'] = 'OK'
                            state['text'] = "Cookie Sạch -> Rejoin..."
                            state['color'] = G
                            u_name = res.get('username') or state.get('bound_name') or 'Roblox'
                            add_log(f"[{pkg[-12:]}] {G}[✓ COOKIE SẠCH] Acc {u_name} ĐÃ BÌNH THƯỜNG! Đang Rejoin vào game...{RESET}")
                            with pkg_restart_locks[pkg]:
                                force_restart_app(pkg, states, current_time, "Cookie Sạch -> Rejoin", G)
                            last_ok_ping[pkg] = current_time
                            stop_event.wait(5)
                            continue
                        else:
                            # Vẫn chưa sạch (vẫn còn Captcha V1 / V2 / Not-Approved)
                            badge = res.get('badge', short_reason)
                            state['block_reason'] = badge
                            state['account_status'] = res.get('status')
                            add_log(f"[{pkg[-12:]}] {Y}[CHỜ COOKIE] Acc vẫn {badge}. Tiếp tục chờ {recheck_interval}s...{RESET}")
                    else:
                        add_log(f"[{pkg[-12:]}] Chưa lấy được Cookie để kiểm tra lại.")

                stop_event.wait(5)
                continue

            # === KIỂM TRA ĐANG TRONG TIẾN TRÌNH BOOT ===
            if pkg in _boot_threads and _boot_threads[pkg].is_alive():
                state['text'] = "Đang Khởi Động..."
                state['color'] = Y
                stop_event.wait(5)
                continue

            # === KIỂM TRA PHÁT HIỆN CAPTCHA V1 / V2 TRONG APP (CHỐNG TREO MÁY) ===
            bound = state.get('bound_name')
            hb = get_heartbeat(bound, pkg) if bound else -1
            if hb != -1 and (current_time - hb <= 120):
                state['in_game'] = True

            if uptime_seconds > 10 and is_app_running(pkg) and not state.get('in_game'):
                last_scr_chk = state.get('last_screen_security_check', 0)
                if current_time - last_scr_chk >= 8:
                    state['last_screen_security_check'] = current_time
                    cap_res = detect_in_app_captcha(pkg, auto_solve_v2=(AUTO_SOLVE_CAPTCHA_V2 == "Enable"))
                    if cap_res.get("detected"):
                        c_type = cap_res.get("type")
                        if c_type == "CAPTCHA_V1":
                            add_log(f"[{pkg[-12:]}] {R}[PHÁT HIỆN CAPTCHA V1 TRONG APP] Game bị chặn bởi câu đố Arkose FunCaptcha!{RESET}")
                            add_log(f"[{pkg[-12:]}] {Y}[CHỐNG TREO] Đã tắt app ngay lập tức để không bị treo. Chuyển sang chờ Cookie sạch...{RESET}")
                            _kill_pkg(pkg)
                            state['is_blocked'] = True
                            state['in_game'] = False
                            state['captcha_type'] = 'CAPTCHA_V1'
                            state['block_reason'] = 'Dính Captcha V1 Trong App'
                            state['text'] = 'Dính V1 App -> Tắt App Chờ'
                            state['color'] = Y
                            state['last_acc_check'] = current_time
                            stop_event.wait(5)
                            continue
                        elif c_type == "CAPTCHAV2":
                            ref = cap_res.get('ref_id', 'N/A')
                            coords = cap_res.get('btn_coords')
                            attempts = state.get('v2_in_app_attempts', 0) + 1
                            state['v2_in_app_attempts'] = attempts

                            if attempts <= 2 and coords:
                                cx, cy = coords
                                add_log(f"[{pkg[-12:]}] {Y}[BẢO MẬT] Phát hiện 'Nhấn và Giữ' in-app (Lần {attempts}/2, ID: {ref[:8]}..)! Đang giữ nút ({cx}, {cy}) 16s...{RESET}")
                                safe_root(f"su -c 'input tap {cx} {cy}'", timeout=3)
                                time.sleep(0.3)
                                safe_root(f"su -c 'input swipe {cx} {cy} {cx} {cy} 16000'", timeout=20)
                                time.sleep(2.5)

                                # Kiểm tra lại xem đã qua chưa
                                re_chk = detect_in_app_captcha(pkg)
                                if not re_chk.get("detected") or re_chk.get("type") != "CAPTCHAV2":
                                    add_log(f"[{pkg[-12:]}] {G}[✓ BẢO MẬT] Đã giữ 16s thành công vượt qua 'Nhấn và Giữ'! Đang nạp game...{RESET}")
                                    state['v2_in_app_attempts'] = 0
                                    state['rejoin_time'] = current_time
                                    state['warmup_until'] = current_time + 45
                                    stop_event.wait(3)
                                    continue
                                else:
                                    add_log(f"[{pkg[-12:]}] {Y}[!] Màn hình 'Nhấn và Giữ' vẫn còn sau lần {attempts}.{RESET}")

                            if attempts > 2 or not coords:
                                add_log(f"[{pkg[-12:]}] {R}[CHỐNG TREO] Đã quá số lần thử 'Nhấn và Giữ' hoặc không có nút. Tắt app ngay để tránh treo máy!{RESET}")
                                _kill_pkg(pkg)
                                state['is_blocked'] = True
                                state['in_game'] = False
                                state['v2_in_app_attempts'] = 0
                                state['block_reason'] = 'Kẹt Nhấn&Giữ Trong App'
                                state['text'] = 'Kẹt Nhấn&Giữ -> Chờ'
                                state['color'] = Y
                                state['last_acc_check'] = current_time
                                stop_event.wait(5)
                                continue

            # === ĐẢM BẢO PROCESS APP PHẢI CHẠY (NẾU KHÔNG CHẠY THÌ BẬT NGAY) ===
            if uptime_seconds > 15 and not is_app_running(pkg):
                # Kiểm tra xem acc có bị kẹt Not-Approved/Captcha không trước khi bật lại
                if check_and_handle_account_health(pkg, states, current_time):
                    stop_event.wait(5)
                    continue

                can_restart = pkg not in last_restart_time or current_time - last_restart_time[pkg] >= 180
                if can_restart:
                    with pkg_restart_locks[pkg]:
                        force_restart_app(pkg, states, current_time, "App không chạy!", R)
                    last_ok_ping[pkg] = current_time
                else:
                    state['text'] = 'App tắt, chờ...'
                    state['color'] = R
                stop_event.wait(5)
                continue

            # === AUTO RESTART THEO THỜI GIAN (dùng session_uptime, tích lũy qua rejoin) ===
            if kill_all_time > 0 and session_uptime / 60 >= kill_all_time:
                if check_and_handle_account_health(pkg, states, current_time):
                    stop_event.wait(5)
                    continue

                with pkg_restart_locks[pkg]:
                    force_restart_app(pkg, states, current_time, f"Auto Restart ({kill_all_time}m)", M)
                # Reset session timer sau khi auto restart
                state['session_start_time'] = current_time
                last_ok_ping[pkg] = current_time
                stop_event.wait(10)
                continue

            # === WARMUP ===
            if current_time < state.get('warmup_until', 0):
                state['text'] = f"Warmup ({int(state['warmup_until'] - current_time)}s)"
                state['color'] = Y
                stop_event.wait(5)
                continue

            # === TÌM TÊN NẾU CHƯA BIND ===
            if not state['bound_name']:
                found = discover_unbound_account(pkg, states)
                if found:
                    state['bound_name'] = found
                    state['display_name'] = found

            bound = state['bound_name']
            is_grace = (uptime_seconds < 120)  # 150s thay vì 240s → detect fail nhanh hơn

            # === CHƯA BIND ĐƯỢC TÊN ===
            if not bound:
                if is_grace:
                    # Nếu app không chạy sau 30s warmup → restart ngay
                    if uptime_seconds > 30 and not is_app_running(pkg):
                        if check_and_handle_account_health(pkg, states, current_time):
                            stop_event.wait(5)
                            continue
                        can_restart = pkg not in last_restart_time or current_time - last_restart_time[pkg] >= 180
                        if can_restart:
                            with pkg_restart_locks[pkg]:
                                force_restart_app(pkg, states, current_time, "App không mở được!", R)
                            last_ok_ping[pkg] = current_time
                        else:
                            state['text'] = 'App lỗi, đang chờ...'
                            state['color'] = R
                    else:
                        state['text'] = f"Đang Load ({int(150 - uptime_seconds)}s)"
                        state['color'] = Y
                else:
                    if check_and_handle_account_health(pkg, states, current_time):
                        stop_event.wait(5)
                        continue
                    can_restart = pkg not in last_restart_time or current_time - last_restart_time[pkg] >= 180
                    if can_restart:
                        with pkg_restart_locks[pkg]:
                            force_restart_app(pkg, states, current_time, "Chưa Load/Kẹt Bind!", R)
                        last_ok_ping[pkg] = current_time
                    else:
                        wait_sec = int(180 - (current_time - last_restart_time.get(pkg, current_time)))
                        state['text'] = f"Chờ Restart ({wait_sec}s)"
                        state['color'] = R
                stop_event.wait(10)
                continue

            # === CHECK HEARTBEAT ===
            other_just_restarted = (current_time - last_any_restart_time < 90) and \
                                   (last_any_restart_time != last_restart_time.get(pkg, 0))

            last_ping = get_heartbeat(bound, pkg)
            if last_ping == -1:
                state['heartbeat_misses'] = state.get('heartbeat_misses', 0) + 1
                misses = state['heartbeat_misses']
                if is_grace or other_just_restarted:
                    remain = int(240 - uptime_seconds) if is_grace else int(180 - (current_time - last_any_restart_time))
                    state['text'] = f"Đang Nạp Data ({max(0,remain)}s)"
                    state['color'] = Y
                elif misses >= 3 and (pkg not in last_restart_time or current_time - last_restart_time[pkg] >= 90):
                    if check_and_handle_account_health(pkg, states, current_time):
                        stop_event.wait(5)
                        continue
                    with pkg_restart_locks[pkg]:
                        force_restart_app(pkg, states, current_time, "Treo Màn/Chưa Vô Game!", R)
                    state['heartbeat_misses'] = 0
                    last_ok_ping[pkg] = current_time
                else:
                    state['text'] = f"Chờ Ping (#{misses})"
                    state['color'] = Y
                stop_event.wait(10)
                continue

            # Heartbeat có ping hợp lệ
            state['heartbeat_misses'] = 0
            diff = current_time - last_ping
            if diff <= 120:
                state['text'] = f"Đang Farm ({int(diff)}s)"
                state['color'] = G
                state['in_game'] = True
                last_ok_ping[pkg] = current_time
            else:
                state['in_game'] = False
                if check_and_handle_account_health(pkg, states, current_time):
                    stop_event.wait(5)
                    continue
                can_restart = pkg not in last_restart_time or current_time - last_restart_time[pkg] >= 90
                if can_restart:
                    with pkg_restart_locks[pkg]:
                        force_restart_app(pkg, states, current_time, f"Mất Ping ({int(diff)}s)!", R)
                    last_ok_ping[pkg] = current_time
                else:
                    wait_sec = int(90 - (current_time - last_restart_time.get(pkg, current_time)))
                    state['text'] = f"Chờ Restart ({wait_sec}s)"
                    state['color'] = R

            stop_event.wait(10)
        except Exception as exc:
            time.sleep(2)

def mask_secret(secret):
    """Che giấu chuỗi bảo mật/API Key khi hiển thị trên terminal hoặc log."""
    if not secret:
        return "<CHƯA CÓ>"
    secret = str(secret).strip()
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"

class BaconApiException(Exception):
    """Lớp Exception cơ sở cho mọi lỗi trả về từ Bacon Bypass API."""
    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
    def __str__(self):
        st = f" [HTTP {self.status_code}]" if self.status_code else ""
        return f"{self.__class__.__name__}{st}: {self.message}"

class BadRequestException(BaconApiException):
    """Mã 400: Thiếu tham số bắt buộc hoặc dữ liệu sai."""
    def __init__(self, message, response_body=None):
        super().__init__(message, status_code=400, response_body=response_body)

class InvalidKeyException(BaconApiException):
    """Mã 403: API Key không hợp lệ, chưa kích hoạt hoặc đã hết hạn."""
    def __init__(self, message, response_body=None):
        super().__init__(message, status_code=403, response_body=response_body)

class RateLimitExceededException(BaconApiException):
    """Mã 429: Vượt quá giới hạn gọi API (>3 req/10s)."""
    def __init__(self, message, response_body=None):
        super().__init__(message, status_code=429, response_body=response_body)

class UpstreamProviderException(BaconApiException):
    """Mã 500: Lỗi máy chủ hoặc upstream link provider không phản hồi."""
    def __init__(self, message, response_body=None):
        super().__init__(message, status_code=500, response_body=response_body)

class BaconTimeoutException(BaconApiException):
    """Lỗi Timeout: Quá 90s không nhận được kết quả giải mã."""
    def __init__(self, message="Request timed out after 90s."):
        super().__init__(message, status_code=408)

class SlidingWindowRateLimiter:
    """Rate Limiter cửa sổ trượt: đảm bảo nghiêm ngặt tối đa 3 requests / 10s (Thread-safe)."""
    def __init__(self, max_requests=3, window_seconds=10.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps = deque()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return
                earliest = self._timestamps[0]
                sleep_sec = earliest + self.window_seconds - now + 0.05
            if sleep_sec > 0:
                time.sleep(sleep_sec)

# Singleton rate limiter dùng chung cho toàn bộ tiến trình
_bacon_rate_limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10.0)

def load_bacon_api_key():
    """Tự động đọc Bacon API Key từ RAM, biến môi trường hoặc các file cấu hình."""
    global BACON_API_KEY
    if BACON_API_KEY:
        return BACON_API_KEY
    env_k = os.environ.get("BACON_API_KEY")
    if env_k:
        BACON_API_KEY = env_k.strip()
        return BACON_API_KEY
    search_files = [
        get_download_save_path("bacon_key.txt"),
        "/storage/emulated/0/Download/bacon_key.txt",
        "/sdcard/Download/bacon_key.txt",
        "bacon_key.txt",
        "/data/media/0/bacon_key.txt",
        "/sdcard/bacon_key.txt",
        "/data/data/com.termux/files/home/bacon_key.txt"
    ]
    for p in search_files:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    k = f.read().strip()
                    if k:
                        BACON_API_KEY = k
                        return BACON_API_KEY
        except:
            pass
    return ""

def save_bacon_api_key(key):
    """Lưu Bacon API Key vào bộ nhớ và file cục bộ."""
    global BACON_API_KEY
    BACON_API_KEY = key.strip()
    search_files = [
        get_download_save_path("bacon_key.txt"),
        "/storage/emulated/0/Download/bacon_key.txt",
        "/sdcard/Download/bacon_key.txt",
        "bacon_key.txt",
        "/sdcard/bacon_key.txt"
    ]
    for p in search_files:
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(BACON_API_KEY)
        except:
            pass

class BaconBypassClient:
    """Client tự động giải mã link qua Bacon Bypass API với chuẩn Production-grade."""
    DEFAULT_BASE_URL = "https://baconbypass.online"
    DEFAULT_TIMEOUT = 90.0
    DEFAULT_MAX_RETRIES = 3

    def __init__(self, api_key=None, base_url=None, timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES):
        self.api_key = api_key or load_bacon_api_key()
        if not self.api_key:
            raise InvalidKeyException("Chưa cấu hình Bacon API Key.")
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = max(float(timeout), 90.0)
        self.max_retries = int(max_retries)

    def _execute_http_post(self, endpoint, payload):
        payload_bytes = _json_mod.dumps(payload).encode('utf-8')
        # Thử sử dụng requests nếu môi trường có sẵn
        try:
            import requests
            r = requests.post(
                endpoint, json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "BaconClient/1.0"},
                timeout=self.timeout
            )
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            return r.status_code, data
        except ImportError:
            pass
        except Exception as e:
            if "timeout" in str(e).lower():
                raise BaconTimeoutException(str(e))

        # Fallback thư viện chuẩn urllib (chạy trên mọi máy Android/Termux không cần pip)
        import urllib.request
        import urllib.error
        req = urllib.request.Request(
            endpoint, data=payload_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "BaconClient/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_txt = resp.read().decode('utf-8', errors='ignore')
                try:
                    data = _json_mod.loads(raw_txt)
                except:
                    data = {"raw": raw_txt}
                return resp.status, data
        except urllib.error.HTTPError as he:
            raw_txt = he.read().decode('utf-8', errors='ignore') if he.fp else ""
            try:
                data = _json_mod.loads(raw_txt)
            except:
                data = {"raw": raw_txt}
            return he.code, data
        except urllib.error.URLError as ue:
            if "timed out" in str(ue.reason).lower():
                raise BaconTimeoutException(str(ue.reason))
            raise BaconApiException(f"Lỗi mạng kết nối: {ue.reason}")
        except TimeoutError as te:
            raise BaconTimeoutException(str(te))

    def bypass(self, target_url):
        if not target_url or not isinstance(target_url, str):
            raise BadRequestException("Target URL không hợp lệ.")
        endpoint = f"{self.base_url}/bypass"
        payload = {"url": target_url.strip(), "apikey": self.api_key}

        for attempt in range(self.max_retries + 1):
            _bacon_rate_limiter.acquire()
            try:
                status, data = self._execute_http_post(endpoint, payload)
                if status == 200:
                    if isinstance(data, dict) and data.get("status") == "success":
                        res = data.get("result")
                        if res:
                            return res
                    raise BaconApiException(f"Phản hồi không hợp lệ: {data}", status_code=status, response_body=data)

                err_msg = data.get("message", str(data)) if isinstance(data, dict) else str(data)

                # Lỗi định danh & cú pháp: Không retry
                if status == 400:
                    raise BadRequestException(err_msg, response_body=data)
                if status == 403:
                    raise InvalidKeyException(err_msg, response_body=data)

                # Lỗi tạm thời: Exponential Backoff với Jitter
                if status in (429, 500):
                    if attempt < self.max_retries:
                        backoff = min(30.0, 2.0 * (2 ** attempt)) + random.uniform(0.5, 1.5)
                        add_log(f"[Bacon] HTTP {status}, thử lại sau {int(backoff)}s ({attempt+1}/{self.max_retries})")
                        time.sleep(backoff)
                        continue
                    if status == 429:
                        raise RateLimitExceededException(f"Vượt giới hạn Rate Limit: {err_msg}", response_body=data)
                    raise UpstreamProviderException(f"Lỗi Upstream Server: {err_msg}", response_body=data)

                raise BaconApiException(f"Lỗi HTTP {status}: {err_msg}", status_code=status, response_body=data)

            except BaconTimeoutException as te:
                if attempt < self.max_retries:
                    backoff = 2.0 * (attempt + 1) + random.uniform(0.5, 1.0)
                    add_log(f"[Bacon] Quá hạn 90s, thử lại sau {int(backoff)}s...")
                    time.sleep(backoff)
                    continue
                raise te
            except BaconApiException:
                raise
            except Exception as ex:
                if attempt < self.max_retries:
                    time.sleep(2)
                    continue
                raise BaconApiException(f"Lỗi không xác định: {str(ex)}")

        raise BaconApiException("Đã thử hết số lần retry cho phép.")

def get_android_clipboard():
    """Đọc dữ liệu từ clipboard Android (termux hoặc su)."""
    try:
        out = subprocess.check_output("termux-clipboard-get 2>/dev/null", shell=True, text=True, timeout=2).strip()
        if out: return out
    except: pass
    try:
        out = subprocess.check_output("su -c 'cmd clipboard get' 2>/dev/null", shell=True, text=True, timeout=2).strip()
        if out: return out
    except: pass
    return ""

def set_android_clipboard(text):
    """Ghi dữ liệu vào clipboard Android."""
    try:
        subprocess.run(f"echo -n \"{text}\" | termux-clipboard-set 2>/dev/null", shell=True, timeout=2)
    except: pass
    try:
        safe_root(f"su -c 'cmd clipboard set \"{text}\" 2>/dev/null'")
    except: pass

def extract_getkey_url(text):
    """Trích xuất URL Get Key từ văn bản (Platoboost, Linkvertise, Lootlabs, Work.ink...)."""
    if not text:
        return None
    patterns = [
        r'(https?://(?:gateway\.)?platoboost\.[^\s"\'<>]+)',
        r'(https?://[^\s"\'<>]*(?:platoboost|linkvertise|loot-link|loot-labs|lootdest|direct-link|deltaexploits|work\.ink)[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+(?:getkey|get-key|key-system|\/key|\?key)[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.[a-z]{2,}[^\s"\'<>]*)'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None

def _http_get_ping(url, timeout=15):
    """Gửi GET request để kích hoạt Whitelist/HWID callback trên hệ thống key."""
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36"}
        requests.get(url, headers=headers, timeout=timeout)
        return True
    except: pass
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return True
    except: pass
    return False

def get_screen_resolution():
    """Lấy độ phân giải màn hình chuẩn Landscape của Roblox (W x H)."""
    try:
        out = subprocess.check_output("su -c 'wm size 2>/dev/null'", shell=True, text=True, timeout=3)
        m = re.findall(r'(\d+)x(\d+)', out)
        if m:
            w, h = int(m[-1][0]), int(m[-1][1])
            return max(w, h), min(w, h)
    except:
        pass
    return 1600, 720

def close_browser_popups():
    """Đóng Chrome hoặc các trình duyệt vừa bị Delta mở khi click Receive Key."""
    browsers = [
        "com.android.chrome",
        "com.google.android.apps.chrome",
        "com.sec.android.app.sbrowser",
        "org.mozilla.firefox",
        "com.opera.browser",
        "com.brave.browser",
        "com.android.browser"
    ]
    for b in browsers:
        safe_root(f"su -c 'am force-stop {b} 2>/dev/null'")

# Tỷ lệ tọa độ chuẩn xác của giao diện Delta (bảng Welcome Back ở góc phải):
DELTA_PANEL_X_RATIO = 0.836    # Trục X tâm bảng (X ~ 83.6% màn hình)
DELTA_INPUT_Y_RATIO = 0.380    # Ô nhập KEY_example (Y ~ 38.0% màn hình)
DELTA_CONTINUE_Y_RATIO = 0.495 # Nút Continue (Y ~ 49.5% màn hình)
DELTA_RECEIVE_Y_RATIO = 0.590  # Nút Receive Key / Copied Link (Y ~ 59.0% màn hình)

def click_receive_key_button():
    """
    Tự động tìm và click vào nút 'Receive Key' của Delta.
    Dùng tọa độ tỷ lệ đo trực tiếp từ pixel: X = 83.6% W, Y = 59.0% H.
    """
    w, h = get_screen_resolution()
    rx = int(w * DELTA_PANEL_X_RATIO)
    ry = int(h * DELTA_RECEIVE_Y_RATIO)

    add_log(f"[Key] Click 'Receive Key' tại ({rx}, {ry}) [Screen: {w}x{h}]")
    safe_root(f"su -c 'input swipe {rx} {ry} {rx} {ry} 120'")
    time.sleep(0.2)
    safe_root(f"su -c 'input tap {rx} {ry}'")
    time.sleep(1.5)
    return True

def auto_enter_key_and_continue(key_str):
    """
    Tự động nhập key dạng 'FREE_...' vào khung 'KEY_example' và bấm nút 'Continue'.
    Tọa độ chuẩn xác từ pixel ảnh thực tế:
    - Input 'KEY_example': X = 83.6% W, Y = 38.0% H
    - Button 'Continue':   X = 83.6% W, Y = 49.5% H
    """
    key_str = key_str.strip()
    if not key_str:
        return False

    w, h = get_screen_resolution()
    in_x = int(w * DELTA_PANEL_X_RATIO)
    in_y = int(h * DELTA_INPUT_Y_RATIO)
    cont_x = int(w * DELTA_PANEL_X_RATIO)
    cont_y = int(h * DELTA_CONTINUE_Y_RATIO)

    add_log(f"[Key] Focus ô 'KEY_example' tại ({in_x}, {in_y}) [Screen: {w}x{h}]")

    # 1. Ghi sẵn key vào Clipboard hệ thống
    set_android_clipboard(key_str)
    time.sleep(0.2)

    # 2. Focus vào ô nhập key:
    # Dùng touch press 150ms để Roblox UI loop bắt trúng con trỏ
    safe_root(f"su -c 'input swipe {in_x} {in_y} {in_x} {in_y} 150'")
    time.sleep(0.3)
    safe_root(f"su -c 'input tap {in_x} {in_y}'")
    time.sleep(0.3)
    # Tap nhẹ thêm 1 nhịp ở nửa bên trái của khung ô nhập để kích hoạt bàn phím
    safe_root(f"su -c 'input tap {int(w * 0.790)} {in_y}'")
    time.sleep(0.6)

    # 3. Gửi lệnh Paste từ Clipboard (KEYCODE_PASTE 279)
    safe_root("su -c 'input keyevent 279 2>/dev/null'")
    time.sleep(0.3)

    # 4. Gõ chuỗi key dạng FREE_... vào ô bằng input text
    safe_root(f"su -c 'input text \"{key_str}\"'")
    time.sleep(0.5)

    # 5. Đóng bàn phím ảo (phím Back 4) để lộ nút Continue bên dưới
    safe_root("su -c 'input keyevent 4 2>/dev/null'")
    time.sleep(0.8)

    # 6. Click nút 'Continue' (X = 83.6% W, Y = 49.5% H)
    add_log(f"[Key] Bấm nút 'Continue' tại ({cont_x}, {cont_y})")
    safe_root(f"su -c 'input swipe {cont_x} {cont_y} {cont_x} {cont_y} 150'")
    time.sleep(0.3)
    safe_root(f"su -c 'input tap {cont_x} {cont_y}'")
    time.sleep(2.0)
    return True

def _get_delta_license_dirs():
    """Trả về danh sách tất cả thư mục có thể chứa Delta license."""
    dirs = [
        "/storage/emulated/0/Delta/Internals/Cache",
        "/data/media/0/Delta/Internals/Cache",
        "/sdcard/Delta/Internals/Cache",
        "/sdcard/DeltaQT/Internals/Cache",
        "/storage/emulated/0/DeltaQT/Internals/Cache",
    ]
    for item in selected_packages:
        pkg = item['pkg']
        dirs.extend([
            f"/sdcard/Android/media/{pkg}/Delta/Internals/Cache",
            f"/data/media/0/Android/media/{pkg}/Delta/Internals/Cache",
            f"/sdcard/Android/data/{pkg}/Delta/Internals/Cache",
            f"/data/media/0/Android/data/{pkg}/Delta/Internals/Cache",
        ])
    return list(set(dirs))


def launch_roblox_and_join_game(pkg):
    """
    Khởi động package và BẮN THẲNG VÀO GAME bằng Place ID để Delta inject và hiện bảng Welcome Back.
    """
    global target_place_id
    # Xóa file license cũ hết hạn (nếu có) để Delta bắt buộc hiện bảng Welcome Back
    dirs = _get_delta_license_dirs()
    for d in dirs:
        lic = f"{d}/license"
        mt = _get_file_mtime_root(lic)
        if mt > 0:
            safe_root(f"su -c 'rm -f \"{lic}\"'")

    safe_root(f"su -c 'am force-stop {pkg}'")
    time.sleep(2)
    uri_k = build_roblox_launch_uri(pkg)
    if uri_k:
        safe_root(
            f"su -c 'am start -p {pkg} -f 0x10008000 -a android.intent.action.VIEW "
            f"-d \"{uri_k}\" 2>/dev/null'"
        )
    else:
        safe_root(f"su -c 'monkey -p {pkg} -c android.intent.category.LAUNCHER 1 2>/dev/null'")
    target_lbl = "VIP Server" if (JOIN_SERVER_MODE == "Enable" and JOIN_SERVER_LINK) else f"Place: {target_place_id or 'Sảnh'}"
    add_log(f"[Key] Bắn {pkg[-14:]} vào game ({target_lbl})")


def obtain_delta_getkey_url(pkg, stop_event, max_wait_secs=120):
    """
    Khởi động và bắn vào game để lấy URL Get Key triệt để:
    - Game load map và asset khá lâu (chờ 2p30s) mới hiện bảng 'Welcome Back!'.
    - Cơ chế: Xóa clipboard cũ -> Bắn vào game -> Chờ 150s khởi tạo -> Quét lặp định kỳ mỗi 3s.
    - Mỗi chu kỳ: Tap 'Receive Key' (83.3% W, 91.0% H) -> Đợi 2s kiểm tra Clipboard -> Bắt URL.
    - Đóng ngay Chrome khi nhận được URL.
    """
    # 1. Kiểm tra nếu clipboard hiện tại đã có link hợp lệ
    clip = get_android_clipboard()
    target_url = extract_getkey_url(clip)
    if target_url:
        add_log(f"[Key] Clipboard đã có sẵn link: {target_url[:20]}...")
        return target_url

    # 2. Xóa sạch clipboard để không nhận link rác/cũ
    set_android_clipboard("")

    # 3. Khởi động và bắn thẳng vào game
    launch_roblox_and_join_game(pkg)
    add_log(f"[Key] Chờ 150s (2p30s) để {pkg[-12:]} load vào giao diện in-game...")

    # Chờ 150s (2 phút 30 giây) cho game tải tài nguyên, kết nối server và hiển thị giao diện
    for _ in range(150):
        if stop_event.is_set():
            return None
        time.sleep(1)

    # 4. Vòng lặp quét liên tục tối đa max_wait_secs
    t_start = time.time()
    attempt = 1
    while time.time() - t_start < max_wait_secs:
        if stop_event.is_set():
            return None

        add_log(f"[Key] Quét lấy URL lần {attempt} ({int(time.time() - t_start)}s)...")
        click_receive_key_button()

        # Chờ 2 giây kiểm tra clipboard (thử 4 lần nhịp 0.5s)
        for _ in range(4):
            time.sleep(0.5)
            clip = get_android_clipboard()
            target_url = extract_getkey_url(clip)
            if target_url:
                close_browser_popups()
                add_log(f"[Key] Đã bắt được URL thành công sau {int(time.time() - t_start)}s!")
                return target_url

        close_browser_popups()
        attempt += 1
        time.sleep(2.5)

    add_log(f"[Key] Hết {max_wait_secs}s chưa bắt được link Get Key.")
    return None


def delta_license_sync_thread(stop_event):
    """
    Thread tự động lấy & nạp key Delta (KHÔNG CẦN BACKUP HAY RESTORE):
    1. Kiểm tra xem app đã có file license còn hạn (< KEY_EXPIRE_HOURS) hay chưa.
    2. Nếu chưa có hoặc hết hạn:
       - Bắn vào game, chờ game load hoàn tất (150s).
       - Lấy URL Get Key triệt để qua vòng lặp quét Receive Key định kỳ.
       - Gửi URL lên Bacon API giải mã lấy chuỗi key 'FREE_...'.
       - Khởi động lại game & bắn vào game để hiện lại bảng 'Welcome Back!'.
       - Chờ 150s game load -> Tự động điền chuỗi key 'FREE_...' vào ô 'KEY_example' và click 'Continue'.
       - Delta sẽ tự động kiểm tra và sinh file license riêng cho app đó!
    """
    global AUTO_RESTORE_DELTA_KEY, selected_packages, _last_key_trigger

    while not stop_event.is_set():
        try:
            if getattr(sys.modules[__name__], 'AUTO_RESTORE_DELTA_KEY', "Disable") != "Enable":
                stop_event.wait(10)
                continue

            bkey = load_bacon_api_key()
            if not bkey:
                stop_event.wait(15)
                continue

            now = time.time()
            expire_secs = KEY_EXPIRE_HOURS * 3600

            for item in selected_packages:
                pkg = item['pkg']
                last_trigger = _last_key_trigger.get(pkg, 0)
                if now - last_trigger < 300:  # Giãn cách 5 phút mỗi lần thử cho 1 pkg
                    continue

                # Kiểm tra app này đã có license hợp lệ từ game chưa
                pkg_dirs = [
                    "/storage/emulated/0/Delta/Internals/Cache",
                    "/sdcard/Delta/Internals/Cache",
                    f"/sdcard/Android/media/{pkg}/Delta/Internals/Cache",
                    f"/sdcard/Android/data/{pkg}/Delta/Internals/Cache",
                ]
                has_license = False
                for d in pkg_dirs:
                    lic = f"{d}/license"
                    mt = _get_file_mtime_root(lic)
                    if mt > 0 and (now - mt < expire_secs):
                        has_license = True
                        break

                if has_license:
                    continue  # App này đã có key hợp lệ, không cần nạp

                # App chưa có key hợp lệ -> Bắt đầu quy trình tự động lấy và nạp key
                _last_key_trigger[pkg] = now
                add_log(f"[Key] {pkg[-12:]} chưa có key, bắt đầu quy trình...")

                # Bước 1: Bắn vào game & Quét lấy URL Get Key triệt để (chờ 150s game load)
                target_url = obtain_delta_getkey_url(pkg, stop_event, max_wait_secs=120)

                # Bước 2: Gửi URL lên Bacon API giải mã
                if target_url:
                    add_log(f"[Bacon] Giải mã link: {target_url[:20]}...")
                    try:
                        client = BaconBypassClient(api_key=bkey, timeout=90.0, max_retries=3)
                        key_res = client.bypass(target_url)
                        add_log(f"[Bacon] Nhận key: {key_res[:16]}...")

                        # Đóng lại trình duyệt nếu có
                        close_browser_popups()

                        # Bước 3: Khởi động lại và BẮN VÀO GAME để quay lại bảng "Welcome Back!" nhập key
                        add_log(f"[Key] Bắn {pkg[-12:]} vào game để nạp key...")
                        launch_roblox_and_join_game(pkg)
                        add_log("[Key] Chờ 150s (2p30s) cho game load vào giao diện & bảng Enter Key...")
                        for _ in range(150):
                            if stop_event.is_set():
                                break
                            time.sleep(1)

                        # Bước 4: Nhập chuỗi key 'FREE_...' vào khung và click 'Continue'
                        if not (key_res.startswith("http://") or key_res.startswith("https://")):
                            auto_enter_key_and_continue(key_res)
                            add_log("[Key] Đã điền key FREE_... & bấm Continue!")
                            stop_event.wait(6)

                            # Kiểm tra nếu chưa sinh file, thử nhập lại lần 2 sau 5s (phòng máy lag)
                            has_lic = any(_get_file_mtime_root(f"{d}/license") > 0 for d in pkg_dirs)
                            if not has_lic:
                                add_log("[Key] Thử nạp lại key lần 2...")
                                auto_enter_key_and_continue(key_res)
                                stop_event.wait(5)
                        else:
                            # Nếu kết quả là URL kích hoạt Whitelist
                            _http_get_ping(key_res)
                            add_log("[Bacon] Đã ping URL kích hoạt!")
                            stop_event.wait(3)

                        # Bước 5: Kiểm tra Delta đã tự sinh file license chưa
                        created = False
                        for d in pkg_dirs:
                            lic = f"{d}/license"
                            if _get_file_mtime_root(lic) > 0:
                                created = True
                                break

                        if created:
                            add_log(f"[Key] {pkg[-12:]} đã tự sinh License thành công!")
                        else:
                            add_log(f"[Key] Đã hoàn tất nạp key cho {pkg[-12:]}")

                    except BaconApiException as be:
                        add_log(f"[Bacon Lỗi] {str(be)[:25]}")
                else:
                    add_log("[Key] Không lấy được URL Get Key.")

                stop_event.wait(10)

        except Exception:
            pass
        stop_event.wait(15)

def start_auto_rejoin():
    global selected_packages, kill_all_time, json_path_cache, heartbeat_last_check, CLAIMED_NAMES, last_restart_time, pkg_restart_locks, global_restart_semaphore, file_to_pkg_binding
    if not selected_packages:
        auto_select_vip_packages()
    if not selected_packages:
        print(f"{R}[!] Chưa tìm thấy package nào! Vui lòng vào mục [1] để chọn.{RESET}")
        time.sleep(2)
        return

    last_restart_time = {}
    last_any_restart_time = 0
    json_path_cache = {}
    heartbeat_last_check = {}
    CLAIMED_NAMES = set()
    pkg_restart_locks = {}
    global_restart_semaphore = threading.Semaphore(1)
    file_to_pkg_binding = {}

    print(f"\n{Y}[*] Inject script universal & user script...{RESET}")
    inject_universal_lua()
    inject_user_script()

    states = {}
    last_ok_ping = {}
    stop_event = threading.Event()
    sync_t = threading.Thread(target=delta_license_sync_thread, args=(stop_event,), daemon=True)
    sync_t.start()

    now = time.time()

    # Bật từng tab theo thứ tự, cách nhau 5s để hệ thống ổn định
    for i, item in enumerate(selected_packages):
        pkg = item['pkg']
        pkg_restart_locks[pkg] = threading.Lock()
        pkg_now = time.time()  # Dùng thời gian thực tế cho từng pkg, không dùng `now` chung
        states[pkg] = {
            'text': 'Đang Khởi Tạo...',
            'color': Y,
            'bound_name': item['name'] if item['name'] else None,
            'display_name': item['name'] if item['name'] else 'Chờ Auto-Bind...',
            'rejoin_time': pkg_now,
            'session_start_time': pkg_now,
            'warmup_until': pkg_now + 90,
            'heartbeat_misses': 0,
            'is_blocked': False,
            'block_reason': '',
            'account_status': 'UNKNOWN',
            'last_acc_check': pkg_now,
            'last_mandatory_cookie_check': pkg_now,
            'captcha_miss_count': 0,
            'cached_cookie': None
        }
        last_ok_ping[pkg] = pkg_now
        last_restart_time.pop(pkg, None)

        # Kiểm tra trước trạng thái tài khoản qua Cookie:
        # Nếu acc đang bị dính Not-Approved / Captcha / Expired -> KHÔNG VÀO GAME
        is_blocked = False
        if AUTO_CHECK_ACC_HEALTH == "Enable":
            is_blocked = check_and_handle_account_health(pkg, states, pkg_now)

        if not is_blocked:
            force_restart_app(pkg, states, pkg_now, 'Đang Mở Sảnh...', Y)
            if i < len(selected_packages) - 1:
                print(f"{Y}[*] Chờ 5s trước khi bật tab tiếp theo...{RESET}")
                time.sleep(5)
        else:
            print(f"{R}[!] Package {pkg[-15:]} bị {states[pkg].get('text')}, tạm dừng không vào game!{RESET}")

    os.system("stty sane < /dev/tty > /dev/null 2>&1")
    # Đợi thêm 2s cho các shell command sau safe_root hoàn tất
    time.sleep(2)

    # Khởi thread riêng cho từng package
    monitor_threads = {}
    for item in selected_packages:
        pkg = item['pkg']
        t = threading.Thread(
            target=monitor_package,
            args=(pkg, states, last_ok_ping, stop_event),
            daemon=True,
            name=f"mon-{pkg[-12:]}"
        )
        t.start()
        monitor_threads[pkg] = t

    # Main thread: hiển thị dashboard + watchdog tự khởi lại thread chết
    last_dashboard = 0
    try:
        while True:
            current_time = time.time()
            if current_time - last_dashboard >= 5:
                print_dashboard(states)
                last_dashboard = current_time

            # === WATCHDOG: phát hiện thread chết và khởi lại ===
            for item in selected_packages:
                pkg = item['pkg']
                t = monitor_threads.get(pkg)
                if t and not t.is_alive():
                    try:
                        states[pkg]['text'] = 'Watchdog: khởi lại...'
                        states[pkg]['color'] = M
                    except:
                        pass
                    new_t = threading.Thread(
                        target=monitor_package,
                        args=(pkg, states, last_ok_ping, stop_event),
                        daemon=True,
                        name=f"mon-{pkg[-12:]}"
                    )
                    new_t.start()
                    monitor_threads[pkg] = new_t

            time.sleep(3)
    except KeyboardInterrupt:
        stop_event.set()
        time.sleep(1.5)  # Đợi thread dừng hết
        fix_tty()
        print(f"\n{R}[!] Đã dừng Auto Rejoin.{RESET}")
        print("-" * 65)
        print(f"{Y}[*] Bấm Enter để về menu...{RESET}")
        try:
            input()  # Chờ người dùng bấm Enter trước khi về menu
        except:
            pass
        fix_tty()

# =====================================================================
# MAIN
# =====================================================================




def test_delta_license():
    clear_screen()
    print(f"\n{C}--- KIỂM TRA FILE DELTA LICENSE (CHẾ ĐỘ XUYÊN KHÔNG GIAN) ---{RESET}")
    
    # Tạo danh sách các đường dẫn thật (bỏ qua ảo hóa mount của Android)
    dirs_to_check = [
        "/storage/emulated/0/Delta/Internals/Cache",
        "/sdcard/Delta/Internals/Cache",
        "/data/media/0/Delta/Internals/Cache"  # Đường dẫn vật lý tuyệt đối
    ]
    if selected_packages:
        for item in selected_packages:
            pkg = item['pkg']
            dirs_to_check.extend([
                f"/sdcard/Android/media/{pkg}/Delta/Internals/Cache",
                f"/sdcard/Android/data/{pkg}/Delta/Internals/Cache",
                f"/data/media/0/Android/media/{pkg}/Delta/Internals/Cache",
                f"/data/media/0/Android/data/{pkg}/Delta/Internals/Cache"
            ])
    
    dirs_to_check = list(set(dirs_to_check))
    found = False
    
    print(f"{Y}[*] Đang quét {len(dirs_to_check)} thư mục Delta...{RESET}\n")
    for d in dirs_to_check:
        lic_path = f"{d}/license"
        mtime = _get_file_mtime_root(lic_path)
        if mtime > 0:
            found = True
            import time
            t_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            print(f"{G}[✓] Đã tìm thấy: {lic_path}{RESET}")
            print(f"    {C}Cập nhật lúc: {t_str}{RESET}")
            
    if not found:
        print(f"\n{R}[✗] CHƯA tìm thấy file license nào từ game.{RESET}")
        print(f"{Y}Hãy dùng chức năng Auto Key để tool tự bấm 'Receive Key' -> Bypass -> Nhập Key 'FREE_...' -> 'Continue' để Delta tự sinh file license.{RESET}")
        
    fix_tty()
    print(f"\n{Y}Bấm Enter để quay lại Menu...{RESET}")
    try:
        input()
    except:
        pass

def delta_key_menu():
    global AUTO_RESTORE_DELTA_KEY
    while True:
        clear_screen()
        print_banner()
        st_col = G if AUTO_RESTORE_DELTA_KEY == "Enable" else R
        current_k = load_bacon_api_key()
        m_bacon = mask_secret(current_k) if current_k else "Chưa cài đặt"
        print(f"{C}--- QUẢN LÝ DELTA KEY & BACON AUTO BYPASS (KHÔNG CẦN BACKUP) ---{RESET}")
        print(f"1. Trạng thái Auto Bypass & Nạp Key: {st_col}{AUTO_RESTORE_DELTA_KEY}{RESET}")
        print(f"2. Bacon Bypass API Key:              {Y}{m_bacon}{RESET}")
        print(f"{Y}Cơ chế: Click 'Receive Key' -> Bypass -> Nhập Key 'FREE_...' -> Click 'Continue'{RESET}")
        print("-" * 65)
        print(f"[{C}1{RESET}] Bật/Tắt Tự động Bypass & Nhập Key")
        print(f"[{C}2{RESET}] Cấu hình / Cập nhật Bacon API Key")
        print(f"[{C}3{RESET}] Test Bypass 1 Link & Tự động nhập vào game")
        print(f"[{C}4{RESET}] Test Click & Căn chỉnh vị trí ô nhập Key / nút Continue")
        print(f"[{C}5{RESET}] Kiểm tra file License tự sinh của các Package")
        print(f"[{C}6{RESET}] Quay lại Menu chính")
        fix_tty()
        c = safe_input(f"\n{M}Chọn [1-6]: {RESET}")
        if c == '1':
            if getattr(sys.modules[__name__], 'AUTO_RESTORE_DELTA_KEY', "Disable") == "Disable":
                AUTO_RESTORE_DELTA_KEY = "Enable"
                print(f"\n{G}[+] Đã BẬT Auto Restore & Bypass Delta Key!{RESET}")
            else:
                AUTO_RESTORE_DELTA_KEY = "Disable"
                print(f"\n{Y}[*] Đã TẮT Auto Restore & Bypass Delta Key!{RESET}")
            time.sleep(1.5)
        elif c == '2':
            fix_tty()
            new_k = safe_input(f"{M}Nhập Bacon API Key mới: {RESET}").strip()
            if new_k:
                save_bacon_api_key(new_k)
                print(f"\n{G}[+] Đã lưu Bacon API Key ({mask_secret(new_k)})!{RESET}")
            else:
                print(f"\n{Y}[*] Đã hủy.{RESET}")
            time.sleep(1.5)
        elif c == '3':
            fix_tty()
            cur_k = load_bacon_api_key()
            if not cur_k:
                print(f"\n{R}[!] Chưa có Bacon API Key! Vui lòng chọn mục [2] trước.{RESET}")
                time.sleep(2)
                continue
            test_url = safe_input(f"{M}Nhập URL cần Bypass (hoặc Enter để quét tự động từ game): {RESET}").strip()
            if not test_url:
                clip = get_android_clipboard()
                test_url = extract_getkey_url(clip)
                if test_url:
                    print(f"{Y}[*] Tự động lấy URL từ Clipboard: {test_url}{RESET}")
                else:
                    if selected_packages:
                        target_pkg = selected_packages[0]['pkg']
                        print(f"{Y}[*] Đang bắn vào game {target_pkg} để lấy URL triệt để...{RESET}")
                        test_url = obtain_delta_getkey_url(target_pkg, threading.Event(), max_wait_secs=120)
                    if not test_url:
                        print(f"{R}[!] Không thể lấy được link Get Key.{RESET}")
                        time.sleep(2)
                        continue
            print(f"\n{Y}[*] Đang gửi yêu cầu giải mã tới Bacon Bypass API (timeout 90s)...{RESET}")
            try:
                client = BaconBypassClient(api_key=cur_k, timeout=90.0, max_retries=3)
                t0 = time.time()
                res = client.bypass(test_url)
                dur = time.time() - t0
                print(f"\n{G}[✓] GIẢI MÃ THÀNH CÔNG trong {dur:.2f}s!{RESET}")
                print(f"    Kết quả: {C}{res}{RESET}")
                if res.startswith("http://") or res.startswith("https://"):
                    print(f"{Y}[*] Đang gửi request kích hoạt Whitelist HWID...{RESET}")
                    ok = _http_get_ping(res)
                    if ok:
                        print(f"{G}[✓] Đã gửi kích hoạt thành công!{RESET}")
                    else:
                        print(f"{Y}[!] Không thể ping URL kích hoạt.{RESET}")
                else:
                    set_android_clipboard(res)
                    print(f"{G}[✓] Đã sao chép key vào Clipboard!{RESET}")
                    fix_tty()
                    auto_c = safe_input(f"\n{M}Tự động bắn vào game, nhập key và bấm Continue ngay? (Y/n): {RESET}").strip().lower()
                    if auto_c != 'n':
                        close_browser_popups()
                        if selected_packages:
                            target_pkg = selected_packages[0]['pkg']
                            print(f"{Y}[*] Đang bắn vào game {target_pkg}...{RESET}")
                            launch_roblox_and_join_game(target_pkg)
                            print(f"{Y}[*] Chờ 150s (2p30s) cho game load vào server & bảng Welcome Back...{RESET}")
                            time.sleep(150)
                        print(f"{Y}[*] Đang focus ô 'KEY_example', nhập key và bấm Continue...{RESET}")
                        auto_enter_key_and_continue(res)
                        print(f"{G}[✓] Đã hoàn tất nhập key và click Continue!{RESET}")
            except BaconApiException as be:
                print(f"\n{R}[✗] Thất bại: {be}{RESET}")
            fix_tty()
            print(f"\n{Y}Bấm Enter để quay lại...{RESET}")
            try: input()
            except: pass
        elif c == '4':
            global DELTA_PANEL_X_RATIO, DELTA_INPUT_Y_RATIO, DELTA_CONTINUE_Y_RATIO, DELTA_RECEIVE_Y_RATIO
            while True:
                clear_screen()
                print_banner()
                w, h = get_screen_resolution()
                in_x = int(w * DELTA_PANEL_X_RATIO)
                in_y = int(h * DELTA_INPUT_Y_RATIO)
                cont_x = int(w * DELTA_PANEL_X_RATIO)
                cont_y = int(h * DELTA_CONTINUE_Y_RATIO)
                rx = int(w * DELTA_PANEL_X_RATIO)
                ry = int(h * DELTA_RECEIVE_Y_RATIO)
                print(f"{C}=== TEST & CĂN CHỈNH TỌA ĐỘ CLICK DELTA TRỰC TIẾP ==={RESET}")
                print(f"Độ phân giải màn hình: {G}{w} x {h}{RESET}")
                print(f"• Ô nhập key:      Pixel ({in_x}, {in_y})  [X={DELTA_PANEL_X_RATIO*100:.1f}%, Y={DELTA_INPUT_Y_RATIO*100:.1f}%]")
                print(f"• Nút Continue:    Pixel ({cont_x}, {cont_y})  [X={DELTA_PANEL_X_RATIO*100:.1f}%, Y={DELTA_CONTINUE_Y_RATIO*100:.1f}%]")
                print(f"• Nút Receive Key: Pixel ({rx}, {ry})  [X={DELTA_PANEL_X_RATIO*100:.1f}%, Y={DELTA_RECEIVE_Y_RATIO*100:.1f}%]")
                print("-" * 65)
                print(f"[{C}1{RESET}] Tap thử ô 'KEY_example' (Để xem con trỏ / bàn phím có bật lên trên máy)")
                print(f"[{C}2{RESET}] Tap & Nhập thử chuỗi text test vào ô 'KEY_example'")
                print(f"[{C}3{RESET}] Tap thử nút 'Continue'")
                print(f"[{C}4{RESET}] Căn chỉnh tỷ lệ X, Y (nếu máy bị lệch)")
                print(f"[{C}5{RESET}] Quay lại")
                fix_tty()
                sub = safe_input(f"\n{M}Chọn [1-5]: {RESET}").strip()
                if sub == '1':
                    print(f"{Y}[*] Đang thực hiện tap 150ms vào ô ({in_x}, {in_y})...{RESET}")
                    safe_root(f"su -c 'input swipe {in_x} {in_y} {in_x} {in_y} 150'")
                    time.sleep(0.3)
                    safe_root(f"su -c 'input tap {in_x} {in_y}'")
                    time.sleep(0.3)
                    safe_root(f"su -c 'input tap {int(w * 0.790)} {in_y}'")
                    print(f"{G}[✓] Đã tap xong! Hãy nhìn vào màn hình điện thoại xem con trỏ đã nhấp nháy chưa.{RESET}")
                    time.sleep(2.5)
                elif sub == '2':
                    test_str = "FREE_test1234567890abcdef"
                    print(f"{Y}[*] Đang focus và gõ '{test_str}'...{RESET}")
                    set_android_clipboard(test_str)
                    safe_root(f"su -c 'input swipe {in_x} {in_y} {in_x} {in_y} 150'")
                    time.sleep(0.3)
                    safe_root(f"su -c 'input tap {in_x} {in_y}'")
                    time.sleep(0.4)
                    safe_root("su -c 'input keyevent 279 2>/dev/null'")
                    safe_root(f"su -c 'input text \"{test_str}\"'")
                    print(f"{G}[✓] Đã gửi lệnh nhập text! Hãy kiểm tra màn hình game.{RESET}")
                    time.sleep(2.5)
                elif sub == '3':
                    print(f"{Y}[*] Đang click nút Continue tại ({cont_x}, {cont_y})...{RESET}")
                    safe_root(f"su -c 'input swipe {cont_x} {cont_y} {cont_x} {cont_y} 150'")
                    time.sleep(0.2)
                    safe_root(f"su -c 'input tap {cont_x} {cont_y}'")
                    print(f"{G}[✓] Đã click Continue!{RESET}")
                    time.sleep(2)
                elif sub == '4':
                    print(f"\n{Y}Tọa độ hiện tại: X={DELTA_PANEL_X_RATIO:.3f}, Y_input={DELTA_INPUT_Y_RATIO:.3f}, Y_continue={DELTA_CONTINUE_Y_RATIO:.3f}{RESET}")
                    try:
                        nx = safe_input(f"Nhập tỷ lệ X mới [0.70 - 0.95] (Enter giữ {DELTA_PANEL_X_RATIO}): ").strip()
                        if nx: DELTA_PANEL_X_RATIO = float(nx)
                        ny = safe_input(f"Nhập tỷ lệ Y ô input mới [0.25 - 0.50] (Enter giữ {DELTA_INPUT_Y_RATIO}): ").strip()
                        if ny: DELTA_INPUT_Y_RATIO = float(ny)
                        nc = safe_input(f"Nhập tỷ lệ Y nút continue mới [0.40 - 0.60] (Enter giữ {DELTA_CONTINUE_Y_RATIO}): ").strip()
                        if nc: DELTA_CONTINUE_Y_RATIO = float(nc)
                        print(f"{G}[✓] Đã cập nhật tọa độ mới thành công!{RESET}")
                    except Exception as err:
                        print(f"{R}[!] Lỗi nhập số: {err}{RESET}")
                    time.sleep(2)
                elif sub == '5':
                    break
        elif c == '5':
            test_delta_license()
        elif c == '6':
            break

def main():
    global SELECTED_SCRIPT_KEY, selected_packages
    fix_tty()
    if not require_rejoin_key():
        print(f"{R}[✗] Không thể xác thực Tool Rejoin. Chương trình đã dừng.{RESET}")
        return
    load_settings()
    init_download_workspace()
    # Mặc định luôn là script số 1 (Hop Fin_Tail) trừ khi người dùng đã chủ động tùy chỉnh
    if not SELECTED_SCRIPT_KEY or (SELECTED_SCRIPT_KEY not in AUTO_INJECT_SCRIPTS and SELECTED_SCRIPT_KEY not in ["custom", "0"]):
        SELECTED_SCRIPT_KEY = "1"
    # Tự động chọn mặc định các package có đầu 'vip'
    auto_select_vip_packages()
    # Tự động inject script user mặc định (số 1: Hop Fin_Tail)
    inject_user_script()

    while True:
        clear_screen()
        print_banner()
        vip_cnt = len(selected_packages)
        vip_tag = f"{GREEN_MINT}({vip_cnt} VIP Active){RESET}" if vip_cnt > 0 else f"{Y}(Chưa có VIP){RESET}"
        def_tag = " [Mặc định]" if SELECTED_SCRIPT_KEY == "1" else ""
        raw_sc = AUTO_INJECT_SCRIPTS.get(SELECTED_SCRIPT_KEY, {}).get("name", "Custom" if SELECTED_SCRIPT_KEY == "custom" else "Tắt")
        sc_display = f"{GOLD_NEON}[{raw_sc}{def_tag}]{RESET}"

        term_w = get_terminal_width()
        inner_w = term_w - 2

        menu_title = " ⚡ MENU ĐIỀU KHIỂN "
        dashes_m = max(2, inner_w - visible_len(menu_title) - 1)
        print(f"{CYAN_NEON}╭─{menu_title}{'─' * dashes_m}╮{RESET}")
        print(f"{CYAN_NEON}│{RESET}{fit_ansi('', inner_w)}{CYAN_NEON}│{RESET}")
        main_items = [
            f"   {BOLD}{C}[1]{RESET} {WHITE}Quét & Chọn Package Roblox{RESET}    {vip_tag}",
            f"   {BOLD}{C}[2]{RESET} {WHITE}Cài Đặt Hệ Thống & Script{RESET}     {sc_display}",
            f"   {BOLD}{C}[3]{RESET} {WHITE}Bắt Đầu Auto Rejoin{RESET}            {BLUE_ICE}(Live Dashboard){RESET}",
            f"   {BOLD}{C}[4]{RESET} {WHITE}Login Cookie Vào App{RESET}           {PURPLE_NEON}(Direct Inject){RESET}",
            f"   {BOLD}{C}[5]{RESET} {WHITE}Quản Lý Delta Key & Bypass{RESET}     {GOLD_NEON}(Bacon API){RESET}",
            f"   {BOLD}{C}[6]{RESET} {WHITE}Kiểm Tra License Delta{RESET}         {GRAY_LIGHT}(Test File){RESET}",
            f"   {BOLD}{C}[7]{RESET} {WHITE}Trạng Thái Acc / Captcha{RESET}       {PINK_NEON}(Diagnostic){RESET}",
            f"   {BOLD}{R}[8]{RESET} {WHITE}Thoát Chương Trình{RESET}"
        ]
        for mi in main_items:
            print(f"{CYAN_NEON}│{RESET}{fit_ansi(mi, inner_w)}{CYAN_NEON}│{RESET}")
        print(f"{CYAN_NEON}│{RESET}{fit_ansi('', inner_w)}{CYAN_NEON}│{RESET}")
        print(f"{CYAN_NEON}╰{'─' * inner_w}╯{RESET}")
# box printed above
        try:
            fix_tty()
            choice = safe_input(f"\n{BOLD}{CYAN_NEON}HuDy{RESET} {PINK_NEON}❯{RESET} ").strip()
        except EOFError:
            fix_tty()
            continue
        if choice == '1':
            select_package_menu()
        elif choice == '2':
            settings_menu()
        elif choice == '3':
            start_auto_rejoin()
        elif choice == '4':
            login_via_cookie()
        elif choice == '5':
            delta_key_menu()
        elif choice == '6':
            test_delta_license()
        elif choice == '7':
            account_captcha_check_menu()
        elif choice == '8':
            clear_screen()
            print(f"{G}Tạm biệt!{RESET}")
            fix_tty()
            break

if __name__ == "__main__":
    fix_tty()
    main()
