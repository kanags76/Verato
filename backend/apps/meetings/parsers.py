import re


def extract_text_from_file(file) -> str:
    """
    Extract plain text from an uploaded transcript or document file.
    Supported: .txt, .vtt (WebVTT), .srt (SubRip), .md, .csv — any UTF-8 text file.
    .docx support requires python-docx (not installed; treat as unsupported for now).
    """
    name = getattr(file, 'name', '').lower()
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')

    if name.endswith('.vtt'):
        return _strip_vtt(content)
    if name.endswith('.srt'):
        return _strip_srt(content)
    return content


_VTT_TS = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}')
_SRT_TS = re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')


def _strip_vtt(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('WEBVTT') or line.startswith('NOTE') or _VTT_TS.search(line):
            continue
        if line.isdigit():
            continue
        lines.append(line)
    return '\n'.join(lines)


def _strip_srt(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.isdigit() or _SRT_TS.match(line):
            continue
        lines.append(line)
    return '\n'.join(lines)
