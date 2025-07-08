import pulp
from itertools import combinations
from collections import defaultdict
from pulp import LpStatus

class SchedulerMIP:
    def __init__(self, preprocessed_modules, compulsory, optional, N):
        self.modules = preprocessed_modules
        self.compulsory = compulsory
        self.optional = optional
        self.N = N

    @staticmethod
    def time_to_minutes(t):
        return int(t[:2]) * 60 + int(t[2:])

    @staticmethod
    def lessons_overlap(l1, l2):
        return (
            l1['day'] == l2['day'] and
            not (
                SchedulerMIP.time_to_minutes(l1['endTime']) <= SchedulerMIP.time_to_minutes(l2['startTime']) or
                SchedulerMIP.time_to_minutes(l2['endTime']) <= SchedulerMIP.time_to_minutes(l1['startTime'])
            )
        )

    def optimize_timetable(self, structured):
        print("🚀 [DEBUG] Running optimize_timetable on:", list(structured.keys()))
        model = pulp.LpProblem("TimetableScheduling", pulp.LpMinimize)

        # 1) Decision vars and info
        x = {}
        group_info = {}
        for mod, data in structured.items():
            for lt, groups in data['lessonTypes'].items():
                for idx, grp in enumerate(groups):
                    key = (mod, lt, idx)
                    x[key] = pulp.LpVariable(f"x_{mod}_{lt}_{idx}", cat="Binary")
                    group_info[key] = grp

        # 2) Exactly one per lessonType
        for mod, data in structured.items():
            for lt, groups in data['lessonTypes'].items():
                model += (
                    pulp.lpSum(x[(mod, lt, i)] for i in range(len(groups))) == 1,
                    f"SelectOne_{mod}_{lt}"
                )

        # 3) No-overlap constraints
        added = 0
        for (k1, l1s), (k2, l2s) in combinations(group_info.items(), 2):
            if k1[0] != k2[0] and any(self.lessons_overlap(a, b) for a in l1s for b in l2s):
                model += x[k1] + x[k2] <= 1, f"NoOverlap_{k1}_{k2}"
                added += 1
        print(f"🔧 Added {added} no-overlap constraints")

        # 4) Day indicators and span variables
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        y = {d: pulp.LpVariable(f"y_{d}", cat="Binary") for d in days}
        S = {d: pulp.LpVariable(f"S_{d}", lowBound=0, upBound=24*60) for d in days}
        E = {d: pulp.LpVariable(f"E_{d}", lowBound=0, upBound=24*60) for d in days}
        M = 24*60

        # Link lessons to days and spans
        for key, lessons in group_info.items():
            for l in lessons:
                d = l['day']
                start = self.time_to_minutes(l['startTime'])
                end = self.time_to_minutes(l['endTime'])
                model += x[key] <= y[d]
                # earliest start upper bound
                model += S[d] <= start + M*(1 - x[key])
                # latest end lower bound
                model += E[d] >= end   - M*(1 - x[key])

        # zero span on off days
        for d in days:
            model += S[d] >= 0
            model += E[d] >= 0
            model += S[d] <= M * y[d]
            model += E[d] <= M * y[d]
            model += S[d] >= y[d]      # If y[d]=1 → S[d] ≥ 1
            model += E[d] >= y[d]      # If y[d]=1 → E[d] ≥ 1

        # 5) Objective: minimize days then campus span
        WEIGHT_SPAN = 1/1440
        campus_span = pulp.lpSum(E[d] - S[d] for d in days)
        model += pulp.lpSum(y.values()) + WEIGHT_SPAN * campus_span

        # 6) Solve and check
        model.solve(pulp.PULP_CBC_CMD(msg=0))
        if LpStatus[model.status] != "Optimal":
            return None

        # 7) Gather selected lessons
        selected = defaultdict(list)
        for k, var in x.items():
            if var.value() > 0.5:
                selected[k[0]].extend(group_info[k])

        # 8) Final clash check
        for (m1, ls1), (m2, ls2) in combinations(selected.items(), 2):
            if any(self.lessons_overlap(a, b) for a in ls1 for b in ls2):
                return None

        # 9) Report campus span
        total_span = sum(E[d].value() - S[d].value() for d in days)
        print(f"⌛ Total on-campus time this week: {total_span/60:.1f} hours")

        # 10) Format output
        final = []
        for mod, lessons in selected.items():
            final.append({
                "module": mod,
                "lessons": sorted(lessons, key=lambda l: (l['day'], l['startTime']))
            })
        return final

    def find_best_schedule(self):
        for opt_subset in combinations(self.optional, self.N - len(self.compulsory)):
            chosen = self.compulsory + list(opt_subset)
            subset = {m: self.modules[m] for m in chosen}
            result = self.optimize_timetable(subset)
            if result:
                return result, chosen
        return None, None
