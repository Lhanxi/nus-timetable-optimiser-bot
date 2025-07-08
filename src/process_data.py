from collections import defaultdict

def preprocess_module(module_code, raw_data, semester=1):
    """
    Transforms raw module JSON data into the required structured format.
    Groups multi-day Lecture sessions (same classNo) into a single option.
    All other lessonTypes remain individually grouped.

    Returns a dict like:
    {
        'CS1010': {
            'lessonTypes': {
                'Lecture': [ [lec1, lec2], [lec3] ],
                'Tutorial': [ [tut1], [tut2] ],
                ...
            }
        }
    }
    """
    lesson_types = defaultdict(list)

    for sem_data in raw_data['semesterData']:
        if sem_data['semester'] == semester:
            timetable = sem_data['timetable']

            # Step 1: Group lectures by classNo
            lectures_by_class = defaultdict(list)
            for lesson in timetable:
                if lesson['lessonType'] == 'Lecture':
                    lectures_by_class[lesson['classNo']].append(lesson)
                else:
                    # Wrap each non-lecture lesson in a list to maintain consistency
                    lesson_types[lesson['lessonType']].append([lesson])

            # Step 2: Add grouped lectures
            for class_no, group in lectures_by_class.items():
                lesson_types['Lecture'].append(group)
    
    for lt in lesson_types:
        lesson_types[lt] = deduplicate_groups(lesson_types[lt])

    return {
        module_code: {
            'lessonTypes': dict(lesson_types)
        }
    }

def deduplicate_groups(groups):
    seen = set()
    unique = []
    for group in groups:
        # Represent group as a sorted tuple of key info
        group_repr = tuple(sorted(
            (l['day'], l['startTime'], l['endTime'], l['venue']) for l in group
        ))
        if group_repr not in seen:
            seen.add(group_repr)
            unique.append(group)
    return unique