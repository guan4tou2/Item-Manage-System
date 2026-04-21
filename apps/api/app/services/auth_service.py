from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_token
from app.auth.password import hash_password, verify_password
from app.config import get_settings
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthError(Exception):
    pass


class EmailAlreadyExists(AuthError):
    pass


class UsernameAlreadyExists(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.settings = get_settings()

    async def register(self, *, email: str, username: str, password: str) -> User:
        if await self.repo.get_by_email(email):
            raise EmailAlreadyExists(email)
        if await self.repo.get_by_username(username):
            raise UsernameAlreadyExists(username)
        return await self.repo.create(
            email=email, username=username, password_hash=hash_password(password)
        )

    async def authenticate(self, *, username: str, password: str) -> User:
        user = await self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        if not user.is_active:
            raise InvalidCredentials()
        return user

    def issue_access_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.access_token_ttl_seconds),
            token_type="access",
        )

    def issue_refresh_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.refresh_token_ttl_seconds),
            token_type="refresh",
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.repo.get_by_id(user_id)
