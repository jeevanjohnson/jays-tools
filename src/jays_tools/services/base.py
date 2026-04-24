from typing import Callable, TypeAlias
from multiprocessing import Process, Event
from multiprocessing.synchronize import Event as EventType
from colorama import Fore, Style
from threading import Thread

ReadinessSignal: TypeAlias = EventType

def success(message: str) -> None:
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

# TODO: learn difference between process, thread, async, and subprocess in depth
class Service:
    def __init__(
        self, 
        name: str, 
        start_func: Callable[[ReadinessSignal], None], 
        stop_func: Callable[[], None] | None = None
    ) -> None:
        self.name = name
        self.start_func = start_func
        self.stop_func = stop_func

        self.process: Process | None = None
        self.ready_event = Event()

        self.ready: bool = False
        self.readiness_watcher: Thread | None = None
    
    def _start(self):
        self.process = Process(
            target=self.start_func,
            args=(self.ready_event,)
        )
        self.process.start()
    
    def wait_until_ready(self):
        self.ready_event.wait()
        success(f"{self.name} is ready.")
        self.ready = True
    
    def is_ready(self) -> bool:
        return self.ready

    def start(self):
        self._start()
        
        self.readiness_watcher = Thread(target=self.wait_until_ready)
        self.readiness_watcher.start()

    # TODO: parallel joining?
    def join(self):
        if self.process:
            if self.readiness_watcher:
                self.readiness_watcher.join()
            
            self.process.join()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.join()
        
        if self.stop_func:
            self.stop_func()
        

        self.ready = False
        self.process = None
        self.ready_event = Event()
        self.readiness_watcher = None

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