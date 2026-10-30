from models.enums import VehicleType

class Vehicle:
    def __init__(self, numberPlate: str, type: VehicleType):   
        self.numberPlate: str = numberPlate
        self.type: VehicleType = type
