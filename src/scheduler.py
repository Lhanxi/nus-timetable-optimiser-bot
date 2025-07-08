from itertools import combinations, product
from collections import defaultdict
import concurrent.futures

def evaluate_subset(opt_subset, preprocessed_modules, compulsory):
    # Re-importing here avoids issues if you later refactor this into packages
    scheduler = TimetableScheduler({m: preprocessed_modules[m] for m in compulsory + list(opt_subset)})
    schedule = scheduler.find_best_schedule()
    if schedule is None:
        return None
    return scheduler.min_days, scheduler.min_total_minutes, schedule, compulsory + list(opt_subset)

class TimetableScheduler:
    def __init__(self, structured_modules):
        self.structured_modules = structured_modules
        self.module_codes = list(structured_modules.keys())
        self.min_days = float('inf')
        self.min_total_minutes = float('inf')
        self.best_schedule = None

        self.module_codes.sort(
            key=lambda code: sum(len(v) for v in structured_modules[code]['lessonTypes'].values())
        )

    @staticmethod
    def time_to_minutes(t):
        return int(t[:2]) * 60 + int(t[2:])

    def has_conflict(self, schedule, lesson):
        day = lesson['day']
        s = self.time_to_minutes(lesson['startTime'])
        e = self.time_to_minutes(lesson['endTime'])
        for existing in schedule[day]:
            es = self.time_to_minutes(existing['startTime'])
            ee = self.time_to_minutes(existing['endTime'])
            if not (e <= es or s >= ee):
                return True
        return False

    def calculate_span(self, schedule_by_day):
        total = 0
        for day, lessons in schedule_by_day.items():
            if not lessons:
                continue
            starts = [self.time_to_minutes(l['startTime']) for l in lessons]
            ends   = [self.time_to_minutes(l['endTime']) for l in lessons]
            total += max(ends) - min(starts)
        return total

    def backtrack(self, idx, current_schedule, current_selection):
        if idx == len(self.module_codes):
            days_used = sum(1 for d in current_schedule if current_schedule[d])
            span = self.calculate_span(current_schedule)
            if days_used < self.min_days or (
                days_used == self.min_days and span < self.min_total_minutes
            ):
                self.min_days = days_used
                self.min_total_minutes = span
                self.best_schedule = list(current_selection)
            return

        if sum(1 for d in current_schedule if current_schedule[d]) > self.min_days:
            return

        code = self.module_codes[idx]
        types = self.structured_modules[code]['lessonTypes']
        groups_per_type = [types[lt] for lt in types]

        for combo in product(*groups_per_type):
            lessons = [l for grp in combo for l in grp]
            if any(self.has_conflict(current_schedule, l) for l in lessons):
                continue
            for l in lessons:
                current_schedule[l['day']].append(l)
            current_selection.append({'module': code, 'lessons': lessons})
            self.backtrack(idx + 1, current_schedule, current_selection)
            current_selection.pop()
            for l in lessons:
                current_schedule[l['day']].remove(l)

    def find_best_schedule(self):
        self.backtrack(0, defaultdict(list), [])
        return self.best_schedule

    @classmethod
    def find_best_module_combination(cls, preprocessed_modules, compulsory, optional, N):
        subsets = list(combinations(optional, N - len(compulsory)))
        best_days = float('inf')
        best_span = float('inf')
        best_schedule = None
        best_modules = None

        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(evaluate_subset, subset, preprocessed_modules, compulsory)
                for subset in subsets
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is None:
                    continue
                days_used, span, schedule, modules = result
                if days_used < best_days or (days_used == best_days and span < best_span):
                    best_days = days_used
                    best_span = span
                    best_schedule = schedule
                    best_modules = modules

        return best_schedule, best_modules
