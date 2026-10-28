"""Atomic copies preserve account/activity identity and reject used targets."""
import uuid
import pytest
from sqlalchemy import func, select
from sqlalchemy.schema import CreateSchema, DropSchema

from app.database_transfer import copy_records
from app.db.base import Base
from app.db.models import AuthSession, Favourite, User
from app.db.session import get_engine
from app.services.accounts import open_login_session
from tests.test_coordination import make_charger, make_user


def test_transfer_preserves_records_excludes_logins_and_refuses_overwrite(db):
    user, charger = make_user(db, "transfer@example.com"), make_charger(db)
    db.add(Favourite(user_id=user.id, charger_id=charger.id))
    open_login_session(db, user)
    db.commit()
    schema = "transfer_check_" + uuid.uuid4().hex
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    target = engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(target)
        counts = copy_records(engine, target)
        assert counts["users"] == counts["chargers"] == counts["favourites"] == 1
        with target.connect() as connection:
            copied = connection.execute(select(User.__table__)).mappings().one()
            assert copied["id"] == user.id and copied["password_hash"] == user.password_hash
            assert connection.scalar(select(func.count()).select_from(AuthSession)) == 0
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 1
        with pytest.raises(ValueError, match="Destination contains"):
            copy_records(engine, target)
        assert db.get(User, user.id).email == "transfer@example.com"
        with target.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(User)) == 1
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
