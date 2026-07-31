import re
from pathlib import Path

def main():
    p = Path("tests/test_cli.py")
    content = p.read_text()

    # 1. Remove the standalone approve tests completely
    # They are between test_glossary_show and test_glossary_manager_edge_cases
    # Or we can just find the functions and remove them.
    patterns_to_remove = [
        r'def test_glossary_approve_merges_pending_terms.*?def test_glossary_approve_clears_pending_file_content',
        r'def test_glossary_approve_clears_pending_file_content.*?def test_translate_command_basic',
        r'def test_glossary_approve_empty_pending_terms.*?def test_glossary_approve_corrupt_pending_file',
        r'def test_glossary_approve_corrupt_pending_file.*?def test_cross_command_init_seed_approve_translate_status_epub',
    ]
    
    # We can also just replace all `runner.invoke(app, ["glossary", "approve", ...])` with `runner.invoke(app, ["glossary", "review", "--skip-llm", ...], input="\n\n\n\n\n")`
    content = content.replace('"approve"', '"review", "--skip-llm"')
    content = content.replace("seed -> approve ->", "seed -> review ->")
    content = content.replace("seed_then_approve_then_show", "seed_then_review_then_show")
    content = content.replace("init_seed_approve_translate", "init_seed_review_translate")
    
    # But wait, review requires stdin. If runner.invoke is called without input="\n", it might block or EOFError.
    # Let's replace runner.invoke for review to include input="\n" * 10
    content = re.sub(
        r'runner\.invoke\(\s*app,\s*\["glossary",\s*"review",\s*"--skip-llm"(.*?)\]\s*\)',
        r'runner.invoke(app, ["glossary", "review", "--skip-llm"\1], input="\\n" * 50)',
        content,
        flags=re.DOTALL
    )

    p.write_text(content)

if __name__ == "__main__":
    main()
