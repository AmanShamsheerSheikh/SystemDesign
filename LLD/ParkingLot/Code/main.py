from models.parkingLot import ParkingLot
from models.floor import Floor
from models.spot import Spot
from typing import List
import uuid
import random
from models.enums import SpotType, VehicleType
from collections import deque
from strategy.pricingStrategy import HourlyPricing
from models.vehicle import Vehicle
from datetime import datetime, timedelta
from models.ticket import Ticket

def main():
    numFloors = 2
    numSpots = 4
    floors: List[Floor] = []
    for i in range(numFloors):
        spots: List[Spot] = []
        availaibleSpots: dict[SpotType, deque[Spot]] = {t: deque() for t in SpotType}
        for _ in range(numSpots):
            spotType = random.choice(list(SpotType))
            spot = Spot(uuid.uuid4(), i, spotType)
            availaibleSpots[spotType].append(spot)
            spots.append(spot)
        floors.append(Floor(spots, i, availaibleSpots))
    pricingStrategy = HourlyPricing()
    parkingLot = ParkingLot(floors, pricingStrategy)

    # vehicle1 = Vehicle("1", VehicleType.Car)
    # vehicle2 = Vehicle("2", VehicleType.MotorCycle)
    # vehicle3 = Vehicle("3", VehicleType.Truck)

    # ticket1 = parkingLot.park(vehicle1)
    # ticket2 = parkingLot.park(vehicle2)
    # ticket3 = parkingLot.park(vehicle3)

    # parkingLot.unPark(ticket1.ticketId, datetime.now() + timedelta(hours=2))
    # parkingLot.unPark(ticket2.ticketId, datetime.now() + timedelta(hours=3))
    # parkingLot.unPark(ticket3.ticketId, datetime.now() + timedelta(hours=4))

    tickets: List[Ticket] = []
    for i in range(numSpots + numFloors):
        vehicle = Vehicle(str(i), random.choice(list(VehicleType)))
        ticket = parkingLot.park(vehicle)
        tickets.append(ticket)

    for i, ticket in enumerate(tickets):
        if ticket:
            parkingLot.unPark(ticket.ticketId, datetime.now() + timedelta(hours=i))



if __name__ == "__main__":
    main()


