import canvasapi as capi
import csv
import json
import requests
import dotenv
import os
import re

from os import getenv, mkdir, listdir, remove
from os.path import isdir, isfile

# load environment variales from .env file
dotenv.load_dotenv()

class Student_Info:
    def __init__(self, student_name, student_id, grade, feedback_file):
        self.student_name = student_name
        self.id = student_id
        self.grade = grade
        self.feedback_file = feedback_file

    def __str__(self):
        return f"id: {self.id}, grade: {self.grade}, feedback: {self.feedback_file}"

if (not getenv("COURSE_ID")):
    print("Error: COURDE_ID not found in .env")
    exit(1)

if (not getenv("CANVAS_API_KEY")):
    print("Error: CANVAS_API_KEY not found in .env")
    exit(1)

BASE_URL  = "https://canvas.vt.edu/"
COURSE_ID = getenv("COURSE_ID")

canvas = capi.Canvas(BASE_URL, getenv("CANVAS_API_KEY"))
course = canvas.get_course(COURSE_ID)

def get_current_submissions(dir_to_grade):
    curr_subs = []

    for i in os.listdir(dir_to_grade):
        if (isdir(dir_to_grade + i)):
            curr_subs.append(dir_to_grade + i)

    return curr_subs
    
def remove_old_submission(dir_to_grade, id):
    for f in listdir(dir_to_grade):
        if ("." in f and str(id) in f):
            os.remove(f"{dir_to_grade}/{f}")
        elif (str(id) in f):
            for i in listdir(f"{dir_to_grade}{f}"):
                os.remove(f"{dir_to_grade}{f}/{i}")
            os.removedirs(f"{dir_to_grade}{f}")
"""
downloads submissions from Canvas, currently just regrades all submissions, not just
new ones 
"""
def download_submissions(assignment_id, dir_to_grade, regrade):
    current_submissions = get_current_submissions(dir_to_grade)
    dont_grade = []    

    if (not isdir(dir_to_grade)):
        mkdir(dir_to_grade)

    student_id_to_name = {}

    assignment = course.get_assignment(assignment_id)
    students = assignment.get_gradeable_students()

    for s in students:
        student_id_to_name[s.id] = s.display_name

    submissions = assignment.get_submissions()

    for sub in submissions:
        if (sub.attempt is not None):
            # gets the submission download url
            url = sub.attachments[0]["url"]
            # gets the submission display name
            sub_name = sub.attachments[0]["display_name"]

            # gets the student's id number
            sub_stud_id = sub.user_id
            # gets the students name with any illegal characers removed
            stud_name = remove_illegal_chars(student_id_to_name[sub_stud_id])

            # downloads the submission
            print(f"Downloading submission for {stud_name}...")
            sub_content = requests.get(url, allow_redirects=True).text 

            generated_file = f"{dir_to_grade}{stud_name}_{sub_stud_id}_{assignment_id}_{sub_name}"

            # ensures only new submissions are graded
            if (generated_file.split(".")[0] not in current_submissions or regrade):
                remove_old_submission(dir_to_grade, sub_stud_id)
                open(f"{dir_to_grade}{stud_name}_{sub_stud_id}_{assignment_id}_{sub_name}", "w").write(sub_content)
            else:
                dont_grade.append(generated_file)

    return dont_grade

"""
removes non-alphanumeric characters from a student name and replaces them with dashes
(i hate regex, but it's perfect for this)
"""
def remove_illegal_chars(name):
    return re.sub("[^0-9a-zA-Z]+", "-", name)

"""
attaches feedback files to submissions and grades them
"""
def attach_files_and_grade(assignment_id, csv_filename):
    assignment = course.get_assignment(assignment_id)

    grades_info = get_grade_info(csv_filename)

    for sub in assignment.get_submissions():
        user_id = str(sub.user_id)
        if user_id in grades_info:
            print(f"Uploading feedback for {grades_info[user_id].student_name}...")
            sub.upload_comment(grades_info[user_id].feedback_file)
            sub.edit(submission={'posted_grade': int(grades_info[user_id].grade)})

"""
gets grading info from a result csv file
"""
def get_grade_info(csv_filename):
    info = {}

    with open(csv_filename, "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            info[row[1]] = Student_Info(row[0], row[1], row[2], row[3])
    return info

if (__name__ == "__main__"):
    remove_old_submission("p1_canvas/", 176460)