"""Which rule pack is in force for a jurisdiction on a pay date — and why not.

This is the gate the payroll lane promised: a pay run is calculated only from
a rule pack that is ``verified`` and whose effective period covers the pay
date. Everything else is refused, and the refusal says what was found and
what has to happen before the run can be calculated.

Why the refusal has to name the state it found
----------------------------------------------
``contracts/errors.md`` §3.1 publishes one code for this — ``rule_pack_not_verified`` —
with the details ``{jurisdiction, pay_date, pack_status, missing}``. The
operator who has to fix it needs to know *which* of four situations they are
in, because the remedy differs:

``absent``
    No pack covers the jurisdiction, or none covers the pay date. An
    administrator has to install one and a named human has to verify it.
``draft``
    A pack exists and covers the pay date, but it is still being written. It
    cannot be used: nobody has checked it.
``pending_verification``
    A pack exists and covers the pay date and is waiting for a human to
    check it. The remedy is a decision, not an installation.
``superseded``
    The pack that applied to this jurisdiction has stopped applying. The
    remedy is a pack that covers this pay date.

The pack's *contents* never appear in the refusal. A rate, a threshold or an
entitlement is not the operator's problem and must not leak through an error
message; the pack's identity and its state are.

Where the packs come from
-------------------------
The directory named by the ``RULE_PACK_DIR`` environment variable, or the
``rule_packs/`` directory the product ships with. The environment variable
is read on every call, not at import time, so a deployment (or a test) can
point at a different directory without restarting the process. The setting
is read here rather than from ``app.core.config`` because that module belongs
to another lane; it is a deployment concern, not an application setting.

No statutory value lives in this module. It reads packs; it never decides
what is in one.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from app.core.observability import get_logger
from app.rules.loader import RulePack, RulePackLoadError, load_rule_pack

log = get_logger("librepeople.rules.resolver")

#: The environment variable that names the rule-pack directory.
PACK_DIR_ENV = "RULE_PACK_DIR"

#: The rule-pack directory the product ships with.
DEFAULT_PACK_DIR = Path(__file__).resolve().parents[3] / "rule_packs"

# Fallback candidates for container layouts where the repo root is not parents[3].
# Keep DEFAULT_PACK_DIR first so local dev (parents[3] == repo root) still wins.
_FALLBACK_PACK_DIRS: list[Path] = [
    Path("/app/rule_packs"),
    Path(__file__).resolve().parents[2] / "rule_packs",
]

#: The pack state a refusal reports when nothing covers the jurisdiction.
STATUS_ABSENT = "absent"
#: The pack state a refusal reports when the pack is still being written.
STATUS_DRAFT = "draft"
#: The pack state a refusal reports when the pack is waiting for a human.
STATUS_PENDING_VERIFICATION = "pending_verification"
#: The pack state a refusal reports when the pack has stopped applying.
STATUS_SUPERSEDED = "superseded"
#: The pack state that means the pack may be used.
STATUS_VERIFIED = "verified"


def pack_directory() -> Path:
    """The directory the rule packs are read from.

    ``RULE_PACK_DIR`` wins when it is set to something; otherwise the
    ``rule_packs/`` directory beside the repository root is used.

    Inside the Docker image ``parents[3]/rule_packs`` resolves to ``/rule_packs``
    (empty) because the context is ``./backend`` and the image's ``WORKDIR`` is
    ``/app``. So after the primary candidates, fall back to ``/app/rule_packs``
    and ``backend/rule_packs`` and return the first that exists.
    """
    configured = os.environ.get(PACK_DIR_ENV, "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(DEFAULT_PACK_DIR)
    candidates.extend(_FALLBACK_PACK_DIRS)

    for cand in candidates:
        if cand.is_dir():
            log.debug("using rule pack dir", chosen=str(cand))
            return cand

    # Nothing exists — return the most explicit choice so the caller can
    # report pack_status=absent with a useful path.
    chosen = candidates[0] if candidates else DEFAULT_PACK_DIR
    log.debug("no rule pack dir found, returning fallback", chosen=str(chosen))
    return chosen


@dataclass(frozen=True)
class PackLoadFailure:
    """A pack file in the directory that could not be loaded.

    The file is named and the reason is kept, but nothing from the file's
    contents is reported: a pack that does not validate cannot be trusted to
    describe itself either.
    """

    path: Path
    reason: str
    jurisdiction: Optional[str]


@dataclass(frozen=True)
class RulePackResolution:
    """The outcome of resolving the rule pack for a jurisdiction and a date.

    ``pack`` is ``None`` when the run must be refused. ``pack_status`` then
    says what was found, and ``missing`` says what has to be done about it.
    """

    jurisdiction: str
    pay_date: date
    pack: Optional[RulePack]
    pack_status: str
    missing: tuple[str, ...]
    pack_dir: Path
    failures: tuple[PackLoadFailure, ...] = ()

    @property
    def is_verified(self) -> bool:
        """Whether a verified pack in force was found."""
        return self.pack is not None and self.pack.is_verified()

    def details(self) -> dict:
        """The ``details`` of the ``rule_pack_not_verified`` envelope.

        The shape is the one published in ``contracts/errors.md`` §3.1:
        ``{jurisdiction, pay_date, pack_status, required}``. The
        ``required`` list is the published one — the checks that have to be
        satisfied before the operation can proceed.
        """
        return {
            "jurisdiction": self.jurisdiction,
            "pay_date": self.pay_date.isoformat(),
            "pack_status": self.pack_status,
            "required": list(self.missing),
        }


def _read_jurisdiction(path: Path) -> Optional[str]:
    """The jurisdiction a pack file claims, read without trusting it.

    A pack that fails schema validation still says, in its ``jurisdiction``
    block, which jurisdiction it was written for. That is enough to tell an
    operator that *their* pack is the broken one, and nothing more is taken
    from the file.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    jurisdiction = data.get("jurisdiction")
    if not isinstance(jurisdiction, dict):
        return None
    country = jurisdiction.get("country")
    if not isinstance(country, str):
        return None
    return country.strip().upper() or None


def load_packs(pack_dir: Path) -> tuple[list[RulePack], list[PackLoadFailure]]:
    """Load every rule pack in ``pack_dir``.

    A pack that does not validate is not a pack: it cannot enable a
    jurisdiction, so it is skipped and reported as a failure rather than
    allowed to stop the whole directory from being read.
    """
    packs: list[RulePack] = []
    failures: list[PackLoadFailure] = []
    if not pack_dir.is_dir():
        return packs, failures

    for path in sorted(pack_dir.glob("*.json")):
        try:
            packs.append(load_rule_pack(path))
        except RulePackLoadError as exc:
            reason = str(exc).splitlines()[0] if str(exc) else "schema validation failed"
            failures.append(
                PackLoadFailure(
                    path=path,
                    reason=reason,
                    jurisdiction=_read_jurisdiction(path),
                )
            )
            log.warning("rule pack could not be loaded", path=str(path))
        except (OSError, ValueError) as exc:  # noqa: BLE001
            failures.append(
                PackLoadFailure(path=path, reason=type(exc).__name__, jurisdiction=None)
            )
            log.warning("rule pack could not be read", path=str(path))
    return packs, failures


def _latest(packs: Iterable[RulePack]) -> Optional[RulePack]:
    """The pack with the most recent effective date."""
    candidates = list(packs)
    if not candidates:
        return None
    return max(candidates, key=lambda pack: pack.meta.effective_from)


def _missing_for_absent(jurisdiction: str, pay_date: date, failures: list[PackLoadFailure]) -> list[str]:
    """What the operator has to do when no pack covers the jurisdiction."""
    missing = [
        f"no rule pack covers jurisdiction '{jurisdiction}' on the pay date "
        f"{pay_date.isoformat()}: an administrator has to install a rule pack "
        f"for that jurisdiction, and a named human verifier - not the author "
        f"of the pack - has to verify it against a cited source and its "
        f"golden cases before any pay run for it can be calculated"
    ]
    for failure in failures:
        if failure.jurisdiction == jurisdiction:
            missing.append(
                f"the rule pack file '{failure.path.name}' for jurisdiction "
                f"'{jurisdiction}' could not be loaded ({failure.reason}): fix "
                f"it, or remove it, before the jurisdiction can be enabled"
            )
    return missing


def _missing_for_draft(pack: RulePack, pay_date: date) -> list[str]:
    """What the operator has to do when the pack in force is a draft."""
    return [
        f"the rule pack '{pack.meta.pack_id}' for jurisdiction "
        f"'{pack.meta.jurisdiction_country}' is in state 'draft' and covers "
        f"the pay date {pay_date.isoformat()}: a named human verifier - not "
        f"the author of the pack - has to verify it against its cited source "
        f"and its golden cases before this pay run can be calculated"
    ]


def _missing_for_pending(pack: RulePack, pay_date: date) -> list[str]:
    """What the operator has to do when the pack in force awaits a human."""
    return [
        f"the rule pack '{pack.meta.pack_id}' for jurisdiction "
        f"'{pack.meta.jurisdiction_country}' is awaiting verification and "
        f"covers the pay date {pay_date.isoformat()}: a named human verifier "
        f"has to complete the verification against its cited source and its "
        f"golden cases before this pay run can be calculated"
    ]


def _missing_for_superseded(pack: RulePack, pay_date: date) -> list[str]:
    """What the operator has to do when the pack has stopped applying."""
    ended = pack.meta.effective_to.isoformat() if pack.meta.effective_to else "an earlier date"
    return [
        f"the rule pack '{pack.meta.pack_id}' for jurisdiction "
        f"'{pack.meta.jurisdiction_country}' stopped applying on {ended}, "
        f"before the pay date {pay_date.isoformat()}: a rule pack whose "
        f"effective period covers the pay date has to be in force, and a "
        f"named human verifier has to have verified it, before this pay run "
        f"can be calculated"
    ]


def _missing_for_not_yet_effective(pack: RulePack, pay_date: date) -> list[str]:
    """What the operator has to do when the pack starts after the pay date."""
    return [
        f"the rule pack '{pack.meta.pack_id}' for jurisdiction "
        f"'{pack.meta.jurisdiction_country}' is effective from "
        f"{pack.meta.effective_from.isoformat()}, after the pay date "
        f"{pay_date.isoformat()}: a rule pack whose effective period covers "
        f"the pay date has to be in force, and a named human verifier has to "
        f"have verified it, before this pay run can be calculated"
    ]


def resolve_rule_pack(
    jurisdiction: str,
    pay_date: date,
    pack_dir: Path | str | None = None,
) -> RulePackResolution:
    """Resolve the rule pack in force for a jurisdiction on a pay date.

    The pack in force is the one whose effective period covers the pay date
    and whose state is ``verified``. A pack that is ``draft``,
    ``pending_verification`` or ``superseded`` is refused exactly as no pack
    at all is, and the resolution says which it was.

    When more than one pack covers the pay date, the most recent
    ``effective_from`` wins; a verified pack in force is preferred over an
    unverified one, because an unverified pack may not be used at all and
    the rules that were verified before it are still the ones in force.
    """
    code = (jurisdiction or "").strip().upper()
    directory = Path(pack_dir).expanduser() if pack_dir else pack_directory()
    packs, failures = load_packs(directory)

    candidates = [
        pack for pack in packs if pack.meta.jurisdiction_country.upper() == code
    ]

    if not candidates:
        return RulePackResolution(
            jurisdiction=code,
            pay_date=pay_date,
            pack=None,
            pack_status=STATUS_ABSENT,
            missing=tuple(_missing_for_absent(code, pay_date, failures)),
            pack_dir=directory,
            failures=tuple(failures),
        )

    in_force = [pack for pack in candidates if pack.is_effective_on(pay_date)]

    verified = [pack for pack in in_force if pack.is_verified()]
    if verified:
        governing = _latest(verified)
        assert governing is not None
        return RulePackResolution(
            jurisdiction=code,
            pay_date=pay_date,
            pack=governing,
            pack_status=STATUS_VERIFIED,
            missing=(),
            pack_dir=directory,
            failures=tuple(failures),
        )

    if in_force:
        governing = _latest(in_force)
        assert governing is not None
        pending = governing.meta.status == "pending_verification"
        status = STATUS_PENDING_VERIFICATION if pending else STATUS_DRAFT
        missing = (
            _missing_for_pending(governing, pay_date)
            if pending
            else _missing_for_draft(governing, pay_date)
        )
        return RulePackResolution(
            jurisdiction=code,
            pay_date=pay_date,
            pack=None,
            pack_status=status,
            missing=tuple(missing),
            pack_dir=directory,
            failures=tuple(failures),
        )

    # Nothing covers the pay date. The pack that ended before it is the one
    # the operator has to replace; a pack that starts after it is the one
    # that is not yet in force.
    ended = [
        pack
        for pack in candidates
        if pack.meta.effective_to is not None and pack.meta.effective_to < pay_date
    ]
    if ended:
        governing = max(ended, key=lambda pack: pack.meta.effective_to)
        assert governing is not None
        return RulePackResolution(
            jurisdiction=code,
            pay_date=pay_date,
            pack=None,
            pack_status=STATUS_SUPERSEDED,
            missing=tuple(_missing_for_superseded(governing, pay_date)),
            pack_dir=directory,
            failures=tuple(failures),
        )

    future = [pack for pack in candidates if pack.meta.effective_from > pay_date]
    if future:
        governing = min(future, key=lambda pack: pack.meta.effective_from)
        assert governing is not None
        pending = governing.meta.status == "pending_verification"
        draft = governing.meta.status == "draft"
        if pending:
            status = STATUS_PENDING_VERIFICATION
            missing = _missing_for_pending(governing, pay_date)
        elif draft:
            status = STATUS_DRAFT
            missing = _missing_for_draft(governing, pay_date)
        else:
            status = STATUS_ABSENT
            missing = _missing_for_not_yet_effective(governing, pay_date)
        return RulePackResolution(
            jurisdiction=code,
            pay_date=pay_date,
            pack=None,
            pack_status=status,
            missing=tuple(missing),
            pack_dir=directory,
            failures=tuple(failures),
        )

    return RulePackResolution(
        jurisdiction=code,
        pay_date=pay_date,
        pack=None,
        pack_status=STATUS_ABSENT,
        missing=tuple(_missing_for_absent(code, pay_date, failures)),
        pack_dir=directory,
        failures=tuple(failures),
    )
