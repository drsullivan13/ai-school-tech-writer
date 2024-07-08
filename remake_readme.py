import os
from github import Github
from dotenv import load_dotenv
from utility import *
from langchain_openai import ChatOpenAI

load_dotenv()

os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_PROJECT"] = "default"

def format_data_for_openai(readme_content, main_content, remake_content, utility_content, upload_content):
    prompt = None

    # Decode the README content
    readme_content = base64.b64decode(readme_content.content).decode("utf-8")
    main_content = base64.b64decode(main_content.content).decode("utf-8")
    remake_content = base64.b64decode(remake_content.content).decode("utf-8")
    utility_content = base64.b64decode(utility_content.content).decode("utf-8")
    upload_content = base64.b64decode(upload_content.content).decode("utf-8")

    # Construct the prompt with clear instructions for the LLM.
    prompt = (
        "Please review the following code from a GitHub repository:\n"
        "Code changes from repo:\n"
        f"{main_content}\n"
        f"{remake_content}\n"
        f"{utility_content}\n"
         f"{upload_content}\n"
        "Here is the current README file content:\n"
        f"{readme_content}\n"
        "Consider the code from the repository. Determine if the README needs to be updated. If so, edit the README to reflect the changes to the capabilities of which the repository offers, ensuring to maintain its existing style and clarity.\n"
        "Updated README:\n"
    )



    return prompt

def call_openai(prompt, context):
    client = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        messages = [
            {
                "role": "system",
                "content": f'''
                    You are a technical document  writer. Your goal is to ensure that the README file that is presented to you contains accurate information representing what the application does. 
                    You will be given the Python contents of a repository that contains all of the logic. 
                    You will be provided with context from the web about creating a good README file, tips for keeping on up to date, and examples of good READMEs.
                    You will use this context to help you create the updated README file.    
                    Based on the provided information, update the README so that it accurately reflects the application and what it does, following the best practices for a README from the gathered context. 
                        Context: {context}
                ''',
            },
            {"role": "user", "content": prompt},
        ]

        # Call OpenAI
        response = client.invoke(input=messages)
        parser = StrOutputParser()
        content = parser.invoke(input=response)
        print(content)
        return content
    except Exception as e:
        print(f"Error making OpenAI API call: {e}")



def main():
    # Initialize GitHub API with token
    g = Github(os.getenv('GITHUB_TOKEN'))

    # Get the repo path and PR number from the environment variables
    repo_path =  os.getenv('REPO_PATH')
    
    # Get the repo object
    repo = g.get_repo(repo_path)

    # Fetch README content (assuming README.md)
    readme_content = repo.get_contents("README.md")
    main_content = repo.get_contents("main.py")
    remake_content = repo.get_contents("remake_readme.py")
    utility_content = repo.get_contents("utility.py")
    upload_content = repo.get_contents("upload.py")
    

    # Get the context from the vector store
    # based on the commit messages and a system prompt get context for creating a good readme update
    context = retrieve_relevant_context("What are the most important elements of a README file? And what are the best practices for describing what an application does.")

    # Format data for OpenAI prompt
    prompt = format_data_for_openai(readme_content, main_content, remake_content, utility_content, upload_content)

    # Call OpenAI to generate the updated README content
    updated_readme = call_openai(prompt, context)

    # Create PR for Updated PR
    update_readme_and_create_pr(repo, updated_readme, readme_content.sha, "Remake README based on entire application")

if __name__ == '__main__':
    main()
