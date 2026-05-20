# Copyright 2026 OpenObserve Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import Settings


_BEARER_PREFIX = "Bearer "


def make_auth_dependency(settings: Settings):
    expected = settings.auth_token

    async def require_bearer(
        authorization: str | None = Header(default=None),
    ) -> None:
        if authorization is None or not authorization.startswith(_BEARER_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or malformed Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization[len(_BEARER_PREFIX) :].strip()
        if not hmac.compare_digest(token, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_bearer
