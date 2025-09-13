# ChronoRetrace 安全配置指南

本文档提供 ChronoRetrace 应用的全面安全配置指南，包括应用安全、基础设施安全、数据保护和合规要求等内容。

## 目录

- [安全架构概述](#安全架构概述)
- [身份认证与授权](#身份认证与授权)
- [网络安全](#网络安全)
- [数据保护](#数据保护)
- [应用安全](#应用安全)
- [基础设施安全](#基础设施安全)
- [监控与审计](#监控与审计)
- [合规要求](#合规要求)
- [安全事件响应](#安全事件响应)
- [安全测试](#安全测试)

## 安全架构概述

### 安全层次模型
```
┌─────────────────────────────────────────┐
│              用户层                      │
├─────────────────────────────────────────┤
│              应用层                      │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │   前端应用   │  │    后端 API     │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│              网络层                      │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │  负载均衡器  │  │   防火墙/WAF    │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│              数据层                      │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │   数据库    │  │      缓存       │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│            基础设施层                     │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │  容器平台   │  │    操作系统     │   │
│  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────┘
```

### 安全原则
1. **最小权限原则**: 用户和服务只获得完成任务所需的最小权限
2. **深度防御**: 多层安全控制，避免单点故障
3. **零信任架构**: 不信任任何网络位置，验证所有访问
4. **数据分类**: 根据敏感性对数据进行分类和保护
5. **持续监控**: 实时监控和审计所有安全事件

## 身份认证与授权

### JWT 认证配置

#### JWT 安全配置
```python
# jwt_config.py
import jwt
import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class JWTConfig:
    def __init__(self):
        # 使用 RS256 算法（非对称加密）
        self.algorithm = 'RS256'
        self.access_token_expire = datetime.timedelta(minutes=15)
        self.refresh_token_expire = datetime.timedelta(days=7)
        
        # 生成 RSA 密钥对
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def generate_token(self, user_id, permissions=None, token_type='access'):
        """生成 JWT 令牌"""
        now = datetime.datetime.utcnow()
        
        if token_type == 'access':
            expire = now + self.access_token_expire
        else:
            expire = now + self.refresh_token_expire
        
        payload = {
            'user_id': user_id,
            'permissions': permissions or [],
            'token_type': token_type,
            'iat': now,
            'exp': expire,
            'jti': str(uuid.uuid4())  # JWT ID，用于令牌撤销
        }
        
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return jwt.encode(payload, private_pem, algorithm=self.algorithm)
    
    def verify_token(self, token):
        """验证 JWT 令牌"""
        try:
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            payload = jwt.decode(token, public_pem, algorithms=[self.algorithm])
            
            # 检查令牌是否在黑名单中
            if self.is_token_blacklisted(payload.get('jti')):
                raise jwt.InvalidTokenError('Token is blacklisted')
            
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError('Token has expired')
        except jwt.InvalidTokenError:
            raise jwt.InvalidTokenError('Invalid token')
```

#### 权限控制系统
```python
# rbac.py
from enum import Enum
from functools import wraps

class Permission(Enum):
    READ_USER = 'read:user'
    WRITE_USER = 'write:user'
    DELETE_USER = 'delete:user'
    READ_ADMIN = 'read:admin'
    WRITE_ADMIN = 'write:admin'
    SYSTEM_CONFIG = 'system:config'

class Role(Enum):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'

# 角色权限映射
ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.READ_USER
    ],
    Role.MODERATOR: [
        Permission.READ_USER,
        Permission.WRITE_USER
    ],
    Role.ADMIN: [
        Permission.READ_USER,
        Permission.WRITE_USER,
        Permission.DELETE_USER,
        Permission.READ_ADMIN
    ],
    Role.SUPER_ADMIN: [
        Permission.READ_USER,
        Permission.WRITE_USER,
        Permission.DELETE_USER,
        Permission.READ_ADMIN,
        Permission.WRITE_ADMIN,
        Permission.SYSTEM_CONFIG
    ]
}

def require_permission(permission):
    """权限装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从请求中获取用户权限
            user_permissions = get_current_user_permissions()
            
            if permission.value not in user_permissions:
                raise PermissionError(f'Required permission: {permission.value}')
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role):
    """角色装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = get_current_user_role()
            required_permissions = ROLE_PERMISSIONS.get(role, [])
            user_permissions = get_current_user_permissions()
            
            if not all(perm.value in user_permissions for perm in required_permissions):
                raise PermissionError(f'Required role: {role.value}')
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### 多因素认证 (MFA)

#### TOTP 实现
```python
# mfa.py
import pyotp
import qrcode
import io
import base64
from cryptography.fernet import Fernet

class MFAManager:
    def __init__(self, encryption_key):
        self.cipher = Fernet(encryption_key)
    
    def generate_secret(self, user_id):
        """为用户生成 TOTP 密钥"""
        secret = pyotp.random_base32()
        
        # 加密存储密钥
        encrypted_secret = self.cipher.encrypt(secret.encode())
        
        # 保存到数据库
        self.save_user_mfa_secret(user_id, encrypted_secret)
        
        return secret
    
    def generate_qr_code(self, user_email, secret):
        """生成 QR 码"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name='ChronoRetrace'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        
        # 转换为 base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f'data:image/png;base64,{img_str}'
    
    def verify_totp(self, user_id, token):
        """验证 TOTP 令牌"""
        # 获取用户的加密密钥
        encrypted_secret = self.get_user_mfa_secret(user_id)
        if not encrypted_secret:
            return False
        
        # 解密密钥
        secret = self.cipher.decrypt(encrypted_secret).decode()
        
        # 验证令牌
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # 允许前后30秒的时间窗口
    
    def generate_backup_codes(self, user_id):
        """生成备用恢复码"""
        codes = []
        for _ in range(10):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            codes.append(code)
        
        # 加密存储备用码
        encrypted_codes = [self.cipher.encrypt(code.encode()) for code in codes]
        self.save_user_backup_codes(user_id, encrypted_codes)
        
        return codes
```

## 网络安全

### 防火墙配置

#### iptables 规则
```bash
#!/bin/bash
# firewall_rules.sh

# 清除现有规则
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# 设置默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH 访问（限制源 IP）
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -m state --state NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -m state --state NEW -j ACCEPT

# HTTP/HTTPS 访问
iptables -A INPUT -p tcp --dport 80 -m state --state NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m state --state NEW -j ACCEPT

# 应用端口（仅内网访问）
iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -m state --state NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -s 10.0.0.0/8 -m state --state NEW -j ACCEPT

# 数据库端口（仅应用服务器访问）
iptables -A INPUT -p tcp --dport 5432 -s 10.0.1.0/24 -m state --state NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 6379 -s 10.0.1.0/24 -m state --state NEW -j ACCEPT

# 监控端口（仅监控服务器访问）
iptables -A INPUT -p tcp --dport 9090 -s 10.0.2.0/24 -m state --state NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 3001 -s 10.0.2.0/24 -m state --state NEW -j ACCEPT

# 防止 DDoS 攻击
iptables -A INPUT -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT

# 防止端口扫描
iptables -A INPUT -m recent --name portscan --rcheck --seconds 86400 -j DROP
iptables -A INPUT -m recent --name portscan --remove
iptables -A INPUT -p tcp -m tcp --dport 139 -m recent --name portscan --set -j LOG --log-prefix "portscan:"
iptables -A INPUT -p tcp -m tcp --dport 139 -m recent --name portscan --set -j DROP

# 记录被丢弃的包
iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables denied: " --log-level 7

# 保存规则
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6
```

### WAF 配置

#### ModSecurity 规则
```apache
# modsecurity.conf

# 基础配置
SecRuleEngine On
SecRequestBodyAccess On
SecResponseBodyAccess Off
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072
SecRequestBodyInMemoryLimit 131072
SecRequestBodyLimitAction Reject

# 审计日志
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogParts ABIJDEFHZ
SecAuditLogType Serial
SecAuditLog /var/log/modsec_audit.log

# 核心规则集
Include /etc/modsecurity/crs/crs-setup.conf
Include /etc/modsecurity/crs/rules/*.conf

# 自定义规则
# 防止 SQL 注入
SecRule ARGS "@detectSQLi" \
    "id:1001,\
    phase:2,\
    block,\
    msg:'SQL Injection Attack Detected',\
    logdata:'Matched Data: %{MATCHED_VAR} found within %{MATCHED_VAR_NAME}',\
    tag:'application-multi',\
    tag:'language-multi',\
    tag:'platform-multi',\
    tag:'attack-sqli'"

# 防止 XSS 攻击
SecRule ARGS "@detectXSS" \
    "id:1002,\
    phase:2,\
    block,\
    msg:'XSS Attack Detected',\
    logdata:'Matched Data: %{MATCHED_VAR} found within %{MATCHED_VAR_NAME}',\
    tag:'application-multi',\
    tag:'language-multi',\
    tag:'platform-multi',\
    tag:'attack-xss'"

# 限制请求频率
SecRule IP:REQUEST_COUNT "@gt 100" \
    "id:1003,\
    phase:1,\
    deny,\
    status:429,\
    msg:'Rate limit exceeded',\
    expirevar:IP:REQUEST_COUNT=60"

SecAction "id:1004,phase:1,initcol:IP=%{REMOTE_ADDR},setvar:IP.REQUEST_COUNT=+1"
```

### TLS/SSL 配置

#### Nginx SSL 配置
```nginx
# nginx_ssl.conf
server {
    listen 443 ssl http2;
    server_name chronoretrace.com;
    
    # SSL 证书
    ssl_certificate /etc/ssl/certs/chronoretrace.crt;
    ssl_certificate_key /etc/ssl/private/chronoretrace.key;
    
    # SSL 协议和加密套件
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # SSL 会话
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
    
    # 隐藏服务器信息
    server_tokens off;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 安全头
        proxy_hide_header X-Powered-By;
        proxy_hide_header Server;
    }
}

# 强制 HTTPS 重定向
server {
    listen 80;
    server_name chronoretrace.com;
    return 301 https://$server_name$request_uri;
}
```

## 数据保护

### 数据加密

#### 数据库加密
```sql
-- PostgreSQL 透明数据加密配置

-- 启用 pgcrypto 扩展
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 创建加密函数
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(encrypt(data::bytea, 'encryption_key', 'aes'), 'base64');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN convert_from(decrypt(decode(encrypted_data, 'base64'), 'encryption_key', 'aes'), 'UTF8');
END;
$$ LANGUAGE plpgsql;

-- 创建加密表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone_encrypted TEXT,  -- 加密存储
    ssn_encrypted TEXT,    -- 加密存储
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入加密数据
INSERT INTO users (username, email, password_hash, phone_encrypted, ssn_encrypted)
VALUES (
    'john_doe',
    'john@example.com',
    '$2b$12$...',  -- bcrypt 哈希
    encrypt_sensitive_data('123-456-7890'),
    encrypt_sensitive_data('123-45-6789')
);

-- 查询解密数据
SELECT 
    username,
    email,
    decrypt_sensitive_data(phone_encrypted) AS phone,
    decrypt_sensitive_data(ssn_encrypted) AS ssn
FROM users
WHERE id = 1;
```

#### 应用层加密
```python
# encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    def __init__(self, password=None):
        if password:
            self.key = self._derive_key(password)
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password):
        """从密码派生加密密钥"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data):
        """加密数据"""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data):
        """解密数据"""
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def encrypt_file(self, file_path):
        """加密文件"""
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        encrypted_data = self.cipher.encrypt(file_data)
        
        with open(f"{file_path}.encrypted", 'wb') as file:
            file.write(encrypted_data)
    
    def decrypt_file(self, encrypted_file_path, output_path):
        """解密文件"""
        with open(encrypted_file_path, 'rb') as file:
            encrypted_data = file.read()
        
        decrypted_data = self.cipher.decrypt(encrypted_data)
        
        with open(output_path, 'wb') as file:
            file.write(decrypted_data)

# 使用示例
encryption = DataEncryption(password="your-secret-password")

# 加密敏感数据
sensitive_data = "用户身份证号码: 123456789012345678"
encrypted = encryption.encrypt(sensitive_data)

# 解密数据
decrypted = encryption.decrypt(encrypted)
print(decrypted)
```

### 数据脱敏

#### 敏感数据脱敏
```python
# data_masking.py
import re
import hashlib

class DataMasking:
    @staticmethod
    def mask_email(email):
        """邮箱脱敏"""
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone):
        """手机号脱敏"""
        phone = re.sub(r'\D', '', phone)  # 移除非数字字符
        if len(phone) >= 7:
            return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]
        return '*' * len(phone)
    
    @staticmethod
    def mask_id_card(id_card):
        """身份证号脱敏"""
        if len(id_card) >= 8:
            return id_card[:4] + '*' * (len(id_card) - 8) + id_card[-4:]
        return '*' * len(id_card)
    
    @staticmethod
    def mask_credit_card(card_number):
        """信用卡号脱敏"""
        card_number = re.sub(r'\D', '', card_number)
        if len(card_number) >= 8:
            return card_number[:4] + '*' * (len(card_number) - 8) + card_number[-4:]
        return '*' * len(card_number)
    
    @staticmethod
    def hash_sensitive_data(data, salt=None):
        """敏感数据哈希化"""
        if salt is None:
            salt = 'default_salt'
        
        combined = f"{data}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def mask_ip_address(ip):
        """IP 地址脱敏"""
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.*.* "
        return ip

# 使用示例
masking = DataMasking()

print(masking.mask_email("user@example.com"))  # u**r@example.com
print(masking.mask_phone("13812345678"))       # 138****5678
print(masking.mask_id_card("123456789012345678"))  # 1234**********5678
print(masking.mask_credit_card("1234567890123456"))  # 1234********3456
```

## 应用安全

### 输入验证和清理

#### 输入验证框架
```python
# input_validation.py
import re
from typing import Any, Dict, List
from html import escape
import bleach

class InputValidator:
    def __init__(self):
        self.patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?[1-9]\d{1,14}$',
            'username': r'^[a-zA-Z0-9_]{3,20}$',
            'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
            'url': r'^https?://[^\s/$.?#].[^\s]*$',
            'ip': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        }
    
    def validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        return bool(re.match(self.patterns['email'], email))
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        result = {
            'valid': False,
            'errors': []
        }
        
        if len(password) < 8:
            result['errors'].append('密码长度至少8位')
        
        if not re.search(r'[a-z]', password):
            result['errors'].append('密码必须包含小写字母')
        
        if not re.search(r'[A-Z]', password):
            result['errors'].append('密码必须包含大写字母')
        
        if not re.search(r'\d', password):
            result['errors'].append('密码必须包含数字')
        
        if not re.search(r'[@$!%*?&]', password):
            result['errors'].append('密码必须包含特殊字符')
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    def sanitize_html(self, html_content: str) -> str:
        """清理 HTML 内容"""
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
        allowed_attributes = {}
        
        return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes)
    
    def escape_sql(self, value: str) -> str:
        """SQL 注入防护"""
        # 使用参数化查询是更好的选择，这里只是额外的防护
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
        for char in dangerous_chars:
            value = value.replace(char, '')
        return value
    
    def validate_file_upload(self, filename: str, content: bytes) -> Dict[str, Any]:
        """文件上传验证"""
        result = {
            'valid': False,
            'errors': []
        }
        
        # 检查文件扩展名
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx']
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if f'.{file_ext}' not in allowed_extensions:
            result['errors'].append(f'不允许的文件类型: {file_ext}')
        
        # 检查文件大小（10MB 限制）
        max_size = 10 * 1024 * 1024
        if len(content) > max_size:
            result['errors'].append('文件大小超过限制')
        
        # 检查文件头（魔数）
        file_signatures = {
            b'\xff\xd8\xff': 'jpg',
            b'\x89PNG\r\n\x1a\n': 'png',
            b'GIF87a': 'gif',
            b'GIF89a': 'gif',
            b'%PDF': 'pdf'
        }
        
        file_type_detected = None
        for signature, file_type in file_signatures.items():
            if content.startswith(signature):
                file_type_detected = file_type
                break
        
        if file_type_detected != file_ext:
            result['errors'].append('文件类型与扩展名不匹配')
        
        result['valid'] = len(result['errors']) == 0
        return result
```

### API 安全

#### API 限流和防护
```python
# api_security.py
import time
import hashlib
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = set()
    
    def is_rate_limited(self, identifier, limit=100, window=3600):
        """检查是否超过速率限制"""
        now = time.time()
        
        # 清理过期记录
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        # 检查请求数量
        if len(self.requests[identifier]) >= limit:
            return True
        
        # 记录当前请求
        self.requests[identifier].append(now)
        return False
    
    def block_ip(self, ip, duration=3600):
        """封禁 IP"""
        self.blocked_ips.add((ip, time.time() + duration))
    
    def is_ip_blocked(self, ip):
        """检查 IP 是否被封禁"""
        now = time.time()
        # 清理过期封禁
        self.blocked_ips = {
            (blocked_ip, expire_time) for blocked_ip, expire_time in self.blocked_ips
            if expire_time > now
        }
        
        return any(blocked_ip == ip for blocked_ip, _ in self.blocked_ips)

class APISecurityMiddleware:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'union.*select',              # SQL 注入
            r'\.\./',                     # 路径遍历
            r'eval\s*\(',                 # 代码注入
        ]
    
    def check_request_security(self, request):
        """检查请求安全性"""
        client_ip = request.remote_addr
        
        # 检查 IP 封禁
        if self.rate_limiter.is_ip_blocked(client_ip):
            return {'blocked': True, 'reason': 'IP blocked'}
        
        # 检查速率限制
        if self.rate_limiter.is_rate_limited(client_ip):
            self.rate_limiter.block_ip(client_ip, 1800)  # 封禁30分钟
            return {'blocked': True, 'reason': 'Rate limit exceeded'}
        
        # 检查恶意模式
        request_data = str(request.get_data())
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                self.rate_limiter.block_ip(client_ip, 3600)  # 封禁1小时
                return {'blocked': True, 'reason': 'Malicious pattern detected'}
        
        return {'blocked': False}

def require_api_key(f):
    """API 密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # 验证 API 密钥
        if not validate_api_key(api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_api_key(api_key):
    """验证 API 密钥"""
    # 从数据库或配置中获取有效的 API 密钥
    valid_keys = get_valid_api_keys()
    
    # 使用哈希比较避免时序攻击
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    for valid_key in valid_keys:
        valid_key_hash = hashlib.sha256(valid_key.encode()).hexdigest()
        if api_key_hash == valid_key_hash:
            return True
    
    return False
```

## 基础设施安全

### 容器安全

#### Docker 安全配置
```dockerfile
# Dockerfile.secure
FROM node:16-alpine AS builder

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖（仅生产依赖）
RUN npm ci --only=production && npm cache clean --force

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产镜像
FROM node:16-alpine AS runner

# 安全更新
RUN apk update && apk upgrade

# 创建用户
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# 设置工作目录
WORKDIR /app

# 复制构建产物
COPY --from=builder --chown=nextjs:nodejs /app/dist ./dist
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json

# 切换到非 root 用户
USER nextjs

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# 启动应用
CMD ["npm", "start"]
```

#### Kubernetes 安全策略
```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: chronoretrace-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chronoretrace-network-policy
  namespace: chronoretrace
spec:
  podSelector:
    matchLabels:
      app: chronoretrace
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### 系统加固

#### Linux 系统加固脚本
```bash
#!/bin/bash
# system_hardening.sh

set -e

echo "开始系统安全加固..."

# 更新系统
apt update && apt upgrade -y

# 安装安全工具
apt install -y fail2ban ufw rkhunter chkrootkit lynis

# 配置防火墙
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 配置 SSH 安全
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
cat > /etc/ssh/sshd_config << EOF
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers chronoretrace
EOF

systemctl restart sshd

# 配置 fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl start fail2ban

# 设置文件权限
chmod 700 /root
chmod 600 /etc/ssh/sshd_config
chmod 644 /etc/passwd
chmod 600 /etc/shadow
chmod 644 /etc/group

# 禁用不必要的服务
systemctl disable avahi-daemon
systemctl disable cups
systemctl disable bluetooth

# 配置内核参数
cat >> /etc/sysctl.conf << EOF
# 网络安全
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.ip_forward = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# 内存保护
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
EOF

sysctl -p

# 配置日志审计
apt install -y auditd
cat > /etc/audit/rules.d/audit.rules << EOF
# 监控重要文件
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k identity
-w /etc/ssh/sshd_config -p wa -k sshd

# 监控系统调用
-a always,exit -F arch=b64 -S adjtimex -S settimeofday -k time-change
-a always,exit -F arch=b64 -S clock_settime -k time-change
-w /etc/localtime -p wa -k time-change

# 监控网络配置
-w /etc/hosts -p wa -k network
-w /etc/network/ -p wa -k network

# 监控登录事件
-w /var/log/faillog -p wa -k logins
-w /var/log/lastlog -p wa -k logins
-w /var/log/tallylog -p wa -k logins
EOF

systemctl enable auditd
systemctl start auditd

echo "系统安全加固完成！"
```

## 监控与审计

### 安全监控

#### 安全事件监控
```python
# security_monitoring.py
import re
import json
import time
from datetime import datetime
from collections import defaultdict

class SecurityMonitor:
    def __init__(self):
        self.failed_logins = defaultdict(list)
        self.suspicious_activities = []
        self.alert_thresholds = {
            'failed_login_attempts': 5,
            'failed_login_window': 300,  # 5分钟
            'suspicious_ip_threshold': 10
        }
    
    def monitor_failed_login(self, ip_address, username, timestamp=None):
        """监控失败登录尝试"""
        if timestamp is None:
            timestamp = time.time()
        
        # 记录失败登录
        self.failed_logins[ip_address].append({
            'username': username,
            'timestamp': timestamp
        })
        
        # 清理过期记录
        window = self.alert_thresholds['failed_login_window']
        self.failed_logins[ip_address] = [
            attempt for attempt in self.failed_logins[ip_address]
            if timestamp - attempt['timestamp'] < window
        ]
        
        # 检查是否超过阈值
        if len(self.failed_logins[ip_address]) >= self.alert_thresholds['failed_login_attempts']:
            self.trigger_alert('brute_force_attack', {
                'ip_address': ip_address,
                'attempts': len(self.failed_logins[ip_address]),
                'usernames': [attempt['username'] for attempt in self.failed_logins[ip_address]]
            })
    
    def monitor_suspicious_activity(self, activity_type, details):
        """监控可疑活动"""
        event = {
            'type': activity_type,
            'details': details,
            'timestamp': time.time()
        }
        
        self.suspicious_activities.append(event)
        
        # 触发相应的告警
        if activity_type == 'sql_injection_attempt':
            self.trigger_alert('sql_injection', details)
        elif activity_type == 'xss_attempt':
            self.trigger_alert('xss_attack', details)
        elif activity_type == 'privilege_escalation':
            self.trigger_alert('privilege_escalation', details)
    
    def trigger_alert(self, alert_type, details):
        """触发安全告警"""
        alert = {
            'type': alert_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'severity': self.get_alert_severity(alert_type)
        }
        
        # 记录告警
        self.log_security_alert(alert)
        
        # 发送通知
        self.send_security_notification(alert)
    
    def get_alert_severity(self, alert_type):
        """获取告警严重级别"""
        severity_map = {
            'brute_force_attack': 'high',
            'sql_injection': 'critical',
            'xss_attack': 'high',
            'privilege_escalation': 'critical',
            'data_breach': 'critical',
            'unauthorized_access': 'high'
        }
        return severity_map.get(alert_type, 'medium')
    
    def log_security_alert(self, alert):
        """记录安全告警"""
        log_entry = {
            'timestamp': alert['timestamp'],
            'level': 'SECURITY_ALERT',
            'type': alert['type'],
            'severity': alert['severity'],
            'details': alert['details']
        }
        
        # 写入安全日志
        with open('/var/log/chronoretrace/security.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def send_security_notification(self, alert):
        """发送安全通知"""
        if alert['severity'] in ['critical', 'high']:
            # 发送紧急通知
            self.send_emergency_notification(alert)
        else:
            # 发送常规通知
            self.send_regular_notification(alert)
    
    def analyze_log_patterns(self, log_file):
        """分析日志模式"""
        patterns = {
            'sql_injection': r'(union|select|insert|update|delete|drop).*?(from|into|table)',
            'xss_attack': r'<script[^>]*>.*?</script>',
            'path_traversal': r'\.\./',
            'command_injection': r'(;|\||&|`|\$\()',
            'brute_force': r'authentication failed|invalid password|login failed'
        }
        
        with open(log_file, 'r') as f:
            for line in f:
                for pattern_name, pattern in patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        self.monitor_suspicious_activity(pattern_name, {
                            'log_line': line.strip(),
                            'pattern': pattern_name
                        })
```

### 审计日志

#### 审计日志配置
```python
# audit_logging.py
import json
import time
from datetime import datetime
from functools import wraps
from flask import request, g

class AuditLogger:
    def __init__(self, log_file='/var/log/chronoretrace/audit.log'):
        self.log_file = log_file
    
    def log_event(self, event_type, details, user_id=None, ip_address=None):
        """记录审计事件"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address or self.get_client_ip(),
            'details': details,
            'session_id': getattr(g, 'session_id', None)
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def get_client_ip(self):
        """获取客户端 IP"""
        if request:
            return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        return None

def audit_action(action_type):
    """审计装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功的操作
                audit_logger.log_event(
                    event_type=f'{action_type}_success',
                    details={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs),
                        'execution_time': time.time() - start_time
                    },
                    user_id=getattr(g, 'user_id', None)
                )
                
                return result
                
            except Exception as e:
                # 记录失败的操作
                audit_logger.log_event(
                    event_type=f'{action_type}_failure',
                    details={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs),
                        'error': str(e),
                        'execution_time': time.time() - start_time
                    },
                    user_id=getattr(g, 'user_id', None)
                )
                raise
        
        return wrapper
    return decorator

# 全局审计日志实例
audit_logger = AuditLogger()

# 使用示例
@audit_action('user_login')
def user_login(username, password):
    # 登录逻辑
    pass

@audit_action('data_access')
def get_user_data(user_id):
    # 数据访问逻辑
    pass

@audit_action('admin_operation')
def delete_user(user_id):
    # 管理员操作逻辑
    pass
```

## 合规要求

### GDPR 合规

#### 数据保护实现
```python
# gdpr_compliance.py
from datetime import datetime, timedelta
import json

class GDPRCompliance:
    def __init__(self):
        self.data_retention_periods = {
            'user_data': 365 * 2,      # 2年
            'log_data': 365,           # 1年
            'session_data': 30,        # 30天
            'analytics_data': 365 * 3  # 3年
        }
    
    def handle_data_subject_request(self, request_type, user_id, details=None):
        """处理数据主体请求"""
        if request_type == 'access':
            return self.export_user_data(user_id)
        elif request_type == 'rectification':
            return self.update_user_data(user_id, details)
        elif request_type == 'erasure':
            return self.delete_user_data(user_id)
        elif request_type == 'portability':
            return self.export_portable_data(user_id)
        elif request_type == 'restriction':
            return self.restrict_data_processing(user_id)
        else:
            raise ValueError(f'Unknown request type: {request_type}')
    
    def export_user_data(self, user_id):
        """导出用户数据（GDPR 第15条）"""
        user_data = {
            'personal_data': self.get_personal_data(user_id),
            'processing_purposes': self.get_processing_purposes(user_id),
            'data_categories': self.get_data_categories(user_id),
            'recipients': self.get_data_recipients(user_id),
            'retention_period': self.get_retention_period(user_id),
            'data_source': self.get_data_source(user_id),
            'automated_decision_making': self.get_automated_decisions(user_id)
        }
        
        # 记录数据导出请求
        self.log_gdpr_request('data_export', user_id, user_data)
        
        return user_data
    
    def delete_user_data(self, user_id):
        """删除用户数据（GDPR 第17条）"""
        try:
            # 删除个人数据
            self.delete_personal_data(user_id)
            
            # 删除关联数据
            self.delete_user_sessions(user_id)
            self.delete_user_logs(user_id)
            self.anonymize_user_analytics(user_id)
            
            # 记录删除操作
            self.log_gdpr_request('data_erasure', user_id, {'status': 'completed'})
            
            return {'status': 'success', 'message': 'User data deleted successfully'}
            
        except Exception as e:
            self.log_gdpr_request('data_erasure', user_id, {'status': 'failed', 'error': str(e)})
            raise
    
    def check_data_retention(self):
        """检查数据保留期限"""
        expired_data = []
        
        for data_type, retention_days in self.data_retention_periods.items():
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            expired_records = self.find_expired_data(data_type, cutoff_date)
            
            if expired_records:
                expired_data.append({
                    'data_type': data_type,
                    'count': len(expired_records),
                    'cutoff_date': cutoff_date.isoformat()
                })
        
        return expired_data
    
    def auto_delete_expired_data(self):
        """自动删除过期数据"""
        expired_data = self.check_data_retention()
        
        for data_info in expired_data:
            data_type = data_info['data_type']
            cutoff_date = datetime.fromisoformat(data_info['cutoff_date'])
            
            deleted_count = self.delete_expired_data(data_type, cutoff_date)
            
            self.log_gdpr_request('auto_deletion', None, {
                 'data_type': data_type,
                 'deleted_count': deleted_count,
                 'cutoff_date': cutoff_date.isoformat()
             })

## 安全事件响应

### 事件响应流程

#### 安全事件分类
```python
# incident_response.py
from enum import Enum
from datetime import datetime
import json

class IncidentSeverity(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class IncidentType(Enum):
    DATA_BREACH = 'data_breach'
    MALWARE = 'malware'
    DDOS = 'ddos'
    UNAUTHORIZED_ACCESS = 'unauthorized_access'
    SYSTEM_COMPROMISE = 'system_compromise'
    INSIDER_THREAT = 'insider_threat'

class IncidentResponse:
    def __init__(self):
        self.response_team = {
            'incident_commander': 'security@chronoretrace.com',
            'technical_lead': 'tech-lead@chronoretrace.com',
            'communications': 'pr@chronoretrace.com',
            'legal': 'legal@chronoretrace.com'
        }
        
        self.escalation_matrix = {
            IncidentSeverity.CRITICAL: {
                'response_time': 15,  # 分钟
                'notification_list': ['ceo', 'cto', 'security_team', 'legal']
            },
            IncidentSeverity.HIGH: {
                'response_time': 60,
                'notification_list': ['cto', 'security_team']
            },
            IncidentSeverity.MEDIUM: {
                'response_time': 240,
                'notification_list': ['security_team']
            },
            IncidentSeverity.LOW: {
                'response_time': 1440,  # 24小时
                'notification_list': ['security_team']
            }
        }
    
    def create_incident(self, incident_type, severity, description, affected_systems=None):
        """创建安全事件"""
        incident = {
            'id': self.generate_incident_id(),
            'type': incident_type.value,
            'severity': severity.value,
            'description': description,
            'affected_systems': affected_systems or [],
            'created_at': datetime.now().isoformat(),
            'status': 'open',
            'assigned_to': None,
            'timeline': []
        }
        
        # 立即响应
        self.initiate_response(incident)
        
        return incident
    
    def initiate_response(self, incident):
        """启动事件响应"""
        severity = IncidentSeverity(incident['severity'])
        
        # 发送通知
        self.send_incident_notifications(incident, severity)
        
        # 执行自动响应
        self.execute_automated_response(incident)
        
        # 记录响应开始
         self.add_timeline_entry(incident, 'response_initiated', {
             'responder': 'system',
             'action': 'Automated response initiated'
         })
```

### 应急响应手册

#### 数据泄露响应
```bash
#!/bin/bash
# data_breach_response.sh

echo "数据泄露应急响应程序启动..."

# 1. 立即隔离受影响系统
echo "步骤1: 隔离受影响系统"
iptables -A INPUT -s $SUSPICIOUS_IP -j DROP
iptables -A OUTPUT -d $SUSPICIOUS_IP -j DROP

# 2. 保存证据
echo "步骤2: 保存证据"
mkdir -p /var/log/incident_$(date +%Y%m%d_%H%M%S)
cp /var/log/nginx/access.log /var/log/incident_$(date +%Y%m%d_%H%M%S)/
cp /var/log/auth.log /var/log/incident_$(date +%Y%m%d_%H%M%S)/
cp /var/log/syslog /var/log/incident_$(date +%Y%m%d_%H%M%S)/

# 3. 通知相关人员
echo "步骤3: 发送通知"
curl -X POST "$SLACK_WEBHOOK" \
  -H 'Content-type: application/json' \
  --data '{"text":"🚨 数据泄露事件检测到，请立即响应！"}'

# 4. 启动备份系统
echo "步骤4: 启动备份系统"
docker-compose -f docker-compose.backup.yml up -d

# 5. 更改所有密码和密钥
echo "步骤5: 轮换密钥"
python /scripts/rotate_secrets.py --emergency

echo "应急响应程序完成，请查看详细日志"
```

## 安全测试

### 渗透测试

#### 自动化安全扫描
```python
# security_scanner.py
import requests
import subprocess
import json
from urllib.parse import urljoin

class SecurityScanner:
    def __init__(self, target_url):
        self.target_url = target_url
        self.vulnerabilities = []
    
    def scan_sql_injection(self):
        """SQL 注入扫描"""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' AND 1=1 --",
            "1' AND 1=2 --"
        ]
        
        test_endpoints = [
            '/api/users',
            '/api/search',
            '/login',
            '/api/data'
        ]
        
        for endpoint in test_endpoints:
            for payload in payloads:
                url = urljoin(self.target_url, endpoint)
                
                # GET 参数测试
                response = requests.get(url, params={'q': payload})
                if self.detect_sql_error(response.text):
                    self.vulnerabilities.append({
                        'type': 'SQL Injection',
                        'severity': 'High',
                        'endpoint': endpoint,
                        'payload': payload,
                        'method': 'GET'
                    })
                
                # POST 数据测试
                response = requests.post(url, data={'input': payload})
                if self.detect_sql_error(response.text):
                    self.vulnerabilities.append({
                        'type': 'SQL Injection',
                        'severity': 'High',
                        'endpoint': endpoint,
                        'payload': payload,
                        'method': 'POST'
                    })
    
    def scan_xss(self):
        """XSS 扫描"""
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in payloads:
            response = requests.post(
                urljoin(self.target_url, '/api/comment'),
                data={'content': payload}
            )
            
            if payload in response.text and 'text/html' in response.headers.get('content-type', ''):
                self.vulnerabilities.append({
                    'type': 'XSS',
                    'severity': 'Medium',
                    'payload': payload,
                    'reflected': True
                })
    
    def scan_directory_traversal(self):
        """目录遍历扫描"""
        payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\drivers\\etc\\hosts',
            '/etc/passwd',
            '/proc/version',
            '/etc/shadow'
        ]
        
        for payload in payloads:
            response = requests.get(
                urljoin(self.target_url, '/api/file'),
                params={'path': payload}
            )
            
            if 'root:' in response.text or 'daemon:' in response.text:
                self.vulnerabilities.append({
                    'type': 'Directory Traversal',
                    'severity': 'High',
                    'payload': payload,
                    'file_accessed': True
                })
    
    def detect_sql_error(self, response_text):
        """检测 SQL 错误"""
        error_patterns = [
            'mysql_fetch_array',
            'ORA-01756',
            'Microsoft OLE DB Provider',
            'PostgreSQL query failed',
            'SQLite error',
            'syntax error'
        ]
        
        return any(pattern.lower() in response_text.lower() for pattern in error_patterns)
    
    def generate_report(self):
        """生成扫描报告"""
        report = {
            'target': self.target_url,
            'scan_date': datetime.now().isoformat(),
            'total_vulnerabilities': len(self.vulnerabilities),
            'vulnerabilities': self.vulnerabilities,
            'summary': {
                'critical': len([v for v in self.vulnerabilities if v['severity'] == 'Critical']),
                'high': len([v for v in self.vulnerabilities if v['severity'] == 'High']),
                'medium': len([v for v in self.vulnerabilities if v['severity'] == 'Medium']),
                'low': len([v for v in self.vulnerabilities if v['severity'] == 'Low'])
            }
        }
        
        return report
```

### 安全最佳实践

#### 开发安全检查清单

**代码审查检查项**
- [ ] 输入验证和清理
- [ ] 输出编码
- [ ] 参数化查询
- [ ] 适当的错误处理
- [ ] 安全的密码存储
- [ ] 会话管理
- [ ] 访问控制
- [ ] 日志记录
- [ ] 加密实现
- [ ] 依赖项安全

**部署安全检查项**
- [ ] 最小权限原则
- [ ] 网络分段
- [ ] 防火墙配置
- [ ] SSL/TLS 配置
- [ ] 安全头设置
- [ ] 日志监控
- [ ] 备份策略
- [ ] 更新管理
- [ ] 访问审计
- [ ] 事件响应计划

#### 安全配置验证脚本
```bash
#!/bin/bash
# security_validation.sh

echo "开始安全配置验证..."

# 检查 SSL 配置
echo "检查 SSL 配置..."
ssl_score=$(curl -s "https://api.ssllabs.com/api/v3/analyze?host=chronoretrace.com" | jq '.endpoints[0].grade')
echo "SSL Labs 评分: $ssl_score"

# 检查安全头
echo "检查安全头..."
curl -I https://chronoretrace.com | grep -E "(Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options|X-XSS-Protection|Content-Security-Policy)"

# 检查开放端口
echo "检查开放端口..."
nmap -sS -O localhost

# 检查文件权限
echo "检查关键文件权限..."
ls -la /etc/passwd /etc/shadow /etc/ssh/sshd_config

# 检查运行服务
echo "检查运行服务..."
systemctl list-units --type=service --state=running

# 检查防火墙状态
echo "检查防火墙状态..."
ufw status verbose

# 检查失败登录
echo "检查最近失败登录..."
lastb | head -10

# 检查系统更新
echo "检查系统更新..."
apt list --upgradable

echo "安全配置验证完成！"
```

## 总结

本安全配置指南涵盖了 ChronoRetrace 应用的全面安全措施，包括：

1. **身份认证与授权**: JWT 认证、多因素认证、基于角色的访问控制
2. **网络安全**: 防火墙配置、WAF 保护、TLS/SSL 加密
3. **数据保护**: 数据加密、数据脱敏、GDPR 合规
4. **应用安全**: 输入验证、API 安全、安全编码实践
5. **基础设施安全**: 容器安全、系统加固、安全监控
6. **事件响应**: 安全监控、审计日志、应急响应
7. **合规要求**: GDPR 实施、数据保护、隐私管理
8. **安全测试**: 渗透测试、漏洞扫描、安全验证

**重要提醒**:
- 定期更新安全配置和策略
- 持续监控和审计安全事件
- 定期进行安全培训和演练
- 保持安全工具和系统的最新状态
- 建立完善的事件响应流程

遵循本指南的安全措施，可以有效保护 ChronoRetrace 应用免受各种安全威胁，确保用户数据和系统的安全性。
```}]},"query_language":"Chinese"}}