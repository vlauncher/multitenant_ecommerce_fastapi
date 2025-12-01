# Import models so that SQLAlchemy metadata includes them on app startup
from .user import User  # noqa: F401
from .otp import OTP  # noqa: F401
from .store import Store  # noqa: F401
from .brand import Brand  # noqa: F401
from .product import Product  # noqa: F401
from .order import Order  # noqa: F401
from .order_item import OrderItem  # noqa: F401
from .payment import Payment  # noqa: F401
