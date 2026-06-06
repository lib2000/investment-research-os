import io
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from research_os.export_utils import build_simple_xlsx, collect_result_export_sheets
from research_os.security import verify_user_token


router = APIRouter(prefix="/api/v1/export", tags=["export"])


def current_storage_timestamp() -> str:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))

    return datetime.now(korea_timezone).isoformat(timespec="seconds")


@router.post("/result-xlsx", dependencies=[Depends(verify_user_token)])
def export_result_xlsx(payload: dict = Body(...)) -> StreamingResponse:
    result_text = str(payload.get("result_text") or "").strip()
    if not result_text or result_text == "대기 중입니다.":
        raise HTTPException(status_code=422, detail="엑셀로 변환할 화면 결과가 없습니다.")

    workbook_bytes = build_simple_xlsx(
        collect_result_export_sheets(payload, generated_at_fallback=current_storage_timestamp())
    )
    timestamp = current_storage_timestamp().replace(":", "").replace("-", "")[:15]
    filename = f"research-os-result-{timestamp}.xlsx"
    return StreamingResponse(
        io.BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
