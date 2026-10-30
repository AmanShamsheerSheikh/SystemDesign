from models.vehicle import Vehicle
from models.spot import Spot
from datetime import datetime

class Ticket:
    def __init__(self, id: str, vehicle: Vehicle, spot: Spot):
        self.ticketId: str = id
        self.spot: Spot = spot
        self.vehicle: Vehicle = vehicle
        self.parkTime = datetime.now()

    def generateReceipt(self):
        print(f"Vechile with number plate {self.vehicle.numberPlate} parked at spot {self.spot.spotId} on floor {self.spot.floorNumber} at time {self.parkTime}")

        