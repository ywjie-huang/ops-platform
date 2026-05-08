"""通用分页参数。"""
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def paginate_query(stmt, db, page: int = 1, page_size: int = 10):
    """对 SQLAlchemy Select 语句应用分页，返回 (items, total)。"""
    from sqlalchemy import func, select

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # 分页
    offset = (max(page, 1) - 1) * page_size
    items = list(db.scalars(stmt.offset(offset).limit(page_size)).all())

    return items, total
