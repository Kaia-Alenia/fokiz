import pytest
import secrets
from app.constants import SECRET_PATH

@pytest.fixture(scope="session", autouse=True)
def ensure_secret_for_tests():
    created = False
    if not SECRET_PATH.exists():
        SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
        SECRET_PATH.write_bytes(secrets.token_bytes(32))
        created = True
    
    yield
    
    if created and SECRET_PATH.exists():
        try:
            SECRET_PATH.unlink()
        except OSError:
            pass
