import logging
import subprocess
import os
import json
def read_file_to_string(file_path):
    with open(file_path, 'r') as file:
        file_contents = file.read()
    return file_contents

SVACE_PATH = "/home/jovyan/CodePatchLLM/svace-4.0.241102-x64-linux-test-non-sec/bin/svace"

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
        compiler_comand = f"cd {dir}; {SVACE_PATH} build -L python --python {file}"
    elif lang == "kotlin":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build kotlinc {file}"
    elif lang == "go":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build go {file}"
    elif lang == "cpp":
        compiler_comand = f"cd {dir}; {SVACE_PATH} build cpp {file}"
    else:
        Exception("Undefined lanuage of programming. Use only java, python, kotlin. Sensetive to capitalization")

    try:
        test = subprocess.run(compiler_comand, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
    except subprocess.CalledProcessError as e:
        logging.info(f"svace build: {test.stdout}")
        logging.error(f"Error executing command: {compiler_comand}")
        logging.error(f"Error message: {e.stderr}")
        if len(e.stderr) == 0:
            result = ""
        else:
            result = e.stderr
    if 'no file found which analysis is supported by Python version' in result: 
        if lang == 'python':
            compiler_comand = f"cd {dir}; {SVACE_PATH} build python {file}"
        try:
            test = subprocess.run(compiler_comand, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            logging.info(f"svace build: {test.stdout}")
            logging.error(f"Error executing command: {compiler_comand}")
            logging.error(f"Error message: {e.stderr}")
            result = e.stderr
            result = 'Error in ' + result[result.find('line'):result.find("svace build: error:")]
    
    if len(result) == 0:
        try:
            test = subprocess.run(f"cd {dir}; {SVACE_PATH} analyze",
                                  shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"svace analyze")
            logging.error(f"Error message: {e.stderr}")

        logging.info(test.stdout)
        directory = dir + "/.svace-dir/analyze-res"
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
            logging.error(f"Not Found analyze result {directory}/{task_id}.txt")

    output_file_path = os.path.join(dir, f"svace_message.txt")
    with open(output_file_path, "w") as f:
        f.write(result)
    logging.info(f"Finished Svace analyzing, result saved in {output_file_path} {result}")
    return 1

def valgrind_analyze(file, lang, dir, task_id):
    if lang != "cpp":
        raise Exception("Unsupported language. Only C++ is supported for dynamic analysis with Valgrind.")

    logging.info(f"Starting Valgrind analysis for file: {file} in directory: {dir}")

    compiled = True
    compile_command = f"cd {dir}; g++ -g -o program {file}"
    try:
        compile_proc = subprocess.run(compile_command, shell=True, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True)
        logging.info(f"Compilation output: {compile_proc.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Compilation failed. Error: {e.stderr}")
        result = e.stderr
        compiled = False

    if compiled:
        valgrind_command = f"cd {dir}; valgrind --tool=memcheck --leak-check=full --track-origins=yes ./program"
        try:
            valgrind_proc = subprocess.run(valgrind_command, shell=True, check=True,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True)
            result = valgrind_proc.stderr
            result = result[result.find('HEAP SUMMARY:'):]
            if "All heap blocks were freed -- no leaks are possible" in result:
                result = ""
            logging.info(f"Valgrind analysis output: {result}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Valgrind execution error: {e.stderr}")
            result = e.stderr
    output_file_path = os.path.join(dir, f"valgrind_message_{task_id}.txt")
    try:
        with open(output_file_path, "w") as f:
            f.write(result)
        logging.info(f"Finished Valgrind analysis, result saved in {output_file_path}")
    except Exception as ex:
        logging.error(f"Failed to write Valgrind output file: {ex}")
        return 0

    return 1
def bandit_analyze(file, lang, dir):
    if lang != "python":
        logging.info("Unsupported language. Only Python is supported for bandit analysis.")
        return 0
    logging.info(f"Starting Bandit analysis for file: {file} in directory: {dir}")
    
    bandit_command = f"cd {dir}; bandit {file}"
    try:
        bandit_proc = subprocess.run(bandit_command, shell=True, check=False,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True)
        result = bandit_proc.stdout + bandit_proc.stderr
        if 'Issue' in result:
            error_prompt = result[result.index("Issue"):result.index("--------")]
        else:
            error_prompt = ""
        output_file_path = os.path.join(dir, f"bandit_message.txt")
        with open(output_file_path, "w") as f:
            f.write(error_prompt)
        logging.info(f"Finished bandit analyzing, result saved in {output_file_path} {result}")
        return 1
    except Exception as e:
        logging.info(f"Error while executing bandit command: {e}")
        return 0