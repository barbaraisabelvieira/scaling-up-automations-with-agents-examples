#!/usr/bin/env python3
import time
import os
import json
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

class TestAnalysis(BaseModel):
    """Structured output for test analysis"""
    purpose: str = Field(description="What the test is testing in one concise sentence")
    test_type: str = Field(description="Type of test (unit, integration, functional, etc.)")
    confidence: int = Field(description="Confidence level in analysis (1-10)", ge=1, le=10)
    


def analyze_test_with_model(method_line, file_path, agent, model_name):
    """Step 4: Analyze test with specific model using structured output"""
    if ':' not in method_line:
        return None, 0
    
    parts = method_line.split(':', 1)
    if len(parts) < 2:
        return None, 0
        
    line_num = parts[0]
    
    try:
        line_num = int(line_num)
    except ValueError:
        return None, 0
    
    # Extract method body
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            start_line = line_num - 1
            method_body = ''.join(lines[start_line:start_line+20])
    except (IOError, IndexError):
        method_body = parts[1]
    
    prompt = f"""
    Analyze this test method and provide structured information about what it's testing:
    
    Code:
    {method_body}
    """
    
    start_time = time.time()
    try:
        #response = agent(prompt, structured_output_model=TestAnalysis)
        response = agent.structured_output(TestAnalysis,prompt)
        execution_time = time.time() - start_time
        # The response itself should be the TestAnalysis object when using structured_output_model
        return response, execution_time
    except Exception as e:
        execution_time = time.time() - start_time
        return TestAnalysis(purpose=f"Analysis failed: {str(e)}", test_type="unknown", confidence=1), execution_time

def compare_models(file_path, test_methods):
    """Compare Nova Lite vs Nova Pro on test analysis"""
    
    # Initialize models
    nova_lite = BedrockModel(model_id="amazon.nova-lite-v1:0",
        #model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
         region_name="us-east-1")
    nova_pro = BedrockModel(model_id="amazon.nova-pro-v1:0",
        #model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
         region_name="us-east-1")
    
    lite_agent = Agent(model=nova_lite)
    pro_agent = Agent(model=nova_pro)
    
    results = []
    
    for method_line in test_methods:
        print(f"\nAnalyzing: {method_line.split(':', 1)[1].strip() if ':' in method_line else method_line}")
        
        # Test with Nova Lite
        lite_result, lite_time = analyze_test_with_model(method_line, file_path, lite_agent, "Nova Lite")
        
        # Test with Nova Pro
        pro_result, pro_time = analyze_test_with_model(method_line, file_path, pro_agent, "Nova Pro")
        
        results.append({
            'method': method_line,
            'nova_lite': {
                'result': lite_result.model_dump() if lite_result else None,
                'time': lite_time
            },
            'nova_pro': {
                'result': pro_result.model_dump() if pro_result else None, 
                'time': pro_time
            }
        })
        
        if lite_result:
            print(f"  Nova Lite ({lite_time:.2f}s): {lite_result.purpose} | Type: {lite_result.test_type} | Confidence: {lite_result.confidence}")
        if pro_result:
            print(f"  Nova Pro  ({pro_time:.2f}s): {pro_result.purpose} | Type: {pro_result.test_type} | Confidence: {pro_result.confidence}")

    return results

def main():
    file_path = input("Enter source code file path: ").strip()
    
    if not file_path or not os.path.exists(file_path):
        print("❌ File not found")
        return
    
    # Extract test methods from file
    test_methods = []
    seen_methods = set()
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                # Only match lines with @Test annotation
                if '@Test' in line:
                    # Look ahead to find the actual method declaration
                    for offset in range(1, 5):
                        if line_num + offset <= len(lines):
                            next_line = lines[line_num + offset - 1]
                            if 'public' in next_line and '(' in next_line:
                                method_signature = next_line.strip()
                                if method_signature not in seen_methods:
                                    seen_methods.add(method_signature)
                                    test_methods.append(f"{line_num + offset}:{method_signature}")
                                break
    except IOError:
        print("❌ Could not read file")
        return
    
    if not test_methods:
        print("❌ No test methods found")
        return
    
    print(f"Found {len(test_methods)} test methods")
    
    # Compare models
    results = compare_models(file_path, test_methods)
    
    # Print JSON serialized results
    print(f'\n{json.dumps(results, indent=4)}')
    
    # Summary
    print(f"\n{'='*80}")
    print("MODEL COMPARISON SUMMARY")
    print(f"{'='*80}")
    
    total_lite_time = sum(r['nova_lite']['time'] for r in results)
    total_pro_time = sum(r['nova_pro']['time'] for r in results)
    
    # Calculate average confidence scores
    lite_confidences = [r['nova_lite']['result']['confidence'] for r in results if r['nova_lite']['result']]
    pro_confidences = [r['nova_pro']['result']['confidence'] for r in results if r['nova_pro']['result']]
    
    avg_lite_confidence = sum(lite_confidences) / len(lite_confidences) if lite_confidences else 0
    avg_pro_confidence = sum(pro_confidences) / len(pro_confidences) if pro_confidences else 0
    
    print(f"Nova Lite - Total time: {total_lite_time:.2f}s | Avg confidence: {avg_lite_confidence:.1f}")
    print(f"Nova Pro  - Total time: {total_pro_time:.2f}s | Avg confidence: {avg_pro_confidence:.1f}")
    print(f"Speed difference: {abs(total_lite_time - total_pro_time):.2f}s")
    
    if total_lite_time < total_pro_time:
        print("🏆 Nova Lite was faster")
    else:
        print("🏆 Nova Pro was faster")
        
    if avg_lite_confidence > avg_pro_confidence:
        print("🎯 Nova Lite had higher confidence")
    elif avg_pro_confidence > avg_lite_confidence:
        print("🎯 Nova Pro had higher confidence")
    else:
        print("🎯 Both models had equal confidence")

if __name__ == "__main__":
    main()
