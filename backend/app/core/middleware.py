import asyncio
import ipaddress
import time
from collections import defaultdict, deque

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.infrastructure.database.models import UserActivityLog


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API限流中间件"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 允许的请求次数
        self.period = period  # 时间窗口（秒）
        self.clients: dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 300  # 清理间隔（秒）
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 获取客户端标识
        client_id = self._get_client_id(request)

        # 检查是否需要清理过期记录
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_expired_records(current_time)
            self.last_cleanup = current_time

        # 检查限流
        if self._is_rate_limited(client_id, current_time):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.calls} per {self.period} seconds",
                    "retry_after": self.period
                },
                headers={"Retry-After": str(self.period)}
            )

        # 记录请求
        self.clients[client_id].append(current_time)

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """获取客户端唯一标识"""
        # 优先使用用户ID（如果已认证）
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # 使用IP地址
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """检查是否超过限流"""
        client_requests = self.clients[client_id]

        # 移除过期的请求记录
        cutoff_time = current_time - self.period
        while client_requests and client_requests[0] <= cutoff_time:
            client_requests.popleft()

        # 检查是否超过限制
        return len(client_requests) >= self.calls

    def _cleanup_expired_records(self, current_time: float):
        """清理过期的客户端记录"""
        cutoff_time = current_time - self.period * 2  # 保留两个周期的数据

        clients_to_remove = []
        for client_id, requests in self.clients.items():
            # 移除过期请求
            while requests and requests[0] <= cutoff_time:
                requests.popleft()

            # 如果没有活跃请求，标记删除
            if not requests:
                clients_to_remove.append(client_id)

        # 删除空的客户端记录
        for client_id in clients_to_remove:
            del self.clients[client_id]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # 添加安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP头部（根据需要调整）
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP白名单中间件"""

    def __init__(self, app, whitelist: list | None = None, admin_only: bool = True):
        super().__init__(app)
        self.whitelist = whitelist or []
        self.admin_only = admin_only  # 是否仅对管理员接口启用
        self.admin_paths = ["/api/v1/admin", "/api/v1/auth/admin"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 如果没有配置白名单，直接通过
        if not self.whitelist:
            return await call_next(request)

        # 检查是否为管理员路径
        if self.admin_only:
            is_admin_path = any(request.url.path.startswith(path) for path in self.admin_paths)
            if not is_admin_path:
                return await call_next(request)

        # 获取客户端IP
        client_ip = self._get_client_ip(request)

        # 检查IP是否在白名单中
        if not self._is_ip_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Access denied",
                    "message": "Your IP address is not allowed to access this resource"
                }
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头部
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """检查IP是否被允许"""
        if client_ip == "unknown":
            return False

        try:
            client_addr = ipaddress.ip_address(client_ip)

            for allowed in self.whitelist:
                try:
                    # 支持单个IP和CIDR网段
                    if "/" in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_addr in network:
                            return True
                    else:
                        allowed_addr = ipaddress.ip_address(allowed)
                        if client_addr == allowed_addr:
                            return True
                except ValueError:
                    continue

            return False
        except ValueError:
            return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app, log_requests: bool = True, log_responses: bool = False):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.sensitive_paths = ["/api/v1/auth/login", "/api/v1/auth/register"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        # 记录请求信息
        if self.log_requests:
            await self._log_request(request)

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # 记录响应信息
        if self.log_responses:
            await self._log_response(request, response, process_time)

        return response

    async def _log_request(self, request: Request):
        """记录请求信息"""
        # 获取用户信息（如果已认证）
        user = None
        try:
            # 这里需要从请求中提取用户信息
            # 由于中间件执行在依赖注入之前，需要手动处理
            pass
        except Exception:
            pass

        # 记录到数据库（异步）
        asyncio.create_task(self._save_activity_log(
            user_id=getattr(user, 'id', None) if user else None,
            action="api_request",
            details={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("User-Agent", "")
            },
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent", "")
        ))

    async def _log_response(self, request: Request, response: Response, process_time: float):
        """记录响应信息"""
        # 只记录错误响应或慢请求
        if response.status_code >= 400 or process_time > 1.0:
            asyncio.create_task(self._save_activity_log(
                user_id=None,
                action="api_response",
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")
            ))

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _save_activity_log(self, user_id: int | None, action: str,
                                details: dict, ip_address: str, user_agent: str):
        """保存活动日志到数据库"""
        try:
            # 这里需要获取数据库会话
            # 由于是异步任务，需要创建新的会话
            from app.infrastructure.database.session import SessionLocal

            db = SessionLocal()
            try:
                activity_log = UserActivityLog(
                    user_id=user_id,
                    action=action,
                    details=str(details),
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                db.add(activity_log)
                db.commit()
            finally:
                db.close()
        except Exception:
            # 静默处理日志错误，不影响主要功能
            pass


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS中间件"""

    def __init__(self, app, allow_origins: list = None, allow_methods: list = None,
                 allow_headers: list = None, allow_credentials: bool = True):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 处理预检请求
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, request)
            return response

        # 处理实际请求
        response = await call_next(request)
        self._add_cors_headers(response, request)
        return response

    def _add_cors_headers(self, response: Response, request: Request):
        """添加CORS头部"""
        origin = request.headers.get("Origin")

        # 检查来源是否被允许
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Max-Age"] = "86400"  # 24小时

    def _is_origin_allowed(self, origin: str | None) -> bool:
        """检查来源是否被允许"""
        if not origin:
            return True

        if "*" in self.allow_origins:
            return True

        return origin in self.allow_origins


# 中间件配置函数
def setup_middleware(app):
    """设置所有中间件"""

    # CORS中间件（最先添加）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS if hasattr(settings, 'ALLOWED_ORIGINS') else ["*"],
        allow_credentials=True
    )

    # 安全头部中间件
    app.add_middleware(SecurityHeadersMiddleware)

    # 限流中间件
    if hasattr(settings, 'RATE_LIMIT_ENABLED') and settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.RATE_LIMIT_REQUESTS_PER_MINUTE if hasattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE') else 100,
            period=60  # 固定为60秒（1分钟）
        )

    # IP白名单中间件（如果配置了白名单）
    if hasattr(settings, 'IP_WHITELIST_ENABLED') and settings.IP_WHITELIST_ENABLED and hasattr(settings, 'IP_WHITELIST_LIST'):
        app.add_middleware(
            IPWhitelistMiddleware,
            whitelist=settings.IP_WHITELIST_LIST,
            admin_only=True
        )

    # 请求日志中间件
    app.add_middleware(
        RequestLoggingMiddleware,
        log_requests=settings.LOG_REQUESTS if hasattr(settings, 'LOG_REQUESTS') else True,
        log_responses=settings.LOG_RESPONSES if hasattr(settings, 'LOG_RESPONSES') else False
    )
