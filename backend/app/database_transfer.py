"""Copy app records into an empty destination; never alter the source."""
from sqlalchemy import func, select, text
from app.db.base import Base
from app.db import models  # noqa: F401

SKIP = {"auth_sessions", "login_attempts"}


def copy_records(source_engine, target_engine) -> dict[str, int]:
    tables = list(Base.metadata.sorted_tables)
    counts = {}
    with source_engine.connect().execution_options(isolation_level="REPEATABLE READ") as source:
        with source.begin(), target_engine.begin() as target:
            source.execute(text("SET TRANSACTION READ ONLY"))
            if any(target.scalar(select(func.count()).select_from(table)) for table in tables):
                raise ValueError("Destination contains app records. Nothing was copied or deleted.")
            for table in tables:
                if table.name in SKIP:
                    continue
                rows = source.execute(select(table)).mappings()
                count = 0
                while batch := rows.fetchmany(500):
                    target.execute(table.insert(), [dict(row) for row in batch])
                    count += len(batch)
                if target.scalar(select(func.count()).select_from(table)) != count:
                    raise RuntimeError("Transfer count mismatch; transaction rolled back.")
                counts[table.name] = count
    return counts
