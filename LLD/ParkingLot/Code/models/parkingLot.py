from models.floor import Floor
from models.ticket import Ticket
from models.vehicle import Vehicle
from models.spot import Spot
from typing import List
from strategy.pricingStrategy import PricingStrategy
import uuid
from datetime import datetime

class ParkingLot:
    def __init__(self, floors: List[Floor], pricingStrategy: PricingStrategy):
        self.floors: List[Floor] = floors
        self.activeTickets: dict[str, Ticket] = {}
        self.pricingStrategy: PricingStrategy = pricingStrategy

    def generateTicket(self, spot: Spot, vehicle: Vehicle):
        ticketId: str = uuid.uuid4()
        ticket = Ticket(ticketId, vehicle, spot)
        self.activeTickets[ticketId] = ticket
        return ticket

    def park(self, vehicle: Vehicle):
        spot: Spot = None
        for floor in self.floors:
            spot = floor.findAndAssignEmptySpot(vehicle)
            if spot:
                break
        if spot:
            print(f"Vehicle parked at spot {spot.spotId} on floor {spot.floorNumber}")
            return self.generateTicket(spot, vehicle)
        else:
            print("No Spot Present")
            return None

    def unPark(self, ticketId: str, currentTime: datetime):
        ticket = self.activeTickets[ticketId]
        ticket.spot.release()
        self.activeTickets.pop(ticket.ticketId)
        price = self.pricingStrategy.calculatePrice(ticket, currentTime)
        print(f"Vehicle unparked, total price: {price}")
        return price
        
