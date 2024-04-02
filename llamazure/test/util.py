from typing import Generator, TypeVar

T = TypeVar("T")
Fixture = Generator[T, None, None]
