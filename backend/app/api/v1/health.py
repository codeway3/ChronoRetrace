"""统一健康检查接口

提供系统级别的健康检查，整合所有模块的健康状态
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
import logging
from app.infrastructure.cache.cache_service import cache_service
from app.infrastructure.cache.cache_warming import cache_warming_service
from app.infrastructure.monitoring.performance_monitor import performance_monitor
from app.services.stock_service import stock_service

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthChecker:
    """统一健康检查器"""

    def __init__(self):
        self.base_url = f"http://localhost:{settings.PORT or 8000}"


    async def check_monitoring_health(self) -> Dict[str, Any]:
        """检查监控模块健康状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/monitoring/health", timeout=5.0
                )
                if response.status_code == 200:
                    return {"status": "healthy", "details": response.json()}
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"监控模块健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def check_cache_health(self) -> Dict[str, Any]:
        """检查缓存模块健康状态"""
        try:
            # 直接调用缓存服务的健康检查
            cache_health = await cache_service.health_check()
            warming_health = cache_warming_service.is_healthy()

            overall_status = (
                "healthy" if cache_health and warming_health else "unhealthy"
            )

            return {
                "status": overall_status,
                "details": {
                    "cache_service": "healthy" if cache_health else "unhealthy",
                    "warming_service": "healthy" if warming_health else "unhealthy",
                },
            }
        except Exception as e:
            logger.error(f"缓存模块健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def check_stock_service_health(self) -> Dict[str, Any]:
        """检查股票服务健康状态"""
        try:
            health_result = await stock_service.health_check()
            return {
                "status": health_result.get("overall_status", "unhealthy"),
                "details": health_result,
            }
        except Exception as e:
            logger.error(f"股票服务健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def check_data_quality_health(self) -> Dict[str, Any]:
        """检查数据质量模块健康状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/data-quality/health", timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"status": data.get("status", "unhealthy"), "details": data}
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            logger.error(f"数据质量模块健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            # 通过监控模块获取数据库状态
            system_metrics = performance_monitor.get_system_metrics()

            # 检查system_metrics是否为字典类型
            if isinstance(system_metrics, dict):
                return {
                    "status": "healthy",
                    "details": {
                        "uptime_seconds": system_metrics.get("uptime_seconds", 0),
                        "memory_usage_mb": system_metrics.get("memory_usage_mb", 0),
                        "cpu_usage_percent": system_metrics.get("cpu_usage_percent", 0),
                    },
                }
            else:
                # 如果是对象类型，使用属性访问
                return {
                    "status": "healthy",
                    "details": {
                        "uptime_seconds": getattr(system_metrics, "uptime_seconds", 0),
                        "memory_usage_mb": getattr(
                            system_metrics, "memory_usage_mb", 0
                        ),
                        "cpu_usage_percent": getattr(
                            system_metrics, "cpu_usage_percent", 0
                        ),
                    },
                }
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def perform_comprehensive_health_check(self) -> Dict[str, Any]:
        """执行全面的健康检查"""
        start_time = datetime.now()

        # 并发执行所有健康检查
        tasks = {
            "monitoring": self.check_monitoring_health(),
            "cache": self.check_cache_health(),
            "stock_service": self.check_stock_service_health(),
            "data_quality": self.check_data_quality_health(),
            "database": self.check_database_health(),
        }

        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"健康检查任务 {name} 失败: {e}")
                results[name] = {"status": "unhealthy", "error": str(e)}

        # 计算总体健康状态
        healthy_services = sum(
            1 for result in results.values() if result["status"] == "healthy"
        )
        total_services = len(results)

        if healthy_services == total_services:
            overall_status = "healthy"
        elif healthy_services >= total_services * 0.7:  # 70%以上服务健康
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        end_time = datetime.now()
        check_duration = (end_time - start_time).total_seconds()

        return {
            "overall_status": overall_status,
            "timestamp": end_time.isoformat(),
            "check_duration_seconds": check_duration,
            "services": results,
            "summary": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": total_services - healthy_services,
                "health_percentage": round(
                    (healthy_services / total_services) * 100, 2
                ),
            },
        }


# 创建健康检查器实例
health_checker = HealthChecker()


@router.get("/system")
async def system_health_check():
    """
    系统级健康检查

    整合所有模块的健康状态，提供统一的健康检查接口

    Returns:
        Dict: 系统健康状态信息
    """
    try:
        health_result = await health_checker.perform_comprehensive_health_check()

        # 根据健康状态设置HTTP状态码
        status_code = 200
        if health_result["overall_status"] == "degraded":
            status_code = 206  # Partial Content
        elif health_result["overall_status"] == "unhealthy":
            status_code = 503  # Service Unavailable

        return JSONResponse(status_code=status_code, content=health_result)

    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


@router.get("/quick")
async def quick_health_check():
    """
    快速健康检查

    仅检查核心服务，用于负载均衡器等场景

    Returns:
        Dict: 快速健康状态信息
    """
    try:
        # 只检查最关键的服务
        cache_health = await cache_service.health_check()

        if cache_health:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Core services are operational",
                },
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Core services are not operational",
                },
            )

    except Exception as e:
        logger.error(f"快速健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )
