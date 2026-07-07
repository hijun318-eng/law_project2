"""LLM-005: OpenAI 호출 실패를 상태코드별로 구분해 사용자 안내 메시지로 변환."""
import openai

_MESSAGES = {
    401: "AI 서비스 인증에 실패했습니다. 잠시 후 다시 시도하거나 관리자에게 문의해주세요.",
    429: "요청이 많아 AI 서비스가 지연되고 있습니다. 잠시 후 다시 시도해주세요.",
}
_TIMEOUT_MESSAGE = "AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
_CONNECTION_MESSAGE = "AI 서비스에 연결할 수 없습니다. 네트워크 상태를 확인 후 다시 시도해주세요."
_SERVER_ERROR_MESSAGE = "AI 서비스에 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
_DEFAULT_MESSAGE = "답변을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


def llm_error_message(exc: Exception) -> str:
    """예외를 401/429/5xx/타임아웃/연결오류로 구분해 한국어 안내 메시지를 반환."""
    if isinstance(exc, openai.APITimeoutError):
        return _TIMEOUT_MESSAGE
    if isinstance(exc, openai.APIConnectionError):
        return _CONNECTION_MESSAGE
    if isinstance(exc, openai.APIStatusError):
        if exc.status_code in _MESSAGES:
            return _MESSAGES[exc.status_code]
        if exc.status_code >= 500:
            return _SERVER_ERROR_MESSAGE
    return _DEFAULT_MESSAGE
