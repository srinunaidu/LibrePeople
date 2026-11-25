"""Roster solver on Google OR-Tools CP-SAT."""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta, time as dtime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("librepeople.solver")

try:
    from ortools.sat.python import cp_model  # type: ignore
    ORTOOLS_AVAILABLE = True
except Exception:
    ORTOOLS_AVAILABLE = False
    cp_model = None

SCALE = 1000


def _to_date(v) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v)
    raise ValueError(f"cannot convert {v!r} to date")


def _to_minutes(t) -> int:
    if isinstance(t, int):
        return t
    if isinstance(t, dtime):
        return t.hour * 60 + t.minute
    if isinstance(t, str):
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    if isinstance(t, timedelta):
        return int(t.total_seconds() // 60)
    raise ValueError(f"cannot convert {t!r} to minutes")


def _shift_minutes(start, end) -> int:
    s = _to_minutes(start)
    e = _to_minutes(end)
    if e <= s:
        e += 24 * 60
    return e - s


def _shift_end_abs(day, start, end):
    s = _to_minutes(start)
    e = _to_minutes(end)
    base = datetime(day.year, day.month, day.day)
    start_dt = base + timedelta(minutes=s)
    if e <= s:
        end_dt = base + timedelta(days=1, minutes=e)
    else:
        end_dt = base + timedelta(minutes=e)
    return start_dt, end_dt


class RosterSolver:
    def __init__(self, time_limit_seconds=60.0, weights=None, min_rest_hours=11.0, max_consecutive_days=6):
        self.time_limit_seconds = float(time_limit_seconds)
        self.weights = weights or {"fairness": 1.0, "preference": 1.0, "cost": 1.0, "continuity": 1.0}
        self.min_rest_hours = float(min_rest_hours)
        self.max_consecutive_days = int(max_consecutive_days)

    def solve(self, problem):
        if not ORTOOLS_AVAILABLE:
            raise RuntimeError("ortools is not available")

        employees_raw = problem.get("employees", [])
        slots_raw = problem.get("slots", [])
        min_rest_hours = float(problem.get("min_rest_hours", self.min_rest_hours))
        max_consec = int(problem.get("max_consecutive_days", self.max_consecutive_days))
        weights = problem.get("weights", self.weights)
        time_limit = float(problem.get("time_limit_seconds", self.time_limit_seconds))
        labour_limits = problem.get("labour_limits", {}) or {}

        employees = []
        for e in employees_raw:
            employees.append({
                "id": e["id"],
                "skills": set(e.get("skills") or []),
                "max_hours_per_day": float(e.get("max_hours_per_day", 8)),
                "max_hours_per_week": float(e.get("max_hours_per_week", 40)),
                "locations": set(e.get("locations") or e.get("location_ids") or []),
                "unavailable": set(_to_date(d) for d in (e.get("unavailable_dates") or e.get("unavailable") or [])),
                "preferences": e.get("preferences") or {},
                "cost": float(e.get("cost_per_slot", e.get("cost", 0))),
                "night_ok": bool(e.get("night_ok", True)),
            })

        slot_instances = []
        for s in slots_raw:
            hc = int(s.get("headcount", 1) or 1)
            for k in range(hc):
                slot_instances.append({
                    "instance_id": f"{s.get('id', len(slot_instances))}__{k}",
                    "base_id": s.get("id"),
                    "date": _to_date(s["date"]),
                    "location": s.get("location", s.get("location_id")),
                    "role": s.get("role", s.get("role_code")),
                    "skill": s.get("skill", s.get("required_skill", s.get("required_skills"))),
                    "start": s.get("start", s.get("start_time", "09:00")),
                    "end": s.get("end", s.get("end_time", "17:00")),
                    "is_night": bool(s.get("is_night", False)),
                    "required": bool(s.get("required", False)),
                })
        for sl in slot_instances:
            sl["weekend"] = sl["date"].weekday() >= 5
            sl["duration"] = _shift_minutes(sl["start"], sl["end"])

        def eligible(emp, sl):
            if sl["date"] in emp["unavailable"]:
                return False
            sk = sl["skill"]
            if sk:
                skills = sk if isinstance(sk, (list, tuple, set)) else [sk]
                if not set(skills).issubset(emp["skills"]):
                    return False
            if sl["location"] is not None and emp["locations"]:
                if sl["location"] not in emp["locations"]:
                    return False
            if sl["is_night"] and not emp["night_ok"]:
                return False
            return True

        model = cp_model.CpModel()
        x = {}
        for ei, emp in enumerate(employees):
            for si, sl in enumerate(slot_instances):
                if eligible(emp, sl):
                    x[(ei, si)] = model.NewBoolVar(f"x_{ei}_{si}")

        y = []
        for si, sl in enumerate(slot_instances):
            yv = model.NewBoolVar(f"y_{si}")
            assigned = [x[(ei, si)] for ei in range(len(employees)) if (ei, si) in x]
            if assigned:
                model.Add(sum(assigned) == yv)
            else:
                model.Add(yv == 0)
            if sl["required"]:
                model.Add(yv == 1)
            y.append(yv)

        # No double booking + rest
        for ei, emp in enumerate(employees):
            emp_slots = [si for si in range(len(slot_instances)) if (ei, si) in x]
            for a in range(len(emp_slots)):
                for b in range(a + 1, len(emp_slots)):
                    sa_idx = emp_slots[a]
                    sb_idx = emp_slots[b]
                    sla = slot_instances[sa_idx]
                    slb = slot_instances[sb_idx]
                    start_a, end_a = _shift_end_abs(sla["date"], sla["start"], sla["end"])
                    start_b, end_b = _shift_end_abs(slb["date"], slb["start"], slb["end"])
                    overlap = not (end_a <= start_b or end_b <= start_a)
                    if overlap:
                        model.Add(x[(ei, sa_idx)] + x[(ei, sb_idx)] <= 1)
                        continue
                    if end_a <= start_b:
                        gap = (start_b - end_a).total_seconds() / 3600.0
                    else:
                        gap = (start_a - end_b).total_seconds() / 3600.0
                    if gap < min_rest_hours:
                        model.Add(x[(ei, sa_idx)] + x[(ei, sb_idx)] <= 1)

        # Max hours per day
        for ei, emp in enumerate(employees):
            days = set(sl["date"] for sl in slot_instances)
            for d in days:
                day_slots = [si for si, sl in enumerate(slot_instances) if sl["date"] == d and (ei, si) in x]
                if day_slots:
                    model.Add(sum(x[(ei, si)] * slot_instances[si]["duration"] for si in day_slots) <= int(emp["max_hours_per_day"] * 60))

        # Max hours per week
        for ei, emp in enumerate(employees):
            weeks = set(sl["date"].isocalendar()[:2] for sl in slot_instances)
            for wk in weeks:
                wk_slots = [si for si, sl in enumerate(slot_instances) if sl["date"].isocalendar()[:2] == wk and (ei, si) in x]
                if wk_slots:
                    model.Add(sum(x[(ei, si)] * slot_instances[si]["duration"] for si in wk_slots) <= int(emp["max_hours_per_week"] * 60))

        # Consecutive days
        for ei, emp in enumerate(employees):
            sorted_days = sorted(set(sl["date"] for sl in slot_instances))
            day_var = {}
            for d in sorted_days:
                dv = model.NewBoolVar(f"work_{ei}_{d}")
                day_slots = [si for si, sl in enumerate(slot_instances) if sl["date"] == d and (ei, si) in x]
                if day_slots:
                    for si in day_slots:
                        model.Add(dv >= x[(ei, si)])
                    model.Add(dv <= sum(x[(ei, si)] for si in day_slots))
                else:
                    model.Add(dv == 0)
                day_var[d] = dv
            if len(sorted_days) > max_consec:
                for i in range(len(sorted_days) - max_consec):
                    window = sorted_days[i:i + max_consec + 1]
                    if all((window[j+1] - window[j]).days == 1 for j in range(len(window)-1)):
                        model.Add(sum(day_var[d] for d in window) <= max_consec)

        # Labour limits
        for (loc, role), cap in labour_limits.items():
            for d in set(sl["date"] for sl in slot_instances):
                group = [si for si, sl in enumerate(slot_instances) if sl["date"] == d and sl["location"] == loc and sl["role"] == role]
                allvars = []
                for si in group:
                    for ei in range(len(employees)):
                        if (ei, si) in x:
                            allvars.append(x[(ei, si)])
                if allvars:
                    model.Add(sum(allvars) <= int(cap))

        fw = float(weights.get("fairness", 1.0))
        pw = float(weights.get("preference", 1.0))
        cw = float(weights.get("cost", 1.0))
        contw = float(weights.get("continuity", 1.0))

        weekend_counts = []
        night_counts = []
        for ei, emp in enumerate(employees):
            wc = model.NewIntVar(0, len(slot_instances), f"wc_{ei}")
            nc = model.NewIntVar(0, len(slot_instances), f"nc_{ei}")
            model.Add(wc == sum(x[(ei, si)] for si in range(len(slot_instances)) if (ei, si) in x and slot_instances[si]["weekend"]))
            model.Add(nc == sum(x[(ei, si)] for si in range(len(slot_instances)) if (ei, si) in x and slot_instances[si]["is_night"]))
            weekend_counts.append(wc)
            night_counts.append(nc)

        if employees and slot_instances:
            min_wc = model.NewIntVar(0, len(slot_instances), "min_wc")
            max_wc = model.NewIntVar(0, len(slot_instances), "max_wc")
            model.AddMinEquality(min_wc, weekend_counts)
            model.AddMaxEquality(max_wc, weekend_counts)
            min_nc = model.NewIntVar(0, len(slot_instances), "min_nc")
            max_nc = model.NewIntVar(0, len(slot_instances), "max_nc")
            model.AddMinEquality(min_nc, night_counts)
            model.AddMaxEquality(max_nc, night_counts)
            weekend_range = model.NewIntVar(0, len(slot_instances), "wr")
            night_range = model.NewIntVar(0, len(slot_instances), "nr")
            model.Add(weekend_range == max_wc - min_wc)
            model.Add(night_range == max_nc - min_nc)
        else:
            weekend_range = None
            night_range = None

        pref_terms = []
        for ei, emp in enumerate(employees):
            for si, sl in enumerate(slot_instances):
                if (ei, si) in x:
                    base_id = sl["base_id"]
                    pref = 0
                    prefs = emp["preferences"]
                    if isinstance(prefs, dict):
                        pref = prefs.get(sl["instance_id"], prefs.get(base_id, 0))
                    try:
                        pref = float(pref)
                    except (TypeError, ValueError):
                        pref = 0.0
                    if pref:
                        pref_terms.append((x[(ei, si)], int(pref * SCALE)))

        cost_terms = []
        for ei, emp in enumerate(employees):
            for si, sl in enumerate(slot_instances):
                if (ei, si) in x:
                    c = emp["cost"]
                    slot_cost = sl.get("cost")
                    if slot_cost is not None:
                        c = float(slot_cost)
                    if c:
                        cost_terms.append((x[(ei, si)], int(c * SCALE)))

        cont_terms = []
        for ei in range(len(employees)):
            for i in range(len(slot_instances)):
                for j in range(i + 1, len(slot_instances)):
                    if (ei, i) not in x or (ei, j) not in x:
                        continue
                    si = slot_instances[i]
                    sj = slot_instances[j]
                    if si["role"] != sj["role"]:
                        continue
                    if (sj["date"] - si["date"]).days != 1:
                        continue
                    prod = model.NewBoolVar(f"cont_{ei}_{i}_{j}")
                    model.AddMultiplicationEquality(prod, [x[(ei, i)], x[(ei, j)]])
                    cont_terms.append(prod)

        obj = []
        if weekend_range is not None:
            obj.append(int(fw * SCALE) * weekend_range)
        if night_range is not None:
            obj.append(int(fw * SCALE) * night_range)
        for var, val in cost_terms:
            obj.append(int(cw * val) * var)
        for var, val in pref_terms:
            obj.append(-int(pw * val) * var)
        for prod in cont_terms:
            obj.append(-int(contw * SCALE) * prod)

        # Coverage: strongly prefer filling every slot.
        COV = SCALE * 1000
        for si in range(len(slot_instances)):
            obj.append(-COV * y[si])

        model.Minimize(sum(obj) if obj else 0)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        solver.parameters.num_search_workers = 4
        status = solver.Solve(model)

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "INFEASIBLE",
            cp_model.UNKNOWN: "INFEASIBLE",
        }
        status_str = status_map.get(status, "INFEASIBLE")
        timed_out = status == cp_model.UNKNOWN

        assignments = []
        for si, sl in enumerate(slot_instances):
            assigned_ei = None
            for ei in range(len(employees)):
                if (ei, si) in x and solver.Value(x[(ei, si)]) == 1:
                    assigned_ei = ei
                    break
            if assigned_ei is not None:
                assignments.append({
                    "slot_instance": sl["instance_id"],
                    "base_slot_id": sl["base_id"],
                    "slot_id": sl["base_id"],
                    "employee_id": employees[assigned_ei]["id"],
                    "date": sl["date"],
                    "location": sl["location"],
                    "role": sl["role"],
                    "start": sl["start"],
                    "end": sl["end"],
                    "is_night": sl["is_night"],
                })

        try:
            obj_val = float(solver.ObjectiveValue())
        except Exception:
            obj_val = None

        weekend_counts_val = {}
        night_counts_val = {}
        for emp in employees:
            weekend_counts_val[emp["id"]] = int(sum(1 for a in assignments if a["employee_id"] == emp["id"] and _to_date(a["date"]).weekday() >= 5))
            night_counts_val[emp["id"]] = int(sum(1 for a in assignments if a["employee_id"] == emp["id"] and a["is_night"]))

        weight_breakdown = {
            "fairness": {
                "weekend_range": (max(weekend_counts_val.values()) - min(weekend_counts_val.values())) if weekend_counts_val else 0,
                "night_range": (max(night_counts_val.values()) - min(night_counts_val.values())) if night_counts_val else 0,
            },
            "preference": int(sum(1 for a in assignments for emp in employees if emp["id"] == a["employee_id"] and (emp["preferences"].get(a["slot_instance"], emp["preferences"].get(a["base_slot_id"], 0)) if isinstance(emp["preferences"], dict) else 0))),
            "cost": float(sum(emp["cost"] for a in assignments for emp in employees if emp["id"] == a["employee_id"])),
            "continuity": 0,
            "weights": dict(weights),
        }

        unfilled_instances = [sl for sl in slot_instances if not any(a["slot_instance"] == sl["instance_id"] for a in assignments)]
        unfilled_groups = {}
        for sl in unfilled_instances:
            unfilled_groups.setdefault(sl["base_id"], []).append(sl)

        unfilled_slots = []
        for base_id, sls in unfilled_groups.items():
            sl0 = sls[0]
            cause = self._blocking_cause(sl0, employees, assignments, timed_out, min_rest_hours)
            unfilled_slots.append({
                "slot_id": base_id,
                "date": sl0["date"].isoformat() if hasattr(sl0["date"], "isoformat") else str(sl0["date"]),
                "location": sl0["location"],
                "role": sl0["role"],
                "headcount": len(sls),
                "cause": cause,
                "blocking_constraint": cause,
                "constraint": cause,
            })

        result = {
            "status": status_str,
            "solver_status": status_str,
            "timed_out": timed_out,
            "objective_value": obj_val,
            "objective": obj_val,
            "weight_breakdown": weight_breakdown,
            "weights": weight_breakdown,
            "assignments": assignments,
            "roster": assignments,
            "unfilled_slots": unfilled_slots,
            "unfilled": unfilled_slots,
            "input_hash": self._input_hash(problem),
        }
        return result

    def _blocking_cause(self, sl, employees, assignments, timed_out, min_rest_hours):
        if timed_out:
            return "solver_timeout"
        skill = sl["skill"]
        skill_set = set(skill if isinstance(skill, (list, tuple, set)) else ([skill] if skill else []))
        candidates = []
        for emp in employees:
            if sl["date"] in emp["unavailable"]:
                continue
            if skill_set and not skill_set.issubset(emp["skills"]):
                continue
            if sl["location"] is not None and emp["locations"] and sl["location"] not in emp["locations"]:
                continue
            if sl["is_night"] and not emp["night_ok"]:
                continue
            candidates.append(emp)
        if not candidates:
            if skill_set and not any(skill_set.issubset(e["skills"]) for e in employees):
                return "skills_mismatch"
            if sl["location"] is not None and any(e["locations"] for e in employees) and not any((not e["locations"]) or sl["location"] in e["locations"] for e in employees):
                return "location_ineligible"
            leave_blocked = False
            skill_emps = [e for e in employees if (not skill_set or skill_set.issubset(e["skills"]))]
            if skill_emps and all(sl["date"] in e["unavailable"] for e in skill_emps):
                leave_blocked = True
            if leave_blocked:
                return "leave_approved"
            return "no_available_staff"
        # rest
        for emp in candidates:
            for a in assignments:
                if a["employee_id"] != emp["id"]:
                    continue
                try:
                    s_start, s_end = _shift_end_abs(sl["date"], sl["start"], sl["end"])
                    a_start, a_end = _shift_end_abs(_to_date(a["date"]), a["start"], a["end"])
                    if a_end <= s_start:
                        gap = (s_start - a_end).total_seconds() / 3600.0
                    elif s_end <= a_start:
                        gap = (a_start - s_end).total_seconds() / 3600.0
                    else:
                        continue
                    if 0 < gap < min_rest_hours:
                        return "rest_constraint"
                except Exception:
                    pass
        # max weekly hours
        for emp in candidates:
            used_min = 0
            for a in assignments:
                if a["employee_id"] == emp["id"] and _to_date(a["date"]).isocalendar()[:2] == sl["date"].isocalendar()[:2]:
                    used_min += _shift_minutes(a["start"], a["end"])
            if used_min + sl["duration"] > emp["max_hours_per_week"] * 60:
                return "max_weekly_hours"
        # max daily hours
        for emp in candidates:
            used_min = 0
            for a in assignments:
                if a["employee_id"] == emp["id"] and _to_date(a["date"]) == sl["date"]:
                    used_min += _shift_minutes(a["start"], a["end"])
            if used_min + sl["duration"] > emp["max_hours_per_day"] * 60:
                return "max_weekly_hours"
        return "no_available_staff"

    @staticmethod
    def _input_hash(problem):
        h = hashlib.sha256()
        h.update(repr(sorted(problem.items(), key=lambda x: str(x[0]))).encode())
        return h.hexdigest()


def solve(problem):
    return RosterSolver().solve(problem)


def solve_roster(problem):
    return solve(problem)


def validate_solution(problem, assignments):
    violations = set()
    employees_raw = problem.get("employees", [])
    emp_by_id = {e["id"]: e for e in employees_raw}
    slots_raw = problem.get("slots", [])
    slot_by_id = {}
    for s in slots_raw:
        slot_by_id[s.get("id")] = s
    min_rest = float(problem.get("min_rest_hours", 11.0))
    by_emp = {}
    for a in assignments:
        by_emp.setdefault(a["employee_id"], []).append(a)
    for a in assignments:
        emp = emp_by_id.get(a["employee_id"], {})
        d = _to_date(a["date"])
        if d in set(_to_date(x) for x in (emp.get("unavailable_dates") or emp.get("unavailable") or [])):
            violations.add("availability")
        slot = slot_by_id.get(a.get("base_slot_id") or a.get("slot_id") or a.get("slot"))
        if slot:
            sk = slot.get("skill") or slot.get("required_skill") or slot.get("required_skills")
            if sk:
                skills = sk if isinstance(sk, (list, tuple, set)) else [sk]
                if not set(skills).issubset(set(emp.get("skills") or [])):
                    violations.add("skills")
            loc = slot.get("location") or slot.get("location_id")
            if loc is not None and (emp.get("locations") or emp.get("location_ids")):
                if loc not in (emp.get("locations") or emp.get("location_ids")):
                    violations.add("location")
    for eid, asgs in by_emp.items():
        for i in range(len(asgs)):
            for j in range(i + 1, len(asgs)):
                a = asgs[i]; b = asgs[j]
                sa, ea = _shift_end_abs(_to_date(a["date"]), a["start"], a["end"])
                sb, eb = _shift_end_abs(_to_date(b["date"]), b["start"], b["end"])
                if not (ea <= sb or eb <= sa):
                    violations.add("no_double_booking")
                else:
                    gap = (sb - ea).total_seconds()/3600.0 if ea <= sb else (sa - eb).total_seconds()/3600.0
                    if 0 < gap < min_rest:
                        violations.add("rest_constraint")
        emp = emp_by_id.get(eid, {})
        by_day = {}
        for a in asgs:
            by_day.setdefault(_to_date(a["date"]), []).append(a)
        for d, lst in by_day.items():
            used = sum(_shift_minutes(a["start"], a["end"]) for a in lst)
            if used > float(emp.get("max_hours_per_day", 8)) * 60 + 1e-9:
                violations.add("max_hours_per_day")
        by_week = {}
        for a in asgs:
            by_week.setdefault(_to_date(a["date"]).isocalendar()[:2], []).append(a)
        for wk, lst in by_week.items():
            used = sum(_shift_minutes(a["start"], a["end"]) for a in lst)
            if used > float(emp.get("max_hours_per_week", 40)) * 60 + 1e-9:
                violations.add("max_hours_per_week")
        days_sorted = sorted(by_day.keys())
        max_consec = int(problem.get("max_consecutive_days", 6))
        run = 1
        for i in range(1, len(days_sorted)):
            if (days_sorted[i] - days_sorted[i-1]).days == 1:
                run += 1
                if run > max_consec:
                    violations.add("consecutive_days")
            else:
                run = 1
    labour_limits = problem.get("labour_limits", {}) or {}
    if labour_limits:
        counts = {}
        for a in assignments:
            slot = slot_by_id.get(a.get("base_slot_id") or a.get("slot_id") or a.get("slot"), {})
            loc = slot.get("location") or slot.get("location_id") or a.get("location")
            role = slot.get("role") or slot.get("role_code") or a.get("role")
            d = _to_date(a["date"])
            counts.setdefault((loc, role), 0)
            counts[(loc, role)] += 1
        for key, cap in labour_limits.items():
            k = tuple(key) if isinstance(key, (list, tuple)) else key
            for ckey, cnt in counts.items():
                if isinstance(k, tuple):
                    if ckey == k[:2] if len(k) >= 2 else ckey == k:
                        if cnt > cap:
                            violations.add("labour_limits")
                else:
                    if ckey == k:
                        if cnt > cap:
                            violations.add("labour_limits")
    return sorted(violations)
