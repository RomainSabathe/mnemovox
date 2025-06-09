# ABOUTME: Playwright configuration for browser-based end-to-end tests
# ABOUTME: Configures browsers, timeouts, and test settings for E2E testing


def pytest_configure(config):
    """Configure pytest for Playwright tests."""
    config.addinivalue_line("markers", "browser: mark test as browser-based E2E test")


# Playwright configuration
def test_browser_config():
    """Basic Playwright browser configuration."""
    return {
        "browser_name": "chromium",  # Use Chromium for consistent testing
        "headless": True,  # Run in headless mode for CI
        "slow_mo": 0,  # No delay between actions
        "timeout": 30000,  # 30 second timeout
        "video": "retain-on-failure",  # Record video on test failure
        "screenshot": "only-on-failure",  # Take screenshots on failure
    }
