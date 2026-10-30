from models.floor import Floor
from models.ticket import Ticket
from models.vehicle import Vehicle
from models.spot import Spot
from models.enums import VehicleType
from typing import List
from strategy.pricingStrategy import PricingStrategy
import uuid
from datetime import datetime

class ParkingLot:
    def __init__(self, floors: List[Floor], pricingStrategy: PricingStrategy):
        self.floors: List[Floor] = floors
        self.activeTickets: dict[str, Ticket] = {}
        self.pricingStrategy: PricingStrategy = pricingStrategy

    def generateTicket(self, spot: Spot, vehicle: Vehicle, floor: Floor):
        ticketId: str = str(uuid.uuid4())
        ticket = Ticket(ticketId, vehicle, spot, floor)
        self.activeTickets[ticketId] = ticket
        return ticket

    def park(self, vehicle: Vehicle):
        spot: Spot = None
        for floor in self.floors:
            spot = floor.findAndAssignEmptySpot(vehicle)
            if spot:
                print(f"{vehicle.type.name} parked at spot {spot.spotId} on floor {spot.floorNumber}")
                return self.generateTicket(spot, vehicle, floor)
        print(f"No Spot Present for {vehicle.type.name}")
        return None

    def unPark(self, ticketId: str, currentTime: datetime):
        ticket = self.activeTickets[ticketId]
        if ticket:
            price = self.pricingStrategy.calculatePrice(ticket, currentTime)
            ticket.floor.freeSpot(ticket.spot)
            self.activeTickets.pop(ticket.ticketId)
            print(f"{ticket.vehicle.type.name} unparked, total price: {price}")
            return price
        else:
            print("ticket not found")
            return 0
        
