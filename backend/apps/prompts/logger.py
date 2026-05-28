"""
Single entry point for all Gemini calls.
Owns the HTTP call, measures duration, and writes an AICallLog row.
Import this instead of calling _call_gemini or generate_content directly.
"""
import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)


def call_gemini(
    prompt_text: str,
    prompt_name: str,
    *,
    organisation=None,
    meeting_id=None,
    commitment_id=None,
    tag_id=None,
    triggered_by=None,
) -> str | None:
    """
    Call Gemini and log the result to AICallLog.

    Returns the raw text response, or None on failure.
    Never raises — failures are logged and None is returned.
    """
    from google import genai
    from apps.prompts.models import Prompt, AICallLog

    # Resolve prompt version (0 if not in DB)
    prompt_version = 0
    try:
        prompt_version = Prompt.objects.get(name=prompt_name).version
    except Prompt.DoesNotExist:
        pass
    except Exception:
        pass

    output_text = ''
    error = ''
    success = False
    start = time.monotonic()

    try:
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if api_key:
            client = genai.Client(api_key=api_key)
        else:
            client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )
        response = client.models.generate_content(
            model=settings.GEMINI_EXTRACTION_MODEL,
            contents=prompt_text,
        )
        output_text = response.text or ''
        success = bool(output_text)
        if not success:
            error = 'Gemini returned empty response'
    except Exception as exc:
        error = str(exc)
        logger.error("call_gemini [%s] failed: %s", prompt_name, exc)

    duration_ms = int((time.monotonic() - start) * 1000)

    try:
        AICallLog.objects.create(
            organisation=organisation,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            input_text=prompt_text,
            output_text=output_text,
            duration_ms=duration_ms,
            success=success,
            error=error,
            meeting_id=meeting_id,
            commitment_id=commitment_id,
            tag_id=tag_id,
            triggered_by=triggered_by,
        )
    except Exception as log_exc:
        logger.error("AICallLog write failed: %s", log_exc)

    return output_text if success else None
