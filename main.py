#!/usr/bin/env python3
"""
Test Automation Tool
Sends questions from text files to multiple AI services and collects results.
"""

import sys
import argparse
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import time

# GUI related imports
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# API client imports (optional)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package is not installed. ChatGPT API cannot be used.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package is not installed. Claude API cannot be used.")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Context Tree structure definition
CONTEXT_TREE_SCHEMA = {
    "Grammer": ["Correct Grammer", "Incorrect Grammer"],
    "Education Level": ["High School", "Bachelor", "Master or Over"],
    "Expertise": ["No experience", "Some experience", "Experts"]
}


def validate_context_tree(context_tree: Dict) -> bool:
    """Validates if the context tree is in the correct format."""
    if not isinstance(context_tree, dict):
        return False
    
    for key, valid_values in CONTEXT_TREE_SCHEMA.items():
        if key in context_tree:
            if context_tree[key] not in valid_values:
                print(f"Warning: Value '{context_tree[key]}' for '{key}' is invalid.")
                print(f"  Valid values: {valid_values}")
                return False
    
    return True


def read_questions(file_path: str) -> List[Dict[str, Any]]:
    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's a structured format separated by pipe (|)
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                question = parts[0] if parts else ""
                
                if question:
                    # Extract keywords (typically after "Correct & Complete" or from field 8 onwards)
                    keywords = []
                    if len(parts) > 8:
                        # Look for "Correct & Complete" or similar patterns
                        keyword_start_idx = 8
                        for i, part in enumerate(parts):
                            if i >= 7 and ("Complete" in part or "Correct" in part):
                                keyword_start_idx = i + 1
                                break
                        
                        # Extract keywords from keyword_start_idx onwards
                        keywords = [kw.lower() for kw in parts[keyword_start_idx:] if kw]
                    
                    questions.append({
                        "question": question,
                        "keywords": keywords,
                        "raw_line": line
                    })
            else:
                # Simple question format
                questions.append({
                    "question": line,
                    "keywords": [],
                    "raw_line": line
                })
    
    return questions


def format_context_for_prompt(context_tree: Dict) -> str:
    """Converts context tree to a format suitable for inclusion in prompts."""
    if not context_tree:
        return ""
    
    context_parts = []
    for key, value in context_tree.items():
        context_parts.append(f"{key}: {value}")
    
    return "\n".join(context_parts)


def format_input_tree_for_prompt(input_tree: Union[Dict, List, str, None], indent: int = 0) -> str:
    """Converts input tree to a format suitable for inclusion in prompts."""
    if not input_tree:
        return ""
    
    lines = []
    prefix = "  " * indent
    sub_prefix = "  " * (indent + 1)
    
    if isinstance(input_tree, dict):
        for key, value in input_tree.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                sub_lines = format_input_tree_for_prompt(value, indent + 1)
                if sub_lines:
                    lines.append(sub_lines)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        sub_lines = format_input_tree_for_prompt(item, indent + 1)
                        if sub_lines:
                            lines.append(sub_lines)
                    else:
                        lines.append(f"{sub_prefix}- {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
    elif isinstance(input_tree, list):
        for item in input_tree:
            if isinstance(item, dict):
                sub_lines = format_input_tree_for_prompt(item, indent)
                if sub_lines:
                    lines.append(sub_lines)
            else:
                lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{input_tree}")
    
    return "\n".join(lines)


def ask_copilot(question: str, context_tree: Optional[Dict] = None, input_tree: Optional[Dict] = None) -> Dict[str, Any]:
    # Include Context and Input tree in the prompt
    context_str = format_context_for_prompt(context_tree) if context_tree else ""
    input_str = format_input_tree_for_prompt(input_tree) if input_tree else ""
    
    full_prompt = question
    prompt_parts = []
    
    if input_str:
        prompt_parts.append(f"Input Tree:\n{input_str}")
    if context_str:
        prompt_parts.append(f"Context:\n{context_str}")
    
    if prompt_parts:
        full_prompt = "\n\n".join(prompt_parts) + f"\n\nQuestion: {question}"
    
    api_key = os.getenv("OPENAI_API_KEY")
    copilot_model = os.getenv("COPILOT_MODEL", "gpt-3.5-turbo")
    
    if not api_key:
        return {
            "service": "copilot",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "OPENAI_API_KEY environment variable not set"
        }
    
    if OPENAI_AVAILABLE:
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=copilot_model,  # Model for Copilot
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant GitHub Copilot."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            response_text = response.choices[0].message.content
            return {
                "service": "copilot",
                "question": question,
                "context_tree": context_tree,
                "input_tree": input_tree,
                "response": response_text,
                "prompt_used": full_prompt,
                "model_used": copilot_model
            }
        except Exception as e:
            return {
                "service": "copilot",
                "question": question,
                "context_tree": context_tree,
                "input_tree": input_tree,
                "response": "",
                "prompt_used": full_prompt,
                "error": str(e)
            }
    else:
        return {
            "service": "copilot",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "OpenAI library not available"
        }


def ask_claude(question: str, context_tree: Optional[Dict] = None, input_tree: Optional[Dict] = None) -> Dict[str, Any]:
    """Sends a question to the Claude API."""
    # Include Context and Input tree in the prompt
    context_str = format_context_for_prompt(context_tree) if context_tree else ""
    input_str = format_input_tree_for_prompt(input_tree) if input_tree else ""
    
    full_prompt = question
    prompt_parts = []
    
    if input_str:
        prompt_parts.append(f"Input Tree:\n{input_str}")
    if context_str:
        prompt_parts.append(f"Context:\n{context_str}")
    
    if prompt_parts:
        full_prompt = "\n\n".join(prompt_parts) + f"\n\nQuestion: {question}"
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "service": "claude",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "ANTHROPIC_API_KEY environment variable not set"
        }
    
    if not ANTHROPIC_AVAILABLE:
        return {
            "service": "claude",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "anthropic library not available"
        }
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # List of available models (latest models first)
        models_to_try = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                message = client.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ]
                )
                response_text = message.content[0].text
                return {
                    "service": "claude",
                    "question": question,
                    "context_tree": context_tree,
                    "input_tree": input_tree,
                    "response": response_text,
                    "prompt_used": full_prompt,
                    "model_used": model
                }
            except anthropic.APIError as e:
                # API error (authentication error, etc.)
                error_msg = f"API Error: {e.message if hasattr(e, 'message') else str(e)}"
                if "authentication" in str(e).lower() or "api key" in str(e).lower() or "401" in str(e):
                    return {
                        "service": "claude",
                        "question": question,
                        "context_tree": context_tree,
                        "input_tree": input_tree,
                        "response": "",
                        "prompt_used": full_prompt,
                        "error": f"Authentication error: API key is invalid. {error_msg}"
                    }
                last_error = error_msg
                continue
            except Exception as e:
                last_error = str(e)
                continue
        
        # All models failed
        return {
            "service": "claude",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": f"All models failed. Last error: {last_error}"
        }
    except Exception as e:
        error_str = str(e)
        if "api key" in error_str.lower() or "authentication" in error_str.lower():
            error_msg = "API key is invalid or not set."
        else:
            error_msg = error_str
        
        return {
            "service": "claude",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": error_msg
        }


def ask_chatgpt(question: str, context_tree: Optional[Dict] = None, input_tree: Optional[Dict] = None) -> Dict[str, Any]:
    """Sends a question to the ChatGPT API."""
    # Include Context and Input tree in the prompt
    context_str = format_context_for_prompt(context_tree) if context_tree else ""
    input_str = format_input_tree_for_prompt(input_tree) if input_tree else ""
    
    full_prompt = question
    prompt_parts = []
    
    if input_str:
        prompt_parts.append(f"Input Tree:\n{input_str}")
    if context_str:
        prompt_parts.append(f"Context:\n{context_str}")
    
    if prompt_parts:
        full_prompt = "\n\n".join(prompt_parts) + f"\n\nQuestion: {question}"
    
    api_key = os.getenv("OPENAI_API_KEY")
    chatgpt_model = os.getenv("CHATGPT_MODEL", "gpt-4")
    
    if not api_key:
        return {
            "service": "chatgpt",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "OPENAI_API_KEY environment variable not set"
        }
    
    if not OPENAI_AVAILABLE:
        return {
            "service": "chatgpt",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": "openai library not available"
        }
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=chatgpt_model,  # Model for ChatGPT (default: gpt-4)
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        response_text = response.choices[0].message.content
        return {
            "service": "chatgpt",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": response_text,
            "prompt_used": full_prompt,
            "model_used": chatgpt_model
        }
    except Exception as e:
        return {
            "service": "chatgpt",
            "question": question,
            "context_tree": context_tree,
            "input_tree": input_tree,
            "response": "",
            "prompt_used": full_prompt,
            "error": str(e)
        }


def classify_response(response_data: Dict[str, Any], expected_keywords: List[str] = None) -> str:
    response = response_data.get("response", "")
    error = response_data.get("error")
    question = response_data.get("question", "").lower()
    
    # If there's an error or no response or empty response, return "No Response from AI"
    if error or not response or response.strip() == "":
        return "No Response from AI"
    
    response_lower = response.lower()
    
    # Check if the response is a clarification request or asking about the question's meaning
    clarification_keywords = [
        "clarify", "rephrase", "unclear", "not sure", "don't understand",
        "not recognized", "not a real word", "typo", "misspelling",
        "could you please", "please provide", "please clarify",
        "what do you mean", "what does", "could you explain",
        "i'm not sure", "i don't know what", "doesn't seem to",
        "appears to be", "might have been", "seems like there might"
    ]
    
    # If the response requests clarification or asks about the question's meaning
    is_clarification_request = any(keyword in response_lower for keyword in clarification_keywords)
    
    # Detect if the question itself is unclear or has typos
    # Incomplete question patterns like "what mean", "what do", "what does"
    question_patterns = [
        "what mean", "what do", "what does", "what is mean",
        "what mean by", "mean by", "mean?"
    ]
    
    is_unclear_question = any(pattern in question for pattern in question_patterns)
    
    # If it's a clarification request or response to an incomplete question, return "Wrong Answer"
    if is_clarification_request or (is_unclear_question and is_clarification_request):
        return "Wrong Answer"
    
    # If the response is very short or meaningless (e.g., "I don't know", "Not sure", etc.)
    short_unclear_responses = ["i don't know", "not sure", "i'm not sure", "i can't"]
    if any(phrase in response_lower for phrase in short_unclear_responses) and len(response.split()) < 10:
        return "Wrong Answer"
    
    # Check expected keywords if provided
    if expected_keywords and len(expected_keywords) > 0:
        keywords_lower = [kw.lower() for kw in expected_keywords]
        found_keywords = [kw for kw in keywords_lower if kw in response_lower]
        keyword_match_ratio = len(found_keywords) / len(keywords_lower) if keywords_lower else 0
        
        # Store keyword matching info in response_data for later use
        response_data["keyword_analysis"] = {
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "missing_keywords": [kw for kw in keywords_lower if kw not in response_lower],
            "match_ratio": keyword_match_ratio
        }
        
        # If less than 50% of keywords are found, consider it "Wrong Answer"
        if keyword_match_ratio < 0.5:
            return "Wrong Answer"
    
    # Otherwise, consider it as "Correct Answer"
    return "Correct Answer"


def categorize_response(response_data: Dict[str, Any], expected_keywords: List[str] = None) -> Dict[str, Any]:
    classification = classify_response(response_data, expected_keywords)
    
    # Classify according to Output tree structure
    if classification == "Correct Answer":
        return {
            "validity": "Valid",
            "result": "Correct Answer",
            "response_data": response_data
        }
    elif classification == "Wrong Answer":
        return {
            "validity": "Invalid",
            "result": "Wrong Answer",
            "response_data": response_data
        }
    else:  # No Response from AI
        return {
            "validity": "Invalid",
            "result": "No Response from AI",
            "response_data": response_data
        }


def process_question(question: str, context_tree: Dict = None, input_tree: Dict = None, use_copilot: bool = True, expected_keywords: List[str] = None) -> Dict[str, Any]:
    results = {
        "question": question,
        "expected_keywords": expected_keywords or [],
        "responses": []
    }
    
    # Copilot (optional)
    if use_copilot:
        copilot_token = os.getenv("GITHUB_COPILOT_TOKEN") or os.getenv("OPENAI_API_KEY")
        if copilot_token:
            copilot_response = ask_copilot(question, context_tree, input_tree)
            results["responses"].append(categorize_response(copilot_response, expected_keywords))
        else:
            print("  [Copilot] Skipping due to missing API key.")
    
    # Claude
    claude_response = ask_claude(question, context_tree, input_tree)
    results["responses"].append(categorize_response(claude_response, expected_keywords))
    
    # ChatGPT
    chatgpt_response = ask_chatgpt(question, context_tree, input_tree)
    results["responses"].append(categorize_response(chatgpt_response, expected_keywords))
    
    return results


def save_output_tree(results: List[Dict], output_path: str):
    """Saves results in output tree format.
    
    Output tree structure:
    {
      "output": {
        "Valid": {
          "Correct Answer": [...]
        },
        "Invalid": {
          "Wrong Answer": [...],
          "No Response from AI": [...]
        }
      }
    }
    """
    # Initialize Output tree structure
    output_tree = {
        "output": {
            "Valid": {
                "Correct Answer": []
            },
            "Invalid": {
                "Wrong Answer": [],
                "No Response from AI": []
            }
        },
        "summary": {
            "total_questions": len(results),
            "total_responses": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "correct_answer_count": 0,
            "wrong_answer_count": 0,
            "no_response_count": 0
        }
    }
    
    # Classify and save responses for each question
    for question_result in results:
        question = question_result["question"]
        for response in question_result["responses"]:
            validity = response["validity"]
            result = response["result"]
            
            # Update statistics
            output_tree["summary"]["total_responses"] += 1
            if validity == "Valid":
                output_tree["summary"]["valid_count"] += 1
                output_tree["summary"]["correct_answer_count"] += 1
            else:
                output_tree["summary"]["invalid_count"] += 1
                if result == "Wrong Answer":
                    output_tree["summary"]["wrong_answer_count"] += 1
                else:
                    output_tree["summary"]["no_response_count"] += 1
            
            # Add response to the corresponding category
            response_entry = {
                "question": question,
                "service": response["response_data"].get("service", "unknown"),
                "response": response["response_data"].get("response", ""),
                "prompt_used": response["response_data"].get("prompt_used", "")
            }
            
            # Add keyword analysis if available
            keyword_analysis = response["response_data"].get("keyword_analysis")
            if keyword_analysis:
                response_entry["keyword_analysis"] = {
                    "expected_keywords": keyword_analysis.get("expected_keywords", []),
                    "found_keywords": keyword_analysis.get("found_keywords", []),
                    "missing_keywords": keyword_analysis.get("missing_keywords", []),
                    "match_ratio": keyword_analysis.get("match_ratio", 0)
                }
            
            output_tree["output"][validity][result].append(response_entry)
    
    # Also include full results (detailed information)
    output_tree["detailed_results"] = results
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_tree, f, ensure_ascii=False, indent=2)


def select_file_gui(title: str, filetypes: list) -> Optional[str]:
    """Selects a file using GUI."""
    if not GUI_AVAILABLE:
        return None
    
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes
    )
    
    root.destroy()
    return file_path if file_path else None


def main():
    parser = argparse.ArgumentParser(description='Test Automation Tool')
    parser.add_argument('questions_file', type=str, nargs='?', help='Path to text file containing questions')
    parser.add_argument('--context-tree', type=str, help='Path to Context tree JSON file (optional)')
    parser.add_argument('--input-tree', type=str, help='Path to Input tree JSON file (optional)')
    parser.add_argument('--output', type=str, default='output.json', help='Output file path (default: output.json)')
    parser.add_argument('--skip-copilot', action='store_true', help='Skip Copilot (useful when API key is missing)')
    parser.add_argument('--gui', action='store_true', help='Select files in GUI mode')
    
    args = parser.parse_args()
    
    # GUI mode
    if args.gui or not args.questions_file:
        if not GUI_AVAILABLE:
            print("Error: GUI is not available. tkinter is not installed.")
            print("Please provide file paths via command line arguments or open gui.html in a browser.")
            sys.exit(1)
        
        print("GUI mode: Please select files...")
        
        # Select questions file
        questions_file = args.questions_file
        if not questions_file:
            questions_file = select_file_gui(
                "Select Questions File (.txt)",
                [("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not questions_file:
                print("Questions file was not selected.")
                sys.exit(1)
        
        # Select Context tree
        context_tree = args.context_tree
        if not context_tree:
            if messagebox.askyesno("Context Tree", "Would you like to select a Context Tree file?"):
                context_tree = select_file_gui(
                    "Select Context Tree File (.json)",
                    [("JSON files", "*.json"), ("All files", "*.*")]
                )
        
        # Select Input tree
        input_tree = args.input_tree
        if not input_tree:
            if messagebox.askyesno("Input Tree", "Would you like to select an Input Tree file?"):
                input_tree = select_file_gui(
                    "Select Input Tree File (.json)",
                    [("JSON files", "*.json"), ("All files", "*.*")]
                )
        
        # Update args with selected files
        args.questions_file = questions_file
        args.context_tree = context_tree
        args.input_tree = input_tree
    
    # Read questions file
    questions_data = read_questions(args.questions_file)
    print(f"Read {len(questions_data)} questions.")
    
    # Check which AI services to use
    use_copilot = not args.skip_copilot
    if use_copilot:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY is missing. Skipping Copilot.")
            print("  (Use --skip-copilot option to hide this message.)")
            use_copilot = False
        else:
            copilot_model = os.getenv("COPILOT_MODEL", "gpt-3.5-turbo")
            print(f"  [Copilot] Using OpenAI model: {copilot_model}")
    
    services = []
    if use_copilot:
        copilot_model = os.getenv("COPILOT_MODEL", "gpt-3.5-turbo")
        services.append(f"Copilot ({copilot_model})")
    
    chatgpt_model = os.getenv("CHATGPT_MODEL", "gpt-4")
    services.append(f"Claude")
    services.append(f"ChatGPT ({chatgpt_model})")
    print(f"AI services to use: {', '.join(services)}")
    
    # Read Context tree and Input tree
    context_tree = None
    if args.context_tree:
        with open(args.context_tree, 'r', encoding='utf-8') as f:
            context_tree = json.load(f)
        if not validate_context_tree(context_tree):
            print("Warning: Context tree validation failed. Continuing anyway.")
    
    input_tree = None
    if args.input_tree:
        with open(args.input_tree, 'r', encoding='utf-8') as f:
            input_tree = json.load(f)
    
    # Process each question
    all_results = []
    for i, q_data in enumerate(questions_data, 1):
        question = q_data["question"]
        keywords = q_data.get("keywords", [])
        print(f"\n[{i}/{len(questions_data)}] Processing: {question[:50]}...")
        if keywords:
            print(f"  Expected keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
        result = process_question(question, context_tree, input_tree, use_copilot=use_copilot, expected_keywords=keywords)
        all_results.append(result)
        
        # Short delay for API rate limiting (optional)
        if i < len(questions_data):
            time.sleep(0.5)
    
    # Save results
    save_output_tree(all_results, args.output)
    print(f"\nResults saved to {args.output}.")


if __name__ == '__main__':
    main()

