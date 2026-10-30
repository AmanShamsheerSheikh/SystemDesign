# SOLID Principles: Explained with a Food-Delivery App

All five principles use the same food-delivery app. For each one: the bad code, what goes wrong, and the fix.

All examples assume this import:

```python
from abc import ABC, abstractmethod
```

---

## 1. Single Responsibility: one reason to change

**The problem:** a class that handles business logic, storage and notifications all at once.

```python
class Order:
    def __init__(self, items):
        self.items = items

    def total(self):
        return sum(item.price * item.qty for item in self.items)

    def save(self):
        db.execute("INSERT INTO orders ...", self.total())

    def send_receipt(self, email):
        smtp.send(email, f"Your total is ₹{self.total()}")
```

**What goes wrong:** this class has three reasons to change. Adding GST changes `total`. Moving from MySQL to Postgres changes `save`. Redesigning the receipt changes `send_receipt`. Each change risks breaking the other two, and you can't test `total()` without a database and an email server in the same object.

**The fix:** split along the reasons to change.

```python
class Order:
    def __init__(self, items):
        self.items = items

    def total(self):
        return sum(item.price * item.qty for item in self.items)


class OrderRepository:
    def save(self, order: Order):
        db.execute("INSERT INTO orders ...", order.total())


class ReceiptSender:
    def send(self, order: Order, email: str):
        smtp.send(email, f"Your total is ₹{order.total()}")
```

Now a receipt redesign only touches `ReceiptSender`, and `Order` can be tested with no database at all.

---

## 2. Open/Closed: add new behavior without editing old code

**The problem:** every new coupon means editing the same method.

```python
class Checkout:
    def final_total(self, total, coupon):
        if coupon == "FLAT100":
            return total - 100
        elif coupon == "PERCENT10":
            return total * 0.9
        # Next week: "FREEDELIVERY". Edit this method again.
        return total
```

**What goes wrong:** `Checkout` already works and is tested. Every new coupon reopens it, so each change can break coupons that were working fine.

**The fix:** define an abstraction, and add new coupons as new classes.

```python
class Discount(ABC):
    @abstractmethod
    def apply(self, total: float) -> float: ...

class FlatDiscount(Discount):
    def __init__(self, amount):
        self.amount = amount
    def apply(self, total):
        return max(total - self.amount, 0)

class PercentDiscount(Discount):
    def __init__(self, percent):
        self.percent = percent
    def apply(self, total):
        return total * (1 - self.percent / 100)

class Checkout:
    def final_total(self, total: float, discount: Discount) -> float:
        return discount.apply(total)
```

A new "free delivery" coupon becomes a new `FreeDeliveryDiscount` class. `Checkout` doesn't change at all, so it's **closed** for modification and **open** for extension.

---

## 3. Liskov Substitution: a child must keep the parent's promises

**The problem:** a subclass that can't do something its parent says every payment method can do.

```python
class PaymentMethod:
    def pay(self, amount): ...
    def refund(self, amount): ...

class CardPayment(PaymentMethod):
    def pay(self, amount):    print(f"Charged ₹{amount} to card")
    def refund(self, amount): print(f"Refunded ₹{amount} to card")

class CashOnDelivery(PaymentMethod):
    def pay(self, amount):    print(f"Collect ₹{amount} at door")
    def refund(self, amount): raise NotImplementedError("Can't refund cash")


def cancel_order(order, method: PaymentMethod):
    method.refund(order.total)   # crashes for CashOnDelivery
```

**What goes wrong:** `cancel_order` trusted the parent's promise that every `PaymentMethod` can refund. `CashOnDelivery` is a valid `PaymentMethod` type, and the code still crashes in production. The type check passes, but the behavior doesn't match what the caller expects.

**The fix:** only promise what every subclass can actually do.

```python
class PaymentMethod:
    def pay(self, amount): ...

class RefundablePaymentMethod(PaymentMethod):
    def refund(self, amount): ...

class CardPayment(RefundablePaymentMethod):
    def pay(self, amount):    print(f"Charged ₹{amount} to card")
    def refund(self, amount): print(f"Refunded ₹{amount} to card")

class CashOnDelivery(PaymentMethod):
    def pay(self, amount):    print(f"Collect ₹{amount} at door")


def cancel_order(order, method: RefundablePaymentMethod):
    method.refund(order.total)   # every allowed type can refund
```

Now the types themselves guarantee that `cancel_order` never receives a payment method that can't refund.

---

## 4. Interface Segregation: don't force classes to implement what they don't need

**The problem:** one large interface for every kind of staff member.

```python
class Staff(ABC):
    @abstractmethod
    def cook(self, order): ...
    @abstractmethod
    def deliver(self, order): ...
    @abstractmethod
    def collect_cash(self, amount): ...

class Chef(Staff):
    def cook(self, order):          print("Cooking")
    def deliver(self, order):       raise NotImplementedError
    def collect_cash(self, amount): raise NotImplementedError
```

**What goes wrong:** `Chef` is forced to write fake methods. Any code that receives a `Staff` object can call `deliver()` on a chef and crash. And if the delivery logic changes, `Chef` is affected even though it has nothing to do with delivery.

**The fix:** several small interfaces, each class implementing only the ones it needs.

```python
class Cook(ABC):
    @abstractmethod
    def cook(self, order): ...

class Deliverer(ABC):
    @abstractmethod
    def deliver(self, order): ...

class CashCollector(ABC):
    @abstractmethod
    def collect_cash(self, amount): ...

class Chef(Cook):
    def cook(self, order): print("Cooking")

class DeliveryPartner(Deliverer, CashCollector):
    def deliver(self, order):       print("Delivering")
    def collect_cash(self, amount): print(f"Collected ₹{amount}")
```

Note how this connects to Liskov. A large interface like `Staff` almost always forces Liskov violations, because some subclass inevitably can't do one of the methods. Interface Segregation is about **designing the interface**; Liskov is about **subclass behavior**.

---

## 5. Dependency Inversion: depend on an abstraction, not a specific class

**The problem:** business logic tied to one specific database.

```python
class MySQLDatabase:
    def save(self, order):
        print("INSERT INTO orders ...")

class OrderService:
    def __init__(self):
        self.db = MySQLDatabase()      # tied to MySQL

    def place_order(self, order):
        # business rules ...
        self.db.save(order)
```

**What goes wrong:** `OrderService` holds your core business logic, and it depends directly on a storage detail. Switching to Postgres means editing `OrderService`. Testing `place_order` requires a real MySQL database.

**The fix:** the business layer defines the abstraction it needs, and the storage classes implement it.

```python
class OrderStore(ABC):
    @abstractmethod
    def save(self, order): ...

class MySQLStore(OrderStore):
    def save(self, order): print("INSERT INTO orders ...")

class InMemoryStore(OrderStore):
    def __init__(self): self.orders = []
    def save(self, order): self.orders.append(order)

class OrderService:
    def __init__(self, store: OrderStore):   # injected from outside
        self.store = store

    def place_order(self, order):
        # business rules ...
        self.store.save(order)


# Production
service = OrderService(MySQLStore())
# Tests: fast, no database needed
service = OrderService(InMemoryStore())
```

**Why it's called "inversion":** before, the dependency arrow pointed from the important class to the detail (`OrderService → MySQLDatabase`). After, both point to an abstraction that the business layer owns (`OrderService → OrderStore ← MySQLStore`). The detail now depends on the business layer's interface, instead of the other way around.

Passing `MySQLStore()` into the constructor is **dependency injection**, which is the technique. Dependency inversion is the principle that technique supports.

---

## Summary

| Principle | Question to ask | Warning sign |
|---|---|---|
| Single Responsibility | How many reasons could this class change for? | Class mixes logic, database and I/O |
| Open/Closed | Does a new feature require editing tested code? | Growing `if/elif` chains on a type |
| Liskov | Can every child replace the parent without surprises? | `raise NotImplementedError` in a subclass |
| Interface Segregation | Does every implementer need every method? | Stub methods that do nothing |
| Dependency Inversion | Does business logic name a specific class? | `self.x = ConcreteClass()` inside a constructor |

## Interview traps

- Saying SRP means "one method per class." It means one reason to change, not one function.
- Treating dependency injection and dependency inversion as the same thing. Injection is the technique; inversion is the principle.
- Not knowing that the payment example breaks two principles. It's a Liskov bug caused by an interface design problem, and pointing that out is a strong signal.
- Over-applying the principles. Five abstract classes for a 50-line script is over-engineering. Apply them where change is actually likely.

## Challenge question

In Kosh, your reconciliation job reads RTA files. CAMS and KFintech use different file formats, and a third format may come later. Which principles would you use to design the parser layer, and what would the classes look like?