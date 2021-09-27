# class that contains and validates info from the info json file
class Grading_Info:
    def __init__(self, json_filename, json_file):
        self.compiled = False
        self.interpreted = False
        self.external = False

        if ("compiler" in json_file):
            self.compiler    = get_value_from_json("compiler", json_file, json_filename)
            self.interpreter = None
            self.compiled    = True
            self.get_compiled_info(json_filename, json_file)

        elif ("interpreter" in json_file):
            self.interpreter = get_value_from_json("interpreter", json_file, json_filename)
            self.compiler    = None
            self.interpreted = True
            self.get_interpreted_info(json_filename, json_file)

        elif ("external_grading" in json_file):
            self.external    = True
            self.interpreter = None
            self.compiler    = None
            self.get_external_grading_info(json_filename, json_file)
        
        self.total_points    = get_value_from_json("total_points", json_file, json_filename)

        if "timeout" in json_file:
            self.timeout = get_value_from_json("timeout", json_file, json_filename)
        else:
            self.timeout = 30

        if self.interpreted or self.compiled:
            self.stdin           = get_value_from_json("stdin", json_file, json_filename)
            self.stdout          = get_value_from_json("stdout", json_file, json_filename)
            self.points_per_line = get_value_from_json("points_per_line", json_file, json_filename)

    def get_external_grading_info(self, json_filename, json_file):
        self.build_step_command   = get_value_from_json("build_step_command", json_file, json_filename)
        self.compile_step_command = get_value_from_json("compile_step_command", json_file, json_filename)
        self.run_step_command     = get_value_from_json("run_step_command", json_file, json_filename)
        self.student_filename     = get_value_from_json("student_filename", json_file, json_filename)
        self.file_with_grade      = get_value_from_json("file_with_grade", json_file, json_filename)
        self.files_to_upload      = get_value_from_json("files_to_upload", json_file, json_filename)
        self.required_files       = get_value_from_json("required_files", json_file, json_filename)

    # gets info for prolog assignments
    def get_prolog_info(self, json_filename, json_file):
        # TODO coming soon, prolog support
        pass

    # gets info for interpreted language assignments (currently only supports ruby)
    def get_interpreted_info(self, json_filename, json_file):
        self.required_files     = get_value_from_json("required_files", json_file, json_filename)
        self.reference_solution = get_value_from_json("reference_solution", json_file, json_filename)
        self.common_file        = get_value_from_json("common_file", json_file, json_filename)
        self.main_file          = get_value_from_json("main_file", json_file, json_filename)

    # gets info for compiled language assignments (pascal, haskell, c)
    def get_compiled_info(self, json_filename, json_file):
        self.generator            = get_value_from_json("generator", json_file, json_filename)
        self.generator_output     = get_value_from_json("generator_output", json_file, json_filename)
        self.reference_exe        = get_value_from_json("reference_exe", json_file, json_filename)
        self.reference_exe_output = get_value_from_json("reference_exe_output", json_file, json_filename)

        self.reference_exe_args = []
        self.student_exe_args   = []

        if "reference_exe_args" in json_file:
            self.reference_exe_args = get_value_from_json("reference_exe_args", json_file, json_filename)

        if "student_exe_args" in json_file:
            self.student_exe_args = get_value_from_json("student_exe_args", json_file, json_filename)

"""
gets values from a given json file
"""
def get_value_from_json(value, data, filename):
    if (value not in data):
        print(f"Error: '{value}' is not found in {filename}")
        return ""
    return data[value]