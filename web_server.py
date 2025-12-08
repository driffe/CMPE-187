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
            max-width: 1400px;
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

        .outputs-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }

        .output-column {
            display: flex;
            flex-direction: column;
        }

        .output-header {
            background: #333;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: 600;
            font-size: 14px;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }

        .log-output {
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-top: none;
            padding: 15px;
            font-family: monospace;
            font-size: 11px;
            height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.4;
            flex: 1;
        }

        .stats-area {
            background: #fff;
            border: 1px solid #ddd;
            border-top: none;
            padding: 15px;
            font-size: 12px;
            display: none;
        }

        .stats-area.active {
            display: block;
        }

        .stats-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }

        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #f5f5f5;
        }

        .stat-label {
            color: #666;
        }

        .stat-value {
            font-weight: 600;
            color: #333;
        }

        .stat-value.success {
            color: #28a745;
        }

        .stat-value.error {
            color: #dc3545;
        }

        .stat-value.warning {
            color: #ffc107;
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

            <div class="outputs-grid">
                <div class="output-column">
                    <div class="output-header">Claude</div>
                    <div class="log-output" id="claudeOutput"></div>
                    <div class="stats-area" id="claudeStats">
                        <div class="stats-title">Statistics</div>
                        <div class="stat-item">
                            <span class="stat-label">Total Questions:</span>
                            <span class="stat-value" id="claudeTotal">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Correct Answers:</span>
                            <span class="stat-value success" id="claudeCorrect">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Wrong Answers:</span>
                            <span class="stat-value error" id="claudeWrong">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">No Response:</span>
                            <span class="stat-value warning" id="claudeNoResponse">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Accuracy:</span>
                            <span class="stat-value" id="claudeAccuracy">0%</span>
                        </div>
                    </div>
                </div>

                <div class="output-column">
                    <div class="output-header">ChatGPT</div>
                    <div class="log-output" id="chatgptOutput"></div>
                    <div class="stats-area" id="chatgptStats">
                        <div class="stats-title">Statistics</div>
                        <div class="stat-item">
                            <span class="stat-label">Total Questions:</span>
                            <span class="stat-value" id="chatgptTotal">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Correct Answers:</span>
                            <span class="stat-value success" id="chatgptCorrect">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Wrong Answers:</span>
                            <span class="stat-value error" id="chatgptWrong">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">No Response:</span>
                            <span class="stat-value warning" id="chatgptNoResponse">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Accuracy:</span>
                            <span class="stat-value" id="chatgptAccuracy">0%</span>
                        </div>
                    </div>
                </div>

                <div class="output-column">
                    <div class="output-header">Copilot</div>
                    <div class="log-output" id="copilotOutput"></div>
                    <div class="stats-area" id="copilotStats">
                        <div class="stats-title">Statistics</div>
                        <div class="stat-item">
                            <span class="stat-label">Total Questions:</span>
                            <span class="stat-value" id="copilotTotal">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Correct Answers:</span>
                            <span class="stat-value success" id="copilotCorrect">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Wrong Answers:</span>
                            <span class="stat-value error" id="copilotWrong">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">No Response:</span>
                            <span class="stat-value warning" id="copilotNoResponse">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Accuracy:</span>
                            <span class="stat-value" id="copilotAccuracy">0%</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="status" id="status"></div>
    </div>
    
    <script>
        let eventSource = null;
        let currentService = null;

        // Statistics tracking
        let stats = {
            claude: { total: 0, correct: 0, wrong: 0, noResponse: 0 },
            chatgpt: { total: 0, correct: 0, wrong: 0, noResponse: 0 },
            copilot: { total: 0, correct: 0, wrong: 0, noResponse: 0 }
        };

        function resetStats() {
            stats = {
                claude: { total: 0, correct: 0, wrong: 0, noResponse: 0 },
                chatgpt: { total: 0, correct: 0, wrong: 0, noResponse: 0 },
                copilot: { total: 0, correct: 0, wrong: 0, noResponse: 0 }
            };

            // Hide all stats areas
            document.getElementById('claudeStats').classList.remove('active');
            document.getElementById('chatgptStats').classList.remove('active');
            document.getElementById('copilotStats').classList.remove('active');
        }

        function updateStatistics(service, result) {
            const serviceLower = service.toLowerCase();

            if (!stats[serviceLower]) {
                return;
            }

            stats[serviceLower].total++;

            if (result === 'Correct Answer') {
                stats[serviceLower].correct++;
            } else if (result === 'Wrong Answer') {
                stats[serviceLower].wrong++;
            } else if (result === 'No Response from AI') {
                stats[serviceLower].noResponse++;
            }
        }

        function displayStatistics() {
            ['claude', 'chatgpt', 'copilot'].forEach(service => {
                const serviceStats = stats[service];
                const total = serviceStats.total;
                const correct = serviceStats.correct;
                const wrong = serviceStats.wrong;
                const noResponse = serviceStats.noResponse;
                const accuracy = total > 0 ? ((correct / total) * 100).toFixed(1) : 0;

                document.getElementById(service + 'Total').textContent = total;
                document.getElementById(service + 'Correct').textContent = correct;
                document.getElementById(service + 'Wrong').textContent = wrong;
                document.getElementById(service + 'NoResponse').textContent = noResponse;
                document.getElementById(service + 'Accuracy').textContent = accuracy + '%';

                // Show stats area
                document.getElementById(service + 'Stats').classList.add('active');
            });
        }

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
            document.getElementById('claudeOutput').innerHTML = '';
            document.getElementById('chatgptOutput').innerHTML = '';
            document.getElementById('copilotOutput').innerHTML = '';
            document.getElementById('status').style.display = 'none';
            resetStats();
            
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
                } else if (data.type === 'classification') {
                    // Update statistics when classification data is received
                    updateStatistics(data.service, data.result);
                } else if (data.type === 'complete') {
                    eventSource.close();
                    document.getElementById('submitBtn').disabled = false;
                    displayStatistics();
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
        
        function addLog(message, service = null) {
            // Determine which tab to add the log to
            let outputElement;

            if (service) {
                // If service is specified, add to that service's tab
                if (service.toLowerCase().includes('claude')) {
                    outputElement = document.getElementById('claudeOutput');
                } else if (service.toLowerCase().includes('chatgpt')) {
                    outputElement = document.getElementById('chatgptOutput');
                } else if (service.toLowerCase().includes('copilot')) {
                    outputElement = document.getElementById('copilotOutput');
                }
            }

            // If no service specified or service not recognized, detect from message
            if (!outputElement) {
                if (message.includes('--- CLAUDE ---')) {
                    currentService = 'claude';
                    outputElement = document.getElementById('claudeOutput');
                } else if (message.includes('--- CHATGPT ---')) {
                    currentService = 'chatgpt';
                    outputElement = document.getElementById('chatgptOutput');
                } else if (message.includes('--- COPILOT ---')) {
                    currentService = 'copilot';
                    outputElement = document.getElementById('copilotOutput');
                } else if (currentService) {
                    // Use the current service if set
                    outputElement = document.getElementById(currentService + 'Output');
                } else {
                    // Default to all tabs if no service detected
                    ['claudeOutput', 'chatgptOutput', 'copilotOutput'].forEach(id => {
                        const elem = document.getElementById(id);
                        elem.textContent += message + '\\n';
                        elem.scrollTop = elem.scrollHeight;
                    });
                    return;
                }
            }

            if (outputElement) {
                outputElement.textContent += message + '\\n';
                outputElement.scrollTop = outputElement.scrollHeight;
            }
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
                    validity = response_item.get("validity", "Invalid")
                    result_classification = response_item.get("result", "No Response from AI")

                    service_header = f"\n--- {service.upper()} ---"
                    yield f"data: {json.dumps({'type': 'log', 'message': service_header})}\n\n"

                    # Send classification result to client for statistics
                    yield f"data: {json.dumps({'type': 'classification', 'service': service, 'validity': validity, 'result': result_classification})}\n\n"

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

