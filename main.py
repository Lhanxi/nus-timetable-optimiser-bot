from src.fetcher import NUSModsAPI
from src.scheduler import TimetableScheduler
from src.data.mock_user_input import mock_user_input
from src.process_data import preprocess_module
from src.scheduler_new import SchedulerMIP
#from src.scheduler import TimetableScheduler

if __name__ == "__main__":
    api = NUSModsAPI()
    all_module_codes = mock_user_input["compulsory"] + mock_user_input["optional"]

    # Step 1: Fetch raw module data
    modules_data = api.fetch_bulk_module_data(
        module_codes=all_module_codes,
        semester=mock_user_input["semester"]
    )

    # Step 2: Preprocess each module only once
    preprocessed_modules = {}
    for module_code in all_module_codes:
        module_raw = modules_data[module_code]
        result = preprocess_module(module_code, module_raw, semester=mock_user_input["semester"])
        preprocessed_modules[module_code] = result[module_code]  # Only the value part

    # Step 3: Find optimal subset of N modules with best schedule
    #best_schedule, selected_modules = TimetableScheduler.find_best_module_combination(
    #    preprocessed_modules=preprocessed_modules,
    #    compulsory=mock_user_input["compulsory"],
    #    optional=mock_user_input["optional"],
    #    N=mock_user_input["N"]
    #)

    # Use MIP scheduler class
    scheduler = SchedulerMIP(
        preprocessed_modules=preprocessed_modules,
        compulsory=mock_user_input["compulsory"],
        optional=mock_user_input["optional"],
        N=mock_user_input["N"]
    )
    best_schedule, selected_modules = scheduler.find_best_schedule()

    # Step 4: Display result
    if best_schedule:
        print("\n✅ Selected Modules:", selected_modules)
        print("\n📅 Optimized Timetable:")
        for entry in best_schedule:
            print(f"\nModule: {entry['module']}")
            for l in entry["lessons"]:
                print(f"  [{l['lessonType']}] {l['day']} {l['startTime']}-{l['endTime']} @ {l['venue']}")
    else:
        print("\n❌ No feasible timetable found. Try reducing the number of modules or relaxing constraints.")

    # print(f"\n📊 Total Days in School: {len(set(l['day'] for mod in best_schedule for l in mod['lessons']))}")
    # print(f"⏱️ Total Time on Campus This Week: {TimetableScheduler.time_to_minutes('0000') + sum([max([TimetableScheduler.time_to_minutes(l['endTime']) for l in mod['lessons']]) - min([TimetableScheduler.time_to_minutes(l['startTime']) for l in mod['lessons']]) for mod in best_schedule]) / 60:.1f} hours")
