#!/data/data/com.termux/files/usr/bin/bash

# =====================================================================
# TOOL REJOIN SETUP SCRIPT FOR TERMUX (HIGH-SPEED & VISIBLE PROGRESS)
# =====================================================================

C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_RESET="\033[0m"

echo -e "${C_CYAN}[*] Đang kiểm tra & khởi tạo môi trường Termux...${C_RESET}"

# Xác thực key trước khi cài phụ thuộc hoặc tải tool.
printf "${C_YELLOW}[?] Nhập Rejoin key được quản trị viên cung cấp: ${C_RESET}"
IFS= read -r HUDY_REJOIN_KEY
if [ -z "$HUDY_REJOIN_KEY" ]; then
    echo -e "${C_RED}[✗] Key không được để trống.${C_RESET}"
    exit 1
fi

DEVICE_FP=""
for DEVICE_PART in "$(settings get secure android_id 2>/dev/null)" "$(getprop ro.serialno 2>/dev/null)" "$(getprop ro.product.model 2>/dev/null)"; do
    case "${DEVICE_PART}" in
        ""|null|unknown) ;;
        *) DEVICE_FP="${DEVICE_FP:+${DEVICE_FP}|}${DEVICE_PART}" ;;
    esac
done
DEVICE_FP="${DEVICE_FP:-hudy-rejoin-device}"
VERIFY_PAYLOAD="{\"token\":\"${HUDY_REJOIN_KEY}\",\"fingerprint\":\"${DEVICE_FP}\",\"deviceName\":\"Termux installer\",\"version\":\"installer-1\"}"
VERIFY_RESPONSE="$(curl -fsS --max-time 20 -A 'HuDy-Rejoin/installer-1' -H 'Content-Type: application/json' -d "$VERIFY_PAYLOAD" https://hudyy.com/api/rejoin/verify 2>/dev/null || true)"
unset HUDY_REJOIN_KEY VERIFY_PAYLOAD

if ! printf '%s' "$VERIFY_RESPONSE" | grep -q '"ok":true'; then
    echo -e "${C_RED}[✗] Key không hợp lệ, đã bị thu hồi, hết slot thiết bị hoặc máy chủ không thể xác thực.${C_RESET}"
    exit 1
fi
unset VERIFY_RESPONSE DEVICE_FP DEVICE_PART
echo -e "${C_GREEN}[✓] Key hợp lệ. Bắt đầu cài đặt Tool Rejoin.${C_RESET}"

# 1. Dọn dẹp tiến trình apt/dpkg bị treo & xóa file lock cũ
killall -9 apt apt-get dpkg dpkg-deb >/dev/null 2>&1 || true
rm -f /data/data/com.termux/files/usr/var/lib/dpkg/lock*
rm -f /data/data/com.termux/files/usr/var/cache/apt/archives/lock
rm -f /data/data/com.termux/files/usr/var/lib/apt/lists/lock

# 2. Yêu cầu quyền bộ nhớ (Thông báo rõ ràng tránh treo chờ popup)
if [ ! -d "$HOME/storage" ]; then
    echo -e "${C_YELLOW}[!] NẾU HỆ ĐIỀU HÀNH HIỆN POPUP HỎI QUYỀN BỘ NHỚ -> HÃY BẤM 'CHO PHÉP' (ALLOW)...${C_RESET}"
    termux-setup-storage
    sleep 2
fi

# 3. Cập nhật gói hệ thống bằng 'pkg' (Tự động chọn Mirror nhanh nhất & hiển thị tiến trình live)
export DEBIAN_FRONTEND=noninteractive
echo -e "${C_CYAN}[*] Đang tải & cài đặt gói phụ thuộc (python, sqlite, tsu, curl, procps)...${C_RESET}"
echo -e "${C_YELLOW}[i] Quá trình này tải khoảng 30-50MB, vui lòng chờ trong giây lát...${C_RESET}"

pkg update -y -o Dpkg::Options::="--force-confold"
pkg install python sqlite tsu curl ncurses-utils procps -y -o Dpkg::Options::="--force-confold"

# 4. Tải Tool Rejoin mới nhất
echo -e "${C_CYAN}[*] Đang tải file script Tool Rejoin (hudy.py)...${C_RESET}"
curl -fLs https://raw.githubusercontent.com/huuduydz/HuDy_Tool/refs/heads/main/hudy.py -o ~/hudy.py
if [ ! -s ~/hudy.py ]; then
    echo -e "${C_RED}[✗] Không thể tải Tool Rejoin từ GitHub.${C_RESET}"
    exit 1
fi
chmod +x ~/hudy.py

# 5. Thiết lập Alias tự động
if ! grep -q 'alias hudy=' ~/.bashrc 2>/dev/null; then
    echo 'alias hudy="python ~/hudy.py"' >> ~/.bashrc
    echo 'alias hudy4="python ~/hudy.py"' >> ~/.bashrc
fi

# Nạp alias vào phiên làm việc hiện tại
alias hudy="python ~/hudy.py" 2>/dev/null || true

echo -e "\n${C_GREEN}[✓] SETUP THÀNH CÔNG HOÀN TẤT!${C_RESET}"
echo -e "${C_YELLOW}[i] Bạn có thể gõ ngay lệnh: ${C_CYAN}hudy${C_YELLOW} hoặc ${C_CYAN}python ~/hudy.py${C_YELLOW} để mở tool.${C_RESET}\n"
