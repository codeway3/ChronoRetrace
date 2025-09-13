#!/usr/bin/env python3
"""
ChronoRetrace 监控系统部署脚本
自动化部署Prometheus、Grafana、Alertmanager等监控组件
"""

import os
import sys
import subprocess
import yaml
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring_deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MonitoringConfig:
    """监控配置类"""
    prometheus_port: int = 9090
    grafana_port: int = 3000
    alertmanager_port: int = 9093
    node_exporter_port: int = 9100
    postgres_exporter_port: int = 9187
    redis_exporter_port: int = 9121
    nginx_exporter_port: int = 9113
    
    # 数据存储路径
    prometheus_data_dir: str = "/var/lib/prometheus"
    grafana_data_dir: str = "/var/lib/grafana"
    
    # 配置文件路径
    config_dir: str = "/Users/apple/code/ChronoRetrace/backend/config"
    
    # Docker网络
    network_name: str = "chronoretrace-monitoring"
    
    # 认证信息
    grafana_admin_user: str = "admin"
    grafana_admin_password: str = "chronoretrace2024"
    
    # 告警配置
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    alert_email: str = "alerts@chronoretrace.com"
    slack_webhook: str = ""

class MonitoringDeployer:
    """监控系统部署器"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.project_root = Path("/Users/apple/code/ChronoRetrace")
        self.config_dir = Path(config.config_dir)
        
    def deploy_all(self) -> bool:
        """部署完整监控系统"""
        try:
            logger.info("开始部署ChronoRetrace监控系统...")
            
            # 1. 环境准备
            self._prepare_environment()
            
            # 2. 创建Docker网络
            self._create_docker_network()
            
            # 3. 部署Prometheus
            self._deploy_prometheus()
            
            # 4. 部署Grafana
            self._deploy_grafana()
            
            # 5. 部署Alertmanager
            self._deploy_alertmanager()
            
            # 6. 部署Exporters
            self._deploy_exporters()
            
            # 7. 配置Grafana数据源和仪表板
            self._configure_grafana()
            
            # 8. 验证部署
            self._verify_deployment()
            
            logger.info("监控系统部署完成!")
            self._print_access_info()
            return True
            
        except Exception as e:
            logger.error(f"监控系统部署失败: {e}")
            return False
    
    def _prepare_environment(self):
        """准备部署环境"""
        logger.info("准备部署环境...")
        
        # 创建数据目录
        os.makedirs(self.config.prometheus_data_dir, exist_ok=True)
        os.makedirs(self.config.grafana_data_dir, exist_ok=True)
        
        # 设置目录权限
        subprocess.run(["sudo", "chown", "-R", "65534:65534", self.config.prometheus_data_dir], check=True)
        subprocess.run(["sudo", "chown", "-R", "472:472", self.config.grafana_data_dir], check=True)
        
        # 检查Docker是否运行
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            raise Exception("Docker未运行，请先启动Docker")
    
    def _create_docker_network(self):
        """创建Docker网络"""
        logger.info(f"创建Docker网络: {self.config.network_name}")
        
        try:
            # 检查网络是否已存在
            result = subprocess.run(
                ["docker", "network", "ls", "--filter", f"name={self.config.network_name}", "--format", "{{.Name}}"],
                capture_output=True, text=True
            )
            
            if self.config.network_name not in result.stdout:
                subprocess.run([
                    "docker", "network", "create",
                    "--driver", "bridge",
                    self.config.network_name
                ], check=True)
                logger.info(f"Docker网络 {self.config.network_name} 创建成功")
            else:
                logger.info(f"Docker网络 {self.config.network_name} 已存在")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"创建Docker网络失败: {e}")
    
    def _deploy_prometheus(self):
        """部署Prometheus"""
        logger.info("部署Prometheus...")
        
        # 停止并删除现有容器
        self._stop_container("chronoretrace-prometheus")
        
        # 启动Prometheus容器
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-prometheus",
            "--network", self.config.network_name,
            "-p", f"{self.config.prometheus_port}:9090",
            "-v", f"{self.config_dir}/prometheus.yml:/etc/prometheus/prometheus.yml",
            "-v", f"{self.config_dir}/alert-rules.yml:/etc/prometheus/alert-rules.yml",
            "-v", f"{self.config.prometheus_data_dir}:/prometheus",
            "--user", "65534:65534",
            "prom/prometheus:latest",
            "--config.file=/etc/prometheus/prometheus.yml",
            "--storage.tsdb.path=/prometheus",
            "--web.console.libraries=/etc/prometheus/console_libraries",
            "--web.console.templates=/etc/prometheus/consoles",
            "--storage.tsdb.retention.time=30d",
            "--web.enable-lifecycle",
            "--web.enable-admin-api"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Prometheus部署成功")
        
        # 等待服务启动
        self._wait_for_service(f"http://localhost:{self.config.prometheus_port}/-/healthy", "Prometheus")
    
    def _deploy_grafana(self):
        """部署Grafana"""
        logger.info("部署Grafana...")
        
        # 停止并删除现有容器
        self._stop_container("chronoretrace-grafana")
        
        # 启动Grafana容器
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-grafana",
            "--network", self.config.network_name,
            "-p", f"{self.config.grafana_port}:3000",
            "-v", f"{self.config.grafana_data_dir}:/var/lib/grafana",
            "-e", f"GF_SECURITY_ADMIN_USER={self.config.grafana_admin_user}",
            "-e", f"GF_SECURITY_ADMIN_PASSWORD={self.config.grafana_admin_password}",
            "-e", "GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource",
            "--user", "472:472",
            "grafana/grafana:latest"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Grafana部署成功")
        
        # 等待服务启动
        self._wait_for_service(f"http://localhost:{self.config.grafana_port}/api/health", "Grafana")
    
    def _deploy_alertmanager(self):
        """部署Alertmanager"""
        logger.info("部署Alertmanager...")
        
        # 停止并删除现有容器
        self._stop_container("chronoretrace-alertmanager")
        
        # 启动Alertmanager容器
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-alertmanager",
            "--network", self.config.network_name,
            "-p", f"{self.config.alertmanager_port}:9093",
            "-v", f"{self.config_dir}/alertmanager.yml:/etc/alertmanager/alertmanager.yml",
            "prom/alertmanager:latest",
            "--config.file=/etc/alertmanager/alertmanager.yml",
            "--storage.path=/alertmanager",
            "--web.external-url=http://localhost:9093"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Alertmanager部署成功")
        
        # 等待服务启动
        self._wait_for_service(f"http://localhost:{self.config.alertmanager_port}/-/healthy", "Alertmanager")
    
    def _deploy_exporters(self):
        """部署各种Exporters"""
        logger.info("部署Exporters...")
        
        # Node Exporter
        self._deploy_node_exporter()
        
        # PostgreSQL Exporter
        self._deploy_postgres_exporter()
        
        # Redis Exporter
        self._deploy_redis_exporter()
        
        # Nginx Exporter
        self._deploy_nginx_exporter()
    
    def _deploy_node_exporter(self):
        """部署Node Exporter"""
        logger.info("部署Node Exporter...")
        
        self._stop_container("chronoretrace-node-exporter")
        
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-node-exporter",
            "--network", self.config.network_name,
            "-p", f"{self.config.node_exporter_port}:9100",
            "--pid", "host",
            "-v", "/:/host:ro,rslave",
            "prom/node-exporter:latest",
            "--path.rootfs=/host"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Node Exporter部署成功")
    
    def _deploy_postgres_exporter(self):
        """部署PostgreSQL Exporter"""
        logger.info("部署PostgreSQL Exporter...")
        
        self._stop_container("chronoretrace-postgres-exporter")
        
        # 从环境变量或配置文件获取数据库连接信息
        db_url = os.getenv('DATABASE_URL', 'postgresql://chronoretrace:password@localhost:5432/chronoretrace')
        
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-postgres-exporter",
            "--network", self.config.network_name,
            "-p", f"{self.config.postgres_exporter_port}:9187",
            "-e", f"DATA_SOURCE_NAME={db_url}",
            "prometheuscommunity/postgres-exporter:latest"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("PostgreSQL Exporter部署成功")
    
    def _deploy_redis_exporter(self):
        """部署Redis Exporter"""
        logger.info("部署Redis Exporter...")
        
        self._stop_container("chronoretrace-redis-exporter")
        
        # Redis连接信息
        redis_addr = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-redis-exporter",
            "--network", self.config.network_name,
            "-p", f"{self.config.redis_exporter_port}:9121",
            "oliver006/redis_exporter:latest",
            f"--redis.addr={redis_addr}"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Redis Exporter部署成功")
    
    def _deploy_nginx_exporter(self):
        """部署Nginx Exporter"""
        logger.info("部署Nginx Exporter...")
        
        self._stop_container("chronoretrace-nginx-exporter")
        
        cmd = [
            "docker", "run", "-d",
            "--name", "chronoretrace-nginx-exporter",
            "--network", self.config.network_name,
            "-p", f"{self.config.nginx_exporter_port}:9113",
            "nginx/nginx-prometheus-exporter:latest",
            "-nginx.scrape-uri=http://nginx:8080/nginx_status"
        ]
        
        subprocess.run(cmd, check=True)
        logger.info("Nginx Exporter部署成功")
    
    def _configure_grafana(self):
        """配置Grafana数据源和仪表板"""
        logger.info("配置Grafana...")
        
        # 等待Grafana完全启动
        time.sleep(10)
        
        # 配置Prometheus数据源
        self._add_prometheus_datasource()
        
        # 导入仪表板
        self._import_dashboard()
    
    def _add_prometheus_datasource(self):
        """添加Prometheus数据源"""
        logger.info("添加Prometheus数据源...")
        
        datasource_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": f"http://chronoretrace-prometheus:9090",
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False
        }
        
        try:
            response = requests.post(
                f"http://localhost:{self.config.grafana_port}/api/datasources",
                json=datasource_config,
                auth=(self.config.grafana_admin_user, self.config.grafana_admin_password),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 409]:  # 200: 成功, 409: 已存在
                logger.info("Prometheus数据源配置成功")
            else:
                logger.warning(f"数据源配置响应: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"配置Prometheus数据源失败: {e}")
    
    def _import_dashboard(self):
        """导入Grafana仪表板"""
        logger.info("导入Grafana仪表板...")
        
        dashboard_file = self.config_dir / "grafana-dashboard.json"
        
        if not dashboard_file.exists():
            logger.warning(f"仪表板文件不存在: {dashboard_file}")
            return
        
        try:
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                dashboard_json = json.load(f)
            
            # 包装仪表板配置
            import_config = {
                "dashboard": dashboard_json,
                "overwrite": True,
                "inputs": [{
                    "name": "DS_PROMETHEUS",
                    "type": "datasource",
                    "pluginId": "prometheus",
                    "value": "Prometheus"
                }]
            }
            
            response = requests.post(
                f"http://localhost:{self.config.grafana_port}/api/dashboards/import",
                json=import_config,
                auth=(self.config.grafana_admin_user, self.config.grafana_admin_password),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("仪表板导入成功")
            else:
                logger.warning(f"仪表板导入响应: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"导入仪表板失败: {e}")
    
    def _stop_container(self, container_name: str):
        """停止并删除容器"""
        try:
            subprocess.run(["docker", "stop", container_name], capture_output=True)
            subprocess.run(["docker", "rm", container_name], capture_output=True)
        except:
            pass  # 容器可能不存在
    
    def _wait_for_service(self, url: str, service_name: str, timeout: int = 60):
        """等待服务启动"""
        logger.info(f"等待{service_name}启动...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"{service_name}启动成功")
                    return
            except:
                pass
            
            time.sleep(2)
        
        raise Exception(f"{service_name}启动超时")
    
    def _verify_deployment(self):
        """验证部署状态"""
        logger.info("验证监控系统部署状态...")
        
        services = [
            (f"http://localhost:{self.config.prometheus_port}/-/healthy", "Prometheus"),
            (f"http://localhost:{self.config.grafana_port}/api/health", "Grafana"),
            (f"http://localhost:{self.config.alertmanager_port}/-/healthy", "Alertmanager"),
            (f"http://localhost:{self.config.node_exporter_port}/metrics", "Node Exporter"),
        ]
        
        all_healthy = True
        for url, name in services:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✓ {name} 运行正常")
                else:
                    logger.error(f"✗ {name} 状态异常: {response.status_code}")
                    all_healthy = False
            except Exception as e:
                logger.error(f"✗ {name} 连接失败: {e}")
                all_healthy = False
        
        if not all_healthy:
            raise Exception("部分服务状态异常")
    
    def _print_access_info(self):
        """打印访问信息"""
        print("\n" + "="*60)
        print("ChronoRetrace 监控系统部署完成!")
        print("="*60)
        print(f"Prometheus:    http://localhost:{self.config.prometheus_port}")
        print(f"Grafana:       http://localhost:{self.config.grafana_port}")
        print(f"  用户名: {self.config.grafana_admin_user}")
        print(f"  密码: {self.config.grafana_admin_password}")
        print(f"Alertmanager:  http://localhost:{self.config.alertmanager_port}")
        print(f"Node Exporter: http://localhost:{self.config.node_exporter_port}")
        print("="*60)
        print("\n监控系统已就绪，可以开始监控ChronoRetrace应用!")
    
    def stop_all(self):
        """停止所有监控服务"""
        logger.info("停止所有监控服务...")
        
        containers = [
            "chronoretrace-prometheus",
            "chronoretrace-grafana",
            "chronoretrace-alertmanager",
            "chronoretrace-node-exporter",
            "chronoretrace-postgres-exporter",
            "chronoretrace-redis-exporter",
            "chronoretrace-nginx-exporter"
        ]
        
        for container in containers:
            self._stop_container(container)
            logger.info(f"已停止: {container}")
        
        # 删除网络
        try:
            subprocess.run(["docker", "network", "rm", self.config.network_name], capture_output=True)
            logger.info(f"已删除网络: {self.config.network_name}")
        except:
            pass
        
        logger.info("所有监控服务已停止")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChronoRetrace监控系统部署工具")
    parser.add_argument("action", choices=["deploy", "stop", "restart"], help="操作类型")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    
    # 加载配置
    config = MonitoringConfig()
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_data = yaml.safe_load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    deployer = MonitoringDeployer(config)
    
    try:
        if args.action == "deploy":
            success = deployer.deploy_all()
            sys.exit(0 if success else 1)
        elif args.action == "stop":
            deployer.stop_all()
        elif args.action == "restart":
            deployer.stop_all()
            time.sleep(5)
            success = deployer.deploy_all()
            sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("部署被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()