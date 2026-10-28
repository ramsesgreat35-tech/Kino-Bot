import asyncio
import ipaddress
import socket
from urllib.parse import urlparse, urljoin

import aiohttp

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # безопасно для серверов без буста
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CinemaBot/1.0)"}
_REDIRECTS = (301, 302, 303, 307, 308)


def sniff_ext(head: bytes) -> str | None:
    """Определяем реальный формат по первым байтам, а не по ссылке."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


async def _is_public_host(host: str) -> bool:
    """Не даём боту ходить во внутреннюю сеть хостинга."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            return False
    return True


async def fetch_image(url: str) -> tuple[tuple[bytes, str] | None, str | None]:
    """
    Скачивает картинку по ссылке.
    Возвращает ((байты, расширение), None) при успехе или (None, причина) при ошибке.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout, headers=_HEADERS) as session:
            for _ in range(4):
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    return None, "некорректная ссылка"
                if not await _is_public_host(parsed.hostname):
                    return None, "ссылка недоступна"

                async with session.get(url, allow_redirects=False) as resp:
                    if resp.status in _REDIRECTS and resp.headers.get("Location"):
                        url = urljoin(url, resp.headers["Location"])
                        continue
                    if resp.status != 200:
                        return None, f"сервер ответил кодом {resp.status}"
                    if resp.content_length and resp.content_length > MAX_IMAGE_BYTES:
                        return None, "файл больше 8 МБ"

                    data = bytearray()
                    async for chunk in resp.content.iter_chunked(65536):
                        data += chunk
                        if len(data) > MAX_IMAGE_BYTES:
                            return None, "файл больше 8 МБ"

                    ext = sniff_ext(bytes(data[:16]))
                    if not ext:
                        return None, "ссылка ведёт не на картинку (нужна прямая ссылка на png/jpg/webp/gif)"
                    return (bytes(data), ext), None
            return None, "слишком много перенаправлений"
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None, "не удалось скачать картинку"
