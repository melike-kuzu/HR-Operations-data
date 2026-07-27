from __future__ import annotations

from dataclasses import dataclass

from workforce_assistant.config.settings import Settings


@dataclass(frozen=True, slots=True)
class CurrentUser:
    user_id: str
    display_name: str
    is_admin: bool = False


class UserService:
    """Resolve the current application user.

    Local development uses environment configuration. This service can later
    resolve identity from Microsoft Entra ID without changing the UI layer.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_current_user(self) -> CurrentUser:
        user_id = self._settings.local_user_id.strip()
        display_name = self._settings.local_user_name.strip()

        if not user_id:
            raise RuntimeError(
                "LOCAL_USER_ID is not configured."
            )

        normalised_user_id = user_id.lower()

        return CurrentUser(
            user_id=normalised_user_id,
            display_name=display_name or normalised_user_id,
            is_admin=(
                normalised_user_id
                in self._settings.admin_users
            ),
        )