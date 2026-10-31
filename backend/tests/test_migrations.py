import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _run_isolated(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout + result.stderr


def test_clean_alembic_upgrade_create_tables_and_seed(tmp_path):
    database_path = tmp_path / "clean-migration.sqlite"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "SEED_ADMIN_PASSWORD": "MigrationTestAdmin123!",
            "SEED_CUSTOMER_PASSWORD": "MigrationTestCustomer123!",
        }
    )

    _run_isolated([sys.executable, "-m", "alembic", "upgrade", "head"], env)

    _run_isolated(
        [
            sys.executable,
            "-c",
            (
                "from app.database import engine; "
                "from create_tables import ensure_schema; "
                "ensure_schema(engine)"
            ),
        ],
        env,
    )
    output = _run_isolated(
        [
            sys.executable,
            "-c",
            (
                "from sqlalchemy import func,select; "
                "from sqlalchemy.orm import sessionmaker; "
                "from app.database import engine; "
                "from app.models import Customer,Product,Order,SupportTicket; "
                "from seed_data import seed_data; "
                "seed_data(engine,sessionmaker(bind=engine)); "
                "s=sessionmaker(bind=engine)(); "
                "print('counts', "
                "s.scalar(select(func.count()).select_from(Customer).where(Customer.role=='admin')), "
                "s.scalar(select(func.count()).select_from(Customer).where(Customer.role=='customer')), "
                "s.scalar(select(func.count()).select_from(Product)), "
                "s.scalar(select(func.count()).select_from(Order)), "
                "s.scalar(select(func.count()).select_from(SupportTicket))); "
                "assert s.scalar(select(func.count()).select_from(Customer).where(Customer.role=='admin'))==2; "
                "assert s.scalar(select(func.count()).select_from(Customer).where(Customer.role=='customer'))>=10; "
                "assert s.scalar(select(func.count()).select_from(Product))>=30; "
                "assert s.scalar(select(func.count()).select_from(Order))>=10; "
                "assert s.scalar(select(func.count()).select_from(SupportTicket))>=1; "
                "s.close()"
            ),
        ],
        env,
    )
    assert "counts 2 12 30 12 5" in output

    drift = _run_isolated(
        [sys.executable, "-m", "alembic", "check"],
        env,
    )
    assert "No new upgrade operations detected" in drift
