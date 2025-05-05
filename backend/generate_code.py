import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import os
import subprocess
import ast
import tempfile
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def extract_executable_code(text):
    code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    if "Assistant:" in text:
        code = text.split("Assistant:")[-1].strip()
        code = re.sub(r'^```python\n|```$', '', code, flags=re.MULTILINE)
        return code.strip()
    return text.strip()

def run_static_analysis(code):
    try:
        ast.parse(code)
        return {"status": "success", "message": ""}
    except SyntaxError as e:
        return {"status": "error", "message": str(e)}

def run_bandit_analysis(code):
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        result = subprocess.run(['bandit', '-r', temp_file], 
                              capture_output=True, 
                              text=True)
        os.unlink(temp_file)
        if result.returncode == 0:
            return {"status": "success", "message": ""}
        else:
            return {"status": "warning", "message": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def generate_code_with_model(model, tokenizer, prompt, max_iterations=3):
    formatted_prompt = f"Human: {prompt}\n\nAssistant:"
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_length=2048,
        temperature=0.7,
        top_p=0.95,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    code = extract_executable_code(generated_text)
    logging.info(f"Извлеченный код: {code[:100]}...")
    return code

def generate_code(model_name, prompt, gpu_id=0, static_analyze=False, bandit_analyze=False, max_iterations=3):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    current_prompt = prompt
    current_code = None
    iteration = 0
    while iteration < max_iterations:
        logging.info(f"Итерация {iteration + 1}/{max_iterations}")
        current_code = generate_code_with_model(model, tokenizer, current_prompt)
        logging.info(f"Сгенерирован код: {current_code[:100]}...")
        analysis_results = {
            "code": current_code,
            "static_analysis": None,
            "bandit_analysis": None,
            "iteration": iteration + 1
        }
        
        has_errors = False
        error_messages = []
        
        if static_analyze:
            static_result = run_static_analysis(current_code)
            analysis_results["static_analysis"] = static_result
            if static_result["status"] != "success":
                has_errors = True
                error_messages.append(f"Статический анализ: {static_result['message']}")
        if bandit_analyze:
            bandit_result = run_bandit_analysis(current_code)
            analysis_results["bandit_analysis"] = bandit_result
            if bandit_result["status"] != "success":
                has_errors = True
                error_messages.append(f"Bandit анализ: {bandit_result['message']}")
        if not has_errors:
            logging.info("Код прошел все проверки!")
            break
        error_feedback = "\n".join(error_messages)
        current_prompt = f"{prompt}\n\nИсправьте следующие ошибки в коде:\n{error_feedback}\n\nПожалуйста, предоставьте исправленный код."
        logging.info(f"Отправляем обратную связь модели: {error_feedback}")
        iteration += 1
    with open('generations.json', 'w') as f:
        json.dump([analysis_results], f)
    return analysis_results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--gpu_id", type=int, default=0)
    parser.add_argument("--static_analyze", action="store_true")
    parser.add_argument("--bandit_analyze", action="store_true")
    parser.add_argument("--max_iterations", type=int, default=3)
    args = parser.parse_args()
    
    result = generate_code(
        args.model, 
        args.prompt, 
        args.gpu_id,
        args.static_analyze,
        args.bandit_analyze,
        args.max_iterations
    )
    print(json.dumps(result, indent=2)) 