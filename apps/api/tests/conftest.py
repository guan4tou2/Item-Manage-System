import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
# ≥ 32 bytes：PyJWT 對 HS256 過短金鑰會發 InsecureKeyLengthWarning（RFC 7518 §3.2）
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod-hs256-32b"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
import app.models  # noqa: F401, E402 — 將所有 ORM model 註冊至 Base.metadata


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session


@pytest.fixture
async def client(test_engine):
    app = create_app()
    maker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def decode_qr():
    """QR PNG 位元組 → 解碼文字（Phase 37：zxing-cpp 真值解碼）。

    回傳 `None` 代表無法解碼（測試應據此斷言失敗，而非靜默通過）。
    """

    def _decode(png: bytes) -> str | None:
        import io

        import zxingcpp
        from PIL import Image

        result = zxingcpp.read_barcode(Image.open(io.BytesIO(png)))
        return result.text if result else None

    return _decode


@pytest.fixture(autouse=True)
def _stub_webhook_dns(monkeypatch):
    """Phase 44：webhook 送出前會解析 DNS。測試一律預設把任何 hostname 解析到
    公網位址，避免打真實 DNS；需要自訂解析結果的測試自行再 monkeypatch。"""
    import ipaddress

    from app.services import url_guard

    async def _fake_resolve(host, port):
        return [ipaddress.ip_address("93.184.216.34")]

    monkeypatch.setattr(url_guard, "resolve_host", _fake_resolve)
