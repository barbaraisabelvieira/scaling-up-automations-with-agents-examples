#!/usr/bin/env python3
"""
Interactive Test Extraction Agent using Strands and Amazon Nova Lite
"""
import sys
from strands import Agent
from strands.models import BedrockModel
from strands_tools import shell, file_read, file_write

def create_test_extraction_agent():
    """Create a Strands agent with Nova Lite model and file tools"""
    
    # Initialize Bedrock model with Nova Lite
    bedrock_model = BedrockModel(
        model_id="amazon.nova-lite-v1:0",
        region_name="us-east-1"
    )
    
    # Create agent with file tools
    agent = Agent(
        model=bedrock_model,
        tools=[shell, file_read, file_write],
        system_prompt="""
            You are a test extraction agent that automates the discovery and analysis of all tests in a source code repository. Follow these 4 steps exactly:

            ## Step 1: List Repository Files
            Use `find` command to locate all source files:
            ```bash
            find /path/to/repo -type f -name "*.java" -o -name "*.py" -o -name "*.js" -o -name "*.ts"
            ```

            ## Step 2: Find Test-Related Lines  
            Use `grep` to identify lines containing test indicators:
            ```bash
            grep -n -i "test\|@Test\|it(\|describe(" file_path
            ```

            ## Step 3: Extract Test Methods
            Use regex patterns to extract actual test methods/functions:
            - Java: `(public|private|protected).*test\w+\s*\(|@Test`
            - Python: `def test_\w+\(|@pytest`
            - JavaScript/TypeScript: `it\(|test\(|describe\(`

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
            1. Execute steps 1-3 using CLI commands
            2. For step 4, read the test method code and provide intelligent analysis
            3. Process maximum 3 test methods per file for efficiency
            4. Focus on meaningful test descriptions, not generic ones

            You have access to shell, file_read, and file_write tools to complete this task."""
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
