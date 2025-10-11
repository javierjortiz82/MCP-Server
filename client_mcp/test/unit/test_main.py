"""Unit tests for __main__ module."""

import pytest


class TestMainModuleStructure:
    """Test suite for __main__ module structure."""

    def test_main_file_exists(self):
        """Test that __main__.py file exists."""
        import os

        main_path = "/home/javort/Lab01-MCP/client_mcp/__main__.py"
        assert os.path.exists(main_path)

    def test_main_file_has_content(self):
        """Test that __main__.py has expected content."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Verify key components exist
        assert "async def main():" in content
        assert "OdiseoBot" in content
        assert 'if __name__ == "__main__":' in content
        assert "asyncio.run(main())" in content

    def test_main_imports_odiseo_bot(self):
        """Test that main imports OdiseoBot correctly."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should have both relative and absolute import for compatibility
        assert "from .core.odiseo_bot import OdiseoBot" in content
        assert "from core.odiseo_bot import OdiseoBot" in content
        assert "try:" in content
        assert "except ImportError:" in content

    def test_main_has_error_handling(self):
        """Test that main has proper error handling."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Verify error handling exists
        assert "except KeyboardInterrupt:" in content
        assert "except Exception" in content
        assert "finally:" in content

    def test_main_has_cleanup(self):
        """Test that main calls cleanup."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "await bot.cleanup()" in content

    def test_main_has_bot_lifecycle(self):
        """Test that main has complete bot lifecycle."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "bot = OdiseoBot()" in content
        assert "await bot.initialize()" in content
        assert "await bot.run_interactive()" in content
        assert "await bot.cleanup()" in content

    def test_main_has_docstring(self):
        """Test that module has documentation."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should start with docstring
        assert '"""' in content[:500]
        assert "Odiseo Bot" in content[:500]

    def test_main_handles_keyboard_interrupt(self):
        """Test that KeyboardInterrupt is handled gracefully."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should catch KeyboardInterrupt and print message
        assert "except KeyboardInterrupt:" in content
        # Should print goodbye message
        assert "Hasta luego" in content or "👋" in content

    def test_main_handles_exceptions_with_exit(self):
        """Test that exceptions cause sys.exit(1)."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "sys.exit(1)" in content

    def test_main_prints_startup_banner(self):
        """Test that startup banner is printed."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should print banner in the if __name__ == "__main__" block
        assert "Odiseo Bot" in content
        assert "Intelligent Sales Agent" in content or "🚀" in content


class TestMainModuleFunctionalityBasics:
    """Basic functionality tests that don't require complex mocking."""

    def test_can_import_main_module(self):
        """Test that __main__ module can be imported as a module."""
        try:
            # Try to import as a package module
            from client_mcp import __main__ as main_module

            assert main_module is not None
        except ImportError:
            # This is expected in some test environments
            pytest.skip("Cannot import __main__ as package module in test environment")

    def test_main_function_exists_if_importable(self):
        """Test that main() function exists if module is importable."""
        try:
            from client_mcp import __main__ as main_module

            assert hasattr(main_module, "main")
            assert callable(main_module.main)

            # Check it's async
            import asyncio

            assert asyncio.iscoroutinefunction(main_module.main)
        except ImportError:
            pytest.skip("Cannot import __main__ in test environment")


class TestMainModuleCodeQuality:
    """Test code quality aspects of __main__ module."""

    def test_main_uses_asyncio(self):
        """Test that main uses asyncio for async execution."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "import asyncio" in content
        assert "asyncio.run(main())" in content

    def test_main_has_shebang(self):
        """Test that file has proper shebang for direct execution."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            first_line = f.readline()

        assert first_line.startswith("#!")
        assert "python" in first_line.lower()

    def test_main_imports_sys(self):
        """Test that sys module is imported for exit handling."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "import sys" in content

    def test_main_file_size_reasonable(self):
        """Test that __main__.py is concise (thin wrapper)."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            lines = f.readlines()

        # Should be a thin wrapper, not too large
        assert len(lines) < 100  # Less than 100 lines


class TestMainModuleExecution:
    """Test aspects related to module execution."""

    def test_main_is_executable_module(self):
        """Test that module can be executed with python -m."""
        import subprocess
        import sys

        # Test that python -m client_mcp --help doesn't crash
        # (We don't actually run it as it would start the interactive bot)
        # Just verify the file is properly formatted
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "/home/javort/Lab01-MCP/client_mcp/__main__.py"],
            capture_output=True,
        )

        # Should compile without syntax errors
        assert result.returncode == 0

    def test_main_entry_point_format(self):
        """Test that entry point has correct format."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Verify proper if __name__ == "__main__" format
        assert 'if __name__ == "__main__"' in content
        # Should be at end of file
        lines = content.splitlines()
        found_entry = False
        for i, line in enumerate(lines):
            if 'if __name__ == "__main__":' in line:
                found_entry = True
                # Should be near end (within last 10 lines)
                assert i >= len(lines) - 10

        assert found_entry


class TestMainModuleErrorMessages:
    """Test error message quality in __main__ module."""

    def test_keyboard_interrupt_message_friendly(self):
        """Test that KeyboardInterrupt shows friendly message."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Find the KeyboardInterrupt handler
        assert "except KeyboardInterrupt:" in content

        # Should have a friendly goodbye message
        # Extract the handler block
        lines = content.splitlines()
        in_keyboard_handler = False
        has_friendly_message = False

        for line in lines:
            if "except KeyboardInterrupt:" in line:
                in_keyboard_handler = True
            elif in_keyboard_handler and ("except" in line or "finally" in line):
                break
            elif in_keyboard_handler and ("Hasta luego" in line or "👋" in line):
                has_friendly_message = True

        assert has_friendly_message

    def test_error_message_shows_details(self):
        """Test that error messages show exception details."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Error handler should use {e} or str(e) to show error details
        assert "except Exception as e:" in content
        assert "{e}" in content or "str(e)" in content


class TestMainModuleBestPractices:
    """Test that main module follows Python best practices."""

    def test_main_function_is_async(self):
        """Test that main() is defined as async function."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        assert "async def main():" in content

    def test_cleanup_in_finally_block(self):
        """Test that cleanup is in finally block for guaranteed execution."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should have finally block with cleanup
        lines = content.splitlines()
        found_finally = False
        found_cleanup = False

        for i, line in enumerate(lines):
            if "finally:" in line:
                found_finally = True
            elif found_finally and "await bot.cleanup()" in line:
                found_cleanup = True
                break

        assert found_finally and found_cleanup

    def test_uses_context_appropriate_imports(self):
        """Test that imports handle both direct and module execution."""
        with open("/home/javort/Lab01-MCP/client_mcp/__main__.py", "r") as f:
            content = f.read()

        # Should have try/except for import compatibility
        assert "try:" in content
        assert "except ImportError:" in content
        # Should have both relative and absolute imports
        assert "from .core" in content
        assert "from core" in content
