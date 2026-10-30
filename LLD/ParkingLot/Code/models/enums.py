from enum import Enum


class SpotType(Enum):
    Small = 1
    Medium = 2
    Large = 3

class VehicleType(Enum):
    MotorCycle = 1
    Car = 2
    Truck = 3

    @property
    def required_spot(self) -> SpotType:
        # Map each vehicle member to its allowed spot type
        mapping = {
            VehicleType.MotorCycle: SpotType.Small,
            VehicleType.Car: SpotType.Medium,
            VehicleType.Truck: SpotType.Large,
        }
        return mapping[self]
