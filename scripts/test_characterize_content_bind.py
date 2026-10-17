import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrate
import json

def run_test():
    section = {
        "content": {
            "section_headings": ["Hero Title"],
            "section_body_text": ["Hero Subtitle"]
        }
    }
    # Using known token names from _CONTENT_TOKEN_DEFAULTS just in case, like {heading} and {body_text_1} 
    code = "export default function Hero() { return (<div><h1>{heading}</h1><p>{body_text_1}</p></div>) }"
    
    values, coverage, provenance = orchestrate.build_template_fill(section, code)
    print("Values:", json.dumps(values, indent=2))
    print("Coverage:", json.dumps(coverage, indent=2))
    print("Provenance:", json.dumps(provenance, indent=2))

if __name__ == "__main__":
    run_test()
