#!/usr/bin/env python3
"""
ChronoRetrace 监控系统健康检查脚本
定期检查监控组件的运行状态，确保监控系统正常工作
"""

import json
import logging
import os
import smtplib
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("monitoring_health.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """服务状态类"""

    name: str
    url: str
    status: str  # 'healthy', 'unhealthy', 'unknown'
    response_time: float
    error_message: str = ""
    last_check: str = ""
    uptime: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HealthCheckConfig:
    """健康检查配置"""

    # 服务端点
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"
    alertmanager_url: str = "http://localhost:9093"
    node_exporter_url: str = "http://localhost:9100"
    postgres_exporter_url: str = "http://localhost:9187"
    redis_exporter_url: str = "http://localhost:9121"
    nginx_exporter_url: str = "http://localhost:9113"

    # 检查间隔（秒）
    check_interval: int = 60

    # 超时设置（秒）
    request_timeout: int = 10

    # 重试次数
    max_retries: int = 3

    # 告警阈值
    response_time_threshold: float = 5.0  # 响应时间阈值（秒）
    failure_threshold: int = 3  # 连续失败次数阈值

    # 通知配置
    enable_email_alerts: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_recipients: list[str] | None = None

    # Slack通知
    enable_slack_alerts: bool = False
    slack_webhook_url: str = ""

    # 状态文件路径
    status_file: str = "/tmp/monitoring_health_status.json"

    def __post_init__(self):
        if self.alert_recipients is None:
            self.alert_recipients = []


class MonitoringHealthChecker:
    """监控系统健康检查器"""

    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.services = self._initialize_services()
        self.failure_counts = dict.fromkeys(self.services.keys(), 0)
        self.last_alert_time = dict.fromkeys(self.services.keys())

    def _initialize_services(self) -> dict[str, dict]:
        """初始化服务配置"""
        return {
            "prometheus": {
                "url": f"{self.config.prometheus_url}/-/healthy",
                "name": "Prometheus",
                "critical": True,
            },
            "grafana": {
                "url": f"{self.config.grafana_url}/api/health",
                "name": "Grafana",
                "critical": True,
            },
            "alertmanager": {
                "url": f"{self.config.alertmanager_url}/-/healthy",
                "name": "Alertmanager",
                "critical": True,
            },
            "node_exporter": {
                "url": f"{self.config.node_exporter_url}/metrics",
                "name": "Node Exporter",
                "critical": False,
            },
            "postgres_exporter": {
                "url": f"{self.config.postgres_exporter_url}/metrics",
                "name": "PostgreSQL Exporter",
                "critical": False,
            },
            "redis_exporter": {
                "url": f"{self.config.redis_exporter_url}/metrics",
                "name": "Redis Exporter",
                "critical": False,
            },
            "nginx_exporter": {
                "url": f"{self.config.nginx_exporter_url}/metrics",
                "name": "Nginx Exporter",
                "critical": False,
            },
        }

    def run_continuous_check(self):
        """运行持续健康检查"""
        logger.info("开始监控系统健康检查...")
        logger.info(f"检查间隔: {self.config.check_interval}秒")

        try:
            while True:
                self.check_all_services()
                time.sleep(self.config.check_interval)
        except KeyboardInterrupt:
            logger.info("健康检查被用户中断")
        except Exception as e:
            logger.exception(f"健康检查异常: {e}")

    def check_all_services(self) -> dict[str, ServiceStatus]:
        """检查所有服务状态"""
        logger.info("执行健康检查...")

        results = {}
        overall_healthy = True

        for service_key, service_config in self.services.items():
            status = self._check_service(service_config["name"], service_config["url"])
            results[service_key] = status

            # 更新失败计数
            if status.status == "unhealthy":
                self.failure_counts[service_key] += 1
                if service_config["critical"]:
                    overall_healthy = False
            else:
                self.failure_counts[service_key] = 0

            # 检查是否需要发送告警
            self._check_alert_conditions(service_key, service_config, status)

        # 保存状态到文件
        self._save_status(results, overall_healthy)

        # 打印状态摘要
        self._print_status_summary(results, overall_healthy)

        return results

    def _check_service(self, name: str, url: str) -> ServiceStatus:
        """检查单个服务状态"""
        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=self.config.request_timeout,
                    headers={"User-Agent": "ChronoRetrace-HealthChecker/1.0"},
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    # 检查响应时间
                    if response_time > self.config.response_time_threshold:
                        status = "unhealthy"
                        error_msg = f"响应时间过长: {response_time:.2f}s"
                    else:
                        status = "healthy"
                        error_msg = ""

                    return ServiceStatus(
                        name=name,
                        url=url,
                        status=status,
                        response_time=response_time,
                        error_message=error_msg,
                        last_check=datetime.now().isoformat(),
                        uptime=self._get_service_uptime(name),
                    )
                else:
                    if attempt == self.config.max_retries - 1:
                        return ServiceStatus(
                            name=name,
                            url=url,
                            status="unhealthy",
                            response_time=time.time() - start_time,
                            error_message=f"HTTP {response.status_code}: {response.text[:100]}",
                            last_check=datetime.now().isoformat(),
                        )
                    time.sleep(1)  # 重试前等待

            except requests.exceptions.Timeout:
                if attempt == self.config.max_retries - 1:
                    return ServiceStatus(
                        name=name,
                        url=url,
                        status="unhealthy",
                        response_time=self.config.request_timeout,
                        error_message="请求超时",
                        last_check=datetime.now().isoformat(),
                    )
                time.sleep(1)

            except requests.exceptions.ConnectionError:
                if attempt == self.config.max_retries - 1:
                    return ServiceStatus(
                        name=name,
                        url=url,
                        status="unhealthy",
                        response_time=0,
                        error_message="连接失败",
                        last_check=datetime.now().isoformat(),
                    )
                time.sleep(1)

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    return ServiceStatus(
                        name=name,
                        url=url,
                        status="unknown",
                        response_time=0,
                        error_message=f"未知错误: {e!s}",
                        last_check=datetime.now().isoformat(),
                    )
                time.sleep(1)

        return ServiceStatus(
            name=name,
            url=url,
            status="unknown",
            response_time=0,
            error_message="所有重试均失败",
            last_check=datetime.now().isoformat(),
        )

    def _get_service_uptime(self, service_name: str) -> float:
        """获取服务运行时间（小时）"""
        try:
            # 尝试通过Docker获取容器运行时间
            container_name = f"chronoretrace-{service_name.lower().replace(' ', '-')}"
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    container_name,
                    "--format",
                    "{{.State.StartedAt}}",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                start_time_str = result.stdout.strip()
                # 解析Docker时间格式
                start_time = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )
                uptime = (
                    datetime.now().replace(tzinfo=start_time.tzinfo) - start_time
                ).total_seconds() / 3600
                return round(uptime, 2)
        except Exception:
            pass

        return 0.0

    def _check_alert_conditions(
        self, service_key: str, service_config: dict, status: ServiceStatus
    ):
        """检查告警条件"""
        failure_count = self.failure_counts[service_key]

        # 检查是否达到告警阈值
        if failure_count >= self.config.failure_threshold and status.status in [
            "unhealthy",
            "unknown",
        ]:
            # 检查是否需要发送告警（避免重复告警）
            last_alert = self.last_alert_time[service_key]
            now = datetime.now()

            if (
                last_alert is None or (now - last_alert).total_seconds() > 3600
            ):  # 1小时内不重复告警
                self._send_alert(service_config["name"], status, failure_count)
                self.last_alert_time[service_key] = now

    def _send_alert(self, service_name: str, status: ServiceStatus, failure_count: int):
        """发送告警通知"""
        logger.warning(f"发送告警: {service_name} 服务异常")

        alert_message = self._format_alert_message(service_name, status, failure_count)

        # 发送邮件告警
        if self.config.enable_email_alerts:
            self._send_email_alert(service_name, alert_message)

        # 发送Slack告警
        if self.config.enable_slack_alerts:
            self._send_slack_alert(service_name, alert_message)

    def _format_alert_message(
        self, service_name: str, status: ServiceStatus, failure_count: int
    ) -> str:
        """格式化告警消息"""
        return f"""
🚨 ChronoRetrace监控告警

服务名称: {service_name}
状态: {status.status.upper()}
错误信息: {status.error_message}
响应时间: {status.response_time:.2f}秒
连续失败次数: {failure_count}
检查时间: {status.last_check}
URL: {status.url}

请立即检查服务状态并采取相应措施。
        """.strip()

    def _send_email_alert(self, service_name: str, message: str):
        """发送邮件告警"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.smtp_user
            msg["Subject"] = f"[ChronoRetrace] {service_name} 服务告警"

            msg.attach(MIMEText(message, "plain", "utf-8"))

            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_user, self.config.smtp_password)

            # 确保alert_recipients不为None且为可迭代对象
            recipients = self.config.alert_recipients or []
            for recipient in recipients:
                msg["To"] = recipient
                server.send_message(msg)
                del msg["To"]

            server.quit()
            logger.info(f"邮件告警已发送: {service_name}")

        except Exception as e:
            logger.exception(f"发送邮件告警失败: {e}")

    def _send_slack_alert(self, service_name: str, message: str):
        """发送Slack告警"""
        try:
            payload = {
                "text": f"ChronoRetrace监控告警: {service_name}",
                "attachments": [
                    {"color": "danger", "text": message, "ts": int(time.time())}
                ],
            }

            response = requests.post(
                self.config.slack_webhook_url, json=payload, timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Slack告警已发送: {service_name}")
            else:
                logger.error(f"Slack告警发送失败: {response.status_code}")

        except Exception as e:
            logger.exception(f"发送Slack告警失败: {e}")

    def _save_status(self, results: dict[str, ServiceStatus], overall_healthy: bool):
        """保存状态到文件"""
        try:
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": overall_healthy,
                "services": {k: v.to_dict() for k, v in results.items()},
                "failure_counts": self.failure_counts,
            }

            with open(self.config.status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.exception(f"保存状态文件失败: {e}")

    def _print_status_summary(
        self, results: dict[str, ServiceStatus], overall_healthy: bool
    ):
        """打印状态摘要"""
        print("\n" + "=" * 60)
        print(f"监控系统健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        for _, status in results.items():
            status_icon = "✓" if status.status == "healthy" else "✗"
            print(
                f"{status_icon} {status.name:<20} {status.status:<10} {status.response_time:.2f}s"
            )
            if status.error_message:
                print(f"  错误: {status.error_message}")

        print("=" * 60)
        overall_status = "正常" if overall_healthy else "异常"
        print(f"整体状态: {overall_status}")
        print("=" * 60)

    def get_status_report(self) -> dict:
        """获取状态报告"""
        try:
            with open(self.config.status_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"error": "状态文件不存在"}
        except Exception as e:
            return {"error": f"读取状态文件失败: {e}"}

    def check_prometheus_targets(self) -> dict:
        """检查Prometheus目标状态"""
        try:
            response = requests.get(
                f"{self.config.prometheus_url}/api/v1/targets",
                timeout=self.config.request_timeout,
            )

            if response.status_code == 200:
                data = response.json()
                targets = data.get("data", {}).get("activeTargets", [])

                healthy_targets = [t for t in targets if t.get("health") == "up"]
                unhealthy_targets = [t for t in targets if t.get("health") != "up"]

                return {
                    "total_targets": len(targets),
                    "healthy_targets": len(healthy_targets),
                    "unhealthy_targets": len(unhealthy_targets),
                    "unhealthy_details": [
                        {
                            "job": t.get("labels", {}).get("job", "unknown"),
                            "instance": t.get("labels", {}).get("instance", "unknown"),
                            "health": t.get("health", "unknown"),
                            "last_error": t.get("lastError", ""),
                        }
                        for t in unhealthy_targets
                    ],
                }
            else:
                return {"error": f"获取Prometheus目标失败: {response.status_code}"}

        except Exception as e:
            return {"error": f"检查Prometheus目标异常: {e}"}


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="ChronoRetrace监控系统健康检查")
    parser.add_argument(
        "--mode", choices=["once", "continuous"], default="once", help="运行模式"
    )
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--interval", type=int, default=60, help="检查间隔（秒）")
    parser.add_argument("--report", action="store_true", help="显示状态报告")
    parser.add_argument("--targets", action="store_true", help="检查Prometheus目标")

    args = parser.parse_args()

    # 加载配置
    config = HealthCheckConfig()
    config.check_interval = args.interval

    if args.config and os.path.exists(args.config):
        import yaml

        with open(args.config) as f:
            config_data = yaml.safe_load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    checker = MonitoringHealthChecker(config)

    try:
        if args.report:
            # 显示状态报告
            report = checker.get_status_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
        elif args.targets:
            # 检查Prometheus目标
            targets = checker.check_prometheus_targets()
            print(json.dumps(targets, indent=2, ensure_ascii=False))
        elif args.mode == "continuous":
            # 持续监控模式
            checker.run_continuous_check()
        else:
            # 单次检查模式
            results = checker.check_all_services()

            # 检查是否有异常服务
            unhealthy_services = [s for s in results.values() if s.status != "healthy"]
            if unhealthy_services:
                sys.exit(1)

    except KeyboardInterrupt:
        logger.info("健康检查被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"健康检查失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
