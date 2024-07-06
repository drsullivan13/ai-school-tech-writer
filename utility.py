import os
import base64
from random import randint
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

PINECONE_INDEX = os.getenv("PINECONE_INDEX")
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

def retrieve_relevant_context(commit_messages):
    prompt = """
        What are important aspects of a README file? And what are the best ways to keep it up to date?
    """

    document_vectorstore = PineconeVectorStore(index_name=PINECONE_INDEX, embedding=embeddings)
    retriever = document_vectorstore.as_retriever()
    context = retriever.get_relevant_documents(prompt)
    return context


def format_data_for_openai(diffs, readme_content, commit_messages):
    prompt = None

    # Combine the changes into a string with clear delineation.
    changes = "\n".join(
        [f'File: {file["filename"]}\nDiff: \n{file["patch"]}\n' for file in diffs]
    )

    # Combine all commit messages
    commit_messages = "\n".join(commit_messages) + "\n\n"

    # Decode the README content
    readme_content = base64.b64decode(readme_content.content).decode("utf-8")

    # Construct the prompt with clear instructions for the LLM.
    prompt = (
        "Please review the following code changes and commit messages from a GitHub pull request:\n"
        "Code changes from Pull Request:\n"
        f"{changes}\n"
        "Commit messages:\n"
        f"{commit_messages}"
        "Here is the current README file content:\n"
        f"{readme_content}\n"
        "Consider the code changes from the Pull Request (including changes in docstrings and other metadata), and the commit messages. Determine if the README needs to be updated. If so, edit the README to reflect the changes to the capabilities of which the repository offers, ensuring to maintain its existing style and clarity.\n"
        "Updated README:\n"
    )



    return prompt

# I want to pull documents from the web around creating a good README file, tips for keeping on up to date, and examples of good READMEs
# I will store these documents in a vector database to be able to use as context on queries
# I will pull the recent commits from github to be able to see the changes in the codebase
# I will look across the entire repository to gain context for what the application is and does
# I will use all of this information to then generate updates to the README
def call_openai(prompt, context):
    client = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        messages = [
            {
                "role": "system",
                "content": """
                        Your task is to update the README file of the project, according to the changes made in a pull request.
                        You shouldn't add a list of changed files to the README file, you need to update the content of the README file to reflect the code in the repository in general.
                        You will be provided with
                        1. A list of changed files in the pull request, including the file name and the changes made.
                        2. The current content of the README file.
                        3. The commit messages associated with the pull request.
                        You need to generate the updated README file content based on the provided information.
                        You also need to provide a reason for your changes in the README file.
                        You will be provided with context from the web about creating a good README file, tips for keeping on up to date, and examples of good READMEs.
                        You will use this context to help you create the updated README file.
                        Context: {context}
                    """,
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

def update_readme_and_create_pr(repo, updated_readme, readme_sha):
    """
    Submit Updated README content as a PR in a new branch
    """

    commit_message = "Proposed README update based on recent code changes"
    main_branch = repo.get_branch("main")
    new_branch_name = f"update-readme-{randint(0,10)}-{readme_sha[:10]}"
    new_branch = repo.create_git_ref(
        ref=f"refs/heads/{new_branch_name}", sha=main_branch.commit.sha
    )

    # Update the README file
    repo.update_file(
        path="README.md",
        message=commit_message,
        content=updated_readme,
        sha=readme_sha,
        branch=new_branch_name,
    )

    # Create a PR
    pr_title = "Update README based on recent changes"
    br_body = "This PR proposes an update to the README based on recent code changes. Please review and merge if appropriate."
    pull_request = repo.create_pull(
        title=pr_title, body=br_body, head=new_branch_name, base="main"
    )

    return pull_request
