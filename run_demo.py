import os
import requests
import json
from rich.console import Console

console = Console()
API_URL = "http://localhost:8000"

def run_demo():
    console.print("\n[bold green]Welcome to the Agentic RAG Terminal Chat![/bold green]")
    
    # Step 1: List Providers
    try:
        resp = requests.get(f"{API_URL}/api/v1/providers")
        providers = resp.json().get("available_providers", [])
        console.print(f"[cyan]Available AI Providers:[/cyan] {providers}")
    except Exception as e:
        console.print("[red]API is not running. Please run 'uvicorn backend.main:app' first.[/red]")
        return
        
    # Step 2: Upload Document
    pdf_path = "data/pdfs/attention_paper.pdf"
    if os.path.exists(pdf_path):
        console.print(f"\n[cyan]Uploading {pdf_path}...[/cyan]")
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            try:
                upload_resp = requests.post(f"{API_URL}/api/v1/upload", files=files)
                console.print(f"Upload status: {upload_resp.json()}")
            except Exception as e:
                console.print(f"[red]Upload failed: {e}[/red]")
    else:
        console.print(f"\n[yellow]Warning: {pdf_path} not found. Make sure you have documents in ChromaDB already.[/yellow]")
        
    # Step 3: Chat Loop
    console.print("\n[bold]Ready for questions![/bold] Type 'quit' to exit.")
    provider = input("Select provider from above (leave blank for default): ").strip()
    
    while True:
        try:
            q = input("\n[bold]Ask a question:[/bold] ")
            if q.lower() in ['quit', 'exit']:
                break
                
            payload = {"question": q}
            if provider:
                payload["provider"] = provider
                
            console.print("[italic]Agent is searching and generating...[/italic]")
            chat_resp = requests.post(f"{API_URL}/api/v1/chat", json=payload)
            data = chat_resp.json()
            
            if chat_resp.status_code == 200:
                console.print(f"\n[bold blue]Answer:[/bold blue] {data.get('generation')}")
                console.print(f"[dim]Provider used: {data.get('provider_used')}[/dim]")
            else:
                console.print(f"[red]Error {chat_resp.status_code}: {data}[/red]")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    run_demo()
