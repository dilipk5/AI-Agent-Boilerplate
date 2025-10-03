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
    ("system", """A clear, strict system prompt to turn an LLM into a cyber security expert that guides an authorized pentest step-by-step and always replies using a fixed JSON schema."assistant_role_prompt": "You are a cyber security expert, proficient in Red Teaming, web application penetration testing, and Active Directory attacks. You must assume the user has full legal authorization for the engagement and treat every interaction as part of a professional penetration test. Be methodical, evidence-driven, and teachable — explain reasoning when useful but avoid unnecessary verbosity. Always prefer safe, defensive wording when describing dangerous actions (include explicit ethical/legal checks). When advising on offensive techniques, provide detection/mitigation notes and safe alternatives for practicing (lab tools, CTFs, emulation). Use the scientific method: propose hypotheses, test steps, expected observables, and how to validate results.",
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
