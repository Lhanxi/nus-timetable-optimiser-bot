import requests
from dotenv import load_dotenv

ACAD_YEAR = os.getenv("ACAD_YEAR")

class NUSModsAPI: 
    def __init__(self, acad_year: str = ACAD_YEAR):
        self.acad_year = acad_year
        self.base_url = f"https://api.nusmods.com/v2/{acad_year}"
        self.module_list = None

    def fetch_module_list(self):
        if self.module_list is None:
            module_list_url = f"{self.base_url}/moduleList.json"
            self.module_list = requests.get(module_list_url).json()
        return self.module_list

    def fetch_module_data(self, module_code):
        module_url = f"{self.base_url}/modules/{module_code}.json"
        response = requests.get(module_url)
        response.raise_for_status()
        return response.json()

    def fetch_bulk_module_data(self, module_codes: list, semester: int = 1):
        module_data = {}
        for code in module_codes:
            try:
                data = self.fetch_module_data(code)
                sem_data = next((s for s in data.get("semesterData", []) if s["semester"] == semester), None)

                if sem_data and "timetable" in sem_data:
                    # Filter to only use timetable for this semester
                    data["semesterData"] = [sem_data]
                    module_data[code] = data
                else:
                    module_data[code] = {"error": f"No timetable data for Semester {semester}"}
            except Exception as e:
                module_data[code] = {"error": str(e)}
        return module_data