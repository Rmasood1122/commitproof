"""Receipt signatures — the ONE place they are made and checked.

  hmac-sha256-v1  HMAC-SHA256 over receipt_hash under the shared .titan/key.
                  Anyone holding the key can make one; a clone without the
                  key can't check one.
  ssh-sig-v1      `ssh-keygen -Y sign` over receipt_hash in the
                  commitproof-receipt namespace, by the committer's own SSH
                  key; checked with `ssh-keygen -Y verify` against the public
                  keys in .titan/allowed_signers. It identifies the key that
                  signed, and needs no secret to check.

The namespace keeps a receipt signature from being replayed as a git commit
signature (namespace "git") or the other way round. An unknown
signing_version is invalid, never skipped.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HMAC_V1 = "hmac-sha256-v1"
SSH_V1 = "ssh-sig-v1"
NAMESPACE = "commitproof-receipt"
TIMEOUT_S = 20      # a passphrase prompt with no terminal must fail, not hang a hook


class SigningError(Exception):
    """A receipt could not be signed, or a key could not be read."""


def keygen() -> str | None:
    return shutil.which("ssh-keygen")


def _keygen(args: list[str], data: bytes | None = None) -> subprocess.CompletedProcess:
    kg = keygen()
    if kg is None:
        raise SigningError("ssh-keygen not found on PATH (OpenSSH 8.2+ needed)")
    try:
        return subprocess.run([kg, *args], input=data, capture_output=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise SigningError("ssh-keygen timed out — is it waiting for a passphrase? "
                           "Load the key with ssh-add") from None


def _last_line(raw: bytes) -> str:
    lines = raw.decode(errors="replace").strip().splitlines()
    return lines[-1] if lines else "no output"


def public_key(key: Path) -> str:
    """'TYPE BASE64' for a private key path (its .pub beside it, or derived)
    or a .pub path."""
    key = Path(key)
    pub = key if key.suffix == ".pub" else Path(f"{key}.pub")
    if pub.is_file():
        parts = pub.read_text(encoding="utf-8").split()
    elif key.is_file():
        r = _keygen(["-y", "-f", str(key)])
        if r.returncode != 0:
            raise SigningError(f"can't read the public half of {key}: {_last_line(r.stderr)}")
        parts = r.stdout.decode().split()
    else:
        raise SigningError(f"no SSH key at {key}")
    if len(parts) < 2 or not re.match(r"(ssh|ecdsa|sk)-", parts[0]):
        raise SigningError(f"{pub} is not an SSH public key")
    return f"{parts[0]} {parts[1]}"


def fingerprint(pub: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "key.pub"
        f.write_text(pub + "\n", encoding="utf-8")
        r = _keygen(["-l", "-E", "sha256", "-f", str(f)])
    if r.returncode != 0:
        raise SigningError(f"can't fingerprint key: {_last_line(r.stderr)}")
    return r.stdout.decode().split()[1]


def ssh_sign(key: Path, message: bytes) -> str:
    """Armored SSH signature over `message`. `key` is a private key, or a .pub
    whose private half is beside it or loaded in ssh-agent."""
    key = Path(key)
    if not key.is_file():
        raise SigningError(f"no SSH key at {key}")
    r = _keygen(["-Y", "sign", "-n", NAMESPACE, "-f", str(key)], message)
    sig = r.stdout.decode("ascii", "replace").replace("\r\n", "\n")
    if r.returncode != 0 or "-----BEGIN SSH SIGNATURE-----" not in sig:
        raise SigningError(f"ssh-keygen could not sign with {key}: {_last_line(r.stderr)}")
    return sig


def hmac_sign(key: bytes, message: bytes) -> str:
    return hmac.new(key, message, hashlib.sha256).hexdigest()


class SshVerifier:
    """Checks ssh-sig-v1 signatures against one allowed_signers file. Works
    on an LF-normalized copy: an autocrlf checkout of the committed file
    must verify the same as the original."""

    def __init__(self, allowed: Path | None):
        self._dir = tempfile.TemporaryDirectory()
        self.allowed = allowed
        self.reason = ""
        if keygen() is None:
            self.reason = "ssh-keygen not found on PATH"
        elif allowed is None or not Path(allowed).is_file():
            self.reason = f"no allowed_signers file at {allowed}"
        else:
            text = Path(allowed).read_bytes().replace(b"\r\n", b"\n")
            self._allowed = Path(self._dir.name) / "allowed_signers"
            self._allowed.write_bytes(text)

    @property
    def available(self) -> bool:
        return not self.reason

    def verify(self, principal: str, key_fp: str, message: bytes, signature: str) -> bool:
        if not principal or not signature:
            return False
        sig = Path(self._dir.name) / "sig"
        sig.write_text(signature, encoding="ascii", errors="replace", newline="\n")
        r = _keygen(["-Y", "verify", "-f", str(self._allowed), "-I", principal,
                     "-n", NAMESPACE, "-s", str(sig)], message)
        out = (r.stdout + r.stderr).decode(errors="replace")
        # the key that actually verified must be the one the receipt names
        return r.returncode == 0 and f"key {key_fp}" in out

    def __enter__(self) -> "SshVerifier":
        return self

    def __exit__(self, *exc) -> None:
        self._dir.cleanup()


def check(receipt: dict, hmac_key: bytes | None, ssh: SshVerifier | None) -> tuple[str, str]:
    """('valid' | 'invalid' | 'unchecked', detail) for one receipt's signature.
    detail: the SSH principal, 'hmac', or why it could not be checked."""
    version = receipt.get("signing_version", HMAC_V1)
    message = str(receipt.get("receipt_hash", "")).encode()
    signature = str(receipt.get("signature", ""))
    if version == HMAC_V1:
        if hmac_key is None:
            return "unchecked", "no .titan/key"
        ok = hmac.compare_digest(hmac_sign(hmac_key, message), signature)
        return ("valid" if ok else "invalid"), "hmac"
    if version == SSH_V1:
        if ssh is None or not ssh.available:
            return "unchecked", ssh.reason if ssh else "SSH not checked"
        signer = receipt.get("signer") or {}
        principal = str(signer.get("principal", ""))
        ok = ssh.verify(principal, str(signer.get("key", "")), message, signature)
        return ("valid" if ok else "invalid"), principal
    return "invalid", f"unknown signing_version {version!r}"
