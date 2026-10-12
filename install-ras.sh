#!/usr/bin/env bash
# ==============================================================================
# Скрипт автоматического развертывания COPP-RAS на Ubuntu Server (24.04 / 26.04)
# Режимы: Тестирование по IP (HTTP) или Боевой запуск по домену с SSL (HTTPS)
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

# ==============================================================================
# ⚙️ НАСТРОЙКИ (МЕНЯЙТЕ ЗДЕСЬ ПРИ ПЕРЕХОДЕ С IP НА ДОМЕН)
# ==============================================================================
# USE_DOMAIN="false" -> РЕЖИМ ТЕСТИРОВАНИЯ: доступ прямо по IP (http://<IP_СЕРВЕРА>/)
# USE_DOMAIN="true"  -> БОЕВОЙ РЕЖИМ: доступ по домену с SSL (https://ras.copp82.ru)
USE_DOMAIN="false"

# Имя домена (активируется при USE_DOMAIN="true" или через ~/switch-to-domain.sh)
DOMAIN="ras.copp82.ru"

# Служебные параметры
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

# Получаем внешний/локальный IP-адрес сервера для подсказок
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "IP_СЕРВЕРА")

echo -e "${BOLD}${BLUE}"
echo "======================================================================"
echo "          АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ СИСТЕМЫ COPP-RAS               "
if [ "$USE_DOMAIN" = "true" ]; then
echo "          Режим: БОЕВОЙ (https://${DOMAIN})                           "
else
echo "          Режим: ТЕСТОВЫЙ ПО IP (http://${SERVER_IP}/)                "
fi
echo "          Служба: ${SERVICE_NAME}.service                             "
echo "======================================================================"
echo -e "${NC}"

# ── Проверка запуска с правами суперпользователя ─────────────────────────────
if [ "$EUID" -ne 0 ]; then
    error "Этот скрипт необходимо запускать с правами sudo: sudo bash install-ras.sh"
    exit 1
fi

info "Целевой пользователь: ${BOLD}${TARGET_USER}${NC} (Домашняя папка: ${USER_HOME})"
info "Каталог проекта: ${BOLD}${PROJECT_DIR}${NC}"

# ==============================================================================
# ШАГ 1: Поиск и подготовка SSL-сертификатов (*.copp82.ru)
# ==============================================================================
echo ""
echo -e "${BOLD}=== [1/9] Проверка и подготовка SSL-сертификатов ===${NC}"

mkdir -p /etc/ssl/certs /etc/ssl/private

SSL_CERT_PATH="/etc/ssl/certs/copp82.ru_fullchain.crt"
SSL_KEY_PATH="/etc/ssl/private/copp82.ru.key"

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

HAVE_SSL="false"
if [ -n "$CERT_TXT" ] && [ -n "$INTER_TXT" ] && [ -n "$KEY_TXT" ]; then
    info "Найден сертификат: ${CERT_TXT}"
    info "Найден промежуточный CA: ${INTER_TXT}"
    [ -n "$ROOT_TXT" ] && info "Найден корневой CA: ${ROOT_TXT}"
    info "Найден приватный ключ: ${KEY_TXT}"

    # Объединение цепочки сертификатов
    > "$SSL_CERT_PATH"
    cat "$CERT_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
    cat "$INTER_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
    if [ -n "$ROOT_TXT" ] && [ -f "$ROOT_TXT" ]; then
        cat "$ROOT_TXT" >> "$SSL_CERT_PATH"; echo "" >> "$SSL_CERT_PATH"
    fi

    cp "$KEY_TXT" "$SSL_KEY_PATH"
    chmod 644 "$SSL_CERT_PATH"
    chmod 600 "$SSL_KEY_PATH"
    HAVE_SSL="true"
    success "SSL-сертификаты подготовлены и сохранены в /etc/ssl/ (готовы к переходу на домен)."
else
    if [ "$USE_DOMAIN" = "true" ]; then
        error "Для режима USE_DOMAIN=true требуются файлы сертификатов!"
        echo "Поместите *certificate*.txt, *intermediate*.txt, *private*.txt в /home/admin-copp"
        exit 1
    else
        warn "Файлы SSL-сертификатов не обнаружены. Так как включен тестовый режим по IP, установка продолжается."
    fi
fi

# ==============================================================================
# ШАГ 2: Обновление системы и установка необходимых пакетов
# ==============================================================================
echo ""
echo -e "${BOLD}=== [2/9] Установка системных пакетов Ubuntu ===${NC}"

export DEBIAN_FRONTEND=noninteractive
info "Обновление индексов пакетов APT..."
apt-get update -y

info "Установка Python3, Nginx, Git, SQLite и инструментов сборки..."
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
    info "Генерация нового SSH-ключа ed25519..."
    sudo -u "$TARGET_USER" ssh-keygen -t ed25519 -C "deploy-ras@copp82.ru" -f "$SSH_KEY" -N ""
    chmod 600 "$SSH_KEY"
    chmod 644 "${SSH_KEY}.pub"
fi

info "Добавление github.com в доверенные хосты..."
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
    warn "СЕРВЕР ЕЩЕ НЕ АВТОРИЗОВАН В GITHUB!"
    warn "Скопируйте публичный SSH-ключ ниже и добавьте его в Deploy Keys репозитория:"
    warn "👉 https://github.com/NKVD2023/copp-ras/settings/keys"
    warn "========================================================================"
    echo ""
    echo -e "${BOLD}${GREEN}"
    cat "$PUB_KEY_FILE"
    echo -e "${NC}"
    echo ""
    read -r -p "После добавления ключа на GitHub нажмите [Enter] для продолжения..."

    sudo -u "$TARGET_USER" ssh -T -o StrictHostKeyChecking=accept-new git@github.com 2>&1 || true
fi
success "SSH-доступ к GitHub подтвержден."

# ==============================================================================
# ШАГ 4: Клонирование репозитория проекта
# ==============================================================================
echo ""
echo -e "${BOLD}=== [4/9] Клонирование репозитория в ${PROJECT_DIR} ===${NC}"

mkdir -p /var/www

if [ -d "${PROJECT_DIR}/.git" ]; then
    info "Каталог проекта уже существует. Подтягиваем свежий код..."
    cd "$PROJECT_DIR"
    sudo -u "$TARGET_USER" git fetch origin "$GIT_BRANCH"
    sudo -u "$TARGET_USER" git checkout "$GIT_BRANCH"
    sudo -u "$TARGET_USER" git pull origin "$GIT_BRANCH"
else
    info "Клонирование ветки ${GIT_BRANCH} из ${GIT_REPO}..."
    sudo -u "$TARGET_USER" git clone -b "$GIT_BRANCH" "$GIT_REPO" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

success "Репозиторий готов (ветка ${GIT_BRANCH})."

# ==============================================================================
# ШАГ 5: Виртуальное окружение Python и зависимости
# ==============================================================================
echo ""
echo -e "${BOLD}=== [5/9] Настройка виртуального окружения Python ===${NC}"

VENV_DIR="${PROJECT_DIR}/venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Создание venv в ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
fi

info "Обновление pip, setuptools, wheel..."
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel --quiet

info "Установка зависимостей проекта (+ gunicorn)..."
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" gunicorn --quiet

success "Зависимости Python установлены."

# ==============================================================================
# ШАГ 6: Директории, wsgi.py и конфигурация
# ==============================================================================
echo ""
echo -e "${BOLD}=== [6/9] Создание директорий, wsgi.py и переменных окружения ===${NC}"

mkdir -p "${PROJECT_DIR}/app/uploads/reports"
mkdir -p "${PROJECT_DIR}/backups"
mkdir -p "${PROJECT_DIR}/scripts"
mkdir -p "/var/log/${SERVICE_NAME}"

# Точка входа wsgi.py
if [ ! -f "${PROJECT_DIR}/wsgi.py" ]; then
    info "Создание wsgi.py..."
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

# Ключ сессий .secret_key
if [ ! -f "${PROJECT_DIR}/.secret_key" ]; then
    info "Генерация секретного ключа .secret_key..."
    python3 -c "import secrets; print(secrets.token_hex(32))" > "${PROJECT_DIR}/.secret_key"
    chmod 600 "${PROJECT_DIR}/.secret_key"
fi

# Файл переменных окружения .env
# Если тестируем по IP (HTTP), куки должны работать без требования HTTPS:
COOKIE_SECURE_VAL="false"
if [ "$USE_DOMAIN" = "true" ]; then
    COOKIE_SECURE_VAL="true"
fi

cat > "${PROJECT_DIR}/.env" <<EOF
FLASK_CONFIG=production
SESSION_COOKIE_SECURE=${COOKIE_SECURE_VAL}
DATABASE_URL=sqlite:///${PROJECT_DIR}/reports.db
SECRET_KEY=$(cat "${PROJECT_DIR}/.secret_key")
EOF
chmod 600 "${PROJECT_DIR}/.env"

# Начальная инициализация структуры БД
if [ ! -f "${PROJECT_DIR}/reports.db" ]; then
    info "Инициализация таблиц базы данных..."
    "${VENV_DIR}/bin/python" -c "
from app import create_app
from app.extensions import db
from config import config_map
app = create_app(config_map['production'])
with app.app_context():
    db.create_all()
" || true
fi

success "Конфигурация и окружение настроены."

# ==============================================================================
# ШАГ 7: Настройка службы Systemd (ras.service)
# ==============================================================================
echo ""
echo -e "${BOLD}=== [7/9] Настройка Systemd-службы ${SERVICE_NAME}.service ===${NC}"

SYSTEMD_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=COPP-RAS Flask Application
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

# Права доступа
chown -R ${APP_USER}:${APP_USER} "$PROJECT_DIR"
chown -R ${APP_USER}:${APP_USER} "/var/log/${SERVICE_NAME}"
chmod -R 775 "${PROJECT_DIR}/app/uploads"
chmod -R 775 "${PROJECT_DIR}/backups"
[ -f "${PROJECT_DIR}/reports.db" ] && chmod 664 "${PROJECT_DIR}/reports.db"

# Запуск службы
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

success "Служба ${SERVICE_NAME}.service успешно запущена."

# ==============================================================================
# ШАГ 8: Настройка Nginx (Тестовый режим по IP или Боевой по Домену)
# ==============================================================================
echo ""
echo -e "${BOLD}=== [8/9] Настройка веб-сервера Nginx ===${NC}"

NGINX_CONF_IP="/etc/nginx/sites-available/ras-ip"
NGINX_CONF_DOMAIN="/etc/nginx/sites-available/${DOMAIN}"

# 1. Конфиг для тестирования по IP-адресу (HTTP, порт 80, без редиректов)
cat > "$NGINX_CONF_IP" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 50M;

    location /static/ {
        alias ${PROJECT_DIR}/app/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, no-transform";
    }

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

# 2. Конфиг для боевого домена (HTTPS, порт 443, SSL, редирект с 80)
cat > "$NGINX_CONF_DOMAIN" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate ${SSL_CERT_PATH};
    ssl_certificate_key ${SSL_KEY_PATH};

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 50M;

    location /static/ {
        alias ${PROJECT_DIR}/app/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, no-transform";
    }

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

# Активация нужного конфига в зависимости от USE_DOMAIN
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/ras-ip
rm -f /etc/nginx/sites-enabled/${DOMAIN}

if [ "$USE_DOMAIN" = "true" ]; then
    ln -sf "$NGINX_CONF_DOMAIN" "/etc/nginx/sites-enabled/${DOMAIN}"
    info "Активирован профиль Nginx: БОЕВОЙ ДОМЕН (https://${DOMAIN})"
else
    ln -sf "$NGINX_CONF_IP" "/etc/nginx/sites-enabled/ras-ip"
    info "Активирован профиль Nginx: ТЕСТИРОВАНИЕ ПО IP (http://${SERVER_IP}/)"
fi

nginx -t
systemctl restart nginx
success "Nginx настроен и перезапущен."

# ==============================================================================
# ШАГ 9: Файрвол UFW и Скрипты Переключения / Обновления
# ==============================================================================
echo ""
echo -e "${BOLD}=== [9/9] Финализация (UFW, update-ras.sh, switch-to-domain.sh) ===${NC}"

# Настройка портов брандмауэра
ufw allow 22/tcp >/dev/null 2>&1 || true
ufw allow 80/tcp >/dev/null 2>&1 || true
ufw allow 443/tcp >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

# 1. Скрипт быстрого обновления кода
UPDATE_SCRIPT="${PROJECT_DIR}/scripts/update-ras.sh"
cat > "$UPDATE_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
echo "=== Обновление COPP-RAS ==="
cd ${PROJECT_DIR}
sudo -u ${TARGET_USER} git pull origin ${GIT_BRANCH}
${VENV_DIR}/bin/pip install -r requirements.txt gunicorn --quiet
sudo chown -R ${APP_USER}:${APP_USER} ${PROJECT_DIR}
sudo systemctl restart ${SERVICE_NAME}
sudo systemctl restart nginx
echo "=== Обновление успешно применено! ==="
EOF
chmod +x "$UPDATE_SCRIPT"

# 2. Скрипт мгновенного переключения с IP на Домен
SWITCH_SCRIPT="${PROJECT_DIR}/scripts/switch-to-domain.sh"
cat > "$SWITCH_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
echo "=== Переключение COPP-RAS на боевой домен ${DOMAIN} (HTTPS) ==="

if [ ! -f "${SSL_CERT_PATH}" ] || [ ! -f "${SSL_KEY_PATH}" ]; then
    echo "[ОШИБКА] Не найдены SSL-сертификаты в /etc/ssl/certs/copp82.ru_fullchain.crt"
    echo "Убедитесь, что сертификаты установлены."
    exit 1
fi

# Переключение Nginx на домен
rm -f /etc/nginx/sites-enabled/ras-ip
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/${DOMAIN}
nginx -t
systemctl restart nginx

# Включение строгой безопасности кук в .env
sed -i 's/SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/g' ${PROJECT_DIR}/.env
systemctl restart ${SERVICE_NAME}

echo "=================================================================="
echo "УСПЕШНО! Система переключена на боевой домен: https://${DOMAIN}"
echo "=================================================================="
EOF
chmod +x "$SWITCH_SCRIPT"

# Ссылки на скрипты в домашнюю папку пользователя
if [ -d "$USER_HOME" ]; then
    ln -sf "$UPDATE_SCRIPT" "${USER_HOME}/update-ras.sh"
    ln -sf "$SWITCH_SCRIPT" "${USER_HOME}/switch-to-domain.sh"
    chown -h "${TARGET_USER}:${TARGET_USER}" "${USER_HOME}/update-ras.sh" 2>/dev/null || true
    chown -h "${TARGET_USER}:${TARGET_USER}" "${USER_HOME}/switch-to-domain.sh" 2>/dev/null || true
fi

success "Скрипты созданы: ~/update-ras.sh и ~/switch-to-domain.sh"

# ==============================================================================
# ИТОГОВЫЙ ОТЧЕТ И НАПОМИНАНИЯ
# ==============================================================================
echo ""
echo -e "${BOLD}${GREEN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}           РАЗВЕРТЫВАНИЕ СИСТЕМЫ УСПЕШНО ЗАВЕРШЕНО!                   ${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}"
echo ""
if [ "$USE_DOMAIN" = "true" ]; then
echo -e "  🌐 Боевой адрес:       ${BOLD}https://${DOMAIN}${NC}"
else
echo -e "  🌐 Тестовый адрес по IP: ${BOLD}http://${SERVER_IP}/${NC}"
fi
echo -e "  ⚙️  Служба Systemd:      ${BOLD}systemctl status ${SERVICE_NAME}${NC}"
echo -e "  📁 Директория проекта:  ${BOLD}${PROJECT_DIR}${NC}"
echo -e "  📜 Логи ошибок:         ${BOLD}/var/log/${SERVICE_NAME}/error.log${NC}"
echo ""
echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────────────────────────${NC}"
echo -e "${BOLD}КАК ПОЗЖЕ ПЕРЕКЛЮЧИТЬСЯ С IP НА ДОМЕН (ras.copp82.ru):${NC}"
echo -e "Когда будете готовы к боевому запуску, выполните на сервере всего одну команду:"
echo -e "  👉 ${BOLD}sudo bash ~/switch-to-domain.sh${NC}"
echo -e "(Либо в install-ras.sh смените USE_DOMAIN=\"false\" на USE_DOMAIN=\"true\")"
echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────────────────────────${NC}"
echo ""
echo -e "${BOLD}${YELLOW}######################################################################${NC}"
echo -e "${BOLD}${YELLOW}#                                                                    #${NC}"
echo -e "${BOLD}${YELLOW}#   [!] ВАЖНО: ЗАГРУЗИТЕ ВАШУ БАЗУ ДАННЫХ reports.db                #${NC}"
echo -e "${BOLD}${YELLOW}#                                                                    #${NC}"
echo -e "${BOLD}${YELLOW}######################################################################${NC}"
echo -e "Чтобы перенести рабочую базу данных, выполните со своего компьютера:"
echo -e "  ${BOLD}scp reports.db ${TARGET_USER}@${SERVER_IP}:/tmp/reports.db${NC}"
echo ""
echo -e "Затем на сервере примените файл и права:"
echo -e "  ${BOLD}sudo mv /tmp/reports.db ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo chown ${APP_USER}:${APP_USER} ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo chmod 664 ${PROJECT_DIR}/reports.db${NC}"
echo -e "  ${BOLD}sudo systemctl restart ${SERVICE_NAME}${NC}"
echo ""
echo -e "${BOLD}${GREEN}======================================================================${NC}"
