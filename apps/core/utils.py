import math
import random
from decimal import Decimal

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    
    # convert decimal degrees to radians
    r = 6371.0 # Radius of earth in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = r * c
    return round(distance, 2)

def calculate_delivery_fee(distance_km: float) -> Decimal:
    """
    Calculate delivery fee:
    Base ₹30 up to 2km, ₹10 per additional km. Minimum ₹30.
    """
    if distance_km <= 2.0:
        return Decimal('30.00')
    extra_km = distance_km - 2.0
    fee = 30.0 + (extra_km * 10.0)
    return Decimal(f"{round(fee, 2):.2f}")

def generate_otp(length: int = 4) -> str:
    """Generates a random numeric OTP code."""
    range_start = 10 ** (length - 1)
    range_end = (10 ** length) - 1
    return str(random.randint(range_start, range_end))

