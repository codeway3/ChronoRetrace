# ============================================================================
# ChronoRetrace Environment Configuration Manager
# Handles multi-environment configuration loading and validation
# ============================================================================

import logging
import os
from pathlib import Path
from typing import Any, ClassVar

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages environment-specific configuration loading and validation."""

    SUPPORTED_ENVIRONMENTS: ClassVar[list[str]] = [
        "development",
        "testing",
        "staging",
        "production",
    ]
    DEFAULT_ENVIRONMENT: ClassVar[str] = "development"

    def __init__(self, base_path: Path | None = None):
        """Initialize the environment manager.

        Args:
            base_path: Base path for configuration files. Defaults to current directory.
        """
        self.base_path = base_path or Path(__file__).parent
        self.environments_path = self.base_path / "environments"
        self.current_environment = self._detect_environment()
        self.config: dict[str, Any] = {}

    def _detect_environment(self) -> str:
        """Detect the current environment from various sources.

        Returns:
            The detected environment name.
        """
        # Priority order: ENV var > ENVIRONMENT var > default
        env = (
            os.getenv("ENV")
            or os.getenv("ENVIRONMENT")
            or os.getenv("FLASK_ENV")
            or os.getenv("FASTAPI_ENV")
            or self.DEFAULT_ENVIRONMENT
        ).lower()

        if env not in self.SUPPORTED_ENVIRONMENTS:
            logger.warning(
                f"Unknown environment '{env}', falling back to '{self.DEFAULT_ENVIRONMENT}'"
            )
            env = self.DEFAULT_ENVIRONMENT

        logger.info(f"Detected environment: {env}")
        return env

    def load_environment_config(self, environment: str | None = None) -> dict[str, Any]:
        """Load configuration for the specified environment.

        Args:
            environment: Environment name. Uses current environment if not specified.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            FileNotFoundError: If the environment configuration file is not found.
            ValueError: If the environment is not supported.
        """
        env = environment or self.current_environment

        if env not in self.SUPPORTED_ENVIRONMENTS:
            raise ValueError(f"Unsupported environment: {env}")

        # Load base configuration first
        base_config = self._load_base_config()

        # Load environment-specific configuration
        env_config = self._load_env_config(env)

        # Merge configurations (environment-specific overrides base)
        merged_config = {**base_config, **env_config}

        # Validate required configuration
        self._validate_config(merged_config, env)

        self.config = merged_config
        logger.info(f"Successfully loaded configuration for environment: {env}")

        return merged_config

    def _load_base_config(self) -> dict[str, Any]:
        """Load base configuration that applies to all environments.

        Returns:
            Dictionary containing base configuration.
        """
        base_config = {}

        # Load from base .env file if it exists
        base_env_file = self.base_path.parent / ".env"
        if base_env_file.exists():
            load_dotenv(base_env_file)
            logger.debug(f"Loaded base configuration from {base_env_file}")

        return base_config

    def _load_env_config(self, environment: str) -> dict[str, Any]:
        """Load environment-specific configuration.

        Args:
            environment: Environment name.

        Returns:
            Dictionary containing environment-specific configuration.

        Raises:
            FileNotFoundError: If the environment configuration file is not found.
        """
        env_file = self.environments_path / f"{environment}.env"

        if not env_file.exists():
            raise FileNotFoundError(
                f"Environment configuration file not found: {env_file}"
            )

        # Load environment file
        load_dotenv(env_file, override=True)
        logger.debug(f"Loaded environment configuration from {env_file}")

        # Convert environment variables to dictionary
        config = {}
        with env_file.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip("\"'")

        return config

    def _validate_config(self, config: dict[str, Any], environment: str) -> None:
        """Validate the loaded configuration.

        Args:
            config: Configuration dictionary to validate.
            environment: Environment name.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        required_keys = {
            "production": [
                "DATABASE_URL",
                "REDIS_URL",
                "JWT_SECRET_KEY",
                "SECRET_KEY",
                "CORS_ALLOWED_ORIGINS",
            ],
            "staging": ["DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY", "SECRET_KEY"],
            "testing": ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"],
            "development": ["JWT_SECRET_KEY", "SECRET_KEY"],
        }

        required = required_keys.get(environment, [])
        missing_keys = []

        for key in required:
            if not config.get(key) and not os.getenv(key):
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(
                f"Missing required configuration for {environment} environment: "
                f"{', '.join(missing_keys)}"
            )

        # Validate specific configuration values
        if environment == "production":
            self._validate_production_config(config)

    def _validate_production_config(self, config: dict[str, Any]) -> None:
        """Validate production-specific configuration.

        Args:
            config: Configuration dictionary to validate.

        Raises:
            ValueError: If production configuration is invalid.
        """
        # Check for default/insecure values in production
        insecure_patterns = [
            "dev-",
            "test-",
            "change-this",
            "your-",
            "secret-key",
            "jwt-secret",
            "localhost",
            "127.0.0.1",
        ]

        security_keys = ["JWT_SECRET_KEY", "SECRET_KEY"]

        for key in security_keys:
            value = config.get(key, "").lower()
            if any(pattern in value for pattern in insecure_patterns):
                raise ValueError(
                    f"Insecure {key} detected in production environment. "
                    f"Please use a strong, unique secret."
                )

        # Validate database URL
        db_url = config.get("DATABASE_URL", "")
        if "sqlite" in db_url.lower():
            logger.warning(
                "SQLite database detected in production. "
                "Consider using PostgreSQL for better performance and reliability."
            )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if key is not found.

        Returns:
            Configuration value or default.
        """
        # Priority: environment variable > loaded config > default
        return os.getenv(key) or self.config.get(key, default)

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if in production environment.
        """
        return self.current_environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if in development environment.
        """
        return self.current_environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing environment.

        Returns:
            True if in testing environment.
        """
        return self.current_environment == "testing"

    def get_environment_info(self) -> dict[str, Any]:
        """Get information about the current environment.

        Returns:
            Dictionary containing environment information.
        """
        return {
            "environment": self.current_environment,
            "config_path": str(self.environments_path),
            "supported_environments": self.SUPPORTED_ENVIRONMENTS,
            "config_loaded": bool(self.config),
            "config_keys_count": len(self.config),
        }


# Global environment manager instance
env_manager = EnvironmentManager()


# Convenience functions
def load_config(environment: str | None = None) -> dict[str, Any]:
    """Load configuration for the specified environment.

    Args:
        environment: Environment name. Uses current environment if not specified.

    Returns:
        Dictionary containing the loaded configuration.
    """
    return env_manager.load_environment_config(environment)


def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value.

    Args:
        key: Configuration key.
        default: Default value if key is not found.

    Returns:
        Configuration value or default.
    """
    return env_manager.get_config_value(key, default)


def get_current_environment() -> str:
    """Get the current environment name.

    Returns:
        Current environment name.
    """
    return env_manager.current_environment


def is_production() -> bool:
    """Check if running in production environment.

    Returns:
        True if in production environment.
    """
    return env_manager.is_production()


def is_development() -> bool:
    """Check if running in development environment.

    Returns:
        True if in development environment.
    """
    return env_manager.is_development()


def is_testing() -> bool:
    """Check if running in testing environment.

    Returns:
        True if in testing environment.
    """
    return env_manager.is_testing()
