from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_token
from app.auth.password import hash_password, verify_password
from app.config import get_settings
from app.models.user import User
from app.repositories.user_repo import UserRepository

#: 未知帳號也跑一次 Argon2，降低「帳號是否存在」的 timing 差異。
#: 這是隨機密碼的合法 hash；永遠不會與使用者輸入相符。
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$0LoXQghhjPFeaw0hREiJ0Q"
    "$jgOC//N5Wp0E1nNoZQwXgmyVYekDhHKIm8d6u1shZ9U"
)


class AuthError(Exception):
    pass


class EmailAlreadyExists(AuthError):
    pass


class UsernameAlreadyExists(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


def bump_token_version(user: User) -> None:
    """遞增 session 版本（不 commit，由呼叫端與其他變更一併提交）。

    PAT（`ims_pat_`）不看此版本，不受影響（Phase 44 D8）。
    """
    user.token_version = (user.token_version or 0) + 1


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
        if user is None:
            # 帳號不存在時仍付一次 Argon2 成本，避免用回應時間列舉帳號。
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentials()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        if not user.is_active:
            raise InvalidCredentials()
        return user

    def issue_access_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.access_token_ttl_seconds),
            token_type="access",
            version=user.token_version,
        )

    def issue_refresh_token(self, user: User) -> str:
        return create_token(
            subject=str(user.id),
            ttl=timedelta(seconds=self.settings.refresh_token_ttl_seconds),
            token_type="refresh",
            version=user.token_version,
        )

    async def revoke_all_sessions(self, user: User) -> None:
        """遞增 session 版本並 commit；此前簽發的 access／refresh token 全部失效。"""
        bump_token_version(user)
        await self.session.commit()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def get_user_by_username(self, username: str) -> User | None:
        """登入失敗後判斷帳號是否存在（僅供稽核使用，不對外揭露）。"""
        return await self.repo.get_by_username(username)
