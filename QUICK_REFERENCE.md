# Quick Reference

## Installation & Setup
```bash
pip install -r requirements.txt
make test              # Verify setup works
```

## Running the App

### Development
```bash
DEBUG=True python main.py
# http://localhost:8000/docs
```

### Testing
```bash
make test              # All tests
make test-auth         # Auth tests only
make test-coverage     # With coverage report
```

## Database Modes

| Mode | Command | Database | Speed | Use Case |
|------|---------|----------|-------|----------|
| Testing | `make test` | In-memory SQLite | < 1s/test | Unit/integration tests |
| Development | `DEBUG=True python main.py` | File SQLite | Fast | Local development |
| Production | `DEBUG=False python main.py` | PostgreSQL | Optimized | Live deployment |

## Key Files

| File | Purpose |
|------|---------|
| `conftest.py` | Pytest fixtures & configuration |
| `core/config.py` | Environment-based configuration |
| `core/db.py` | Database engine setup |
| `core/tenancy.py` | Multitenancy logic |
| `models/store.py` | Store (tenant) model |
| `models/user.py` | User model with roles |
| `routes/auth.py` | Authentication endpoints |
| `tests/test_auth.py` | Auth tests |
| `tests/test_multitenancy.py` | Multitenancy tests |

## Common Tasks

### Run Tests
```bash
make test                    # All tests
make test-auth              # Auth tests
make test-multitenancy      # Multitenancy tests
make test-coverage          # With coverage
make test-watch             # Auto-rerun on changes
```

### Create Store
```python
from models.store import Store
from core.db import db_session

with db_session() as db:
    store = Store(
        name="My Store",
        domain="mystore.example.com",
        owner_id=user_id,
        plan="premium"
    )
    db.add(store)
    db.commit()
```

### Add User to Store
```python
from models.user import user_store_roles
from core.db import db_session

with db_session() as db:
    stmt = user_store_roles.insert().values(
        user_id=user_id,
        store_id=store_id,
        role="admin"
    )
    db.execute(stmt)
    db.commit()
```

### Tenant-Aware Endpoint
```python
from fastapi import APIRouter, Depends
from core.tenancy import get_current_store
from models.store import Store

@router.get("/products")
def list_products(
    store: Store = Depends(get_current_store),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(
        Product.store_id == store.id
    ).all()
    return products
```

### Test with Auth
```python
def test_endpoint(client, auth_headers, test_store):
    response = client.get(
        "/products/",
        headers={
            **auth_headers,
            "X-Store-Domain": test_store.domain
        }
    )
    assert response.status_code == 200
```

## API Endpoints

### Auth
- `POST /auth/register` - Register user
- `POST /auth/login` - Login user
- `POST /auth/verify-otp` - Verify email
- `POST /auth/change-password` - Change password
- `POST /auth/refresh-token` - Refresh JWT token

### Products
- `GET /products/` - List products
- `POST /products/` - Create product
- `GET /products/{slug}` - Get product
- `PATCH /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product

### Orders
- `GET /orders/` - List orders
- `POST /orders/` - Create order
- `GET /orders/{id}` - Get order
- `PATCH /orders/{id}` - Update order

## Environment Variables

### Testing
```
TESTING=True
DATABASE_URL=sqlite:///:memory:
```

### Development
```
DEBUG=True
DATABASE_URL=sqlite:///./db.sqlite3
```

### Production
```
DEBUG=False
POSTGRES_DATABASE_URL=postgresql://user:pass@host/db
```

## User Roles

| Role | Permissions |
|------|-------------|
| owner | Full control, manage users |
| admin | Manage products, orders, staff |
| staff | Manage products and orders |
| member | Read-only access |

## Store Plans

| Plan | Products | Orders/Month | Support |
|------|----------|--------------|---------|
| free | Limited | Limited | Community |
| basic | 500 | 1,000 | Email |
| premium | 5,000 | 50,000 | Priority |
| enterprise | Unlimited | Unlimited | Dedicated |

## Fixtures (Testing)

```python
# Available in tests
db                    # Fresh database
client                # Test client
test_user             # Pre-created user
test_store            # Pre-created store
test_user_with_store  # User with owner role
auth_token            # Valid JWT token
auth_headers          # Authorization headers
```

## Debugging

### Check Database
```python
from core.db import SessionLocal
db = SessionLocal()
users = db.query(User).all()
print(users)
```

### Check Token
```python
from security import jwt as jwt_utils
payload = jwt_utils.decode_access(token)
print(payload)
```

### Check Store Access
```python
from core.tenancy import get_user_role_in_store
role = get_user_role_in_store(user_id, store_id, db)
print(role)
```

## Documentation

- [SETUP.md](SETUP.md) - Installation & setup
- [TESTING.md](TESTING.md) - Testing guide
- [MULTITENANCY.md](MULTITENANCY.md) - Multitenancy details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - What was added

## Useful Commands

```bash
# Clean up
make clean

# Stop services
make stop

# View API docs
open http://localhost:8000/docs

# Run specific test
pytest tests/test_auth.py::TestLogin::test_login_success -v

# Run with print statements
pytest tests/ -v -s

# Run with specific marker
pytest tests/ -v -m "not slow"
```

## Common Issues

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | `pip install -r requirements.txt` |
| Database locked | `make clean && make test` |
| Port in use | `python main.py --port 8001` |
| Redis error | `redis-server` or `docker run -d -p 6379:6379 redis` |
| Import error | Run from project root |

## Performance Tips

1. Use in-memory SQLite for tests (< 1s per test)
2. Use file SQLite for development (fast)
3. Use PostgreSQL for production (optimized)
4. Index frequently queried fields
5. Use connection pooling
6. Cache store lookups

## Security Checklist

- [ ] Change JWT_SECRET in production
- [ ] Change REFRESH_SECRET in production
- [ ] Use HTTPS in production
- [ ] Validate all user input
- [ ] Check user roles before operations
- [ ] Filter queries by store_id
- [ ] Use strong passwords
- [ ] Enable CORS carefully
- [ ] Log security events
- [ ] Monitor for suspicious activity
