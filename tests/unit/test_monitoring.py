"""
监控模块测试
验证结构化日志、指标收集、健康检查、告警机制
"""
import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from monitoring import StructuredLogger, LogLevel, MetricsCollector, Metric, HealthChecker, HealthStatus, AlertManager, AlertLevel, Alert
from monitoring.health import HealthCheck


class TestStructuredLogger:
    """测试结构化日志"""
    
    def test_logger_creation(self, tmp_path):
        """测试日志器创建"""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger("test", log_file, LogLevel.INFO)
        
        assert logger.name == "test"
        assert logger.log_file == log_file
        assert logger.log_level == LogLevel.INFO
    
    def test_log_levels(self, tmp_path, capsys):
        """测试日志级别"""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger("test", log_file, LogLevel.DEBUG)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # 检查日志文件
        assert log_file.exists()
        
        # 检查控制台输出
        captured = capsys.readouterr()
        assert "Debug message" in captured.out
        assert "Info message" in captured.out
    
    def test_json_format(self, tmp_path):
        """测试 JSON 格式"""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger("test", log_file, LogLevel.INFO, json_format=True)
        
        logger.info("Test message", extra={"key": "value"})
        
        # 读取日志文件
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 应该是有效的 JSON
        data = json.loads(content)
        assert data["message"] == "Test message"
        assert data["extra"]["key"] == "value"
    
    def test_add_context(self, tmp_path):
        """测试添加上下文"""
        log_file = tmp_path / "test.log"
        logger = StructuredLogger("test", log_file, LogLevel.INFO)
        
        # 添加上下文
        context_logger = logger.add_context(user="test_user", request_id="123")
        
        context_logger.info("Test message")
        
        # 检查日志文件
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        data = json.loads(content)
        assert data["extra"]["user"] == "test_user"
        assert data["extra"]["request_id"] == "123"


class TestMetricsCollector:
    """测试指标收集器"""
    
    def test_counter(self, tmp_path):
        """测试计数器"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 增加计数器
        collector.counter("test_counter", 1.0)
        collector.counter("test_counter", 2.0)
        
        # 检查值
        assert collector.get_counter("test_counter") == 3.0
        
        # 检查指标
        metric = collector.get_metric("test_counter")
        assert metric is not None
        assert metric.value == 3.0
    
    def test_gauge(self, tmp_path):
        """测试仪表盘"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 设置仪表盘值
        collector.gauge("test_gauge", 10.0)
        
        # 检查值
        assert collector.get_gauge("test_gauge") == 10.0
        
        # 更新值
        collector.gauge("test_gauge", 20.0)
        assert collector.get_gauge("test_gauge") == 20.0
    
    def test_histogram(self, tmp_path):
        """测试直方图"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 记录直方图值
        collector.histogram("test_histogram", 1.0)
        collector.histogram("test_histogram", 2.0)
        collector.histogram("test_histogram", 3.0)
        
        # 检查值
        values = collector.get_histogram("test_histogram")
        assert len(values) == 3
        assert values == [1.0, 2.0, 3.0]
        
        # 检查统计信息
        stats = collector.get_histogram_stats("test_histogram")
        assert stats["count"] == 3
        assert stats["sum"] == 6.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["avg"] == 2.0
    
    def test_labels(self, tmp_path):
        """测试标签"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 使用标签
        collector.counter("test_counter", 1.0, labels={"env": "prod"})
        collector.counter("test_counter", 2.0, labels={"env": "dev"})
        
        # 检查值
        assert collector.get_counter("test_counter", labels={"env": "prod"}) == 1.0
        assert collector.get_counter("test_counter", labels={"env": "dev"}) == 2.0
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 添加指标
        collector.counter("test_counter", 5.0)
        collector.gauge("test_gauge", 10.0)
        
        # 保存
        collector.save()
        
        # 创建新的收集器并加载
        new_collector = MetricsCollector(metrics_file)
        new_collector.load()
        
        # 检查值
        assert new_collector.get_counter("test_counter") == 5.0
        assert new_collector.get_gauge("test_gauge") == 10.0
    
    def test_export_prometheus(self, tmp_path):
        """测试导出 Prometheus 格式"""
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(metrics_file)
        
        # 添加指标
        collector.counter("http_requests_total", 100.0, labels={"method": "GET"})
        collector.gauge("memory_usage_bytes", 1024.0)
        
        # 导出
        prometheus_output = collector.export_prometheus()
        
        # 检查内容
        assert "http_requests_total" in prometheus_output
        assert "memory_usage_bytes" in prometheus_output
        assert 'method="GET"' in prometheus_output


class TestHealthChecker:
    """测试健康检查器"""
    
    def test_register_and_run(self, tmp_path):
        """测试注册和运行"""
        health_file = tmp_path / "health.json"
        checker = HealthChecker(health_file)
        
        # 注册检查
        def check_database():
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
            )
        
        checker.register_check("database", check_database)
        
        # 运行检查
        result = checker.run_check("database")
        
        assert result is not None
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Database is healthy"
    
    def test_overall_status(self, tmp_path):
        """测试整体状态"""
        health_file = tmp_path / "health.json"
        checker = HealthChecker(health_file)
        
        # 注册检查
        def check_healthy():
            return HealthCheck(name="healthy", status=HealthStatus.HEALTHY)
        
        def check_degraded():
            return HealthCheck(name="degraded", status=HealthStatus.DEGRADED)
        
        def check_unhealthy():
            return HealthCheck(name="unhealthy", status=HealthStatus.UNHEALTHY)
        
        checker.register_check("healthy", check_healthy)
        checker.register_check("degraded", check_degraded)
        checker.register_check("unhealthy", check_unhealthy)
        
        # 运行检查
        checker.run_all_checks()
        
        # 检查整体状态（应该不健康）
        assert checker.get_overall_status() == HealthStatus.UNHEALTHY
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        health_file = tmp_path / "health.json"
        checker = HealthChecker(health_file)
        
        # 注册检查
        def check_database():
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="OK",
            )
        
        checker.register_check("database", check_database)
        
        # 运行检查
        checker.run_check("database")
        
        # 保存
        checker.save()
        
        # 创建新的检查器并加载
        new_checker = HealthChecker(health_file)
        new_checker.load()
        
        # 检查结果
        result = new_checker.get_check("database")
        assert result is not None
        assert result.status == HealthStatus.HEALTHY


class TestAlertManager:
    """测试告警管理器"""
    
    def test_create_alert(self, tmp_path):
        """测试创建告警"""
        alerts_file = tmp_path / "alerts.json"
        manager = AlertManager(alerts_file)
        
        # 创建告警
        alert = manager.create_alert(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="This is a test alert",
            source="test",
        )
        
        assert alert is not None
        assert alert.level == AlertLevel.ERROR
        assert alert.title == "Test Alert"
        assert not alert.resolved
    
    def test_resolve_alert(self, tmp_path):
        """测试解决告警"""
        alerts_file = tmp_path / "alerts.json"
        manager = AlertManager(alerts_file)
        
        # 创建告警
        alert = manager.create_alert(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="This is a test alert",
            source="test",
        )
        
        # 解决告警
        assert manager.resolve_alert(alert.id)
        
        # 检查状态
        updated_alert = manager.get_alert(alert.id)
        assert updated_alert.resolved
        assert updated_alert.resolved_at is not None
    
    def test_get_alerts_by_level(self, tmp_path):
        """测试根据级别获取告警"""
        alerts_file = tmp_path / "alerts.json"
        manager = AlertManager(alerts_file)
        
        # 创建不同级别的告警
        manager.create_alert(AlertLevel.INFO, "Info", "Info message")
        manager.create_alert(AlertLevel.WARNING, "Warning", "Warning message")
        manager.create_alert(AlertLevel.ERROR, "Error", "Error message")
        
        # 获取错误级别的告警
        error_alerts = manager.get_alerts_by_level(AlertLevel.ERROR)
        assert len(error_alerts) == 1
        assert error_alerts[0].title == "Error"
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        alerts_file = tmp_path / "alerts.json"
        manager = AlertManager(alerts_file)
        
        # 创建告警
        manager.create_alert(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="This is a test alert",
            source="test",
        )
        
        # 保存
        manager.save()
        
        # 创建新的管理器并加载
        new_manager = AlertManager(alerts_file)
        new_manager.load()
        
        # 检查告警
        alerts = new_manager.get_all_alerts()
        assert len(alerts) == 1
        assert alerts[0].title == "Test Alert"


@pytest.mark.unit
def test_monitoring_module_import():
    """测试监控模块导入"""
    from monitoring import StructuredLogger, LogLevel, MetricsCollector, Metric, HealthChecker, HealthStatus, AlertManager, AlertLevel, Alert
    from monitoring.health import HealthCheck
    
    assert StructuredLogger is not None
    assert LogLevel is not None
    assert MetricsCollector is not None
    assert Metric is not None
    assert HealthChecker is not None
    assert HealthStatus is not None
    assert AlertManager is not None
    assert AlertLevel is not None
    assert Alert is not None
    assert HealthCheck is not None
    
    print("✓ 监控模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])