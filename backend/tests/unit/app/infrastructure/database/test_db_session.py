from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.infrastructure.database.session import Base, SessionLocal, engine, get_db


def test_session_local_creation():
    """Test that SessionLocal is properly configured."""
    assert SessionLocal is not None
    # SessionLocal is a sessionmaker instance, not a session instance
    # So it doesn't have a 'bind' attribute directly
    # We can check that it's properly configured by checking its type
    from sqlalchemy.orm import sessionmaker

    assert isinstance(SessionLocal, sessionmaker)


def test_base_declarative_base():
    """Test that Base is properly configured."""
    assert Base is not None
    assert hasattr(Base, "metadata")


def test_engine_configuration():
    """Test that engine is properly configured."""
    assert engine is not None
    assert hasattr(engine, "url")
    # Check that it's configured for PostgreSQL
    assert "postgresql" in str(engine.url).lower()


@patch("app.infrastructure.database.session.SessionLocal")
def test_get_db_generator(mock_session_local):
    """Test that get_db is a generator function that yields a session."""
    mock_session = MagicMock(spec=Session)
    mock_session_local.return_value = mock_session

    # Get the generator
    db_generator = get_db()

    # Get the first yielded value
    db = next(db_generator)

    # Verify it's the mock session
    assert db == mock_session

    # Verify session was created
    mock_session_local.assert_called_once()


@patch("app.infrastructure.database.session.SessionLocal")
def test_get_db_session_cleanup(mock_session_local):
    """Test that get_db properly closes the session."""
    mock_session = MagicMock(spec=Session)
    mock_session_local.return_value = mock_session

    # Get the generator
    db_generator = get_db()

    # Get the first yielded value
    next(db_generator)

    # Simulate the generator being closed (this would happen in FastAPI)
    try:
        # This would normally be handled by FastAPI's dependency injection
        pass
    finally:
        # Simulate the finally block
        db_generator.close()

    # Verify session close was called
    mock_session.close.assert_called_once()


def test_get_db_is_generator():
    """Test that get_db returns a generator."""
    db_generator = get_db()

    # Check that it's a generator
    assert hasattr(db_generator, "__iter__")
    assert hasattr(db_generator, "__next__")


def test_session_local_autocommit_setting():
    """Test that SessionLocal has correct autocommit and autoflush settings."""
    # These settings are important for database transaction management
    assert SessionLocal.kw["autocommit"] is False
    assert SessionLocal.kw["autoflush"] is False
