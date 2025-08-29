"""Basic tests for gentle-man-tg-bot."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import BotConfig
from core.locale_manager import LocaleManager
from core.keyboard_manager import KeyboardManager


class TestGentleManTgBot:
    """Test suite for the bot."""
    
    def test_config_loading(self):
        """Test configuration can be loaded."""
        config = BotConfig(
            bot_token="test_token",
            database_url="postgresql://test:test@localhost/test",
            bot_name="gentle-man-tg-bot",
            default_language="en",
            supported_languages="en,ru,es"
        )
        assert config.bot_token == "test_token"
        assert config.bot_name == "gentle-man-tg-bot"
    
    def test_locale_manager(self):
        """Test locale manager functionality."""
        locale_manager = LocaleManager(
            default_language="en",
            supported_languages="en,ru,es".split(",")
        )
        
        # Test getting a message
        message = locale_manager.get("welcome_message", "en")
        assert message is not None
        assert len(message) > 0
    
    def test_keyboard_manager(self):
        """Test keyboard manager."""
        locale_manager = LocaleManager(
            default_language="en",
            supported_languages="en,ru,es".split(",")
        )
        keyboard_manager = KeyboardManager(locale_manager)
        
        # Test main menu keyboard
        keyboard = keyboard_manager.get_main_menu_keyboard("en")
        assert keyboard is not None