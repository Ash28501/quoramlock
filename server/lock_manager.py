"""
Core lock management logic for QuorumLock.
 
This module has no networking and no Raft yet -- just the pure semantics of:
  - granting a lock with a lease (TTL)
  - rejecting a grant if the lock is already held and not expired
  - issuing a strictly increasing fencing token on every successful grant
  - renewing a lease
  - releasing a lock
  - lazily expiring locks whose lease has lapsed
 
Keeping this logic isolated (no gRPC, no Raft) makes it easy to unit test
in the next step, and easy to reason about correctness before we add the
complexity of networking and consensus on top of it.
"""
 
from dataclasses import dataclass
import threading
import time
 
 
@dataclass
class LockState:
    holder: str
    fencing_token: int
    expires_at: float
 
 
class LockManager:
    def __init__(self):
        # resource_id -> LockState
        self._locks: dict[str, LockState] = {}
        # Global, strictly-increasing counter. Every successful acquire
        # (even for different resources) gets a higher token than the
        # last one. This is simpler than a per-resource counter and is
        # still a valid fencing token: downstream systems just need
        # "did I see a higher token than this before?" to hold true.
        self._next_token = 1
        # Protects both _locks and _next_token from concurrent access.
        # We'll be calling this from multiple gRPC request handlers at
        # once later, so this isn't optional.
        self._lock = threading.Lock()
 
    def acquire(self, resource_id: str, client_id: str, ttl_seconds: float) -> tuple[bool, int | None, str | None]:
        """
        Attempt to acquire `resource_id` for `client_id`.
 
        Returns (granted, fencing_token, error_message).
        - granted=True  -> fencing_token is set, error_message is None
        - granted=False -> fencing_token is None, error_message explains why
        """
        with self._lock:
            now = time.monotonic()
            existing = self._locks.get(resource_id)
 
            if existing is not None and existing.expires_at > now:
                # Someone else holds it, and their lease hasn't expired yet.
                if existing.holder == client_id:
                    # Same client re-acquiring -- treat as idempotent success,
                    # but do NOT hand out a new token; the one they have is
                    # still valid until it expires.
                    return True, existing.fencing_token, None
                return False, None, f"resource held by {existing.holder} until lease expires"
 
            # Either nobody holds it, or the previous holder's lease expired
            # (we lazily reclaim it right here rather than needing a
            # background sweep thread for correctness).
            token = self._next_token
            self._next_token += 1
 
            self._locks[resource_id] = LockState(
                holder=client_id,
                fencing_token=token,
                expires_at=now + ttl_seconds,
            )
            return True, token, None
 
    def renew(self, resource_id: str, client_id: str, ttl_seconds: float) -> tuple[bool, str | None]:
        """Extend the lease on a lock the client currently holds."""
        with self._lock:
            existing = self._locks.get(resource_id)
            now = time.monotonic()
 
            if existing is None or existing.expires_at <= now:
                return False, "lock not held (expired or never acquired)"
            if existing.holder != client_id:
                return False, f"lock held by a different client ({existing.holder})"
 
            existing.expires_at = now + ttl_seconds
            return True, None
 
    def release(self, resource_id: str, client_id: str) -> tuple[bool, str | None]:
        """Voluntarily release a lock before its lease expires."""
        with self._lock:
            existing = self._locks.get(resource_id)
 
            if existing is None:
                return False, "lock not held"
            if existing.holder != client_id:
                return False, f"lock held by a different client ({existing.holder})"
 
            del self._locks[resource_id]
            return True, None
 
    def status(self, resource_id: str) -> LockState | None:
        """Read-only check of a lock's current state (None if free)."""
        with self._lock:
            existing = self._locks.get(resource_id)
            if existing is None or existing.expires_at <= time.monotonic():
                return None
            return existing
 