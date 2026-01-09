#!/usr/bin/env python3
"""
Interactive Test Extraction Agent using Strands with Custom Tools
"""
import sys
import os
import subprocess
import shlex
from pathlib import Path
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import file_read, file_write

@tool
def find_files(path: str, name_pattern: str = "*.java") -> str:
    """Find files in a directory matching a pattern.
    
    Args:
        path: Directory path to search in
        name_pattern: File pattern to match (e.g., "*.java", "*.py", "*.js", "*.ts")
    
    Returns:
        Newline-separated list of file paths
    """
    try:
        # Validate and sanitize path
        safe_path = os.path.abspath(path)
        if not os.path.exists(safe_path) or not os.path.isdir(safe_path):
            return "Error: Invalid or non-existent directory"
        
        # Whitelist allowed patterns
        allowed_patterns = ["*.java", "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.c", "*.cpp", "*.h"]
        if name_pattern not in allowed_patterns:
            return f"Error: Pattern '{name_pattern}' not allowed. Use one of: {', '.join(allowed_patterns)}"
        
        # Use shell escaping for safety
        result = subprocess.run(
            ['find', shlex.quote(safe_path), '-type', 'f', '-name', shlex.quote(name_pattern)],
            capture_output=True, text=True, check=True, shell=False
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def grep_pattern(file_path: str, pattern: str, case_insensitive: bool = True) -> str:
    """Search for patterns in a file using grep.
    
    Args:
        file_path: Path to the file to search
        pattern: Pattern to search for (supports regex)
        case_insensitive: Whether to ignore case (default: True)
    
    Returns:
        Grep output with line numbers and matching lines
    """
    try:
        # Validate file path
        safe_file_path = os.path.abspath(file_path)
        if not os.path.exists(safe_file_path) or not os.path.isfile(safe_file_path):
            return "Error: File does not exist or is not a regular file"
        
        # Whitelist allowed patterns for security
        allowed_patterns = [
            "test", "@Test", "it\\(", "describe\\(", "def test_", "@pytest",
            "public.*test", "private.*test", "protected.*test"
        ]
        if not any(allowed in pattern for allowed in allowed_patterns):
            return f"Error: Pattern not allowed for security reasons"
        
        # Build command with proper escaping
        cmd = ['grep', '-n']
        if case_insensitive:
            cmd.append('-i')
        cmd.extend([shlex.quote(pattern), shlex.quote(safe_file_path)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return result.stdout.strip() if result.stdout else "No matches found"
    except Exception as e:
        return f"Error: {str(e)}"

def create_test_extraction_agent():
    """Create a Strands agent with Nova Lite model and custom tools"""
    
    # Initialize Bedrock model with Nova Lite
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1"
    )
    
    # Create agent with custom and file tools
    agent = Agent(
        model=bedrock_model,
        tools=[find_files, grep_pattern, file_read, file_write],
        system_prompt="""
            You are a test extraction agent that automates the discovery and analysis of all tests in a source code repository. Follow these 4 steps exactly:

            ## Step 1: List Repository Files
            Use the find_files tool to locate all source files:
            - For Java: find_files(path="/path/to/repo", name_pattern="*.java")
            - For Python: find_files(path="/path/to/repo", name_pattern="*.py")
            - For JavaScript/TypeScript: find_files(path="/path/to/repo", name_pattern="*.js") or "*.ts"

            ## Step 2: Find Test-Related Lines  
            Use grep_pattern tool to identify lines containing test indicators:
            - grep_pattern(file_path="path/to/file", pattern="test|@Test|it\\(|describe\\(")

            ## Step 3: Extract Test Methods
            Use regex patterns to extract actual test methods/functions:
            - Java: `(public|private|protected).*test\\w+\\s*\\(|@Test`
            - Python: `def test_\\w+\\(|@pytest`
            - JavaScript/TypeScript: `it\\(|test\\(|describe\\(`

            ## Step 4: Analyze Test Purpose (AI Analysis)
            For each extracted test method, analyze the code and provide a concise description in format:
            `"Tests [specific functionality]"`

            ## Output Format:
            ```
            Repository: /path/to/repo
            Total Files: X
            Total Tests Found: Y

            === TEST ANALYSIS ===
            File: path/to/test/file
            Method: test_method_name
            Purpose: Tests [specific functionality]
            ---
            ```

            ## Instructions:
            1. Execute steps 1-3 using the custom find_files and grep_pattern tools
            2. For step 4, read the test method code using file_read and provide intelligent analysis
            3. Process maximum 3 test methods per file for efficiency
            4. Focus on meaningful test descriptions, not generic ones

            You have access to find_files, grep_pattern, file_read, and file_write tools to complete this task."""
    )
    
    return agent

def main():
    """Main interactive loop"""
    print("🤖 Test Extraction Agent - Powered by Amazon Nova Lite")
    print("=" * 60)
    
    # Create the agent
    try:
        agent = create_test_extraction_agent()
        print("✅ Agent initialized successfully with Nova Lite model")
        print("🔧 Custom tools: find_files, grep_pattern, file_read, file_write")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        sys.exit(1)
    
    # Interactive loop
    while True:
        print("\nOptions:")
        print("1. Extract tests from repository")
        print("2. Chat with agent")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            repo_path = input("Enter repository path: ").strip()
            if not repo_path:
                print("❌ Repository path cannot be empty")
                continue
                
            print(f"\n🔍 Analyzing repository: {repo_path}")
            print("This may take a few minutes...")
            
            prompt = f"Execute the test extraction process for repository: {repo_path}"
            
            try:
                result = agent(prompt)
                print("\n" + "="*60)
                print("ANALYSIS COMPLETE")
                print("="*60)
                
                # Save results to file
                output_file = f"test_analysis_{repo_path.replace('/', '_').replace(' ', '_')}.txt"
                with open(output_file, 'w') as f:
                    f.write(str(result.message))
                
                print(f"📄 Results saved to: {output_file}")
                
            except Exception as e:
                print(f"❌ Analysis failed: {e}")
        
        elif choice == "2":
            user_input = input("\n💬 Chat with agent: ").strip()
            if not user_input:
                continue
                
            try:
                result = agent(user_input)
                print(f"\n🤖 Agent: {result.message}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "3":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()
