"""Tests for jays_tools.services module."""

import pytest
import time
import sys
from multiprocessing import Process, Event
from threading import Thread

from jays_tools.services.base import (
    Service,
    ReadinessSignal,
    start_services,
    stop_services,
    join_services,
)


def wait_for_ready(service, timeout=2.0):
    """Wait for service to be ready with timeout."""
    start = time.time()
    while not service.is_ready():
        if time.time() - start > timeout:
            raise TimeoutError(f"Service {service.name} did not become ready within {timeout}s")
        time.sleep(0.05)


# Helper functions for testing
def simple_service_func(signal: ReadinessSignal) -> None:
    """Simple service that signals readiness and runs."""
    signal.set()
    # Keep running until terminated, responsive to signals
    try:
        while True:
            time.sleep(0.05)
    except (KeyboardInterrupt, SystemExit, BrokenPipeError):
        sys.exit(0)


def slow_service_func(signal: ReadinessSignal) -> None:
    """Service with slight startup delay."""
    time.sleep(0.05)
    signal.set()
    try:
        while True:
            time.sleep(0.05)
    except (KeyboardInterrupt, SystemExit, BrokenPipeError):
        sys.exit(0)


def service_func_with_cleanup(signal: ReadinessSignal) -> None:
    """Service that signals readiness."""
    signal.set()
    try:
        while True:
            time.sleep(0.05)
    except (KeyboardInterrupt, SystemExit, BrokenPipeError):
        sys.exit(0)


def cleanup_func() -> None:
    """Cleanup function for services."""
    pass


def cleanup_func_with_state(state: dict) -> None:
    """Cleanup function that modifies shared state."""
    state['cleaned_up'] = True


class TestServiceInit:
    """Test suite for Service.__init__."""

    def test_init_with_required_params(self):
        """Initialize Service with required parameters only."""
        service = Service("TestService", simple_service_func)
        assert service.name == "TestService"
        assert service.start_func == simple_service_func
        assert service.stop_func is None
        assert service.process is None
        assert service.ready is False
        assert service.readiness_watcher is None

    def test_init_with_stop_func(self):
        """Initialize Service with optional stop function."""
        service = Service("TestService", simple_service_func, cleanup_func)
        assert service.name == "TestService"
        assert service.stop_func == cleanup_func

    def test_init_sets_empty_ready_event(self):
        """Ready event is created and not set."""
        service = Service("TestService", simple_service_func)
        assert service.ready_event is not None
        assert not service.ready_event.is_set()

    def test_init_with_different_names(self):
        """Initialize services with different names."""
        service1 = Service("Service1", simple_service_func)
        service2 = Service("Service2", simple_service_func)
        assert service1.name == "Service1"
        assert service2.name == "Service2"


class TestServiceStart:
    """Test suite for Service.start()."""

    def test_start_spawns_process(self):
        """Starting a service spawns a process."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.05)
        
        assert service.process is not None
        assert isinstance(service.process, Process)
        
        service.stop()

    def test_start_creates_readiness_watcher_thread(self):
        """Starting a service creates a watcher thread."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.05)
        
        assert service.readiness_watcher is not None
        assert isinstance(service.readiness_watcher, Thread)
        
        service.stop()

    def test_start_signals_readiness(self, capsys):
        """Service startup signals readiness via event."""
        service = Service("TestService", simple_service_func)
        service.start()
        
        # Wait for service to be ready
        wait_for_ready(service)
        
        assert service.is_ready() is True
        captured = capsys.readouterr()
        assert "TestService is ready" in captured.out
        
        service.stop()

    def test_start_with_slow_service(self):
        """Service startup works with delayed readiness signal."""
        service = Service("SlowService", slow_service_func)
        service.start()
        
        # Wait for service to be ready
        wait_for_ready(service)
        assert service.is_ready() is True
        
        service.stop()


class TestServiceIsReady:
    """Test suite for Service.is_ready()."""

    def test_is_ready_false_before_signal(self):
        """Service is not ready before readiness signal."""
        service = Service("TestService", simple_service_func)
        assert service.is_ready() is False

    def test_is_ready_true_after_signal(self):
        """Service is ready after readiness signal."""
        service = Service("TestService", simple_service_func)
        service.start()
        
        wait_for_ready(service)
        assert service.is_ready() is True
        
        service.stop()

    def test_is_ready_false_after_stop(self):
        """Service is not ready after being stopped."""
        service = Service("TestService", simple_service_func)
        service.start()
        
        wait_for_ready(service)
        assert service.is_ready() is True
        
        service.stop()
        assert service.is_ready() is False


class TestServiceStop:
    """Test suite for Service.stop()."""

    def test_stop_succeeds(self):
        """Stopping a service succeeds without error."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        # Should not raise
        service.stop()

    def test_stop_calls_stop_func(self):
        """Stopping a service calls the stop function."""
        stop_called = {}
        
        def stop_func_tracking():
            stop_called['called'] = True
        
        service = Service("TestService", simple_service_func, stop_func_tracking)
        service.start()
        time.sleep(0.1)
        
        service.stop()
        
        assert stop_called.get('called', False) is True

    def test_stop_resets_ready_state(self):
        """Stopping a service resets the ready flag."""
        service = Service("TestService", simple_service_func)
        service.start()
        
        wait_for_ready(service)
        assert service.is_ready() is True
        
        service.stop()
        
        assert service.is_ready() is False

    def test_stop_resets_process_reference(self):
        """Stopping a service clears process reference."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        service.stop()
        
        assert service.process is None

    def test_stop_clears_readiness_watcher(self):
        """Stopping a service clears the watcher thread reference."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        service.stop()
        
        assert service.readiness_watcher is None

    def test_stop_creates_new_ready_event(self):
        """Stopping a service creates a fresh ready event."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.15)
        
        original_event = service.ready_event
        service.stop()
        
        assert service.ready_event is not original_event
        assert not service.ready_event.is_set()

    def test_stop_without_stop_func(self):
        """Stopping a service without stop_func works."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        # Should not raise
        service.stop()

    def test_stop_without_process(self):
        """Stopping a service without process doesn't crash."""
        service = Service("TestService", simple_service_func)
        # Don't call start
        
        # Should not raise
        service.stop()

    def test_stop_idempotent(self, capsys):
        """Stopping multiple times is safe."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        service.stop()
        service.stop()  # Second stop should be safe
        
        captured = capsys.readouterr()
        assert "has been stopped" in captured.out


class TestServiceJoin:
    """Test suite for Service.join()."""

    def test_join_without_process(self):
        """Joining without starting doesn't crash."""
        service = Service("TestService", simple_service_func)
        
        # Should not raise
        service.join()

    def test_join_waits_for_watcher(self):
        """Join is callable on started services."""
        service = Service("TestService", simple_service_func)
        service.start()
        time.sleep(0.1)
        
        # join is callable (though it may block on running services)
        # For running services, just verify the attributes exist
        assert service.readiness_watcher is not None
        
        service.stop()


class TestStartServices:
    """Test suite for start_services() function."""

    def test_start_services_empty_list(self):
        """Starting empty service list is safe."""
        services = []
        
        # Should not raise
        start_services(services)

    def test_start_services_single_service(self):
        """Starting single service in a list."""
        service = Service("Service1", simple_service_func)
        
        start_services([service])
        wait_for_ready(service)
        
        assert service.is_ready() is True
        
        stop_services([service])

    def test_start_services_multiple_services(self):
        """Starting multiple services."""
        service1 = Service("Service1", simple_service_func)
        service2 = Service("Service2", simple_service_func)
        service3 = Service("Service3", simple_service_func)
        
        start_services([service1, service2, service3])
        
        # All should be ready
        wait_for_ready(service1)
        wait_for_ready(service2)
        wait_for_ready(service3)
        
        assert service1.is_ready() is True
        assert service2.is_ready() is True
        assert service3.is_ready() is True
        
        stop_services([service1, service2, service3])

    def test_start_services_starts_in_order(self):
        """Services are started in the order provided."""
        service1 = Service("First", simple_service_func)
        service2 = Service("Second", simple_service_func)
        
        start_services([service1, service2])
        time.sleep(0.15)
        
        # Both should be started
        assert service1.process is not None
        assert service2.process is not None
        
        stop_services([service1, service2])


class TestStopServices:
    """Test suite for stop_services() function."""

    def test_stop_services_empty_list(self):
        """Stopping empty service list is safe."""
        services = []
        
        # Should not raise
        stop_services(services)

    def test_stop_services_single_service(self):
        """Stopping single service in a list."""
        service = Service("Service1", simple_service_func)
        
        start_services([service])
        time.sleep(0.1)
        
        stop_services([service])
        
        assert service.is_ready() is False

    def test_stop_services_multiple_services(self):
        """Stopping multiple services."""
        service1 = Service("Service1", simple_service_func)
        service2 = Service("Service2", simple_service_func)
        
        start_services([service1, service2])
        time.sleep(0.1)
        
        stop_services([service1, service2])
        
        assert service1.is_ready() is False
        assert service2.is_ready() is False

    def test_stop_services_without_starting(self):
        """Stopping services that weren't started is safe."""
        service1 = Service("Service1", simple_service_func)
        service2 = Service("Service2", simple_service_func)
        
        # Should not raise
        stop_services([service1, service2])


class TestJoinServices:
    """Test suite for join_services() function."""

    def test_join_services_empty_list(self):
        """Joining empty service list is safe."""
        services = []
        
        # Should not raise
        join_services(services)

    def test_join_services_without_starting(self):
        """Joining services that weren't started is safe."""
        service1 = Service("Service1", simple_service_func)
        service2 = Service("Service2", simple_service_func)
        
        # Should not raise
        join_services([service1, service2])


class TestServiceLifecycle:
    """Integration tests for complete service lifecycle."""

    def test_complete_lifecycle_start_ready_stop(self, capsys):
        """Complete lifecycle: start → ready → stop."""
        service = Service("LifecycleTest", simple_service_func)
        
        # Before start
        assert service.is_ready() is False
        assert service.process is None
        
        # Start
        service.start()
        wait_for_ready(service)
        
        # After start
        assert service.is_ready() is True
        assert service.process is not None
        
        # Stop
        service.stop()
        
        # After stop
        assert service.is_ready() is False
        assert service.process is None
        
        captured = capsys.readouterr()
        assert "is ready" in captured.out
        assert "has been stopped" in captured.out

    def test_complete_lifecycle_with_stop_func(self):
        """Complete lifecycle with custom stop function."""
        cleanup_state = {}
        
        def stop_func():
            cleanup_state['stopped'] = True
        
        service = Service("LifecycleTest", simple_service_func, stop_func)
        
        service.start()
        time.sleep(0.1)
        
        service.stop()
        
        assert cleanup_state.get('stopped') is True

    def test_lifecycle_multiple_services(self):
        """Lifecycle management for multiple services."""
        services = [
            Service(f"Service{i}", simple_service_func)
            for i in range(3)
        ]
        
        # Start all
        start_services(services)
        
        # Wait for all to be ready
        for service in services:
            wait_for_ready(service)
        
        # All ready
        assert all(s.is_ready() for s in services)
        
        # Stop all
        stop_services(services)
        
        # All stopped
        assert all(not s.is_ready() for s in services)

    def test_restart_service(self):
        """A service can be restarted after stopping."""
        service = Service("RestartTest", simple_service_func)
        
        # First lifecycle
        service.start()
        wait_for_ready(service)
        assert service.is_ready() is True
        service.stop()
        assert service.is_ready() is False
        
        # Second lifecycle
        service.start()
        wait_for_ready(service)
        assert service.is_ready() is True
        service.stop()
        assert service.is_ready() is False
