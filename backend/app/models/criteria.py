import uuid
from sqlalchemy import String, Integer, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class SearchCriteria(Base):
    __tablename__ = "search_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    titles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_salary: Mapped[int] = mapped_column(Integer, default=0)
    exclude_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company_blacklist: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company_whitelist: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    matches: Mapped[list["JobMatch"]] = relationship("JobMatch", back_populates="criteria")
