from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import json
import os
import sys

app = Flask(__name__)
CORS(app)

@app.route('/')
def serve():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    os.environ["CUDA_VISIBLE_DEVICES"] = str(data['gpuId'])
    cmd = [
        'python', 'main.py',
        '--model', data['model'],
        '--tasks', data['task'],
        '--static_analyze' if data['staticAnalysis'] else '',
        '--bandit_analyze' if data['banditAnalysis'] else '',
        '--static_analyze_epochs', str(data['iterations']),
        '--bandit_analyze_epochs', str(data['iterations']),
        '--allow_code_execution',
    ]
    if 'instruct' in data['model'].lower() or 'chat' in data['model'].lower():
        if 'qwen' in data['model'].lower():
            cmd.extend(['--instruction_tokens', '<|im_start|>,<|im_end|>,<|im_start|>assistant'])
        else:
            cmd.extend(['--instruction_tokens', '<|user|>,<|end|>,<|assistant|>'])
    if data.get('limit'):
        cmd.extend(['--limit', str(data['limit'])])
    
    if data.get('peftModel'):
        cmd.extend(['--peft_model', data['peftModel']])
    cmd = [arg for arg in cmd if arg]
    print(f"Выполняемая команда: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        if process.returncode != 0:
            return jsonify({
                'error': f'Ошибка выполнения: {stderr}',
                'stdout': stdout
            }), 500
        try:
            with open('evaluation_results.json', 'r') as f:
                results = json.load(f)
        except FileNotFoundError:
            return jsonify({
                'error': 'Файл с результатами не найден'
            }), 500
            
        return jsonify(results)
        
    except Exception as e:
        print(f"Исключение: {str(e)}")
        return jsonify({
            'error': f'Ошибка: {str(e)}'
        }), 500
        
@app.route('/api/save', methods=['POST'])
def save_code():
    data = request.json
    code = data.get('code')
    filename = data.get('filename', 'saved_code.py')
    if not code:
        return jsonify({'error': 'Код не предоставлен'}), 400
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        return jsonify({'message': f'Файл "{filename}" успешно сохранён!'})
    except Exception as e:
        return jsonify({'error': f'Ошибка при сохранении: {str(e)}'}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    print(f"Получены данные: {data}")
    cmd = [
        'python', 'backend/generate_code.py',
        '--model', data['model'],
        '--prompt', data['prompt'],
        '--gpu_id', str(data['gpuId']),
        '--max_iterations', str(data.get('iterations', 3))
    ]
    if data.get('staticAnalysis'):
        cmd.append('--static_analyze')
    if data.get('banditAnalysis'):
        cmd.append('--bandit_analyze')
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        if process.returncode != 0:
            return jsonify({
                'error': f'Ошибка выполнения: {stderr}',
                'stdout': stdout
            }), 500
        try:
            with open('generations.json', 'r') as f:
                results = json.load(f)
                if results and len(results) > 0:
                    return jsonify(results[0])
                else:
                    return jsonify({
                        'error': 'Нет результатов генерации'
                    }), 500
        except FileNotFoundError:
            return jsonify({
                'error': 'Файл с результатами не найден'
            }), 500
            
    except Exception as e:
        print(f"Исключение: {str(e)}")
        return jsonify({
            'error': f'Ошибка: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5688)