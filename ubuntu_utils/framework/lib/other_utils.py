import platform
from abc import ABC, abstractmethod
from typing import Any


class FunctionClass(ABC):
    def __new__(cls, *args, **kwargs) -> Any:
        instance = super().__new__(cls)
        instance._init()
        return instance(*args, **kwargs)

    def _init(self) -> None: ...

    @abstractmethod
    def __call__(self, *args, **kwargs): ...


class is_sys(FunctionClass):
    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS = "Darwin"

    def __new__(cls, os_name: str) -> bool:
        return super().__new__(cls, os_name)

    def __call__(self, os_name: str) -> bool:
        this_os_name = platform.system()
        if os_name == this_os_name:
            return True
        return False


class ClassProperty:
    """A decorator similar to 'property', but with the ability to use the class to access it,
    and the 'fget' method receives the class as its argument, rather than an instance"""

    def __init__(self, fget=None):
        self.fget = fget

    def __set_name__(self, owner, name):
        self._name = name

    def getter(self, fget):
        self.fget = fget
        return self

    def __get__(self, instance, owner: type) -> Any:
        if self.fget is None:
            raise AttributeError(f"can't read attribute '{self._name}'")
        return self.fget(owner)
