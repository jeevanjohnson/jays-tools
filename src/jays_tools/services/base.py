from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as EventType
from threading import Thread
from typing import Callable, TypeAlias

from colorama import Fore, Style

ReadinessSignal: TypeAlias = EventType


def success(message: str) -> None:
    """Print a success message in green."""
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")


class Service:
    """Manages a service lifecycle with readiness signaling."""

    # TODO: learn difference between process, thread, async, and subprocess in depth

    def __init__(
        self,
        name: str,
        description: str,
        start_func: Callable[[ReadinessSignal], None],
        stop_func: Callable[[], None] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.start_func = start_func
        self.stop_func = stop_func

        self.process: Process | None = None
        self.running: bool = False        

        self.ready_event = Event()
        self.ready: bool = False
        self.readiness_watcher: Thread | None = None

    def _start(self) -> None:
        self.process = Process(
            target=self.start_func,
            args=(self.ready_event,)
        )
        self.process.start()
    
    def wait_until_ready(self) -> None:
        """Wait for readiness signal and update state."""
        self.ready_event.wait()
        success(f"{self.name} is ready.")
        self.ready = True

    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self.ready

    def is_running(self) -> bool:
        """Check if service process is alive."""
        return self.running

    def start(self) -> None:
        """Start the service and watch for readiness."""
        self._start()

        self.readiness_watcher = Thread(target=self.wait_until_ready)
        self.readiness_watcher.start()

        self.running = True

        success(f"{self.name} has been started. Waiting for readiness...")

    def join(self) -> None:
        """Wait for service to complete.

        TODO: parallel joining?
        """
        if self.process:
            if self.readiness_watcher:
                self.readiness_watcher.join()

            self.process.join()

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.join()
            self.running = False

        if self.stop_func:
            self.stop_func()        

        self.ready = False
        self.process = None
        self.ready_event = Event()
        self.readiness_watcher = None

        if self.process or self.stop_func:
            success(f"{self.name} has been stopped.")

def start_services(services: list[Service]) -> None:
    for service in services:
        service.start()
    
def stop_services(services: list[Service]) -> None:
    for service in services:
        service.stop()

def join_services(services: list[Service]) -> None:
    for service in services:
        service.join()