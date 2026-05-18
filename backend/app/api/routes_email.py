"""邮件相关 HTTP 接口。

第二阶段只实现 Gmail 最近邮件列表。
第三阶段开始会在这里继续扩展邮件分析、详情页、草稿生成等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email import EmailListResponse
from app.services.google_service import GoogleService

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=EmailListResponse)
def list_emails(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> EmailListResponse:
    """读取 Gmail Inbox 最近邮件。"""

    try:
        # 真正的 Gmail API 调用放在 GoogleService / GmailTool 中，
        # 路由层只负责处理 HTTP 参数和异常转换。
        items = GoogleService(db).list_recent_emails(limit=limit)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return EmailListResponse(items=items, total=len(items))
