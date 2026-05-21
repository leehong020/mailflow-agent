"""邮件相关 HTTP 接口。

第二阶段只实现 Gmail 最近邮件列表。
第三阶段开始会在这里继续扩展邮件分析、详情页、草稿生成等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email import EmailRecord
from app.schemas.email import (
    AnalyzeEmailsRequest,
    AnalyzeEmailsResponse,
    BatchEmailActionRequest,
    EmailAnalysisInfo,
    EmailDetailResponse,
    EmailListItem,
    EmailListResponse,
    EmailOperationResponse,
    GmailLabelInfo,
    GmailLabelListResponse,
    LabelActionRequest,
    ReanalyzeEmailResponse,
    SyncEmailsRequest,
    SyncEmailsResponse,
    TaskInfo,
)
from app.schemas.draft import CreateDraftPreviewRequest, CreateDraftPreviewResponse
from app.schemas.draft import CreateManualDraftRequest, CreateSendActionResponse
from app.services.draft_service import DraftService
from app.services.email_analysis_service import EmailAnalysisService
from app.services.email_operation_service import EmailOperationService

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=EmailListResponse)
def list_emails(
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    need_reply: bool | None = Query(default=None),
    has_meeting_request: bool | None = Query(default=None),
    has_task: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    analyzed: bool | None = Query(default=None),
    label: str | None = Query(default=None),
    is_read: bool | None = Query(default=None),
    is_starred: bool | None = Query(default=None),
    mailbox_status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EmailListResponse:
    """读取本地邮件列表。

    这个接口是 Inbox 看板的主入口，前端所有列表、筛选、搜索、分页都会
    汇聚到这里。它的设计原则是：

    1. 只读本地 SQLite，不直接打 Gmail API；
    2. 支持分析结果筛选，也支持 Gmail 原始状态筛选；
    3. 统一返回已分析 / 未分析统计，便于前端展示顶部状态条；
    4. 所有异常都转换成 HTTP 状态码，避免前端看到底层 SQLAlchemy 异常。
    """

    try:
        service = EmailAnalysisService(db)
        records, total = service.list_emails(
            category=category,
            priority=priority,
            need_reply=need_reply,
            has_meeting_request=has_meeting_request,
            has_task=has_task,
            search=search,
            analyzed=analyzed,
            label=label,
            is_read=is_read,
            is_starred=is_starred,
            mailbox_status=mailbox_status,
            limit=limit,
            offset=offset,
        )
        analyzed_total, unanalyzed_total = service.analysis_totals()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return EmailListResponse(
        items=[_email_list_item(record) for record in records],
        total=total,
        analyzed_total=analyzed_total,
        unanalyzed_total=unanalyzed_total,
    )


@router.post("/analyze", response_model=AnalyzeEmailsResponse)
def analyze_emails(
    payload: AnalyzeEmailsRequest,
    db: Session = Depends(get_db),
) -> AnalyzeEmailsResponse:
    """同步 Gmail 最近邮件，并只分析本地尚未分析的邮件。"""

    try:
        analyzed_count, trace_ids = EmailAnalysisService(db).analyze_unanalyzed_emails(limit=payload.limit)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AnalyzeEmailsResponse(
        status="completed",
        analyzed_count=analyzed_count,
        message=f"已完成 {analyzed_count} 封邮件的摘要、分类和任务提取。",
        trace_ids=trace_ids,
    )


@router.post("/sync", response_model=SyncEmailsResponse)
def sync_emails(
    payload: SyncEmailsRequest,
    db: Session = Depends(get_db),
) -> SyncEmailsResponse:
    """只同步 Gmail 最近邮件到本地数据库，不触发 Agent 分析。

    Inbox 的“刷新看板”适合调用这个接口：它会让新收到的 Gmail 邮件先进入本地库，
    但不会消耗大模型 token。同步后的新邮件会以“未分析”状态显示，用户需要时再点击
    “同步并分析邮件”统一执行 Email Summarizer / Triage / Task Extraction Agent。
    """

    try:
        records = EmailAnalysisService(db).sync_recent_emails(limit=payload.limit)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return SyncEmailsResponse(
        status="completed",
        synced_count=len(records),
        message=f"已同步 Gmail 最近 {payload.limit} 封邮件，新增 {len(records)} 封。",
    )


@router.get("/labels", response_model=GmailLabelListResponse)
def list_gmail_labels(db: Session = Depends(get_db)) -> GmailLabelListResponse:
    """读取 Gmail 标签列表，供标签修改操作选择。"""

    try:
        labels = EmailOperationService(db).list_labels()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return GmailLabelListResponse(items=[GmailLabelInfo(**item) for item in labels])


@router.post("/{email_id}/mark-read", response_model=EmailOperationResponse)
def mark_email_read(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    return _quick_email_operation(db=db, email_id=email_id, operation="mark_read", message="邮件已标记为已读。")


@router.post("/{email_id}/mark-unread", response_model=EmailOperationResponse)
def mark_email_unread(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    return _quick_email_operation(db=db, email_id=email_id, operation="mark_unread", message="邮件已标记为未读。")


@router.post("/{email_id}/star", response_model=EmailOperationResponse)
def star_email(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    return _quick_email_operation(db=db, email_id=email_id, operation="star", message="邮件已加星标。")


@router.post("/{email_id}/unstar", response_model=EmailOperationResponse)
def unstar_email(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    return _quick_email_operation(db=db, email_id=email_id, operation="unstar", message="邮件已取消星标。")


@router.post("/{email_id}/archive-action", response_model=EmailOperationResponse)
def create_archive_action(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    """创建归档待确认操作。"""

    try:
        action = EmailOperationService(db).create_archive_action(email_id=email_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EmailOperationResponse(status="pending", action_id=action.id, message="已创建归档待确认操作。")


@router.post("/{email_id}/trash-action", response_model=EmailOperationResponse)
def create_trash_action(email_id: str, db: Session = Depends(get_db)) -> EmailOperationResponse:
    """创建移动到垃圾箱待确认操作。"""

    try:
        action = EmailOperationService(db).create_trash_action(email_id=email_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EmailOperationResponse(status="pending", action_id=action.id, message="已创建移动到垃圾箱待确认操作。")


@router.post("/{email_id}/labels-action", response_model=EmailOperationResponse)
def create_labels_action(
    email_id: str,
    payload: LabelActionRequest,
    db: Session = Depends(get_db),
) -> EmailOperationResponse:
    """创建标签修改待确认操作。"""

    try:
        action = EmailOperationService(db).create_labels_action(
            email_id=email_id,
            add_label_ids=payload.add_label_ids,
            remove_label_ids=payload.remove_label_ids,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EmailOperationResponse(status="pending", action_id=action.id, message="已创建标签修改待确认操作。")


@router.post("/batch-action", response_model=EmailOperationResponse)
def create_batch_action(payload: BatchEmailActionRequest, db: Session = Depends(get_db)) -> EmailOperationResponse:
    """创建批量邮件待确认操作。"""

    try:
        action = EmailOperationService(db).create_batch_action(
            email_ids=payload.email_ids,
            operation=payload.operation,
            add_label_ids=payload.add_label_ids,
            remove_label_ids=payload.remove_label_ids,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EmailOperationResponse(status="pending", action_id=action.id, message="已创建批量邮件待确认操作。")


@router.post("/send-action", response_model=CreateSendActionResponse)
def create_direct_send_action(
    payload: CreateManualDraftRequest,
    db: Session = Depends(get_db),
) -> CreateSendActionResponse:
    """直接撰写邮件并创建发送待确认操作。"""

    try:
        action = DraftService(db).create_direct_send_action(
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreateSendActionResponse(
        action_id=action.id,
        status=action.status,
        message="已创建发送邮件待确认操作，请到 Pending Actions 页面确认。",
    )


@router.post("/{email_id}/draft-forward", response_model=CreateDraftPreviewResponse)
def create_forward_draft(email_id: str, db: Session = Depends(get_db)) -> CreateDraftPreviewResponse:
    """根据原邮件创建转发草稿。"""

    try:
        email = EmailAnalysisService(db).get_email_detail(email_id)
        if email is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        preview = DraftService(db).create_forward_preview(email=email)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateDraftPreviewResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        generation_reason=preview.generation_reason,
    )


@router.post("/{email_id}/reanalyze", response_model=ReanalyzeEmailResponse)
def reanalyze_email(email_id: str, db: Session = Depends(get_db)) -> ReanalyzeEmailResponse:
    """手动重新分析单封邮件。"""

    try:
        service = EmailAnalysisService(db)
        record = service.get_email_detail(email_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        service.reanalyze_email(record)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ReanalyzeEmailResponse(status="completed", message="已重新分析当前邮件。")


@router.post("/{email_id}/draft-reply", response_model=CreateDraftPreviewResponse)
def create_draft_reply(
    email_id: str,
    payload: CreateDraftPreviewRequest,
    db: Session = Depends(get_db),
) -> CreateDraftPreviewResponse:
    """开发文档 12.5 的草稿生成 API。

    该接口只生成 draft_preview，不直接创建 Gmail 草稿。
    用户需要进入 Draft Review 页面审核后，再创建 Pending Action。
    """

    try:
        email = EmailAnalysisService(db).get_email_detail(email_id)
        if email is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        preview = DraftService(db).create_draft_preview(email=email, tone=payload.tone, language=payload.language)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CreateDraftPreviewResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        generation_reason=preview.generation_reason,
    )


@router.get("/{email_id}", response_model=EmailDetailResponse)
def get_email_detail(email_id: str, db: Session = Depends(get_db)) -> EmailDetailResponse:
    """邮件详情页：返回原始邮件、Agent 分析结果和任务列表。"""

    try:
        record = EmailAnalysisService(db).get_email_detail(email_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")

    item = _email_list_item(record)
    return EmailDetailResponse(
        **item.model_dump(),
        body_text=record.body_text,
        tasks=[
            TaskInfo(
                id=task.id,
                title=task.title,
                description=task.description,
                deadline=task.deadline,
                priority=task.priority,
                status=task.status,
            )
            for task in record.tasks
        ],
    )


def _quick_email_operation(
    *,
    db: Session,
    email_id: str,
    operation: str,
    message: str,
) -> EmailOperationResponse:
    """执行低风险 Gmail 操作并返回最新本地邮件状态。"""

    try:
        email = EmailOperationService(db).execute_quick_operation(email_id=email_id, operation=operation)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return EmailOperationResponse(status="completed", message=message, email=_email_list_item(email))


def _email_list_item(record: EmailRecord) -> EmailListItem:
    """把 ORM 邮件模型转换为 API 响应。"""

    analysis = None
    if record.analysis:
        analysis = EmailAnalysisInfo(
            summary=record.analysis.summary,
            key_points=record.analysis.key_points,
            category=record.analysis.category,
            priority=record.analysis.priority,
            need_reply=record.analysis.need_reply,
            has_task=record.analysis.has_task,
            has_meeting_request=record.analysis.has_meeting_request,
            reason=record.analysis.reason,
            recommended_actions=record.analysis.recommended_actions,
        )

    return EmailListItem(
        id=record.id,
        thread_id=record.thread_id,
        subject=record.subject,
        sender=record.sender,
        recipients=record.recipients,
        label_ids=record.label_ids or [],
        is_read=record.is_read,
        is_starred=record.is_starred,
        mailbox_status=record.mailbox_status,
        received_at=record.received_at.isoformat() if record.received_at else None,
        snippet=record.snippet,
        body_preview=(record.body_text or record.snippet)[:500] if (record.body_text or record.snippet) else None,
        analysis=analysis,
    )
