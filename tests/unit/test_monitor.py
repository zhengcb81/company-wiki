"""
监控模块测试
"""
import pytest
import time
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from monitor import Monitor, Metric, ErrorRecord, Timer, track_performance, track_errors


@pytest.fixture
def monitor(tmp_path):
    """创建测试监控器"""
    metrics_file = tmp_path / "metrics.json"
    return Monitor(metrics_file)


class TestMonitor:
    """测试监控器"""
    
    def test_counter(self, monitor):
        """测试计数器"""
        monitor.counter("test_counter", 1.0)
        monitor.counter("test_counter", 2.0)
        
        assert monitor.get_counter("test_counter") == 3.0
    
    def test_counter_with_labels(self, monitor):
        """测试带标签的计数器"""
        monitor.counter("requests", 1.0, {"method": "GET"})
        monitor.counter("requests", 2.0, {"method": "POST"})
        
        assert monitor.get_counter("requests", {"method": "GET"}) == 1.0
        assert monitor.get_counter("requests", {"method": "POST"}) == 2.0
    
    def test_gauge(self, monitor):
        """测试仪表盘"""
        monitor.gauge("memory", 100.0)
        assert monitor.get_gauge("memory") == 100.0
        
        monitor.gauge("memory", 200.0)
        assert monitor.get_gauge("memory") == 200.0
    
    def test_timer(self, monitor):
        """测试计时器"""
        monitor.timer("duration", 1.5)
        monitor.timer("duration", 2.5)
        
        stats = monitor.get_timer_stats("duration")
        assert stats["count"] == 2
        assert stats["avg"] == 2.0
        assert stats["min"] == 1.5
        assert stats["max"] == 2.5
    
    def test_record_error(self, monitor):
        """测试错误记录"""
        try:
            raise ValueError("测试错误")
        except Exception as e:
            monitor.record_error(e, module="test", function="test_func")
        
        assert monitor.get_error_count() == 1
        assert monitor.get_error_count("ValueError") == 1
        
        errors = monitor.get_recent_errors()
        assert len(errors) == 1
        assert errors[0].error_type == "ValueError"
        assert errors[0].message == "测试错误"
    
    def test_get_summary(self, monitor):
        """测试获取摘要"""
        monitor.counter("test", 1.0)
        monitor.gauge("test", 100.0)
        
        summary = monitor.get_summary()
        assert "counters" in summary
        assert "gauges" in summary
        assert "errors" in summary
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        metrics_file = tmp_path / "metrics.json"
        
        # 创建并保存
        monitor1 = Monitor(metrics_file)
        monitor1.counter("test", 5.0)
        monitor1.gauge("test", 100.0)
        monitor1.save()
        
        # 加载
        monitor2 = Monitor(metrics_file)
        assert monitor2.get_counter("test") == 5.0
        assert monitor2.get_gauge("test") == 100.0
    
    def test_reset(self, monitor):
        """测试重置"""
        monitor.counter("test", 5.0)
        monitor.gauge("test", 100.0)
        
        monitor.reset()
        
        assert monitor.get_counter("test") == 0.0
        assert monitor.get_gauge("test") is None


class TestMetric:
    """测试指标"""
    
    def test_metric_creation(self):
        """测试创建指标"""
        metric = Metric("test", 100.0, {"label": "value"})
        
        assert metric.name == "test"
        assert metric.value == 100.0
        assert metric.labels == {"label": "value"}
        assert metric.timestamp  # 应该有时间戳
    
    def test_metric_to_dict(self):
        """测试转换为字典"""
        metric = Metric("test", 100.0)
        data = metric.to_dict()
        
        assert data["name"] == "test"
        assert data["value"] == 100.0


class TestErrorRecord:
    """测试错误记录"""
    
    def test_error_record_creation(self):
        """测试创建错误记录"""
        error = ErrorRecord(
            error_type="ValueError",
            message="测试错误",
            module="test",
            function="test_func",
        )
        
        assert error.error_type == "ValueError"
        assert error.message == "测试错误"
    
    def test_error_record_to_dict(self):
        """测试转换为字典"""
        error = ErrorRecord("ValueError", "测试错误", "test", "test_func")
        data = error.to_dict()
        
        assert data["error_type"] == "ValueError"
        assert data["message"] == "测试错误"


class TestTimer:
    """测试计时器"""
    
    def test_timer_context(self, monitor):
        """测试计时器上下文"""
        with Timer("test_timer", monitor):
            time.sleep(0.01)
        
        stats = monitor.get_timer_stats("test_timer")
        assert stats["count"] == 1
        assert stats["avg"] > 0
    
    def test_timer_with_error(self, monitor):
        """测试计时器错误处理"""
        with pytest.raises(ValueError):
            with Timer("error_timer", monitor):
                raise ValueError("测试错误")
        
        assert monitor.get_error_count() == 1


class TestDecorators:
    """测试装饰器"""
    
    def test_track_performance(self, monitor):
        """测试性能追踪装饰器"""
        # 临时设置全局监控器
        import monitor as monitor_module
        old_monitor = monitor_module._default_monitor
        monitor_module._default_monitor = monitor
        
        try:
            @track_performance("decorated_func")
            def test_func():
                time.sleep(0.01)
                return "ok"
            
            result = test_func()
            assert result == "ok"
            
            # 检查指标
            stats = monitor.get_timer_stats("decorated_func_duration")
            assert stats["count"] == 1
            assert monitor.get_counter("decorated_func_calls") == 1.0
        finally:
            monitor_module._default_monitor = old_monitor
    
    def test_track_errors(self, monitor):
        """测试错误追踪装饰器"""
        import monitor as monitor_module
        old_monitor = monitor_module._default_monitor
        monitor_module._default_monitor = monitor
        
        try:
            @track_errors
            def error_func():
                raise ValueError("测试错误")
            
            with pytest.raises(ValueError):
                error_func()
            
            assert monitor.get_error_count() == 1
        finally:
            monitor_module._default_monitor = old_monitor


@pytest.mark.unit
def test_monitor_module_import():
    """测试监控模块导入"""
    from monitor import Monitor, Metric, ErrorRecord, Timer, track_performance
    
    assert Monitor is not None
    assert Metric is not None
    assert ErrorRecord is not None
    assert Timer is not None
    assert track_performance is not None
    
    print("✅ 监控模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])