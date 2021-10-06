#!/usr/bin/env python3

import sys
import os
import os.path
import json
import re
import argparse
import subprocess as sp
from os import path
from shutil import copy, rmtree

from canvas_utils import download_submissions, attach_files_and_grade
from grading_info import Grading_Info, get_value_from_json

"""
run a given test case generator, if the generator is a python file, it should have a shebang and 'x' permissions so
it can be run with './'
"""
def poke_generator(data, generator_filename):
    process = None
    if ("generator_args" not in data):
        process = sp.run([f"./{generator_filename}"], check=False, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        process = sp.run([f"./{generator_filename}"] + data["generator_args"], check=False, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)

    try:
        process.check_returncode()
    except Exception as e:
        error = process.stderr.replace("\n", "\n> ")
        print(f"Error: Generator '{generator_filename}' returned a non-zero exit code:\nGenerator stderr:\n\n{error}")
        exit(1)

"""
kicks off all the grading 
"""
def grade(args):
    regrade = debug =  False

    # ensures first argument is a directory
    if (not os.path.isdir(args.directory)):
        print(f"Creating {args.directory}...")
        os.mkdir(f"{args.directory}/")

    # checks for command line arguments
    # debug argument
    if (args.debug):
        print("<!> Running in debug mode. Grades will not updated in Canvas and feedback will not be uploaded!\n")
        regrade = True
        debug = True
    # force-regrade 
    elif (args.force_regrade):
        print("<!> Forcefully regarding! All student's latest submissions will be dowloaded and regraded!\n")
        regrade = True

    # gets the directory to put the submissions in
    dir_to_grade = f"{os.getcwd()}/{args.directory}"

    # ensures there is a slash in the dir name
    if (dir_to_grade[-1] != '/'):
        dir_to_grade += '/'

    # gets the json_filename
    json_filename = args.json

    # ensures second file is a json info file
    if (not os.path.isfile(json_filename) and ".json" not in json_filename):
        print(f"Error: {json_filename} is not a valid json file")
        return 

    # loads the json file
    json_file = json.load(open(json_filename))

    # gets the assignment id
    assignment_id = get_value_from_json("assignment_id", json_file, json_filename)

    if (not assignment_id):
        exit(1)
    
    # gets info from the json file and checks everything is there
    info = Grading_Info(json_filename, json_file)
    if missing_json(info):
        exit(1) 

    timeout = info.timeout
    
    if info.external:
        # makes sure all the files required for grading exist
        check_external_required_files(info)

        # movies copies of all the required files into the dir to grade
        copy_external_required_files(info, dir_to_grade)
    else:
        # makes sure all required files are in cwd for the language you are using
        check_compiled_required_files(info) if info.compiled else check_interpreted_required_files(info)

        # moves copies of all the required files into the dir to grade for the language you are using
        copy_compiled_required_files(info, dir_to_grade) if info.compiled else copy_interpreted_required_files(info, dir_to_grade)
    
    dont_grade = []

    # downloads all the submissions and gets the submissions that shouldn't be graded
    # this is the case with submissions that have not been updated since the last run
    # this won't be run if you are running on local files only
    if not args.local:
        dont_grade = download_submissions(assignment_id, dir_to_grade, regrade)
    
    for i in range(len(dont_grade)):
        dont_grade[i] = dont_grade[i].split("/")[-1]
    
    # store the current directory
    orig_dir = os.getcwd()
    # move into the directory to start grading
    os.chdir(dir_to_grade)

    # create the result file
    result_csv = open("results.csv", "w+")

    # summary variables
    total_submissions = graded_submissions = scores_for_avg = 0

    if info.compiled:
        results = grade_compiled(info, dir_to_grade, dont_grade, orig_dir, json_file, json_filename, result_csv, timeout)
    elif info.interpreted:
        results = grade_interpreted(info, dir_to_grade, dont_grade, result_csv, timeout)
    elif info.external:
        results = grade_external(info, dir_to_grade, dont_grade, result_csv, timeout)

    total_submissions  += results[0]
    graded_submissions += results[1]
    scores_for_avg     += results[2] 
    
    result_csv.close()

    if not debug:
        if not args.local:
            attach_files_and_grade(assignment_id, "results.csv")
        
        print(f"""Finished!\nGrades have been updated in Canvas and feedback has been uploaded\n
              Check {dir_to_grade}results.csv for grades""")
    else:
        print(f"Finished!\nCheck {dir_to_grade}results.csv for grades")
    
    # shows stats for run
    print(f"\nStats:")
    print(f"New/Updated Submissions:         {graded_submissions}")
    print(f"Total Submissions:               {total_submissions}")
    if graded_submissions > 0:
        print(f"Average Score (for new/updated): {scores_for_avg/graded_submissions}/{info.total_points}")

def grade_external(info, dir_to_grade, dont_grade, result_csv, timeout):
    total_submissions = graded_submissions = scores_for_avg = 0
    
    for submission in os.listdir(os.getcwd()):
        score = 0

        if (submission not in info.required_files and ".txt" not in submission and ".csv" not in submission and 
            not os.path.isdir(os.path.join(os.getcwd(), submission))):
            total_submissions += 1
            
            if submission in dont_grade:
                continue
            
            graded_submissions += 1

            # submissions are in this format: 
            #           <pid>_<canvas id>_<assignment id>_<submission name>.<file extension>
            #           jamesw98_1234_4242_p2.hs
            sub_split = submission.split("_")
            sub_file = submission.split(".")[0]
            student_id = sub_split[1]
            student_name = sub_split[0]

            # if there is not already a directory for this student, create one
            if (not os.path.isdir(sub_file)):
                os.mkdir(sub_file)

            copy(submission, f"{sub_file}/")

            for f in info.required_files:
                copy(f, f"{sub_file}/")
            
            os.chdir(f"{sub_file}/")

            print(f"Grading {student_name}'s submission...", end=" ")

            # creates an output result file for this submission 
            output_file = open(f"{student_name}.results.txt", "w")

            os.rename(submission, info.student_filename)

            run_cmd(info.build_step_command, timeout)
            compile_result = run_cmd(info.compile_step_command, timeout)

            if not compile_result[0]:
                output_file.write(f"Your submission did not compile. See compiler output below\nYour score: 0/{info.total_points}\n\nCompiler Output:\n")
                output_file.write(compile_result[1])

                if (os.path.isdir(os.path.join(os.getcwd(), "CMakeFiles/"))):
                    rmtree(os.path.join(os.getcwd(), "CMakeFiles/"))
                elif (os.path.isdir(os.path.join(os.getcwd(), "build/"))):
                    rmtree(os.path.join(os.getcwd(), "build/"))

                os.chdir(dir_to_grade)
                print("[0/100] <!> Didn't compile\n")
                result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
                continue

            run_result = run_cmd(info.run_step_command, timeout)

            if not run_result[0] or not os.path.isfile(info.file_with_grade):
                output_file.write(f"Your submission did not produce the expected result file when running the driver. Most likely a Segmentation Fault\nYour score: 0/{info.total_points}")

                if (os.path.isdir(os.path.join(os.getcwd(), "CMakeFiles/"))):
                    rmtree(os.path.join(os.getcwd(), "CMakeFiles/"))
                elif (os.path.isdir(os.path.join(os.getcwd(), "build/"))):
                    rmtree(os.path.join(os.getcwd(), "build/"))

                os.chdir(dir_to_grade)
                print("[0/100] <!> Crashed or Encounted an Error\n")
                result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
                continue
            
            score = grab_score(info.file_with_grade)

            if (score > info.total_points):
                score = info.total_points
            
            if (score == info.total_points):
                output_file.write(f"All output matched expected!\nYour score: {score}/{info.total_points}\nCongrats, full points!")
            else:
                output_file.write(f"Your score: {score}/{info.total_points}")
            
            output_file.write("\n\nDriver Output:\n")
            
            with open(info.file_with_grade) as result_file:
                for line in result_file.readlines():
                    output_file.write(line)

            print(f"[{score}/{info.total_points}]\n")

            result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
            scores_for_avg += score
            output_file.close()
            
            if (os.path.isdir(os.path.join(os.getcwd(), "CMakeFiles/"))):
                rmtree(os.path.join(os.getcwd(), "CMakeFiles/"))
            elif (os.path.isdir(os.path.join(os.getcwd(), "build/"))):
                rmtree(os.path.join(os.getcwd(), "build/"))

            os.chdir(dir_to_grade)

    return (total_submissions, graded_submissions, scores_for_avg)

"""
Grades interpreted submissions

@params:
    info         - the grading info object
    dir_to_grade - the directory to grade and download submissions to
    dont_grade   - submissions to skip over, usually unchanged submissions
    result_csv   - the csv file to write results to
"""
def grade_interpreted(info, dir_to_grade, dont_grade, result_csv, timeout):
    total_submissions = graded_submissions = scores_for_avg = 0

    for submission in os.listdir(os.getcwd()):
        score = 0

        # makes sure to only run student submissions and submission that should be graded
        if (".txt" not in submission and ".csv" not in submission and submission 
           not in info.required_files and submission != info.reference_solution and 
           not os.path.isdir(os.path.join(os.getcwd(), submission))):

            total_submissions += 1

            # if the submission shouldn't be graded, don't grade it
            if submission in dont_grade:
                continue
                
            graded_submissions += 1

            # submissions are in this format: 
            #           <pid>_<canvas id>_<assignment id>_<submission name>.<file extension>
            #           jamesw98_1234_4242_p2.hs
            sub_split = submission.split("_")
            sub_file = submission.split(".")[0]
            student_id = sub_split[1]
            student_name = sub_split[0]

            # if there is not already a directory for this student, create one
            if (not os.path.isdir(sub_file)):
                os.mkdir(sub_file)
            
            copy(submission, f"{sub_file}/")

            for f in info.required_files:
                copy(f, f"{sub_file}/")
            copy(info.reference_solution, f"{sub_file}/")

            os.chdir(f"{sub_file}/")

            print(f"Grading {student_name}'s submission...", end=" ")

            # creates an output result file for this submission 
            output_file = open(f"{student_name}.results.txt", "w")
            output_file.write(f"Running tests for {sub_file}...\n\n")

            score = run_test_interpreted(submission, 
                                        info.points_per_line, 
                                        info.reference_solution, 
                                        info.main_file, 
                                        info.common_file, 
                                        output_file,
                                        timeout)
                
            # write score, special message for people that got a 100 :)
            if (score == info.total_points):
                output_file.write(f"All output matched expected!\nYour score: {score}/{info.total_points}\nCongrats, full points!")
            else:
                output_file.write(f"Your score: {score}/{info.total_points}")

            os.chdir(dir_to_grade)

            print(f"[{score}/{info.total_points}]\n")

            result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
            scores_for_avg += score
            output_file.close()
    
    return (total_submissions, graded_submissions, scores_for_avg)

"""
Grades compiled submissions

@params:
    info          - the grading info object
    dir_to_grade  - the directory to grade and download submissions to
    dont_grade    - submissions to skip over, usually unchanged submissions
    orig_dir      - the original directory
    json_file     - the json file object
    json_filename - the filename for the json file
    result_csv    - the csv file to write results to
"""
def grade_compiled(info, dir_to_grade, dont_grade, orig_dir, json_file, json_filename, result_csv, timeout):
    total_submissions = graded_submissions = scores_for_avg = 0

    for submission in os.listdir(os.getcwd()):
        score = 0

        # makes sure to only run student submissions and submission that should be graded
        if (submission != info.generator_output and submission not in info.reference_exe and 
           ".txt" not in submission and ".csv" not in submission and
           not os.path.isdir(os.path.join(os.getcwd(), submission))):

            total_submissions += 1

            # if the submission shouldn't be graded, don't grade it
            if submission in dont_grade:
                continue
                
            graded_submissions += 1

            # go and create a randomized input file for each submission
            os.chdir(orig_dir)

            print(f"Running {info.generator}...", end=" ")
            poke_generator(json_file, info.generator)
            if (info.generator_output not in os.listdir(dir_to_grade)):
                copy(info.generator_output, os.path.join(dir_to_grade, info.generator_output))
            
            os.chdir(dir_to_grade)
            
            # give some info about the generator output
            print(f"{len(open(dir_to_grade + info.generator_output).readlines())} lines generated")

            # submissions are in this format: 
            #           <pid>_<canvas id>_<assignment id>_<submission name>.<file extension>
            #           jamesw98_1234_4242_p2.hs
            sub_split = submission.split("_")
            sub_file = submission.split(".")[0]
            student_id = sub_split[1]
            student_name = sub_split[0]

            # if there is not already a directory for this student, create one
            if (not os.path.isdir(sub_file)):
                os.mkdir(sub_file)
            
            copy(submission, f"{sub_file}/")

            copy(info.generator_output, f"{sub_file}/")

            copy(info.reference_exe, f"{sub_file}/")

            os.chdir(f"{sub_file}/")

            print(f"Grading {student_name}'s submission...", end=" ")

            # creates an output result file for this submission 
            output_file = open(f"{student_name}.results.txt", "w")
            output_file.write(f"Running tests for {sub_file}...\n\n")

            student_compiled = True
            if (info.compiled):
                student_compiled = compile(info.compiler, submission)

            # compile, and make sure it actually compiled successfully  
            if (info.compiled and not student_compiled[0]):
                # Sad! submission didn't compile, award no points
                output_file.write(f"""Your submission did not compile. See compiler output below\n
                                  Your score: 0/{info.total_points}\n\n
                                  Compiler Output:\n""")
                output_file.write(student_compiled[1])
                output_file.close()

                os.chdir(dir_to_grade)
                print("[0/100] <!> Didn't compile\n")
                result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
                continue
        
            # if the project being graded takes input from stdin, as is the case for 3304 p1 (sentence diagramming)
            if (info.stdout):
                score = run_tests_stdout(info.generator_output, 
                                            f"./{sub_file}", 
                                            f"./{info.reference_exe}", 
                                            info.points_per_line, 
                                            output_file,
                                            info.reference_exe_args,
                                            info.student_exe_args,
                                            timeout, 
                                            True)
            else:
                student_output = get_value_from_json("output_filename", json_file, json_filename)

                if (not student_output):
                    print(f"Error: 'output_filename' not found in {json_filename}")
                    exit(1)

                score = run_tests_output_files(info.generator_output, 
                                                f"./{sub_file}", 
                                                f"./{info.reference_exe}", 
                                                info.points_per_line, 
                                                info.reference_exe_output, 
                                                student_output, 
                                                output_file,
                                                info.reference_exe_args,
                                                info.student_exe_args,
                                                timeout)

            # write score, special message for people that got a 100 :)
            if (score == info.total_points):
                output_file.write(f"All output matched expected!\nYour score: {score}/{info.total_points}\nCongrats, full points!")
            else:
                output_file.write(f"Your score: {score}/{info.total_points}")

            os.chdir(dir_to_grade)

            print(f"[{score}/{info.total_points}]\n")

            result_csv.write(f"{student_name},{student_id},{score},{dir_to_grade}{sub_file}/{student_name}.results.txt\n")
            scores_for_avg += score
            output_file.close()

    return (total_submissions, graded_submissions, scores_for_avg)

"""
Runs tests for interpreted submissions

@params:
    student_file       - the student's submission
    points             - the points off per wrong line
    reference_solution - the reference solution to compare the student's submission to
    main_file          - the main file to be run
    common_file        - the file/class that is represented by both the student's submission and the reference solution
    output_file        - the output file for this submission
"""
def run_test_interpreted(student_file, points, reference_solution, main_file, common_file, output_file, timeout):
    score = 0

    os.rename(student_file, common_file)
    student_run = run_cmd(f"./{main_file}", timeout)

    if (not student_run[0]):
        output_file.write(f"An exception occurred while running your program:\n{student_run[1]}\n")
        return 0

    student_output = student_run[1].split("\n")
    os.rename(common_file, student_file)
    os.rename(reference_solution, common_file)

    # shouldn't need to check that the reference solution encounters an exception
    reference_output = run_cmd(f"./{main_file}", timeout)[1].split("\n")

    for i in range(len(reference_output) - 1):
        if (i >= len(student_output)):
            output_file.write(f"Your code did not produce enough lines! -{points} points")
            output_file.write(f"Expected: {reference_output[i]}\n")
            output_file.write(f"Recieved: <empty line>\n\n")
        elif (student_output[i].lower() == reference_output[i].lower()):
            score += points
        else:
            output_file.write(f"Output did not match expected! -{points} points\n")
            output_file.write(f"Expected: {reference_output[i]}\n")
            output_file.write(f"Received: {student_output[i]}\n\n")

    return score

"""
Runs tests that write to standard output

@params:
    input_file  - the input file
    student_exe - the student's executable name
    ref_exe     - the reference/solution executable name
    points      - the points off per wrong line
    output_file - the output file
    stdin       - whether or not the student submission expects input from stdin
"""
def run_tests_stdout(input_file, student_exe, ref_exe, points, output_file, ref_args, stu_args, timeout, stdin=False):
    score = 0

    # reads all the lines from the input file
    for line in open(input_file, "r").readlines():
        # runs the reference and student solutions and gets there outputs
        if (stdin):
            correct_output = get_exe_output_stdin(ref_exe, ref_args, line, timeout)[1]
            student_output = get_exe_output_stdin(student_exe, stu_args, line, timeout)

        if (not student_output[0]):
            output_file.write(f"Your code produced an error! -{points} points\n")
            output_file.write(f"Input: {line}")
            output_file.write(f"Expected: {correct_output}")
            output_file.write(f"Error:\n{student_output[1]}")
            continue

        # if the output matches, award a point
        # TODO manage spaces
        # TODO managing blank lines (ignore them?)
        combine_whitespace = re.compile(r"\s+")
        correct_output = combine_whitespace.sub(" ", correct_output)
        student_output = combine_whitespace.sub(" ", student_output)

        if (correct_output.replace("\n", "").lower() == student_output[1].replace("\n", "").lower()):  
            score += points
        # if the output does not match, report the error including input, expected output, and received output 
        else:
            output_file.write(f"Output did not match expected! -{points} points\n")
            output_file.write(f"Input: {line}") 
            output_file.write(f"Expected: {correct_output}")
            output_file.write(f"Received: {student_output[1]}\n")

    return score

"""
Runs tests that write to standard output

@params:
    input_file     - the input file
    student_exe    - the student's executable name
    ref_exe        - the reference/solution executable name
    points         - the points off per wrong line
    exp_ref_output - the output of the reference solution
    exp_stu_output - the output of the student's solution
    output_file    - the output file for this submission
"""
def run_tests_output_files(input_file, student_exe, ref_exe, points, exp_ref_output, exp_stu_output, output_file, ref_args, stu_args, timeout):
    score = 0

    # run reference solution on generated input
    run_cmd(f"{ref_exe}", ref_args, timeout)
    if (not os.path.exists(exp_ref_output)):
        print(f"Error: looking for {exp_ref_output}, but it was not found!")
        exit(0)
    
    ref_lines = open(exp_ref_output, "r").readlines()
    # run student solution on generated input

    student_output = run_cmd(student_exe, stu_args, timeout)
    if (not student_output[0]):
        output_file.write(f"An exception occurred while running your program:\n{student_output[1]}\n")
        return 0

    if (path.isfile(exp_stu_output)):
        student_lines = open(exp_stu_output, "r").readlines()

        input_lines = open(input_file, "r").readlines()    

        for i in range(len(ref_lines)):
            if  (( i < len(ref_lines)) and (i < len(student_lines))):
                combine_whitespace = re.compile(r"\s+")
                
                if combine_whitespace.sub(" ", ref_lines[i]) == combine_whitespace.sub(" ", student_lines[i]):
                    score += points
                else:
                    output_file.write(f"Output did not match expected! -{points} point(s)\n")
                    output_file.write(f"Input: {input_lines[i]}") # no \n needed, since line already contains one
                    output_file.write(f"Expected: {ref_lines[i]}")
                    output_file.write(f"Received: {student_lines[i]}\n")
    else:
        output_file.write("You did not create the expected output file. Please check the project specification")
    
    return score

def check_external_required_files(info):
    for f in info.required_files:
        if (not os.path.isfile(f)):
            print(f"Error: '{f}' not found in the same dir as 'gradingtools.py'.")
            exit(1)

# ensures all the files required for a compiled language are in cwd
def check_compiled_required_files(info):
    if (not os.path.isfile(info.reference_exe)):
        print(f"Error: '{info.reference_exe}' not found in the same dir as 'gradingtools.py'.")
        exit(1)
        
    if (not os.path.isfile(info.generator)):
        print(f"Error: '{info.generator}' not found in the same dir as 'gradingtools.py'.")
        exit(1)

# ensures all the files required for an interpreted language are in cwd
def check_interpreted_required_files(info):
    # ensures the required files in cwd
    for f in info.required_files:
        if (not os.path.isfile(f)):
            print(f"Error: '{f}' is a required file, but was not found in the same dir as 'gradingtools.py'")
            exit(1)
    
    # ensures the reference solution is in cwd
    if (not os.path.isfile(info.reference_solution)):
        print(f"Error: '{info.reference_solution}' is a required file, but was not found in the same dir as 'gradingtools.py'")
        exit(1)

# copies all the files required for compiled languages into the dir to grade
def copy_compiled_required_files(info, dir_to_grade):
    # puts a copy the reference output in the dir to be graded
    copy(info.reference_exe, f"{dir_to_grade}")

    if (not os.path.isfile(info.generator_output)):
        f = open(info.generator_output, "x")
        f.close()

# same as above, but for interpreted
def copy_interpreted_required_files(info, dir_to_grade):
    for f in info.required_files:
        copy(f, f"{dir_to_grade}")
    copy(info.reference_solution, f"{dir_to_grade}")

def copy_external_required_files(info, dir_to_grade):
    for f in info.required_files:
        copy(f, f"{dir_to_grade}")

# checks to make sure all the required fields are in the json file
def missing_json(info):
    # I am  proud of this, but it does work
    return (
        (info.compiled and (
         not info.compiler or
         not info.generator or not info.generator_output or
         not info.reference_exe or not info.reference_exe_output or
         not info.total_points or not info.points_per_line)) 
        or 
        (info.interpreted and (
             not info.reference_solution or not info.required_files or not info.main_file))
        or 
        (info.external and (
            not info.compile_step_command or not info.run_step_command or 
            not info.student_filename or not info.file_with_grade or 
            not info.files_to_upload or not info.required_files
        )))

# compiles a submission
def compile(compiler, submission):
    process = sp.run([compiler, submission], check=False, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)

    try:
        process.check_returncode()
        return (True, process.stdout)
    except Exception as e:
        error = process.stdout.replace("\n", "\n> ")
        return (False, error)       

# removes the CMakeFiles folder
def remove_cmake_junk():
    rmtree("CMakeFiles")

# grabs the score from a result file for external grading
def grab_score(filename):
    score = 0
    with open(filename, "r") as result_file:
        for line in result_file.readlines():
            temp_score_normal_format = re.findall(">>\s*Score.*:\s+(\d+)", line)
            temp_score_c06_format    = re.findall("String_.*\(\):\s+(\d+)", line)
            
            if temp_score_normal_format:
                score += int(temp_score_normal_format[0])
            elif temp_score_c06_format:
                score += int(temp_score_c06_format[0])

    return score

# runs a command through the subprocess library
def run_cmd(exe, args, timeout):
    exe = [exe]

    try:
        exe = sp.run(exe + args, check=False, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE, timeout=timeout)
    except sp.TimeoutExpired as e:
        error = "Your program has timed out! Check for an infinite loop or contact your instructor"
        return (False, error)

    try:
        exe.check_returncode()
        return (True, exe.stdout)
    except Exception as e:
        error = "> " + exe.stderr.replace("\n", "\n> ")
        return (False, error)

# similar to run_cmd, but with stdin
def get_exe_output_stdin(exe, args, input_, timeout):
    exe = [exe]
    exe = sp.run(exe + args, check=False, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE, input=input_, timeout=timeout)

    try:
        exe.check_returncode()
        return (True, exe.stdout)
    except Exception as e:
        error = exe.stdout.replace("\n", "\n> ")
        return (False, error)

# gets the arguments for the program
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", type=str, required="True", help="The dir to create (first time grading) or to regrade\nNote: for local grading, the dir must exist")
    parser.add_argument("-j", "--json", type=str, required="True", help="The json info file for this assignment")
    parser.add_argument("-f", "--force-regrade", action="store_true", help="Forcefully regrade an entire directory/assignment")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode, regrades all and does not upload grades")
    parser.add_argument("-l", "--local", action="store_true", help="Use this when you are only grading locally, no downloading/uploading submissions")
    args = parser.parse_args()
    
    return args

# main
if (__name__ == "__main__"):
    args = get_args()
    print(args)
    grade(args)