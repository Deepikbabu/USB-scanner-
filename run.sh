#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

log() { printf '%s\n' "$*"; }
die() { log "[ERROR] $*"; exit 1; }
as_root() {
    if [[ ${EUID:-$(id -u)} -eq 0 ]]; then "$@"; else sudo "$@"; fi
}

install_official_clamav_arm64() {
    [[ "$(dpkg --print-architecture)" == "arm64" ]] || return 1
    log "[*] Debian ClamAV package unavailable; checking official clamav.net ARM64 download..."
    local url tmp
    url="$(python3 - <<'PY'
import re, urllib.parse, urllib.request
page = urllib.request.urlopen('https://www.clamav.net/downloads', timeout=30).read().decode()
matches = re.findall(r'href=["\']([^"\']*clamav-[0-9.]+\.linux\.aarch64\.deb)["\']', page)
if not matches:
    matches = ['https://www.clamav.net/downloads/production/clamav-1.5.3.linux.aarch64.deb']
print(urllib.parse.urljoin('https://www.clamav.net/downloads', matches[0]))
PY
)"
    tmp="$(mktemp --suffix=.deb)"
    trap 'rm -f "$tmp"' RETURN
    curl --fail --location --proto '=https' --tlsv1.2 "$url" --output "$tmp"
    dpkg-deb --info "$tmp" >/dev/null
    as_root apt-get install -y "$tmp"
}

install_system_dependencies() {
    command -v apt-get >/dev/null || die "Raspberry Pi OS/Debian with apt-get is required."
    local packages=(python3 python3-venv python3-dev build-essential curl ca-certificates
                    yara libyara-dev clamav clamav-daemon usbguard udisks2 usbutils libgl1 libegl1)
    local missing=() package
    for package in "${packages[@]}"; do
        dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed' || missing+=("$package")
    done
    if ((${#missing[@]})); then
        log "[*] Installing missing system dependencies: ${missing[*]}"
        as_root apt-get update
        if ! as_root apt-get install -y "${missing[@]}"; then
            install_official_clamav_arm64 || die "System dependency installation failed."
            local remaining=()
            for package in "${missing[@]}"; do
                [[ "$package" == "clamav" || "$package" == "clamav-daemon" ]] || remaining+=("$package")
            done
            ((${#remaining[@]} == 0)) || as_root apt-get install -y "${remaining[@]}"
        fi
    else
        log "[+] System dependencies already installed."
    fi
}

setup_python() {
    [[ -d .venv ]] || python3 -m venv .venv
    .venv/bin/python3 -m pip install --quiet --upgrade pip
    .venv/bin/python3 -m pip install --quiet -r requirements.txt
    # Dashboard and read-only diagnostic commands do not need to rewrite an
    # existing signature database. The root backend initializes it again when
    # it starts. This also supports databases created by the systemd service.
    if [[ ! -e malware_hashes.db || -w malware_hashes.db ]]; then
        .venv/bin/python3 db_init.py
    else
        log "[+] Using existing read-only malware database: $ROOT/malware_hashes.db"
    fi
}

setup_clamav() {
    command -v clamscan >/dev/null || die "ClamAV engine is unavailable after installation."
    if ! find /var/lib/clamav -maxdepth 1 -type f \( -name '*.cvd' -o -name '*.cld' \) -print -quit 2>/dev/null | grep -q .; then
        log "[*] Downloading initial ClamAV virus definitions..."
        as_root systemctl stop clamav-freshclam 2>/dev/null || true
        as_root freshclam || die "FreshClam could not download virus definitions. Check network and system time."
    fi
    as_root systemctl enable --now clamav-freshclam 2>/dev/null || true
    as_root systemctl enable --now clamav-daemon 2>/dev/null || true
}

setup_usbguard() {
    command -v usbguard >/dev/null || die "USBGuard is required for pre-authorization HID isolation."
    local policy=/etc/usbguard/rules.conf
    if [[ ! -s "$policy" ]]; then
        log "[*] Creating USBGuard baseline from devices connected right now."
        log "[!] Disconnect every untrusted USB/HID device before continuing."
        local tmp
        tmp="$(mktemp)"
        as_root usbguard generate-policy >"$tmp"
        as_root install -m 0600 "$tmp" "$policy"
        rm -f "$tmp"
    fi
    if [[ -f /etc/usbguard/usbguard-daemon.conf ]]; then
        as_root sed -i 's/^ImplicitPolicyTarget=.*/ImplicitPolicyTarget=block/' /etc/usbguard/usbguard-daemon.conf
        as_root grep -q '^ImplicitPolicyTarget=' /etc/usbguard/usbguard-daemon.conf || \
            echo 'ImplicitPolicyTarget=block' | as_root tee -a /etc/usbguard/usbguard-daemon.conf >/dev/null
    fi
    as_root systemctl enable --now usbguard
}

verify_usbguard_enforcement() {
    command -v usbguard >/dev/null || die "USBGuard is required for pre-driver HID isolation."
    as_root systemctl is-active --quiet usbguard || die "USBGuard service is not active; refusing to start the scanner."
    local config=/etc/usbguard/usbguard-daemon.conf
    if [[ ! -f "$config" ]] || ! grep -Eq '^\s*ImplicitPolicyTarget\s*=\s*block\s*$' "$config"; then
        die "USBGuard is not configured with ImplicitPolicyTarget=block; refusing to start."
    fi
    as_root usbguard list-devices >/dev/null || die "USBGuard is not responding; refusing to start the scanner."
}

preflight() {
    log "[*] Running security-engine preflight..."
    .venv/bin/python3 tools/preflight.py
}

cleanup_stale_isolation() {
    local base=/tmp/usb_scanner_quarantine target
    [[ -d "$base" ]] || return 0
    while IFS= read -r target; do
        [[ "$target" == "$base"/* ]] || continue
        log "[*] Releasing stale scanner mount: $target"
        as_root umount "$target" 2>/dev/null || true
    done < <(findmnt -rn -o TARGET 2>/dev/null | grep "^${base}/" || true)
}

reconcile_usbguard_state() {
    # Reload only persistent policy; transient instance decisions from a crashed
    # scanner are discarded. Verified trusted HID instances are repaired next.
    as_root systemctl restart usbguard
    as_root "$ROOT/.venv/bin/python3" "$ROOT/tools/hid_trust.py" repair || true
}

install_service() {
    local source="$ROOT/config/usb-scanner.service" failure_source="$ROOT/config/usb-scanner-failure.service" tmp
    [[ -f "$source" ]] || die "Service template is missing."
    [[ -f "$failure_source" ]] || die "Service failure template is missing."
    as_root groupadd --force usb-scanner
    local desktop_user="${SUDO_USER:-${USER:-pi}}"
    [[ "$desktop_user" == "root" ]] || as_root usermod -a -G usb-scanner "$desktop_user"
    tmp="$(mktemp)"
    sed "s|__PROJECT_ROOT__|$ROOT|g" "$source" >"$tmp"
    as_root install -m 0644 "$tmp" /etc/systemd/system/usb-scanner.service
    rm -f "$tmp"
    tmp="$(mktemp)"
    sed "s|__PROJECT_ROOT__|$ROOT|g" "$failure_source" >"$tmp"
    as_root install -m 0644 "$tmp" /etc/systemd/system/usb-scanner-failure.service
    rm -f "$tmp"
    as_root install -d -m 0755 /etc/systemd/journald.conf.d
    tmp="$(mktemp)"
    printf '%s\n' '[Journal]' 'SystemMaxUse=200M' 'RuntimeMaxUse=50M' 'MaxFileSec=1day' >"$tmp"
    as_root install -m 0644 "$tmp" /etc/systemd/journald.conf.d/usb-scanner-limits.conf
    rm -f "$tmp"
    as_root systemctl restart systemd-journald
    as_root systemctl daemon-reload
    as_root systemctl enable usb-scanner.service
    as_root systemctl restart usb-scanner.service
    log "[+] USB Scanner service installed and started."
    if [[ "$desktop_user" != "root" ]]; then
        log "[+] Dashboard access configured for $desktop_user. No logout is required."
        log "[*] Start it with: ./run.sh --dashboard"
    fi
    log "[*] View logs: journalctl -u usb-scanner -f"
}

reset_usbguard_policy() {
    log "[!] Disconnect every untrusted USB device now. Regenerating policy from connected devices."
    as_root systemctl stop usbguard 2>/dev/null || true
    local tmp
    tmp="$(mktemp)"
    as_root usbguard generate-policy >"$tmp"
    [[ -s "$tmp" ]] || die "USBGuard generated an empty policy; previous policy was not changed."
    [[ ! -e /etc/usbguard/rules.conf ]] || as_root cp /etc/usbguard/rules.conf /etc/usbguard/rules.conf.bak
    as_root install -m 0600 "$tmp" /etc/usbguard/rules.conf
    rm -f "$tmp"
    as_root systemctl start usbguard
    log "[+] USBGuard baseline regenerated."
}

if [[ "${1:-}" == "--reset-usbguard" ]]; then
    install_system_dependencies
    reset_usbguard_policy
    exit 0
fi

if [[ "${1:-}" == "--install-service" ]]; then
    install_system_dependencies
    setup_python
    setup_clamav
    setup_usbguard
    install_service
    exit 0
fi

if [[ "${1:-}" == "--uninstall-service" ]]; then
    as_root systemctl disable --now usb-scanner.service 2>/dev/null || true
    as_root rm -f /etc/systemd/system/usb-scanner.service
    as_root rm -f /etc/systemd/system/usb-scanner-failure.service
    as_root rm -f /etc/systemd/journald.conf.d/usb-scanner-limits.conf
    as_root systemctl daemon-reload
    log "[+] USB Scanner service removed."
    exit 0
fi

if [[ "${1:-}" == "--dashboard" ]]; then
    if [[ "$EUID" -eq 0 ]]; then
        die "Run the dashboard as the desktop user: ./run.sh --dashboard (without sudo)"
    fi
    setup_python
    if ! systemctl is-active --quiet usb-scanner.service; then
        die "Backend service is not active. Run: sudo ./run.sh --install-service"
    fi
    if ! id -nG | tr ' ' '\n' | grep -qx usb-scanner; then
        # usermod updates the account database immediately, but an existing
        # desktop login does not inherit the new supplementary group. Start
        # this process with the protected group automatically—no logout/reboot.
        dashboard_user="${SUDO_USER:-${USER:-}}"
        if [[ -n "$dashboard_user" ]] && id -nG "$dashboard_user" | tr ' ' '\n' | grep -qx usb-scanner; then
            printf -v root_quoted '%q' "$ROOT"
            log "[*] Activating secure dashboard access for this launch..."
            exec sg usb-scanner -c "cd $root_quoted && exec ./run.sh --dashboard"
        fi
        die "Dashboard access is not configured. Run once: sudo ./run.sh --install-service"
    fi
    [[ -S /run/usb-scanner/backend.sock ]] || \
        die "Backend socket is missing. Check: sudo journalctl -u usb-scanner -n 100"
    [[ -r /run/usb-scanner/backend.sock && -w /run/usb-scanner/backend.sock ]] || \
        die "Backend socket is not accessible. Re-run once: sudo ./run.sh --install-service"
    export PYTHONPATH="$ROOT"
    exec "$ROOT/.venv/bin/python3" "$ROOT/ui/sentinel/main_sys.py"
fi

if [[ "${1:-}" == "--list-hid" || "${1:-}" == "--trust-hid" || \
      "${1:-}" == "--untrust-hid" || "${1:-}" == "--repair-input" || \
      "${1:-}" == "--approve-hid" || "${1:-}" == "--revoke-hid" || \
      "${1:-}" == "--rescan-hid" ]]; then
    install_system_dependencies
    setup_python
    setup_usbguard
    case "$1" in
        --list-hid) action=list ;;
        --trust-hid) action=trust ;;
        --untrust-hid) action=untrust ;;
        --repair-input) action=repair ;;
        --approve-hid) action=approve ;;
        --revoke-hid) action=revoke ;;
        --rescan-hid) action=rescan ;;
    esac
    as_root "$ROOT/.venv/bin/python3" "$ROOT/tools/hid_trust.py" "$action"
    exit $?
fi

if [[ "${1:-}" == "--status" ]]; then
    setup_python
    preflight
    as_root usbguard list-devices
    exit 0
fi

if [[ "${1:-}" == "--test-yara" ]]; then
    setup_python
    .venv/bin/python3 -c 'from backend.scanner.yara_engine import load_rules,last_load_error; assert load_rules(), last_load_error(); print("YARA READY")'
    exit 0
fi

if [[ "${1:-}" == "--test-clamav" ]]; then
    install_system_dependencies
    setup_clamav
    tmp="$(mktemp --suffix=.com)"
    trap 'rm -f "$tmp"' EXIT
    printf '%s' 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' >"$tmp"
    set +e
    clamscan --no-summary "$tmp"
    result=$?
    set -e
    [[ $result -eq 1 ]] || die "ClamAV did not detect the EICAR test file (exit=$result)."
    log "[+] ClamAV EICAR detection READY"
    exit 0
fi

if [[ "${1:-}" == "--configure-nvd" ]]; then
    read -r -s -p "Enter your individual NVD API key (input hidden): " nvd_key
    printf '\n'
    [[ -n "$nvd_key" ]] || die "NVD key cannot be empty."
    as_root install -d -m 0700 /etc/usb-scanner
    tmp="$(mktemp)"
    printf 'NVD_API_KEY=%s\n' "$nvd_key" >"$tmp"
    as_root install -m 0600 "$tmp" /etc/usb-scanner/nvd.env
    rm -f "$tmp"
    log "[+] NVD API key configured without storing it in the repository."
    exit 0
fi

if [[ "${1:-}" == "--test-nvd" ]]; then
    setup_python
    .venv/bin/python3 tools/test_nvd.py
    exit 0
fi

if [[ "${1:-}" == "--configure-email" || "${1:-}" == "--test-email" || \
      "${1:-}" == "--email-status" || "${1:-}" == "--enable-email" || \
      "${1:-}" == "--disable-email" || "${1:-}" == "--retry-email" ]]; then
    setup_python
    case "$1" in
        --configure-email) action=configure ;;
        --test-email) action=test ;;
        --email-status) action=status ;;
        --enable-email) action=enable ;;
        --disable-email) action=disable ;;
        --retry-email) action=retry ;;
    esac
    as_root "$ROOT/.venv/bin/python3" "$ROOT/tools/email_admin.py" "$action"
    exit $?
fi

if [[ "${1:-}" == "--simulate" ]]; then
    setup_python
    .venv/bin/python3 tools/simulate_security_flow.py "${2:-all}"
    exit $?
fi

if [[ "${1:-}" == "--validate-dashboard" ]]; then
    setup_python
    QT_QPA_PLATFORM=offscreen .venv/bin/python3 tools/validate_dashboard.py
    exit $?
fi

if [[ "${1:-}" == "--validate" ]]; then
    install_system_dependencies
    setup_python
    setup_clamav
    .venv/bin/python3 tools/validate_backend.py
    exit $?
fi

if [[ "${1:-}" == "--list-trusted-storage" || "${1:-}" == "--forget-storage" || \
      "${1:-}" == "--approve-storage" || "${1:-}" == "--revoke-storage" || \
      "${1:-}" == "--rescan-storage" ]]; then
    setup_python
    action=list
    [[ "$1" == "--forget-storage" ]] && action=forget
    [[ "$1" == "--approve-storage" ]] && action=approve
    [[ "$1" == "--revoke-storage" ]] && action=revoke
    [[ "$1" == "--rescan-storage" ]] && action=rescan
    as_root "$ROOT/.venv/bin/python3" "$ROOT/tools/storage_trust.py" "$action"
    exit $?
fi

if [[ "${1:-}" == "--list-quarantine" ]]; then
    setup_python
    as_root "$ROOT/.venv/bin/python3" "$ROOT/changed.py" --quarantine list
    exit $?
fi

if [[ "${1:-}" == "--restore-quarantine" || "${1:-}" == "--delete-quarantine" ]]; then
    setup_python
    action=restore
    [[ "$1" == "--delete-quarantine" ]] && action=delete
    as_root "$ROOT/.venv/bin/python3" "$ROOT/changed.py" --quarantine "$action"
    exit $?
fi

if [[ "${1:-}" == "--service-run" ]]; then
    cleanup_stale_isolation
    reconcile_usbguard_state
    verify_usbguard_enforcement
    export PYTHONPATH="$ROOT"
    exec "$ROOT/.venv/bin/python3" "$ROOT/changed.py" --cli-auto
fi

if [[ "${1:-}" == "--check" ]]; then
    install_system_dependencies
    setup_python
    setup_clamav
    setup_usbguard
    preflight
    exit 0
fi

if [[ -n "${1:-}" ]]; then
    die "Unknown option: $1. See README.md for supported management and test commands."
fi

install_system_dependencies
setup_python
setup_clamav
setup_usbguard
preflight
verify_usbguard_enforcement
cleanup_stale_isolation
reconcile_usbguard_state

# Remove the legacy permanent ignore rule. Isolation is now enforced by the
# backend's explicit read-only mount instead of making clean remount impossible.
if [[ -e /etc/udev/rules.d/99-hide-usb-from-udisks.rules ]]; then
    as_root rm -f /etc/udev/rules.d/99-hide-usb-from-udisks.rules
    as_root udevadm control --reload-rules
fi

# Authenticate once in the launching terminal. The GUI backend uses sudo -n so
# it can never hang behind an invisible password prompt.
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    sudo -v
fi

export PYTHONPATH="$ROOT"
log "[*] Starting CLI USB Security Engine (Ctrl+C to stop)..."
exec sudo -n "$ROOT/.venv/bin/python3" "$ROOT/changed.py" --cli-auto
