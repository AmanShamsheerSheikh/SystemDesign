from models.spot import Spot
from models.vehicle import Vehicle
from models.enums import SpotType
from typing import List
from collections import deque


class Floor:
    def __init__(self, spots: List[Spot], floorNumber: int, availableSpots: dict[SpotType, deque[Spot]]):
        self.spots: List[Spot] = spots
        self.floorNumber: int = floorNumber
        self.availableSpots: dict[SpotType, deque[Spot]] = availableSpots

    def findAndAssignEmptySpot(self, vehicle: Vehicle) -> Spot | None:
        spotType = vehicle.type.required_spot
        queue = self.availableSpots[spotType]
        if not queue:
            return None
        spot: Spot = queue.popleft()
        spot.assign(vehicle)
        return spot

    def freeSpot(self, spot: Spot):
        spot.release()
        self.availableSpots[spot.spotId] = spot
    
    