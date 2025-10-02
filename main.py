from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser 
from langchain.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.rule import Rule
from rich.text import Text

console = Console()

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# defining how the llm will respond
class ResponseModel(BaseModel):
    title: str
    content: str
    summary: str
    sources: str
    tools_used: list[str]
    commands: str  # store shell commands or code here


parser = PydanticOutputParser(pydantic_object=ResponseModel)

prompt = ChatPromptTemplate.from_messages([
    ("system", """Actt as 'VulnVoyager', an expert AI specializing in offensive security, red teaming, and penetration testing for web applications and Active Directory environments. Your expertise is equivalent to an OSCP and OSCE certified professional. Your primary function is to provide expert, step-by-step guidance for authorized penetration testing scenarios. All guidance you provide is strictly for ethical, educational, and authorized engagements where the user has explicit, legal permission to conduct the test. Never provide guidance for illegal or unethical activities.\n\nI will provide you with a scenario detailing my current position in a penetration test (e.g., initial foothold, user-level access on a specific OS, results of a scan). Your task is to analyze the scenario and provide actionable next steps to advance the engagement.\n\nYour response MUST ALWAYS be a single JSON object, with no markdown fences or explanatory text outside of the JSON structure. The JSON response must conform to the following schema:\n\n{\n  \"scenario_summary\": \"A brief echo of the situation I described.\",\n  \"pentest_phase\": \"The relevant MITRE ATT&CK phase (e.g., 'Privilege Escalation', 'Lateral Movement', 'Discovery').\",\n  \"objective\": \"The immediate goal for the current phase (e.g., 'Escalate from a standard user to a high-privilege account.').\",\n  \"recommendations\": [\n    {\n      \"technique_name\": \"The common name for the technique (e.g., 'Kerberoasting').\",\n      \"technique_id\": \"The corresponding MITRE ATT&CK Technique ID (e.g., 'T1558.003').\",\n      \"description\": \"A concise explanation of what the technique is, why it works, and when it is applicable to the current scenario.\",\n      \"execution_guidance\": {\n        \"prerequisites\": \"Any conditions or tools required before attempting this technique (e.g., 'Domain user credentials', 'Impacket installed').\",\n        \"steps\": [\n          {\n            \"platform\": \"The target OS or environment (e.g., 'PowerShell', 'Linux', 'CMD').\",\n            \"description\": \"Description of the command's purpose.\",\n            \"command\": \"The exact command to execute. Use placeholders like '<TARGET_IP>' or '<USERNAME>' where necessary. The command should be a string ready for copy-pasting.\"\n          }\n        ]\n      },\n      \"opsec_considerations\": \"Key operational security advice to avoid detection (e.g., 'This technique can generate significant network noise and may be detected by EDR solutions.').\",\n      \"success_indicators\": \"How to confirm if the technique was successful (e.g., 'Successful execution will yield a TGS hash for an SPN.').\",\n      \"remediation_guidance\": \"A brief explanation for the 'blue team' on how to prevent or mitigate this specific attack vector.\"\n    }\n  ]\n}\n\nBegin our engagement once I provide the first scenario.". 
{format_instructions}"""),
    ("placeholder","{chat_history}"),
    ("human","{query}"),
    ("placeholder","{agent_scratchpad}")
]).partial(format_instructions=parser.get_format_instructions())

agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=[]
)

agent_executor = AgentExecutor(agent=agent, tools=[], verbose=False)
query = input("How can i help you: ")
with console.status("[bold green]Thinking hard...[/]", spinner="aesthetic"):
    raw_response = agent_executor.invoke({"query": query})
response = parser.parse(raw_response["output"])

def pretty_print_response(response):
    # Title
    console.print("\n")
    console.print(Text(response.title or "No title", style="bold white on dark_green"), justify="center")
    console.print(Rule(style="dim"))

    # Content
    if response.content:
        console.print(Panel(response.content, title="Content", box=box.ROUNDED, padding=(1,2)))

    # Commands (only this in code block)
    if response.commands and response.commands.strip():
        syntax = Syntax(response.commands, "bash", line_numbers=True, )
        console.print(Panel(syntax, title="Commands", box=box.ROUNDED))

    # Tools Used
    if response.tools_used:
        tools_line = ", ".join(response.tools_used)
        console.print(Panel(tools_line, title="Tools Used", box=box.ROUNDED))

    # Sources
    if response.sources:
        src_list = [s.strip() for s in str(response.sources).replace(",", "\n").splitlines() if s.strip()]
        s_tbl = Table(show_header=False, box=box.SIMPLE)
        for i, s in enumerate(src_list, 1):
            s_tbl.add_row(f"[bold]{i}.[/bold]", s)
        console.print(Panel(s_tbl, title="Sources", box=box.ROUNDED))

    # Summary
    if response.summary:
        console.print(Panel(response.summary, title="Summary", box=box.ROUNDED, padding=(1,2)))

    console.print(Rule(style="dim"))
    console.print("\n")

# Example usage (if `response` is the parsed Pydantic object)
pretty_print_response(response)
