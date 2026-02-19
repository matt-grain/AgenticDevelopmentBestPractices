---
paths: "**/*.py"
---

# SOLID Principles for Python

## Single Responsibility Principle (SRP)
- Each class/module has ONE reason to change.
- A service handles business logic for one domain concept.
- A repository handles persistence for one aggregate.
- Never mix HTTP concerns with business logic.
- If a class needs a conjunction to describe it ("UserService AND email sender"), split it.

## Open/Closed Principle (OCP)
- Design for extension without modifying existing code.
- Use abstract base classes (`ABC`) and Protocol classes to define contracts.
- Prefer composition and strategy pattern over deep inheritance.
- Use dependency injection to swap implementations.

```python
from abc import ABC, abstractmethod

class NotificationSender(ABC):
    @abstractmethod
    async def send(self, recipient: str, message: str) -> None: ...

class EmailSender(NotificationSender):
    async def send(self, recipient: str, message: str) -> None: ...

class SmsSender(NotificationSender):
    async def send(self, recipient: str, message: str) -> None: ...
```

## Liskov Substitution Principle (LSP)
- Subtypes must be substitutable for their base types without altering correctness.
- Never raise unexpected exceptions in overridden methods.
- Maintain covariant return types and contravariant parameter types.
- If overriding narrows behavior, it violates LSP — redesign.

## Interface Segregation Principle (ISP)
- Prefer small, focused `Protocol` classes over large abstract interfaces.
- Clients should not depend on methods they don't use.
- Split fat interfaces into role-specific ones.

```python
from typing import Protocol

class Readable(Protocol):
    async def get(self, id: int) -> Model: ...

class Writable(Protocol):
    async def save(self, entity: Model) -> Model: ...

class ReadWriteRepository(Readable, Writable, Protocol): ...
```

## Dependency Inversion Principle (DIP)
- High-level modules must not depend on low-level modules; both depend on abstractions.
- Services depend on repository Protocols, not concrete implementations.
- Use FastAPI's `Depends()` to inject concrete implementations at runtime.
- Configuration and wiring happen in `dependencies.py`, not inside business logic.
