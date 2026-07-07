from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


database_url = _normalize_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


RLS_STATEMENTS = (
    """
    alter table public.video_jobs enable row level security;
    """,
    """
    alter table public.video_jobs force row level security;
    """,
    """
    drop policy if exists "video_jobs_select_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_select_own" on public.video_jobs
    for select
    to authenticated
    using (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_insert_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_insert_own" on public.video_jobs
    for insert
    to authenticated
    with check (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_update_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_update_own" on public.video_jobs
    for update
    to authenticated
    using (user_id = (select auth.uid())::text)
    with check (user_id = (select auth.uid())::text);
    """,
    """
    drop policy if exists "video_jobs_delete_own" on public.video_jobs;
    """,
    """
    create policy "video_jobs_delete_own" on public.video_jobs
    for delete
    to authenticated
    using (user_id = (select auth.uid())::text);
    """,
    """
    alter table public.video_caption_results enable row level security;
    """,
    """
    alter table public.video_caption_results force row level security;
    """,
    """
    drop policy if exists "video_caption_results_select_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_select_own" on public.video_caption_results
    for select
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_insert_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_insert_own" on public.video_caption_results
    for insert
    to authenticated
    with check (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_update_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_update_own" on public.video_caption_results
    for update
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    )
    with check (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
    """
    drop policy if exists "video_caption_results_delete_own" on public.video_caption_results;
    """,
    """
    create policy "video_caption_results_delete_own" on public.video_caption_results
    for delete
    to authenticated
    using (
      exists (
        select 1
        from public.video_jobs
        where public.video_jobs.id = public.video_caption_results.job_id
          and public.video_jobs.user_id = (select auth.uid())::text
      )
    );
    """,
)


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def apply_row_level_security() -> None:
    if not _is_postgres():
        return

    with engine.begin() as connection:
        for statement in RLS_STATEMENTS:
            connection.execute(text(statement))


def initialize_database() -> None:
    from app.models.job import VideoCaptionResult, VideoJob

    Base.metadata.create_all(bind=engine)
    apply_row_level_security()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
