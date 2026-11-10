#!/usr/bin/env python3
"""Check/provision HML runtime ACLs without replacing ownership or file data."""
import argparse
import errno
import json
import os
import stat
import struct

ACCESS = "system.posix_acl_access"
DEFAULT = "system.posix_acl_default"
UNDEFINED = 0xFFFFFFFF
# Passes allowed when the filesystem changes between planning and applying.
ATTEMPTS = 3


class ConcurrentChange(RuntimeError):
    """The filesystem changed after planning; a fresh plan may still succeed."""


def read_acl(fd, key):
    try:
        return os.getxattr(fd, key)
    except OSError as exc:
        if exc.errno != errno.ENODATA:
            raise
        return None


def entries(raw, mode):
    if raw is None:
        return [
            (1, (mode >> 6) & 7, UNDEFINED),
            (4, (mode >> 3) & 7, UNDEFINED),
            (32, mode & 7, UNDEFINED),
        ]
    if raw[:4] != struct.pack("<I", 2) or (len(raw) - 4) % 8:
        raise ValueError("Unsupported ACL encoding")
    return [struct.unpack("<HHI", raw[i : i + 8]) for i in range(4, len(raw), 8)]


def grant(raw, mode, uid, permissions, *, owner_uid=None):
    current = entries(raw, mode)
    mask = next(
        (p for tag, p, _ in current if tag == 16),
        next(p for tag, p, _ in current if tag == 4),
    )
    updated = []
    for tag, perm, identity in current:
        if tag == 16 or (tag == 2 and identity == uid):
            continue
        if tag == 1 and owner_uid == uid:
            perm |= permissions
        if tag in (2, 4, 8):
            perm &= mask
        updated.append((tag, perm, identity))
    updated += [(2, permissions, uid), (16, mask | permissions, UNDEFINED)]
    return struct.pack("<I", 2) + b"".join(
        struct.pack("<HHI", *entry)
        for entry in sorted(updated, key=lambda e: (e[0], e[2]))
    )


def walk(roots):
    for root in roots:
        if os.path.islink(root):
            raise ValueError("A symlink root is not allowed")
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for path, _, files, directory_fd in os.fwalk(
                ".", dir_fd=root_fd, follow_symlinks=False
            ):
                yield root, path, directory_fd
                for name in files:
                    info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode):
                        continue
                    fd = os.open(
                        name,
                        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        dir_fd=directory_fd,
                    )
                    try:
                        if stat.S_ISREG(os.fstat(fd).st_mode):
                            yield root, os.path.join(path, name), fd
                    finally:
                        os.close(fd)
        finally:
            os.close(root_fd)


def plan(roots, uid):
    changes = {}
    seen = set()
    for root, path, fd in walk(roots):
        info = os.fstat(fd)
        # Hard links share one inode and ACL: plan each inode once, or the
        # second path would see the ACL applied through the first one.
        if (info.st_dev, info.st_ino) in seen:
            continue
        seen.add((info.st_dev, info.st_ino))
        mode = stat.S_IMODE(info.st_mode)
        before = {ACCESS: read_acl(fd, ACCESS)}
        after = {
            ACCESS: grant(
                before[ACCESS],
                mode,
                uid,
                7 if stat.S_ISDIR(info.st_mode) else 6,
                owner_uid=info.st_uid,
            )
        }
        if stat.S_ISDIR(info.st_mode):
            before[DEFAULT] = read_acl(fd, DEFAULT)
            # A new default grants only creator/application access. Inheriting
            # directory group/other bits would bypass restrictive writer umasks.
            after[DEFAULT] = grant(before[DEFAULT], 0o700, uid, 7)
        if before != after:
            changes[(root, path)] = {
                "root": root,
                "path": path,
                "device": info.st_dev,
                "inode": info.st_ino,
                "mode": mode,
                "uid": info.st_uid,
                "gid": info.st_gid,
                "before": {
                    k: None if v is None else v.hex() for k, v in before.items()
                },
                "after": {k: v.hex() for k, v in after.items()},
            }
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", action="append", help="Mounted data root; repeat as needed"
    )
    parser.add_argument(
        "--uid", type=int, default=10001, help="Dedicated non-root application UID"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply ACLs; default is read-only check"
    )
    parser.add_argument(
        "--backup", help="New private backup file, required with --apply"
    )
    args = parser.parse_args()
    if args.uid <= 0:
        parser.error("A non-root UID is required")
    if args.apply and (not args.backup or os.geteuid() != 0):
        parser.error("--apply requires a root provisioner and --backup")
    roots = [
        os.path.abspath(p)
        for p in (args.root or ["/sisoc/media", "/sisoc/logs", "/beat"])
    ]
    changes = plan(roots, args.uid)
    pending = len(changes)
    applied = []
    attempts = 0
    if args.apply:
        while True:
            attempts += 1
            backup = args.backup if attempts == 1 else f"{args.backup}.{attempts}"
            try:
                apply(roots, args.uid, changes, backup, applied)
                break
            except ConcurrentChange:
                # Never retry a stale plan: plan again from the current state,
                # with its own backup. A change that persists still fails.
                if attempts == ATTEMPTS:
                    raise
                changes = plan(roots, args.uid)
    # Count every inode written, including partial passes before a retry.
    print(
        json.dumps(
            {"pending": pending, "applied": len(set(applied)), "attempts": attempts}
        )
    )
    return 0 if args.apply or pending == 0 else 1


def apply(roots, uid, changes, backup, applied):
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"roots": roots, "entries": list(changes.values())}, handle)
        handle.flush()
        os.fsync(handle.fileno())
    for root, path, fd in walk(roots):
        change = changes.get((root, path))
        if change is None:
            continue
        info = os.fstat(fd)
        if (
            info.st_dev,
            info.st_ino,
            info.st_uid,
            info.st_gid,
            stat.S_IMODE(info.st_mode),
        ) != (
            change["device"],
            change["inode"],
            change["uid"],
            change["gid"],
            change["mode"],
        ):
            raise ConcurrentChange("Filesystem identity changed; backup retained")
        for key, original in change["before"].items():
            raw = read_acl(fd, key)
            if raw != (None if original is None else bytes.fromhex(original)):
                raise ConcurrentChange("ACL changed concurrently; backup retained")
        for key, desired in change["after"].items():
            os.setxattr(fd, key, bytes.fromhex(desired))
        applied.append((change["device"], change["inode"]))
    if plan(roots, uid):
        raise ConcurrentChange("Permission provisioning incomplete; backup retained")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        # Never emit document names from filesystem exceptions. ValueError and
        # RuntimeError carry only the fixed messages raised in this script.
        print(
            json.dumps(
                {
                    "error": (
                        "RuntimeError"
                        if isinstance(error, RuntimeError)
                        else type(error).__name__
                    ),
                    "detail": (
                        error.strerror if isinstance(error, OSError) else str(error)
                    ),
                }
            )
        )
        raise SystemExit(2) from None
