import logging
import subprocess
import os

def read_file_to_string(file_path):
    with open(file_path, 'r') as file:
        file_contents = file.read()
    return file_contents

SVACE_PATH = "/home/jovyan/CodePatchLLM/bigcode-evaluation-harness/svace-4.0.0-x64-linux/bin/svace"

def svace_analyze(file, lang, dir, task_id):
    logging.info(f"File Name: {file}, Directory: {dir}")
    compiler_comand = ""
    result = ""
    try:
        test = subprocess.run(f"cd {dir}; {SVACE_PATH} init", shell=True, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        logging.info(test.stdout)
        test = subprocess.run(f"pwd", shell=True, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error message: {e.stderr}")
        return 0

    if lang == "java":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build javac {file}"
    elif lang == "python":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build python {file}"
    elif lang == "kotlin":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build kotlinc {file}"
    else:
        Exception("Undefined lanuage of programming. Use only java, python, kotlin. Sensetive to capitalization")

    try:
        test = subprocess.run(compiler_comand, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        # logging.info(f"Svace build out: {test.stdout} for file: {file}")
    except subprocess.CalledProcessError as e:
        logging.info(f"svace build: {test.stdout}")
        logging.error(f"Error executing command: {compiler_comand}")
        logging.error(f"Error message: {e.stderr}")
        if len(e.stderr) == 0:
            #result = "Write the full code with the correction."
            result = ""
        else:
            result = e.stderr
            result = result[:result.find("svace build: error:") + len("svace build: error:")]
            '''
            if result.find("svace build: error:") != -1:
                result = result[:result.find("svace build: error:") + len("svace build: error:")]
            elif 'root: warning: Failed to compile' in result: 
                result = 'svace build: error: Failed to compile, syntax error
            '''
            #logging.info(f'result: {result, e.stderr}')

    '''
    if len(result) == 0:
        try:
            test = subprocess.run(f"cd {dir}; {SVACE_PATH} analyze",
                                  shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"svace analyze")
            logging.error(f"Error message: {e.stderr}")

        logging.info(test.stdout)
        directory = dir + ".svace-dir/analyze-res"
        try:
            files = os.listdir(directory)
            txt = [file for file in files if file.endswith(f"{task_id}.txt")]
            warnings = ""
        except: 
            txt = []
        if len(txt) != 0:
            svace_an = read_file_to_string(directory + f"/{txt[0]}")
            mask = 'Total warnings: '
            svace_an = svace_an[svace_an.find(mask) + len(mask):]
            total_warnings = int(svace_an.split("\n")[0].strip())
            t = svace_an.find("* ")
            svace_an = svace_an[t + 2:]
            while t != -1:
                t = svace_an.find("* ")
                warnings += svace_an[svace_an.find(":") + 2:t] + "\n"
                svace_an = svace_an[t + 2:]
            logging.info(f"Total warnings: {total_warnings}, Warnings: {warnings}")
            result += warnings
        else:
            logging.error(f"Not Found analyze result {directory}/{task_id}.txt")'''

    output_file_path = os.path.join(dir, f"svace_message.txt")
    with open(output_file_path, "w") as f:
        f.write(result)
    logging.info(f"Finished Svace analyzing, result saved in {output_file_path} {result}")
    return 1
