"""Unit tests for error handling utilities."""

import pytest
from utils.error_handler import (
    ApplicationError,
    DatabaseError,
    ErrorContext,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
    handle_api_errors,
    handle_database_errors,
    handle_service_errors,
    handle_tool_errors,
    handle_utility_errors,
    safe_fallback,
)


class TestApplicationError:
    """Test suite for ApplicationError class."""

    def test_basic_error(self):
        """Test basic ApplicationError creation."""
        error = ApplicationError("Test error")
        assert str(error) == "Test error"
        assert error.context is None
        assert error.details == {}

    def test_error_with_context(self):
        """Test ApplicationError with context."""
        error = ApplicationError("Database error", context=ErrorContext.DATABASE, details={"table": "users"})

        assert str(error) == "Database error"
        assert error.context == ErrorContext.DATABASE
        assert error.details["table"] == "users"

    def test_to_dict(self):
        """Test ApplicationError to_dict method."""
        error = ApplicationError("Service error", context=ErrorContext.SERVICE, details={"code": 500})

        error_dict = error.to_dict()

        assert error_dict["error"] == "ApplicationError"
        assert error_dict["message"] == "Service error"
        assert error_dict["context"] == "service"
        assert error_dict["details"]["code"] == 500


class TestErrorDecorators:
    """Test suite for error handling decorators."""

    @pytest.mark.asyncio
    async def test_handle_service_errors_success(self):
        """Test handle_service_errors with successful execution."""

        @handle_service_errors
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_service_errors_application_error(self):
        """Test handle_service_errors passes through ApplicationError."""

        @handle_service_errors
        async def test_func():
            raise ValidationError("Invalid input")

        with pytest.raises(ValidationError):
            await test_func()

    @pytest.mark.asyncio
    async def test_handle_service_errors_generic_exception(self):
        """Test handle_service_errors wraps generic exceptions."""

        @handle_service_errors
        async def test_func():
            raise ValueError("Something went wrong")

        with pytest.raises(ApplicationError) as exc_info:
            await test_func()

        assert "Service operation failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.SERVICE

    def test_handle_service_errors_sync(self):
        """Test handle_service_errors with sync function."""

        @handle_service_errors
        def test_func():
            return "sync success"

        result = test_func()
        assert result == "sync success"

    @pytest.mark.asyncio
    async def test_handle_api_errors_success(self):
        """Test handle_api_errors with successful execution."""

        @handle_api_errors
        async def test_func():
            return "api success"

        result = await test_func()
        assert result == "api success"

    @pytest.mark.asyncio
    async def test_handle_api_errors_validation_error(self):
        """Test handle_api_errors returns dict for ValidationError."""

        @handle_api_errors
        async def test_func():
            raise ValidationError("Bad input", details={"field": "email"})

        result = await test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Invalid input"
        assert "Bad input" in result["message"]

    @pytest.mark.asyncio
    async def test_handle_api_errors_not_found(self):
        """Test handle_api_errors handles ResourceNotFoundError."""

        @handle_api_errors
        async def test_func():
            raise ResourceNotFoundError("User not found")

        result = await test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Not found"

    @pytest.mark.asyncio
    async def test_handle_api_errors_generic_exception(self):
        """Test handle_api_errors handles unexpected exceptions."""

        @handle_api_errors
        async def test_func():
            raise RuntimeError("Unexpected error")

        result = await test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Internal error"
        assert result["message"] == "An unexpected error occurred"

    @pytest.mark.asyncio
    async def test_handle_tool_errors_success(self):
        """Test handle_tool_errors with successful execution."""

        @handle_tool_errors
        async def test_func():
            return {"result": "data"}

        result = await test_func()
        assert result["result"] == "data"

    @pytest.mark.asyncio
    async def test_handle_tool_errors_validation_error(self):
        """Test handle_tool_errors wraps ValidationError."""

        @handle_tool_errors
        async def test_func():
            raise ValidationError("Invalid parameters")

        with pytest.raises(ValidationError) as exc_info:
            await test_func()

        assert "Invalid tool parameters" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.TOOL

    @pytest.mark.asyncio
    async def test_handle_tool_errors_generic_exception(self):
        """Test handle_tool_errors wraps generic exceptions."""

        @handle_tool_errors
        async def test_func():
            raise RuntimeError("Tool failed")

        with pytest.raises(ApplicationError) as exc_info:
            await test_func()

        assert "Tool execution failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.TOOL

    @pytest.mark.asyncio
    async def test_safe_fallback_success(self):
        """Test safe_fallback with successful execution."""

        @safe_fallback(default_value="default")
        async def test_func():
            return "actual value"

        result = await test_func()
        assert result == "actual value"

    @pytest.mark.asyncio
    async def test_safe_fallback_on_error(self):
        """Test safe_fallback returns default on error."""

        @safe_fallback(default_value="fallback")
        async def test_func():
            raise ValueError("Error")

        result = await test_func()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_safe_fallback_none_default(self):
        """Test safe_fallback with None as default."""

        @safe_fallback(default_value=None)
        async def test_func():
            raise ValueError("Error")

        result = await test_func()
        assert result is None

    def test_safe_fallback_sync(self):
        """Test safe_fallback with sync function."""

        @safe_fallback(default_value="sync fallback")
        def test_func():
            raise ValueError("Error")

        result = test_func()
        assert result == "sync fallback"


class TestCustomExceptions:
    """Test suite for custom exception classes."""

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid data", context=ErrorContext.API)
        assert isinstance(error, ApplicationError)
        assert str(error) == "Invalid data"

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        error = ResourceNotFoundError("Item not found")
        assert isinstance(error, ApplicationError)
        assert str(error) == "Item not found"

    def test_external_service_error(self):
        """Test ExternalServiceError."""
        error = ExternalServiceError("API call failed")
        assert isinstance(error, ApplicationError)
        assert str(error) == "API call failed"

    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError("Connection failed", context=ErrorContext.DATABASE)
        assert isinstance(error, ApplicationError)
        assert str(error) == "Connection failed"
        assert error.context == ErrorContext.DATABASE


class TestMissingDecorators:
    """Test suite for decorators not yet covered."""

    def test_handle_database_errors_success(self):
        """Test handle_database_errors with successful execution."""

        @handle_database_errors
        def test_func():
            return "database success"

        result = test_func()
        assert result == "database success"

    def test_handle_database_errors_psycopg2_error(self):
        """Test handle_database_errors wraps psycopg2 errors."""

        @handle_database_errors
        def test_func():
            raise Exception("psycopg2.OperationalError: connection failed")

        with pytest.raises(DatabaseError) as exc_info:
            test_func()

        assert "Database operation failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.DATABASE

    def test_handle_database_errors_connection_error(self):
        """Test handle_database_errors wraps connection errors."""

        @handle_database_errors
        def test_func():
            raise Exception("Connection to database lost")

        with pytest.raises(DatabaseError) as exc_info:
            test_func()

        assert "Database operation failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.DATABASE

    def test_handle_database_errors_non_db_error(self):
        """Test handle_database_errors passes through non-database errors."""

        @handle_database_errors
        def test_func():
            raise ValueError("Not a database error")

        with pytest.raises(ValueError) as exc_info:
            test_func()

        assert str(exc_info.value) == "Not a database error"

    def test_handle_utility_errors_success(self):
        """Test handle_utility_errors with successful execution."""

        @handle_utility_errors
        def test_func():
            return "utility success"

        result = test_func()
        assert result == "utility success"

    def test_handle_utility_errors_exception(self):
        """Test handle_utility_errors wraps exceptions."""

        @handle_utility_errors
        def test_func():
            raise ValueError("Utility failed")

        with pytest.raises(ApplicationError) as exc_info:
            test_func()

        assert "Utility operation failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.UTILITY
        assert "traceback" in exc_info.value.details


class TestSyncDecoratorCoverage:
    """Test suite for sync versions of decorators."""

    def test_handle_service_errors_sync_exception(self):
        """Test handle_service_errors sync wrapper with exception."""

        @handle_service_errors
        def test_func():
            raise RuntimeError("Sync service error")

        with pytest.raises(ApplicationError) as exc_info:
            test_func()

        assert "Service operation failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.SERVICE

    def test_handle_service_errors_sync_application_error(self):
        """Test handle_service_errors sync passes through ApplicationError."""

        @handle_service_errors
        def test_func():
            raise ValidationError("Validation failed")

        with pytest.raises(ValidationError):
            test_func()

    def test_handle_api_errors_sync_success(self):
        """Test handle_api_errors sync with successful execution."""

        @handle_api_errors
        def test_func():
            return "sync api success"

        result = test_func()
        assert result == "sync api success"

    def test_handle_api_errors_sync_validation_error(self):
        """Test handle_api_errors sync returns dict for ValidationError."""

        @handle_api_errors
        def test_func():
            raise ValidationError("Bad input", details={"field": "username"})

        result = test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Invalid input"
        assert "Bad input" in result["message"]
        assert result["details"]["field"] == "username"

    def test_handle_api_errors_sync_not_found(self):
        """Test handle_api_errors sync handles ResourceNotFoundError."""

        @handle_api_errors
        def test_func():
            raise ResourceNotFoundError("Product not found")

        result = test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Not found"
        assert "Product not found" in result["message"]

    def test_handle_api_errors_sync_application_error(self):
        """Test handle_api_errors sync handles ApplicationError."""

        @handle_api_errors
        def test_func():
            raise ApplicationError("Operation failed")

        result = test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Operation failed"

    def test_handle_api_errors_sync_generic_exception(self):
        """Test handle_api_errors sync handles unexpected exceptions."""

        @handle_api_errors
        def test_func():
            raise RuntimeError("Unexpected sync error")

        result = test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Internal error"
        assert result["message"] == "An unexpected error occurred"

    def test_handle_tool_errors_sync_success(self):
        """Test handle_tool_errors sync with successful execution."""

        @handle_tool_errors
        def test_func():
            return {"result": "sync tool data"}

        result = test_func()
        assert result["result"] == "sync tool data"

    def test_handle_tool_errors_sync_validation_error(self):
        """Test handle_tool_errors sync wraps ValidationError."""

        @handle_tool_errors
        def test_func():
            raise ValidationError("Invalid tool params")

        with pytest.raises(ValidationError) as exc_info:
            test_func()

        assert "Invalid tool parameters" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.TOOL

    def test_handle_tool_errors_sync_generic_exception(self):
        """Test handle_tool_errors sync wraps generic exceptions."""

        @handle_tool_errors
        def test_func():
            raise RuntimeError("Sync tool failed")

        with pytest.raises(ApplicationError) as exc_info:
            test_func()

        assert "Tool execution failed" in str(exc_info.value)
        assert exc_info.value.context == ErrorContext.TOOL


class TestEdgeCases:
    """Test suite for edge cases and corner scenarios."""

    def test_application_error_to_dict_without_context(self):
        """Test ApplicationError.to_dict() with None context."""
        error = ApplicationError("Simple error")
        error_dict = error.to_dict()

        assert error_dict["error"] == "ApplicationError"
        assert error_dict["message"] == "Simple error"
        assert error_dict["context"] is None
        assert error_dict["details"] == {}

    def test_validation_error_to_dict(self):
        """Test ValidationError.to_dict() method."""
        error = ValidationError(
            "Invalid email",
            context=ErrorContext.API,
            details={"field": "email", "value": "invalid"},
        )
        error_dict = error.to_dict()

        assert error_dict["error"] == "ValidationError"
        assert error_dict["message"] == "Invalid email"
        assert error_dict["context"] == "api"
        assert error_dict["details"]["field"] == "email"

    def test_error_context_values(self):
        """Test all ErrorContext enum values."""
        assert ErrorContext.SERVICE.value == "service"
        assert ErrorContext.API.value == "api"
        assert ErrorContext.DATABASE.value == "database"
        assert ErrorContext.TOOL.value == "tool"
        assert ErrorContext.UTILITY.value == "utility"

    def test_safe_fallback_with_list_default(self):
        """Test safe_fallback with list as default value."""

        @safe_fallback(default_value=[])
        def test_func():
            raise ValueError("Error")

        result = test_func()
        assert result == []

    def test_safe_fallback_with_dict_default(self):
        """Test safe_fallback with dict as default value."""

        @safe_fallback(default_value={})
        def test_func():
            raise ValueError("Error")

        result = test_func()
        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_api_errors_application_error(self):
        """Test handle_api_errors async handles ApplicationError."""

        @handle_api_errors
        async def test_func():
            raise ApplicationError("Generic app error")

        result = await test_func()

        assert isinstance(result, dict)
        assert result["error"] == "Operation failed"
        assert "Generic app error" in result["message"]
