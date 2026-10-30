from models.enums import SpotType
from models.vehicle import Vehicle

class Spot:
    def __init__(self, id: str, floorNumber: int, type: SpotType):
        self.spotId: str = id
        self.floorNumber: int = floorNumber
        self.type: SpotType = type
        self.vehicle: None | Vehicle  = None
        self.isOccupied = False

    def assign(self, vehicle: Vehicle):
        self.vehicle = vehicle
        self.isOccupied = True

    def release(self):
        self.vehicle = None
        self.isOccupied = False

        