#!/usr/bin/env python3
"""
Test Automation Tool Web Server
HTML 인터페이스를 통해 파일을 선택하고 실행할 수 있는 웹 서버
"""

from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import os
import sys
import json
import subprocess
import threading
import queue
from pathlib import Path

# main.py의 함수들을 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import read_questions, process_question, save_output_tree, validate_context_tree

app = Flask(__name__)
CORS(app)

# 전역 변수로 실행 상태 관리
execution_queue = queue.Queue()
current_execution = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Automation Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 40px 20px;
            line-height: 1.6;
        }
        
        .container {
            background: white;
            border: 1px solid #ddd;
            max-width: 600px;
            margin: 0 auto;
            padding: 30px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .file-input-label {
            display: block;
            cursor: pointer;
        }
        
        .file-input-label input[type="file"] {
            position: absolute;
            width: 0;
            height: 0;
            opacity: 0;
        }
        
        .file-input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            background: #fff;
            cursor: pointer;
            font-size: 14px;
            text-align: center;
        }
        
        .file-input:hover {
            border-color: #999;
        }
        
        .file-name {
            margin-top: 8px;
            color: #666;
            font-size: 13px;
        }
        
        .btn {
            width: 100%;
            padding: 12px;
            background: #333;
            color: white;
            border: none;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        
        .btn:hover:not(:disabled) {
            background: #555;
        }
        
        .btn:disabled {
            background: #999;
            cursor: not-allowed;
        }
        
        .progress-container {
            margin-top: 30px;
            display: none;
        }
        
        .progress-container.active {
            display: block;
        }
        
        .progress-bar {
            width: 100%;
            height: 24px;
            background: #eee;
            border: 1px solid #ddd;
            margin-bottom: 15px;
        }
        
        .progress-fill {
            height: 100%;
            background: #333;
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
        }
        
        .log-output {
            background: #f9f9f9;
            border: 1px solid #ddd;
            padding: 15px;
            font-family: monospace;
            font-size: 11px;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.4;
        }
        
        .status {
            margin-top: 20px;
            padding: 12px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Automation Tool</h1>
        <p class="subtitle">Select a questions file and run the test</p>
        
        <form id="testForm">
            <div class="form-group">
                <label for="questionsFile">Questions File (Required)</label>
                <label for="questionsFile" class="file-input-label">
                    <div class="file-input" id="questionsFileDisplay">Click to select file (.txt)</div>
                    <input type="file" id="questionsFile" accept=".txt" required>
                </label>
                <div class="file-name" id="questionsFileName"></div>
            </div>
            
            <button type="submit" class="btn" id="submitBtn">Run</button>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="log-output" id="logOutput"></div>
        </div>
        
        <div class="status" id="status"></div>
    </div>
    
    <script>
        let eventSource = null;
        
        document.getElementById('questionsFile').addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || '';
            const display = document.getElementById('questionsFileName');
            display.textContent = fileName || '';
            document.getElementById('questionsFileDisplay').textContent = fileName || 'Click to select file (.txt)';
        });
        
        document.getElementById('testForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const questionsFile = document.getElementById('questionsFile').files[0];
            if (!questionsFile) {
                showStatus('Please select a questions file.', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', questionsFile);
            
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('progressContainer').classList.add('active');
            document.getElementById('logOutput').innerHTML = '';
            document.getElementById('status').style.display = 'none';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (result.success) {
                    startProgress(result.filename);
                } else {
                    showStatus('File upload failed: ' + result.error, 'error');
                    document.getElementById('submitBtn').disabled = false;
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
                document.getElementById('submitBtn').disabled = false;
            }
        });
        
        function startProgress(filename) {
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource(`/run/${filename}`);
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'progress') {
                    updateProgress(data.current, data.total, data.message);
                } else if (data.type === 'log') {
                    addLog(data.message);
                } else if (data.type === 'complete') {
                    eventSource.close();
                    document.getElementById('submitBtn').disabled = false;
                    showStatus('Complete! Results saved to ' + data.output_file, 'success');
                } else if (data.type === 'error') {
                    eventSource.close();
                    document.getElementById('submitBtn').disabled = false;
                    showStatus('Error: ' + data.message, 'error');
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                document.getElementById('submitBtn').disabled = false;
            };
        }
        
        function updateProgress(current, total, message) {
            const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
            document.getElementById('progressFill').style.width = percentage + '%';
            document.getElementById('progressFill').textContent = percentage + '%';
            if (message) {
                addLog(message);
            }
        }
        
        function addLog(message) {
            const logOutput = document.getElementById('logOutput');
            logOutput.textContent += message + '\\n';
            logOutput.scrollTop = logOutput.scrollHeight;
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and file.filename.endswith('.txt'):
        filename = file.filename
        filepath = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'success': False, 'error': 'Invalid file format'})

@app.route('/run/<filename>')
def run_test(filename):
    def generate():
        filepath = os.path.join('uploads', filename)
        
        if not os.path.exists(filepath):
            yield f"data: {json.dumps({'type': 'error', 'message': 'File not found'})}\n\n"
            return
        
        try:
            # Read questions
            questions = read_questions(filepath)
            total = len(questions)
            
            yield f"data: {json.dumps({'type': 'log', 'message': f'Read {total} questions.'})}\n\n"
            
            # Automatically find Context tree and Input tree (optional)
            context_tree = None
            input_tree = None
            
            # Auto-find in the same directory
            base_dir = os.path.dirname(filepath) or '.'
            context_path = os.path.join(base_dir, 'example_context_tree.json')
            input_path = os.path.join(base_dir, 'example_input_tree.json')
            
            if os.path.exists(context_path):
                with open(context_path, 'r', encoding='utf-8') as f:
                    context_tree = json.load(f)
                yield f"data: {json.dumps({'type': 'log', 'message': 'Found Context tree.'})}\n\n"
            
            if os.path.exists(input_path):
                with open(input_path, 'r', encoding='utf-8') as f:
                    input_tree = json.load(f)
                yield f"data: {json.dumps({'type': 'log', 'message': 'Found Input tree.'})}\n\n"
            
            # Process each question
            all_results = []
            for i, q_data in enumerate(questions, 1):
                question = q_data["question"]
                keywords = q_data.get("keywords", [])
                yield f"data: {json.dumps({'type': 'progress', 'current': i, 'total': total, 'message': f'[{i}/{total}] Processing: {question[:50]}...'})}\n\n"
                
                if keywords:
                    keywords_display = ", ".join(keywords[:5])
                    if len(keywords) > 5:
                        keywords_display += "..."
                    keywords_msg = f"Expected keywords: {keywords_display}"
                    yield f"data: {json.dumps({'type': 'log', 'message': keywords_msg})}\n\n"
                
                result = process_question(question, context_tree, input_tree, use_copilot=True, expected_keywords=keywords)
                all_results.append(result)
                
                # Display prompt_used and response for each AI service
                for response_item in result["responses"]:
                    response_data = response_item.get("response_data", {})
                    service = response_data.get("service", "unknown")
                    prompt_used = response_data.get("prompt_used", "")
                    ai_response = response_data.get("response", "")
                    error = response_data.get("error", "")
                    keyword_analysis = response_data.get("keyword_analysis")
                    
                    service_header = f"\n--- {service.upper()} ---"
                    yield f"data: {json.dumps({'type': 'log', 'message': service_header})}\n\n"
                    
                    if error:
                        yield f"data: {json.dumps({'type': 'log', 'message': f'Error: {error}'})}\n\n"
                    else:
                        if prompt_used:
                            prompt_preview = prompt_used[:200] + "..." if len(prompt_used) > 200 else prompt_used
                            yield f"data: {json.dumps({'type': 'log', 'message': f'Prompt: {prompt_preview}'})}\n\n"
                        if ai_response:
                            response_preview = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
                            yield f"data: {json.dumps({'type': 'log', 'message': f'Response: {response_preview}'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'log', 'message': 'Response: (empty)'})}\n\n"
                        
                        # Display keyword analysis if available
                        if keyword_analysis:
                            match_ratio = keyword_analysis.get("match_ratio", 0)
                            found_count = len(keyword_analysis.get("found_keywords", []))
                            total_count = len(keyword_analysis.get("expected_keywords", []))
                            keywords_msg = f"Keywords: {found_count}/{total_count} found ({match_ratio*100:.0f}%)"
                            yield f"data: {json.dumps({'type': 'log', 'message': keywords_msg})}\n\n"
                            if keyword_analysis.get("missing_keywords"):
                                missing = keyword_analysis["missing_keywords"][:3]
                                missing_display = ", ".join(missing)
                                if len(keyword_analysis["missing_keywords"]) > 3:
                                    missing_display += "..."
                                missing_msg = f"Missing: {missing_display}"
                                yield f"data: {json.dumps({'type': 'log', 'message': missing_msg})}\n\n"
            
            # Save results
            output_file = 'output.json'
            save_output_tree(all_results, output_file)
            
            yield f"data: {json.dumps({'type': 'log', 'message': f'Results saved to {output_file}.'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'output_file': output_file})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    print("Starting web server...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)

