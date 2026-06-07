from __future__ import annotations

from keyhaven.sdk.exceptions import (
    AuthenticationError,
    KeyhavenError,
    KeyhavenHTTPError,
    KeyhavenNetworkError,
    NotFoundError,
    OwnerMismatchError,
    ProviderError,
)


class TestInheritance:
    def test_keyhaven_error_is_base(self) -> None:
        assert issubclass(AuthenticationError, KeyhavenError)
        assert issubclass(NotFoundError, KeyhavenError)
        assert issubclass(OwnerMismatchError, KeyhavenError)
        assert issubclass(KeyhavenHTTPError, KeyhavenError)
        assert issubclass(KeyhavenNetworkError, KeyhavenError)
        assert issubclass(ProviderError, KeyhavenError)

    def test_http_errors_are_keyhaven_http_error(self) -> None:
        assert issubclass(AuthenticationError, KeyhavenHTTPError)
        assert issubclass(NotFoundError, KeyhavenHTTPError)
        assert issubclass(OwnerMismatchError, KeyhavenHTTPError)
        assert issubclass(ProviderError, KeyhavenHTTPError)

    def test_keyhaven_network_error_is_not_http(self) -> None:
        assert not issubclass(KeyhavenNetworkError, KeyhavenHTTPError)


class TestKeyhavenHTTPError:
    def test_basic_attributes(self) -> None:
        exc = KeyhavenHTTPError(
            "something went wrong",
            status_code=400,
            error_code="BAD_REQUEST",
            details={"field": "name"},
        )
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.details == {"field": "name"}
        assert str(exc) == "something went wrong"

    def test_default_details(self) -> None:
        exc = KeyhavenHTTPError("msg", status_code=500)
        assert exc.details == {}

    def test_none_error_code(self) -> None:
        exc = KeyhavenHTTPError("msg", status_code=500)
        assert exc.error_code is None


class TestSubclasses:
    def test_authentication_error(self) -> None:
        exc = AuthenticationError("invalid key", status_code=401, error_code="AUTH_FAILED")
        assert exc.status_code == 401
        assert exc.error_code == "AUTH_FAILED"
        assert isinstance(exc, KeyhavenHTTPError)

    def test_owner_mismatch_error(self) -> None:
        exc = OwnerMismatchError("wrong owner", status_code=403, error_code="OWNER_MISMATCH")
        assert exc.status_code == 403
        assert exc.error_code == "OWNER_MISMATCH"

    def test_not_found_error(self) -> None:
        exc = NotFoundError("not found", status_code=404, error_code="NOT_FOUND")
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"

    def test_provider_error(self) -> None:
        exc = ProviderError("provider down", status_code=502, error_code="PROVIDER_ERROR")
        assert exc.status_code == 502
        assert exc.error_code == "PROVIDER_ERROR"

    def test_details_preserved(self) -> None:
        exc = ProviderError(
            "msg",
            status_code=502,
            error_code="PROVIDER_ERROR",
            details={"cause": "rate_limit"},
        )
        assert exc.details == {"cause": "rate_limit"}


class TestKeyhavenNetworkError:
    def test_no_http_status(self) -> None:
        exc = KeyhavenNetworkError("connection refused")
        assert str(exc) == "connection refused"
        assert not hasattr(exc, "status_code")

    def test_wrapping(self) -> None:
        original = ConnectionError("failed")
        exc = KeyhavenNetworkError(str(original))
        assert str(exc) == "failed"
