from abc import ABC, abstractmethod
import math
from models.ticket import Ticket
from datetime import datetime

class PricingStrategy(ABC):

    def __init__(self):
        super().__init__()
        self.hourlyPrice = 100
        self.flatPrice = 1000

    @abstractmethod
    def calculatePrice(self, ticket: Ticket, currentTime: datetime):
        pass


class HourlyPricing(PricingStrategy):

    def calculatePrice(self, ticket: Ticket, currentTime: datetime):
        elapsed = currentTime - ticket.parkTime
        hours = math.ceil(elapsed.total_seconds() / 3600)
        hours = max(hours, 1)
        return hours * self.hourlyPrice
