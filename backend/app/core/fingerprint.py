import hashlib
import os
from pathlib import Path


def file_fingerprint_md5(path: str, include_inode: bool = True, sample_bytes: int = 0) -> str:
    """
    Compute a deterministic MD5 fingerprint for a file based on normalized path
    and stable metadata to avoid reading entire large files.

    Components used:
    - realpath (absolute, resolved)
    - size (bytes)
    - mtime (nanoseconds when available)
    - inode and birth/ctime when available
    - optional light content sample (first/last N bytes)
    """
    # Browser-native virtual datasets have no filesystem metadata.
    # Fingerprint deterministically from the virtual path itself.
    if isinstance(path, str) and path.startswith("browser://"):
        h = hashlib.md5()
        h.update(f"virtual|{path}".encode("utf-8"))
        return h.hexdigest()

    p = Path(path)
    st = p.stat()

    parts: list[str] = []

    # Normalize path to avoid different spellings of same file
    parts.append(os.path.realpath(str(p)))

    # Core metadata
    parts.append(str(st.st_size))
    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
    parts.append(str(mtime_ns))

    # Optional: inode/birth/ctime if available
    if include_inode and hasattr(st, "st_ino"):
        parts.append(str(st.st_ino))

    # macOS has st_birthtime; on Linux st_ctime is metadata change time
    birth = getattr(st, "st_birthtime", None)
    if birth is not None:
        parts.append(str(int(birth * 1e9)))
    else:
        parts.append(str(getattr(st, "st_ctime_ns", int(st.st_ctime * 1e9))))

    # Optional: lightweight content sample for extra confidence
    if sample_bytes > 0 and st.st_size > 0:
        with open(p, "rb") as f:
            head = f.read(min(sample_bytes, st.st_size))
            tail = b""
            if st.st_size > sample_bytes:
                f.seek(max(0, st.st_size - sample_bytes))
                tail = f.read(sample_bytes)
        parts.append(hashlib.md5(head + tail).hexdigest())

    h = hashlib.md5()
    h.update("|".join(parts).encode("utf-8"))
    return h.hexdigest()
