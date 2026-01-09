#!/usr/bin/env python3
import subprocess
import re
import os
import boto3
from strands import Agent
from strands.models import BedrockModel

def list_files(repo_path):
    """Step 1: List all files in repository"""
    result = subprocess.run(['find', repo_path, '-type', 'f', '-name', '*.java'], 
                          capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout else []

def find_test_lines(file_path):
    """Step 2: Find lines containing 'test'"""
    result = subprocess.run(['grep', '-n', '-i', 'test', file_path], 
                          capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout else []

def extract_test_methods(test_lines):
    """Step 3: Extract actual test methods/functions"""
    test_methods = []
    for line in test_lines:
        # Match Java test methods with @Test annotation or test_ prefix
        if re.search(r'(public|private|protected).*test\w+\s*\(', line, re.IGNORECASE) or '@Test' in line:
            test_methods.append(line)
    return test_methods

def analyze_test_with_agent(method_line, file_path, agent):
    """Step 4: AGENT TASK - identify what test is doing"""
    if ':' not in method_line:
        return "Unknown test"
    
    parts = method_line.split(':', 1)
    if len(parts) < 2:
        return "Unknown test"
        
    line_num = parts[0]
    method_content = parts[1]
    
    try:
        line_num = int(line_num)
    except ValueError:
        return "Unknown test"
    
    # Extract method body
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            start_line = line_num - 1
            method_body = ''.join(lines[start_line:start_line+20])
    except (IOError, IndexError):
        method_body = method_content
    
    # Use agent to analyze test purpose
    prompt = f"""
    Analyze this Java test method and describe what it's testing in one concise sentence:
    
    Code:
    {method_body}
    
    Respond with format: "Tests [specific functionality]"
    """
    
    try:
        response = agent(prompt)
        return response.message if hasattr(response, 'message') else str(response)
    except Exception as e:
        return f"Analysis failed: {str(e)}"

def main(repo_path):
    # Initialize Bedrock model with Nova Lite using default credentials
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1"
    )
    
    # Initialize Strands agent with Bedrock model
    agent = Agent(model=bedrock_model)
    
    print(f"Analyzing repository: {repo_path}")
    
    # Step 1: List files
    files = list_files(repo_path)
    print(f"Found {len(files)} Java files")
    
    all_tests = []
    
    for file_path in files:
        if not os.path.exists(file_path):
            continue
            
        # Step 2: Find test lines
        test_lines = find_test_lines(file_path)
        
        if not test_lines or test_lines == ['']:
            continue
            
        # Step 3: Extract test methods
        test_methods = extract_test_methods(test_lines)
        
        if not test_methods:
            continue
            
        print(f"\nProcessing {file_path} - found {len(test_methods)} test methods")
        
        # Step 4: Analyze each test with AGENT
        for method_line in test_methods[:3]:  # Limit to first 3 for demo
            purpose = analyze_test_with_agent(method_line, file_path, agent)
            all_tests.append({
                'file': file_path,
                'method': method_line,
                'purpose': purpose
            })
    
    # Output results
    print(f"\n{'='*80}")
    print("TEST ANALYSIS RESULTS")
    print(f"{'='*80}")
    
    for test in all_tests:
        print(f"\nFile: {test['file']}")
        print(f"Method: {test['method'].split(':', 1)[1].strip() if ':' in test['method'] else test['method']}")
        print(f"Purpose: {test['purpose']}")
        print("-" * 50)

if __name__ == "__main__":
    repo_path = input("Enter repository path: ").strip()
    if not repo_path:
        print("❌ Repository path cannot be empty")
        exit(0)
    main(repo_path)
