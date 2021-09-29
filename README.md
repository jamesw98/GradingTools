# GradingTools
## About
This tool was written originally for the Virginia Tech CS3304 course, taught by David McPherson. I just recently (as of 9/27/21) got permission to add it to a public repo. 
***
This tool will download submissions from Canvas, grade them based on info provided by a `json` file, store the results, upload the grades to Canvas, and attach a feedback file to the submission.
## Requirements 
### Linux
This tool is designed to run on a Linux system, since it is written in Python, the distro should not matter.   
If you are running Windows, I would look into [WSL](https://docs.microsoft.com/en-us/windows/wsl/about). I have not tested it on MacOS.
### [CanvasAPI](https://github.com/ucfopen/canvasapi)
A Canvas API wrapper is used in this tool, you can install it with `pip`:
```
pip3 install canvasapi
```
### [DotEnv](https://pypi.org/project/python-dotenv/)
Used to hide secrets in a `.env` file such as API Keys and Course IDs, you can install it with `pip`:
```
pip3 install python-dotenv
```
All that is required to be included in the `.env` file is below:
```
CANVAS_API_KEY=<key>
COURSE_ID=<id>
```
## More Info/Getting Started
For more information/examples, check out the wiki on this repo
