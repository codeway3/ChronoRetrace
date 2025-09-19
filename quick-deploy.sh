#!/bin/bash

# ChronoRetrace 一键部署脚本
# 适用于 Ubuntu/macOS 系统
# 作者: ChronoRetrace Team

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/ubuntu-release ] || [ -f /etc/debian_version ]; then
            DISTRO="ubuntu"
        elif [ -f /etc/redhat-release ]; then
            DISTRO="centos"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    log_info "检测到操作系统: $OS"
}

# 检查并安装依赖
install_dependencies() {
    log_info "检查并安装系统依赖..."
    
    if [[ "$OS" == "macos" ]]; then
        # macOS 使用 Homebrew
        if ! command -v brew &> /dev/null; then
            log_info "安装 Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # 安装依赖
        brew update
        brew install python@3.9 postgresql redis node npm
        
    elif [[ "$OS" == "linux" && "$DISTRO" == "ubuntu" ]]; then
        # Ubuntu 系统
        sudo apt update
        sudo apt install -y python3.9 python3.9-pip python3.9-venv postgresql postgresql-contrib redis-server nodejs npm curl
        
    elif [[ "$OS" == "linux" && "$DISTRO" == "centos" ]]; then
        # CentOS 系统
        sudo yum update -y
        sudo yum install -y python39 python39-pip postgresql-server postgresql-contrib redis nodejs npm curl
    fi
    
    log_success "系统依赖安装完成"
}

# 检测 Docker Compose 命令
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        echo ""
    fi
}

# 检查 Docker
check_docker() {
    # 如果环境变量已设置，优先使用环境变量
    if [ "$USE_DOCKER" = "false" ]; then
        log_info "环境变量设置为本地部署，将使用本地部署"
        USE_DOCKER=false
    elif [ "$USE_DOCKER" = "true" ]; then
        log_info "环境变量设置为 Docker 部署，将使用 Docker 部署"
        USE_DOCKER=true
    elif command -v docker &> /dev/null && (command -v docker-compose &> /dev/null || docker compose version &> /dev/null); then
        log_info "检测到 Docker，将使用 Docker 部署"
        USE_DOCKER=true
    else
        log_info "未检测到 Docker，将使用本地部署"
        USE_DOCKER=false
    fi
}

# Docker 部署
deploy_with_docker() {
    log_info "使用 Docker 部署 ChronoRetrace..."
    
    # 获取正确的 docker compose 命令
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    if [ -z "$DOCKER_COMPOSE_CMD" ]; then
        log_error "未找到可用的 Docker Compose 命令"
        exit 1
    fi
    
    # 检查 docker-compose.yml
    if [ ! -f "docker-compose.yml" ]; then
        log_error "未找到 docker-compose.yml 文件"
        exit 1
    fi
    
    # 创建环境变量文件
    if [ ! -f ".env" ]; then
        log_info "创建环境配置文件..."
        cat > .env << EOF
# 数据库配置
POSTGRES_DB=chronoretrace
POSTGRES_USER=chronoretrace
POSTGRES_PASSWORD=chronoretrace123
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# 应用配置
SECRET_KEY=your-secret-key-change-in-production
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1

# 前端配置
REACT_APP_API_URL=http://localhost:8000
EOF
    fi
    
    # 构建并启动服务
    log_info "构建 Docker 镜像..."
    $DOCKER_COMPOSE_CMD build
    
    log_info "启动服务..."
    $DOCKER_COMPOSE_CMD up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    $DOCKER_COMPOSE_CMD exec backend python -c "from app.infrastructure.database.migrations import run_database_migrations; run_database_migrations()"
    
    log_success "Docker 部署完成！"
    log_info "前端访问地址: http://localhost:3000"
    log_info "后端 API 地址: http://localhost:8000"
}

# 本地部署
deploy_locally() {
    log_info "使用本地环境部署 ChronoRetrace..."
    
    # 配置数据库
    setup_database
    
    # 配置 Redis
    setup_redis
    
    # 部署后端
    deploy_backend
    
    # 部署前端
    deploy_frontend
    
    log_success "本地部署完成！"
    log_info "前端访问地址: http://localhost:3000"
    log_info "后端 API 地址: http://localhost:8000"
}

# 配置数据库
setup_database() {
    log_info "配置 PostgreSQL 数据库..."
    
    if [[ "$OS" == "macos" ]]; then
        # macOS
        brew services start postgresql
        sleep 5
        
        # 创建数据库和用户
        psql postgres -c "CREATE DATABASE chronoretrace;" 2>/dev/null || true
        psql postgres -c "CREATE USER chronoretrace WITH PASSWORD 'chronoretrace123';" 2>/dev/null || true
        psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE chronoretrace TO chronoretrace;" 2>/dev/null || true
        
    elif [[ "$OS" == "linux" ]]; then
        # Linux
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
        # 创建数据库和用户
        sudo -u postgres psql -c "CREATE DATABASE chronoretrace;" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE USER chronoretrace WITH PASSWORD 'chronoretrace123';" 2>/dev/null || true
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chronoretrace TO chronoretrace;" 2>/dev/null || true
    fi
    
    log_success "数据库配置完成"
}

# 配置 Redis
setup_redis() {
    log_info "配置 Redis..."
    
    if [[ "$OS" == "macos" ]]; then
        brew services start redis
    elif [[ "$OS" == "linux" ]]; then
        sudo systemctl start redis
        sudo systemctl enable redis
    fi
    
    log_success "Redis 配置完成"
}

# 部署后端
deploy_backend() {
    log_info "部署后端服务..."
    
    cd backend
    
    # 创建虚拟环境
    python3.9 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建环境配置
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Python Path
PYTHONPATH=/Users/apple/code/ChronoRetrace/backend

# Database Configuration (PostgreSQL for production)
DATABASE_URL=postgresql://chronoretrace:chronoretrace123@localhost:5432/chronoretrace

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Keys
TUSHARE_TOKEN=your_tushare_token_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
EOF
    fi
    
    # 运行数据库迁移
    python -c "from app.infrastructure.database.migrations import run_database_migrations; run_database_migrations()"
    
    # 启动后端服务
    nohup python start_dev.py > ../logs/backend.log 2>&1 &
    echo $! > ../logs/backend.pid
    
    cd ..
    log_success "后端服务启动完成"
}

# 部署前端
deploy_frontend() {
    log_info "部署前端服务..."
    
    cd frontend
    
    # 安装依赖
    npm install
    
    # 创建环境配置
    if [ ! -f ".env" ]; then
        cat > .env << EOF
REACT_APP_API_URL=http://localhost:8000
PORT=3000
EOF
    fi
    
    # 启动前端服务
    nohup npm start > ../logs/frontend.log 2>&1 &
    echo $! > ../logs/frontend.pid
    
    cd ..
    log_success "前端服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端系统健康状态（使用统一健康检查接口）
    for i in {1..30}; do
        response=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/health/system 2>/dev/null)
        http_code=${response: -3}
        
        if [ "$http_code" = "200" ]; then
            log_success "后端系统健康检查通过 - 所有服务正常"
            break
        elif [ "$http_code" = "206" ]; then
            log_warning "后端系统健康检查通过 - 部分服务降级"
            break
        elif [ "$http_code" = "503" ]; then
            if [ $i -eq 30 ]; then
                log_error "后端系统健康检查失败 - 服务不可用"
                return 1
            fi
        else
            if [ $i -eq 30 ]; then
                log_warning "后端服务健康检查超时，请检查日志"
                return 1
            fi
        fi
        sleep 2
    done
    
    # 检查前端
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_success "前端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_warning "前端服务健康检查超时，请检查日志"
            return 1
        fi
        sleep 2
    done
}

# 初始化管理员账号
initialize_admin_account() {
    log_info "正在初始化管理员账号..."
    
    # 等待后端服务完全启动
    sleep 3
    
    # 尝试初始化管理员账号
    for i in {1..5}; do
        response=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/api/v1/admin/init-admin 2>/dev/null)
        http_code=${response: -3}
        response_body=${response%???}
        
        if [ "$http_code" = "200" ]; then
            log_success "管理员账号初始化成功"
            log_info "管理员账号信息:"
            log_info "  用户名: admin"
            log_info "  邮箱: admin@chronoretrace.com"
            log_info "  密码: ChronoAdmin2024!"
            log_warning "请在首次登录后立即修改默认密码！"
            return 0
        elif [ "$http_code" = "400" ] && echo "$response_body" | grep -q "已存在"; then
            log_info "管理员账号已存在，跳过初始化"
            log_info "如需重置管理员账号，请手动操作"
            return 0
        else
            if [ $i -eq 5 ]; then
                log_warning "管理员账号初始化失败 (HTTP: $http_code)"
                log_warning "请部署完成后手动执行: curl -X POST http://localhost:8000/api/v1/admin/init-admin"
                return 1
            fi
            log_info "初始化尝试 $i/5 失败，等待重试..."
            sleep 2
        fi
    done
}

# 创建日志目录
create_log_dir() {
    mkdir -p logs
}

# 显示部署信息
show_deployment_info() {
    echo
    log_success "=== ChronoRetrace 部署完成 ==="
    echo
    log_info "访问地址:"
    if [ "$USE_DOCKER" = true ]; then
        log_info "  前端: http://localhost:3000"
        log_info "  后端 API: http://localhost:8000"
        log_info "  管理后台: http://localhost:8000/admin"
    else
        log_info "  前端: http://localhost:3000"
        log_info "  后端 API: http://localhost:8000"
        log_info "  管理后台: http://localhost:8000/admin"
    fi
    echo
    log_info "默认管理员账号:"
    log_info "  用户名: admin"
    log_info "  邮箱: admin@chronoretrace.com"
    log_info "  密码: ChronoAdmin2024!"
    log_warning "⚠️  请在首次登录后立即修改默认密码！"
    echo
    log_info "常用命令:"
    if [ "$USE_DOCKER" = true ]; then
        DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
        log_info "  查看服务状态: $DOCKER_COMPOSE_CMD ps"
        log_info "  查看日志: $DOCKER_COMPOSE_CMD logs -f"
        log_info "  停止服务: $DOCKER_COMPOSE_CMD down"
        log_info "  重启服务: $DOCKER_COMPOSE_CMD restart"
    else
        log_info "  查看后端日志: tail -f logs/backend.log"
        log_info "  查看前端日志: tail -f logs/frontend.log"
        log_info "  停止服务: ./quick-deploy.sh stop"
    fi
    echo
}

# 停止服务
stop_services() {
    log_info "停止 ChronoRetrace 服务..."
    
    if [ "$USE_DOCKER" = true ]; then
        DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
        $DOCKER_COMPOSE_CMD down
    else
        # 停止本地服务
        if [ -f "logs/backend.pid" ]; then
            kill $(cat logs/backend.pid) 2>/dev/null || true
            rm logs/backend.pid
        fi
        
        if [ -f "logs/frontend.pid" ]; then
            kill $(cat logs/frontend.pid) 2>/dev/null || true
            rm logs/frontend.pid
        fi
    fi
    
    log_success "服务已停止"
}

# 显示帮助信息
show_help() {
    echo "ChronoRetrace 一键部署脚本"
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --local              强制使用本地部署模式"
    echo "  --docker             强制使用Docker部署模式"
    echo "  --health-check-only  仅执行健康检查"
    echo "  stop                 停止所有服务"
    echo "  --help, -h           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                   自动检测并部署"
    echo "  $0 --local           使用本地部署"
    echo "  $0 --docker          使用Docker部署"
    echo "  $0 stop              停止服务"
}

# 主函数
main() {
    echo
    log_info "=== ChronoRetrace 一键部署脚本 ==="
    echo
    
    # 检查参数
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        show_help
        exit 0
    fi
    
    if [ "$1" = "stop" ]; then
        check_docker
        stop_services
        exit 0
    fi
    
    if [ "$1" = "--health-check-only" ]; then
        log_info "仅执行健康检查..."
        health_check
        exit 0
    fi
    
    if [ "$1" = "--local" ]; then
        log_info "强制使用本地部署模式..."
        USE_DOCKER=false
    fi
    
    if [ "$1" = "--docker" ]; then
        log_info "强制使用Docker部署模式..."
        USE_DOCKER=true
    fi
    
    # 检测操作系统
    detect_os
    
    # 创建日志目录
    create_log_dir
    
    # 检查 Docker
    check_docker
    
    # 安装依赖
    install_dependencies
    
    # 部署应用
    if [ "$USE_DOCKER" = true ]; then
        deploy_with_docker
    else
        deploy_locally
    fi
    
    # 健康检查
    health_check
    
    # 初始化管理员账号
    initialize_admin_account
    
    # 显示部署信息
    show_deployment_info
}

# 执行主函数
main "$@"