#!/usr/bin/env bash
# ==============================================================================
# Скрипт автоматического развертывания COPP-RAS на Ubuntu Server (24.04 / 26.04)
# Домен: ras.copp82.ru | Служба: ras.service | Репозиторий: git@github.com:NKVD2023/copp-ras.git
# ==============================================================================

set -euo pipefail

# ── Цвета для вывода в терминал ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} ${BOLD}$*${NC}"; }
warn()    { echo -e "${YELLOW}[ВНИМАНИЕ]${NC} $*"; }
error()   { echo -e "${RED}[ОШИБКА]${NC} $*" >&2; }

# ── Параметры развертывания ───────────────────────────────────────────────────
DOMAIN="ras.copp82.ru"
SERVICE_NAME="ras"
PROJECT_DIR="/var/www/copp-ras"
GIT_REPO="git@github.com:NKVD2023/copp-ras.git"
GIT_BRANCH="main"
APP_USER="www-data"
APP_PORT="5000"

# Определяем пользователя, вызвавшего sudo (например, admin-copp)
TARGET_USER="${SUDO_USER:-$(whoami)}"
if [ "$TARGET_USER" = "root" ]; then
    USER_HOME="/root"
else
    USER_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
fi

echo -e "${BOLD}${BLUE}"
echo "======================================================================"
echo "          АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ СИСТЕМЫ COPP-RAS               "
echo "              Домен: https://${DOMAIN}                                "
echo "              Служба: ${SERVICE_NAME}.service                         "
echo "======================================================================"
echo -e "${NC}"

# ── Проверка запуска с правами суперпользователя ─────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Этот скрипт необходимо запускать с правами sudo: sudo bash install-ras.sh"
    exit 1
fi

info "Целевой пользователь системы: ${BOLD}${TARGET_USER}${NC} (Домашняя папка: ${USER_HOME})"
info "Каталог проекта: ${BOLD}${PROJECT_DIR}${NC}"

# ==============================================================================
# ШАГ 1: Поиск и установка SSL-сертификатов (*.copp82.ru)
# ==============================================================================
echo ""
echo -e "${BOLD}=== [1/9] Настройка SSL-сертификатов для ${DOMAIN} ===${NC}"

CERT_TXT=""
INTER_TXT=""
ROOT_TXT=""
KEY_TXT=""

SEARCH_DIRS=(
    "$(pwd)"
    "$(dirname "$0")"
    "/home/admin-copp"
    "${USER_HOME}"
    "/root"
)

find_cert_file() {
    local pattern="$1"
    for dir in "${SEARCH_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            local match
            match=$(find "$dir" -maxdepth 1 -name "$pattern" 2>/dev/null | head -n 1 || true)
            if [ -n "$match" ] && [ -f "$match" ]; then
                echo "$match"
                return 0
            fi
        fi
    done
    return 1
}

CERT_TXT=$(find_cert_file "*certificate*.txt" || true)
INTER_TXT=$(find_cert_file "*intermediate*.txt" || true)
ROOT_TXT=$(find_cert_file "*rootCA*.txt" || true)
KEY_TXT=$(find_cert_file "*private*.txt" || true)

if [ -z "$CERT_TXT" ] || [ -z "$INTER_TXT" ] || [ -z "$KEY_TXT" ]; then
    error "Не найдены необходимые файлы сертификатов!"
    echo "Требуются файлы: *certificate*.txt, *intermediate*.txt, *private*.txt"
    echo "Поместите их в текущую папку или в /home/admin-copp и перезапустите скрипт."
    exit 1
fi

info "Найден сертификат: ${CERT_TXT}"
info "Найден промежуточный CA: ${INTER_TXT}"
[ -n "$ROOT_TXT" ] && info "Найден корневой CA: ${ROOT_TXT}"
info "Найден приватный ключ: ${KEY_TXT}"

mkdir -p /etc/ssl/certs /etc/ssl/private

SSL_CERT_PATH="/etc/ssl/certs/copp82.ru_fullchain.crt"
SSL_KEY_PATH="/etc/ssl/private/copp82.ru.key"

# Безопасное объединение цепочки сертификатов (с гарантированным переносом строк)
> "$SSL_CERT_PATH"
cat "$CERT_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
cat "$INTER_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
if [ -n "$ROOT_TXT" ] && [ -f "$ROOT_TXT" ]; then
    cat "$ROOT_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
fi

# Установка приватного ключа
cp "$KEY_TXT" "$SSL_KEY_PATH"

chmod 644 "$SSL_CERT_PATH"
chmod 600 "$SSL_KEY_PATH"
success "SSL-сертификаты успешно объединены и установлены в /etc/ssl/"

# ==============================================================================
# ШАГ 2: Обновление системы и установка необходимых пакетов
# ==============================================================================
echo ""
echo -e "${BOLD}=== [2/9] Установка системных пакетов Ubuntu ===${NC}"

export DEBIAN_FRONTEND=noninteractive
info "Обновление индексов APT..."
apt-get update -y

info "Установка Python3, Nginx, Git, SQLite и зависимостей сборки..."
apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    curl \
    nginx \
    ufw \
    sqlite3 \
    libsqlite3-dev

success "Системные пакеты установлены."

# ==============================================================================
# ШАГ 3: Проверка и настройка SSH-доступа к GitHub
# ==============================================================================
echo ""
echo -e "${BOLD}=== [3/9] Настройка SSH-доступа к GitHub для пользователя ${TARGET_USER} ===${NC}"

SSH_DIR="${USER_HOME}/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

SSH_KEY="${SSH_DIR}/id_ed25519"
if [ ! -f "$SSH_KEY" ] && [ ! -f "${SSH_DIR}/id_rsa" ]; then
    info "SSH-ключ не найден. Генерируем новый ключ ed25519..."
    sudo -u "$TARGET_USER" ssh-keygen -t ed25519 -C "deploy-ras@copp82.ru" -f "$SSH_KEY" -N ""
    chmod 600 "$SSH_KEY"
    chmod 644 "${SSH_KEY}.pub"
fi

# Добавляем github.com в доверенные хосты
info "Добавление github.com в known_hosts..."
touch "${SSH_DIR}/known_hosts"
ssh-keyscan -H github.com 2>/dev/null >> "${SSH_DIR}/known_hosts" || true
chown -R "${TARGET_USER}:${TARGET_USER}" "$SSH_DIR"

# Проверка доступа к GitHub
info "Проверка SSH-подключения к GitHub..."
set +e
sudo -u "$TARGET_USER" ssh -T -o StrictHostKeyChecking=accept-new git@github.com 2>&1 | grep -E "(successfully authenticated|Hi)" >/dev/null
SSH_STATUS=$?
set -e

if [ $SSH_STATUS -ne 0 ]; then
    PUB_KEY_FILE="${SSH_KEY}.pub"
    [ ! -f "$PUB_KEY_FILE" ] && PUB_KEY_FILE="${SSH_DIR}/id_rsa.pub"

    echo ""
    warn "========================================================================"
    warn "ВАШ СЕРВЕР ПОКА НЕ АВТОРИЗОВАН В GITHUB!"
    warn "Скопируйте публичный SSH-ключ ниже и добавьте его в Deploy Keys репозитория:"
    warn "👉 https://github.com/NKVD2023/copp-ras/settings/keys"
    warn "========================================================================"
    echo ""
    echo -e "${BOLD}${GREEN}"
    cat "$PUB_KEY_FILE"
    echo -e "${NC}"
    echo ""
    read -r -p "После добавления ключа на GitHub нажмите [Enter] для продолжения..."

    # Повторная проверка
    sudo -u "$TARGET_USER" ssh -T -o StrictHostKeyChecking=accept-new git@github.com 2>&1 || true
fi
success "SSH-доступ к GitHub готов."

# ==============================================================================
# ШАГ 4: Клонирование репозитория проекта
# ==============================================================================
echo ""
echo -e "${BOLD}=== [4/9] Клонирование репозитория в ${PROJECT_DIR} ===${NC}"

mkdir -p /var/www

if [ -d "${PROJECT_DIR}/.git" ]; then
    info "Каталог проекта уже существует. Подтягиваем обновления..."
    cd "$PROJECT_DIR"
    sudo -u "$TARGET_USER" git fetch origin "$GIT_BRANCH"
    sudo -u "$TARGET_USER" git checkout "$GIT_BRANCH"
    sudo -u "$TARGET_USER" git pull origin "$GIT_BRANCH"
else
    info "Клонирование ветки ${GIT_BRANCH} из ${GIT_REPO}..."
    sudo -u "$TARGET_USER" git clone -b "$GIT_BRANCH" "$GIT_REPO" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

success "Репозиторий актуализирован (ветка ${GIT_BRANCH})."

# ==============================================================================
# ШАГ 5: Виртуальное окружение Python и зависимости
# ==============================================================================
echo ""
echo -e "${BOLD}=== [5/9] Настройка виртуального окружения Python ===${NC}"

VENV_DIR="${PROJECT_DIR}/venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Создание виртуального окружения в ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
fi

info "Обновление pip, setuptools, wheel..."
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel --quiet

info "Установка зависимостей проекта (+ gunicorn)..."
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" gunicorn --quiet

success "Зависимости Python успешно установлены."

# ==============================================================================
# ШАГ 6: Служебные директории, конфиги и точка входа WSGI
# ==============================================================================
echo ""
echo -e "${BOLD}=== [6/9] Создание директорий, wsgi.py и конфигурации ===${NC}"

# Папки для загрузки файлов и бэкапов
mkdir -p "${PROJECT_DIR}/app/uploads/reports"
mkdir -p "${PROJECT_DIR}/backups"
mkdir -p "${PROJECT_DIR}/scripts"
mkdir -p "/var/log/${SERVICE_NAME}"

# Генерация wsgi.py (если отсутствует в репозитории)
if [ ! -f "${PROJECT_DIR}/wsgi.py" ]; then
    info "Генерация точки входа wsgi.py..."
    cat > "${PROJECT_DIR}/wsgi.py" <<'EOF'
import os
from app import create_app
from config import config_map

config_name = os.environ.get('FLASK_CONFIG', 'production')
app = create_app(config_map.get(config_name, config_map['default']))

if __name__ == '__main__':
    app.run()
EOF
fi

# Генерация случайного SECRET_KEY (если отсутствует)
if [ ! -f "${PROJECT_DIR}/.secret_key" ]; then
    info "Генерация криптографического ключа сессий .secret_key..."
    python3 -c "import secrets; print(secrets.token_hex(32))" > "${PROJECT_DIR}/.secret_key"
    chmod 600 "${PROJECT_DIR}/.secret_key"
fi

# Файл .env
cat > "${PROJECT_DIR}/.env" <<EOF
FLASK_CONFIG=production
DATABASE_URL=sqlite:///${PROJECT_DIR}/reports.db
SECRET_KEY=$(cat "${PROJECT_DIR}/.secret_key")
EOF
chmod 600 "${PROJECT_DIR}/.env"

# Инициализация пустой базы (если файла reports.db ещё нет)
if [ ! -f "${PROJECT_DIR}/reports.db" ]; then
    info "Создание структуры таблиц базы данных..."
    "${VENV_DIR}/bin/python" -c "
from app import create_app
from app.extensions import db
from config import config_map
app = create_app(config_map['production'])
with app.app_context():
    db.create_all()
" || true
fi

success "Файлы конфигурации подготовлены."

# ==============================================================================
# ШАГ 7: Настройка службы Systemd (ras.service)
# ==============================================================================
echo ""
echo -e "${BOLD}=== [7/9] Настройка Systemd-службы ${SERVICE_NAME}.service ===${NC}"

SYSTEMD_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=COPP-RAS Flask Application (ras.copp82.ru)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin"
Environment="FLASK_CONFIG=production"
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --workers 4 \\
    --bind 127.0.0.1:${APP_PORT} \\
    --timeout 120 \\
    --access-logfile /var/log/${SERVICE_NAME}/access.log \\
    --error-logfile /var/log/${SERVICE_NAME}/error.log \\
    wsgi:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Настройка прав на проект для веб-сервера www-data
chown -R ${APP_USER}:${APP_USER} "$PROJECT_DIR"
chown -R ${APP_USER}:${APP_USER} "/var/log/${SERVICE_NAME}"
chmod -R 775 "${PROJECT_DIR}/app/uploads"
chmod -R 775 "${PROJECT_DIR}/backups"
[ -f "${PROJECT_DIR}/reports.db" ] && chmod 664 "${PROJECT_DIR}/reports.db"

# Перезапуск службы
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

success "Служба ${SERVICE_NAME}.service включена и запущена."

# ==============================================================================
# ШАГ 8: Настройка Nginx с SSL для ras.copp82.ru
# ==============================================================================
echo ""
echo -e "${BOLD}=== [8/9] Настройка виртуального хоста Nginx ===${NC}"

NGINX_AVAILABLE="/etc/nginx/sites-available/${DOMAIN}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${DOMAIN}"

cat > "$NGINX_AVAILABLE" <<EOF
# Редирект HTTP -> HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}

# Основной защищенный HTTPS-сервер
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    # SSL Сертификаты (*.copp82.ru)
    ssl_certificate ${SSL_CERT_PATH};
    ssl_certificate_key ${SSL_KEY_PATH};

    # Протоколы и шифры безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    # Лимит на размер загружаемых файлов (отчеты до 50 МБ)
    client_max_body_size 50M;

    # Прямая быстрая отдача статических файлов (CSS, JS, Fonts, Images)
    location /static/ {
        alias ${PROJECT_DIR}/app/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, no-transform";
    }

    # Проксирование запросов к Gunicorn
    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
EOF

# Включение конфигурации
ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
# Отключение дефолтного сайта Nginx (если включен)
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации Nginx
nginx -t
systemctl restart nginx

success "Nginx настроен и успешно перезапущен с SSL."

# ==============================================================================
# ШАГ 9: Файрвол UFW и скрипт быстрого обновления update-ras.sh
# ==============================================================================
echo ""
echo -e "${BOLD}=== [9/9] Финализация (UFW и скрипт обновления) ===${NC}"

# Настройка брандмауэра
info "Настройка портов UFW (SSH, HTTP, HTTPS)..."
ufw allow 22/tcp >/dev/null 2>&1 || true
ufw allow 80/tcp >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

# Создание скрипта быстрого обновления
UPDATE_SCRIPT="${PROJECT_DIR}/scripts/update-ras.sh"
cat > "$UPDATE_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
echo "=== Обновление системы COPP-RAS (${DOMAIN}) ==="
cd ${PROJECT_DIR}
sudo -u ${TARGET_USER} git pull origin ${GIT_BRANCH}
${VENV_DIR}/bin/pip install -r requirements.txt gunicorn --quiet
sudo chown -R ${APP_USER}:${APP_USER} ${PROJECT_DIR}
sudo systemctl restart ${SERVICE_NAME}
sudo systemctl restart nginx
echo "=== Обновление успешно применено! ==="
EOF
chmod +x "$UPDATE_SCRIPT"

# Ссылка на скрипт обновления в домашнюю папку пользователя
if [ -d "$USER_HOME" ]; then
    ln -sf "$UPDATE_SCRIPT" "${USER_HOME}/update-ras.sh"
    chown -h "${TARGET_USER}:${TARGET_USER}" "${USER_HOME}/update-ras.sh" 2>/dev/null || true
fi

success "Скрипт обновления создан: ${UPDATE_SCRIPT} (и в ~user/update-ras.sh)"

# ==============================================================================
# ИТОГОВЫЙ ОТЧЕТ И НАПОМИНАНИЕ
# ==============================================================================
echo ""
echo -e "${BOLD}${GREEN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}           РАЗВЕРТЫВАНИЕ СИСТЕМЫ УСПЕШНО ЗАВЕРШЕНО!                   ${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}"
echo ""
echo -e "  🌐 Домен системы:      ${BOLD}https://${DOMAIN}${NC}"
echo -e "  ⚙️  Служба Systemd:     ${BOLD}systemctl status ${SERVICE_NAME}${NC}"
echo -e "  📁 Директория проекта: ${BOLD}${PROJECT_DIR}${NC}"
echo -e "  📜 Логи приложения:    ${BOLD}/var/log/${SERVICE_NAME}/error.log${NC}"
echo -e "  🔄 Быстрое обновление: ${BOLD}sudo bash ~/update-ras.sh${NC}"
echo ""
echo -e "${BOLD}${YELLOW}######################################################################${NC}"
echo -e "${BOLD}${YELLOW}#                                                                    #${NC}"
echo -e "${BOLD}${YELLOW}#   [!] ВАЖНО: ЗАГРУЗИТЕ ВАШУ БАЗУ ДАННЫХ reports.db                #${NC}"
echo -e "${BOLD}${YELLOW}#                                                                    #${NC}"
echo -e "${BOLD}${YELLOW}######################################################################${NC}"
echo -e "Чтобы перенести рабочую базу данных, выполните со своего компьютера:"
echo -e "  ${BOLD}scp reports.db ${TARGET_USER}@<IP_СЕРВЕРА>:/tmp/reports.db${NC}"
echo ""
echo -e "Затем на сервере перенесите файл и примените права:"
echo -e "  ${BOLD}sudo mv /tmp/reports.db ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo chown ${APP_USER}:${APP_USER} ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo chmod 664 ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo systemctl restart ${SERVICE_NAME}${NC}"
echo ""
echo -e "${BOLD}${GREEN}======================================================================${NC}"
