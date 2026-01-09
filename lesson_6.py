#!/usr/bin/env python3
import subprocess
import re
import os
import json
from typing import List
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

# Pydantic models for structured output
class TestMethod(BaseModel):
    """Model representing a single test method"""
    name: str = Field(description="Name of the test method")
    line_number: int = Field(description="Line number where the test method is defined")
    purpose: str = Field(description="Description of what the test method tests")
    file_path: str = Field(description="Path to the file containing the test method")

class FileAnalysis(BaseModel):
    """Model representing analysis of a single file"""
    file_path: str = Field(description="Path to the analyzed file")
    test_methods: List[TestMethod] = Field(default=[], description="List of test methods found in the file")
    total_tests: int = Field(default=0, description="Total number of test methods in the file")

class TestExtractionResult(BaseModel):
    """Model representing the complete test extraction analysis"""
    repository_path: str = Field(description="Path to the analyzed repository")
    total_files_analyzed: int = Field(default=0, description="Total number of files analyzed")
    total_tests_found: int = Field(default=0, description="Total number of test methods found across all files")
    file_analyses: List[FileAnalysis] = Field(default=[], description="Detailed analysis for each file")
    summary: str = Field(default="Analysis incomplete", description="Summary of the analysis results")

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
    """Step 4: AGENT TASK - identify what test is doing using structured output"""
    if ':' not in method_line:
        return TestMethod(name="Unknown", line_number=0, purpose="Unknown test", file_path=file_path)
    
    parts = method_line.split(':', 1)
    if len(parts) < 2:
        return TestMethod(name="Unknown", line_number=0, purpose="Unknown test", file_path=file_path)
        
    line_num = parts[0]
    method_content = parts[1]
    
    try:
        line_num_int = int(line_num)
    except ValueError:
        line_num_int = 0
    
    # Extract method name
    method_name = "Unknown"
    if '@Test' in method_content:
        # Look for method name after @Test
        method_match = re.search(r'(public|private|protected).*?(\w+)\s*\(', method_content)
        if method_match:
            method_name = method_match.group(2)
    else:
        # Look for test method name
        method_match = re.search(r'(test\w+)', method_content, re.IGNORECASE)
        if method_match:
            method_name = method_match.group(1)
    
    # Extract method body
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            start_line = line_num_int - 1
            method_body = ''.join(lines[start_line:start_line+20])
    except (IOError, IndexError):
        method_body = method_content
    
    # Use agent to analyze test purpose with structured output
    prompt = f"""
    Analyze this Java test method and return structured information about it:
    
    Method name: {method_name}
    Code:
    {method_body}
    
    Provide a concise description of what this test method tests.
    """
    
    class TestPurpose(BaseModel):
        purpose: str = Field(description="What the test method tests, starting with 'Tests'")
    
    try:
        response = agent.structured_output(TestPurpose, prompt)
        purpose = response.purpose
    except Exception as e:
        purpose = f"Analysis failed: {str(e)}"
    
    return TestMethod(
        name=method_name,
        line_number=line_num_int,
        purpose=purpose,
        file_path=file_path
    )

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
    
    file_analyses = []
    total_tests = 0
    
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
        
        # Step 4: Analyze each test with AGENT using structured output
        analyzed_methods = []
        for method_line in test_methods[:3]:  # Limit to first 3 for demo
            test_method = analyze_test_with_agent(method_line, file_path, agent)
            analyzed_methods.append(test_method)
        
        file_analysis = FileAnalysis(
            file_path=file_path,
            test_methods=analyzed_methods,
            total_tests=len(analyzed_methods)
        )
        file_analyses.append(file_analysis)
        total_tests += len(analyzed_methods)
    
    # Create final structured result
    result = TestExtractionResult(
        repository_path=repo_path,
        total_files_analyzed=len([f for f in files if os.path.exists(f)]),
        total_tests_found=total_tests,
        file_analyses=file_analyses,
        summary=f"Analyzed {len(file_analyses)} files with test methods, found {total_tests} total test methods"
    )
    
    # Output structured results
    print(f"\n{'='*80}")
    print("TEST ANALYSIS RESULTS - STRUCTURED OUTPUT")
    print(f"{'='*80}")
    print(f"Repository: {result.repository_path}")
    print(f"Total Files Analyzed: {result.total_files_analyzed}")
    print(f"Total Tests Found: {result.total_tests_found}")
    print(f"Summary: {result.summary}")
    print()
    
    for file_analysis in result.file_analyses:
        print(f"FILE: {file_analysis.file_path}")
        print(f"Tests in file: {file_analysis.total_tests}")
        print()
        
        for test_method in file_analysis.test_methods:
            print(f"  Method: {test_method.name}")
            print(f"  Line: {test_method.line_number}")
            print(f"  Purpose: {test_method.purpose}")
            print("  " + "-" * 50)
        print()
    
    # Save structured results to JSON
    output_file = f"test_analysis_structured_{repo_path.replace('/', '_').replace(' ', '_')}.json"
    with open(output_file, 'w') as f:
        json.dump(result.model_dump(), f, indent=2)
    
    print(f"📄 Structured results saved to: {output_file}")

if __name__ == "__main__":
    repo_path = input("Enter repository path: ").strip()
    if not repo_path:
        print("❌ Repository path cannot be empty")
        exit(0)
    main(repo_path)
